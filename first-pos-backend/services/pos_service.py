from decimal import Decimal
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime
import uuid
from collections import defaultdict
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from models.pos import (
    PaymentMethod,
    OrderStatus,
    ShiftStatus,
    CashCut,
    MenuItem,
    Order,
    OrderItem,
)
from models.inventory import (
    Ingredient,
    Recipe,
    RecipeItem,
    SubrecipeStock,
    StockMovement,
    MovementType,
)
from schemas.pos import (
    ShiftOpenRequest,
    ShiftCloseRequest,
    MenuItemCreate,
    OrderCheckoutRequest,
)


# ============================================================================
# 1. SERVICIOS DE TURNOS DE CAJA (CASH CUT / SHIFT)
# ============================================================================

def open_shift(db: Session, data: ShiftOpenRequest) -> CashCut:
    """
    Abre un nuevo turno de caja.
    Reglas de negocio:
    - No permite abrir un turno si ya hay uno abierto (status = OPEN).
    - Monto inicial validado previamente por Pydantic (1000, 2000 o 3000).
    """
    existing_open = db.query(CashCut).filter(CashCut.status == ShiftStatus.OPEN).first()
    if existing_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya hay un turno abierto por '{existing_open.cashier_name}'. Debe cerrarlo antes de abrir uno nuevo."
        )

    shift = CashCut(
        cashier_name=data.cashier_name.strip(),
        status=ShiftStatus.OPEN,
        initial_cash=data.initial_cash,
        expected_cash=data.initial_cash,
        cash_sales_total=Decimal("0.00"),
        card_sales_total=Decimal("0.00"),
        opened_at=datetime.utcnow(),
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


def get_current_shift(db: Session) -> Optional[CashCut]:
    """Obtiene el turno actualmente abierto en la caja registradora."""
    return db.query(CashCut).filter(CashCut.status == ShiftStatus.OPEN).first()


def close_shift(db: Session, shift_id: UUID, data: ShiftCloseRequest) -> CashCut:
    """
    Cierra un turno de caja y realiza el arqueo de dinero:
    - Calcula la diferencia = actual_cash - expected_cash (faltante o sobrante).
    """
    shift = db.query(CashCut).filter(CashCut.id == shift_id).with_for_update().first()
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno de caja no encontrado.")
    if shift.status != ShiftStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este turno ya se encuentra cerrado.")

    shift.status = ShiftStatus.CLOSED
    shift.closed_at = datetime.utcnow()
    shift.actual_cash = data.actual_cash
    shift.difference = data.actual_cash - shift.expected_cash
    shift.notes = data.notes

    db.commit()
    db.refresh(shift)
    return shift


# ============================================================================
# 2. SERVICIOS DEL MENÚ
# ============================================================================

def create_menu_item(db: Session, data: MenuItemCreate) -> MenuItem:
    """Crea un platillo a la venta asociado a su Receta obligatoria."""
    recipe = db.query(Recipe).filter(Recipe.id == data.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La receta especificada no existe.")

    existing = db.query(MenuItem).filter(MenuItem.name.ilike(data.name.strip())).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ya existe un platillo llamado '{data.name}'.")

    menu_item = MenuItem(
        name=data.name.strip(),
        category=data.category.strip() if data.category else None,
        price=data.price,
        recipe_id=recipe.id,
        is_active=True,
    )
    db.add(menu_item)
    db.commit()
    db.refresh(menu_item)
    return menu_item


def get_menu_items(db: Session, active_only: bool = True) -> List[MenuItem]:
    """Lista todos los platillos disponibles para vender en el POS."""
    query = db.query(MenuItem)
    if active_only:
        query = query.filter(MenuItem.is_active == True)
    return query.order_by(MenuItem.name.asc()).all()


# ============================================================================
# 3. EL FLUJO DORADO DE COBRO (CHECKOUT ATÓMICO CON INVENTARIO)
# ============================================================================

def checkout_order(db: Session, data: OrderCheckoutRequest) -> Order:
    """
    Cobro de orden con garantía ACID en PostgreSQL:
    1. Verifica que haya un turno de caja abierto (ShiftStatus.OPEN).
    2. Recorre los platillos y suma las cantidades requeridas de cada insumo/subreceta.
    3. Bloquea y valida con `with_for_update()` la existencia y stock en bodega.
    4. Si algún insumo no alcanza, lanza error y PostgreSQL hace ROLLBACK automático.
    5. Descuenta el inventario y genera los movimientos de Kardex (SALIDA_VENTA).
    6. Registra el pago en efectivo/tarjeta y acumula en el turno de caja.
    7. Guarda la orden y sus items.
    """
    # 1. Validar que la caja esté abierta
    shift = db.query(CashCut).filter(CashCut.status == ShiftStatus.OPEN).with_for_update().first()
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pueden cobrar órdenes. No hay un turno de caja abierto."
        )

    # 2. Calcular subtotales y acumular ingredientes requeridos
    subtotal = Decimal("0.00")
    order_items_to_create = []

    # Diccionarios para acumular la demanda total de la orden
    needed_ingredients: Dict[UUID, Decimal] = defaultdict(lambda: Decimal("0.000"))
    needed_subrecipes: Dict[UUID, Decimal] = defaultdict(lambda: Decimal("0.000"))

    for item_data in data.items:
        # Cargar el MenuItem con su Receta y los RecipeItems
        menu_item = db.query(MenuItem).filter(MenuItem.id == item_data.menu_item_id).first()
        if not menu_item or not menu_item.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Platillo {item_data.menu_item_id} no encontrado o inactivo."
            )

        item_subtotal = menu_item.price * Decimal(item_data.quantity)
        subtotal += item_subtotal

        order_items_to_create.append({
            "menu_item_id": menu_item.id,
            "quantity": item_data.quantity,
            "unit_price": menu_item.price,
            "subtotal": item_subtotal,
            "notes": item_data.notes,
        })

        # Obtener los ingredientes requeridos según la receta
        recipe = db.query(Recipe).filter(Recipe.id == menu_item.recipe_id).first()
        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El platillo '{menu_item.name}' no tiene una receta válida asignada."
            )

        # Factor según el rendimiento de la receta y la cantidad de platillos ordenados
        factor = Decimal(item_data.quantity) / recipe.yield_quantity

        for r_item in recipe.items:
            qty_required = r_item.quantity * factor
            if r_item.ingredient_id:
                needed_ingredients[r_item.ingredient_id] += qty_required
            elif r_item.subrecipe_id:
                needed_subrecipes[r_item.subrecipe_id] += qty_required

    # 3. Validar y descontar Insumos Base con Bloqueo Pesimista
    for ing_id, qty_needed in needed_ingredients.items():
        ingredient = db.query(Ingredient).filter(Ingredient.id == ing_id).with_for_update().first()
        if not ingredient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Insumo {ing_id} no encontrado.")
        if ingredient.current_stock < qty_needed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Stock insuficiente para completar la venta. "
                    f"Insumo: '{ingredient.name}'. Requerido: {qty_needed}{ingredient.unit.value}, "
                    f"Disponible: {ingredient.current_stock}{ingredient.unit.value}"
                )
            )
        # Descuento atómico
        ingredient.current_stock = ingredient.current_stock - qty_needed
        db.add(StockMovement(
            movement_type=MovementType.SALIDA_VENTA,
            ingredient_id=ingredient.id,
            quantity=-qty_needed,
            balance_after=ingredient.current_stock,
            unit=ingredient.unit,
            note="Venta cobrada en caja",
        ))

    # 4. Validar y descontar Subrecetas con Bloqueo Pesimista
    for sub_id, qty_needed in needed_subrecipes.items():
        sub_stock = db.query(SubrecipeStock).filter(SubrecipeStock.recipe_id == sub_id).with_for_update().first()
        sub_recipe = db.query(Recipe).filter(Recipe.id == sub_id).first()
        recipe_name = sub_recipe.name if sub_recipe else "Subreceta"

        if not sub_stock or sub_stock.current_stock < qty_needed:
            disponible = sub_stock.current_stock if sub_stock else Decimal("0.000")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Stock insuficiente para completar la venta. "
                    f"Subreceta: '{recipe_name}'. Requerido: {qty_needed}, "
                    f"Disponible en refrigerador: {disponible}"
                )
            )
        # Descuento atómico
        sub_stock.current_stock = sub_stock.current_stock - qty_needed
        db.add(StockMovement(
            movement_type=MovementType.SALIDA_VENTA,
            subrecipe_id=sub_id,
            quantity=-qty_needed,
            balance_after=sub_stock.current_stock,
            unit=sub_stock.unit,
            note="Venta cobrada en caja",
        ))

    # 5. Cálculos de Pago y Cambio
    total_amount = subtotal
    cash_given = None
    change_given = None

    if data.payment_method == PaymentMethod.CASH:
        if data.cash_given is not None:
            if data.cash_given < total_amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El efectivo entregado (${data.cash_given}) es menor al total (${total_amount})."
                )
            cash_given = data.cash_given
            change_given = data.cash_given - total_amount
        else:
            cash_given = total_amount
            change_given = Decimal("0.00")

        # Acumular en turno de caja
        shift.cash_sales_total = shift.cash_sales_total + total_amount
        shift.expected_cash = shift.expected_cash + total_amount
    else:
        # Pago con Tarjeta
        shift.card_sales_total = shift.card_sales_total + total_amount

    # 6. Generar folio de orden único
    now_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_suffix = uuid.uuid4().hex[:4].upper()
    order_number = f"ORD-{now_str}-{random_suffix}"

    order = Order(
        order_number=order_number,
        cash_cut_id=shift.id,
        status=OrderStatus.COMPLETED,
        payment_method=data.payment_method,
        subtotal=subtotal,
        tax=Decimal("0.00"),
        total_amount=total_amount,
        cash_given=cash_given,
        change_given=change_given,
        notes=data.notes,
        created_at=datetime.utcnow(),
    )
    db.add(order)
    db.flush()

    # 7. Crear los OrderItems
    for oi in order_items_to_create:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=oi["menu_item_id"],
            quantity=oi["quantity"],
            unit_price=oi["unit_price"],
            subtotal=oi["subtotal"],
            notes=oi["notes"],
        )
        db.add(order_item)

    db.commit()
    db.refresh(order)
    return order
