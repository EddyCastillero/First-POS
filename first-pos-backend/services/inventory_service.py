from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.inventory import (
    Ingredient,
    Recipe,
    RecipeItem,
    SubrecipeStock,
    StockMovement,
    WasteLog,
    ProductionLog,
    UnitType,
    WasteType,
    MovementType,
    RecipeType,
)
from schemas.inventory import (
    IngredientCreate,
    IngredientUpdate,
    StockEntryCreate,
    ProcessWasteCreate,
    GeneralWasteCreate,
    RecipeCreate,
    SubrecipeProductionCreate,
    LowStockAlertResponse,
)


# ============================================================================
# 1. SERVICIOS DE INSUMOS / INGREDIENTES
# ============================================================================

def create_ingredient(db: Session, data: IngredientCreate) -> Ingredient:
    """
    Crea un nuevo insumo en la base de datos.
    Si se especifica un stock inicial mayor a 0, genera su movimiento contable en el Kardex.
    """
    # 1. Verificar si ya existe un insumo con el mismo nombre
    existing = db.query(Ingredient).filter(Ingredient.name.ilike(data.name.strip())).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un insumo con el nombre '{data.name}'."
        )

    # 2. Instanciar el modelo ORM (crear el objeto en memoria)
    ingredient = Ingredient(
        name=data.name.strip(),
        category=data.category.strip() if data.category else None,
        unit=data.unit,
        current_stock=data.initial_stock,
        min_stock=data.min_stock,
        cost_per_unit=data.cost_per_unit,
        waste_percentage=data.waste_percentage,
        is_active=True,
    )
    db.add(ingredient)
    db.flush()  # Asigna el ID UUID generado sin cerrar la transacción todavía

    # 3. Si hubo stock inicial, registrar el movimiento en el Kardex
    if data.initial_stock > Decimal("0.000"):
        movement = StockMovement(
            movement_type=MovementType.ENTRADA_MANUAL,
            ingredient_id=ingredient.id,
            quantity=data.initial_stock,
            balance_after=data.initial_stock,
            unit=ingredient.unit,
            note="Stock inicial al dar de alta el insumo",
        )
        db.add(movement)

    db.commit()
    db.refresh(ingredient)
    return ingredient


def get_ingredients(
    db: Session,
    category: Optional[str] = None,
    active_only: bool = True
) -> List[Ingredient]:
    """Obtiene el listado de insumos con filtros opcionales."""
    query = db.query(Ingredient)
    if active_only:
        query = query.filter(Ingredient.is_active == True)
    if category:
        query = query.filter(Ingredient.category.ilike(f"%{category}%"))
    return query.order_by(Ingredient.name.asc()).all()


def get_ingredient_by_id(db: Session, ingredient_id: UUID) -> Ingredient:
    """Busca un insumo por su ID único; si no existe, lanza un error 404."""
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insumo no encontrado."
        )
    return ingredient


# ============================================================================
# 2. ENTRADA MANUAL DE STOCK (COMPRAS / REPOSICIÓN)
# ============================================================================

def add_stock_manual(db: Session, data: StockEntryCreate) -> StockMovement:
    """
    Añade stock a un ingrediente y lo registra en el Kardex.
    Usa bloqueo pesimista (with_for_update) para garantizar consistencia ACID.
    """
    # with_for_update bloquea la fila del ingrediente hasta que termine el commit
    ingredient = db.query(Ingredient).filter(Ingredient.id == data.ingredient_id).with_for_update().first()
    if not ingredient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insumo no encontrado.")

    # 1. Sumar al stock actual
    new_stock = ingredient.current_stock + data.quantity
    ingredient.current_stock = new_stock

    # 2. Si se mandó un costo nuevo, actualizar el costo unitario
    if data.cost_per_unit is not None:
        ingredient.cost_per_unit = data.cost_per_unit

    # 3. Registrar el movimiento en el Kardex
    movement = StockMovement(
        movement_type=MovementType.ENTRADA_MANUAL,
        ingredient_id=ingredient.id,
        quantity=data.quantity,
        balance_after=new_stock,
        unit=ingredient.unit,
        note=data.note or "Entrada manual de inventario",
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


# ============================================================================
# 3. MERMAS (WASTE) — REGLA BRUTO/NETO Y MERMAS GENERALES
# ============================================================================

def register_process_waste(db: Session, data: ProcessWasteCreate) -> WasteLog:
    """
    Aplica la Regla de Merma por Proceso:
    1. Calcula: Merma = Peso Bruto - Peso Neto
    2. Calcula: % de Merma = (Merma / Peso Bruto) * 100
    3. Descuenta la merma del inventario con bloqueo pesimista.
    4. Guarda el registro en WasteLog y en StockMovement.
    """
    ingredient = db.query(Ingredient).filter(Ingredient.id == data.ingredient_id).with_for_update().first()
    if not ingredient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insumo no encontrado.")

    # 1. Algoritmo de cálculo de merma
    waste_qty = data.gross_quantity - data.net_quantity
    if data.gross_quantity > Decimal("0.000"):
        waste_pct = (waste_qty / data.gross_quantity) * Decimal("100.00")
    else:
        waste_pct = Decimal("0.00")

    # 2. Validar que tengamos suficiente stock registrado para descontar la merma
    if ingredient.current_stock < waste_qty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock insuficiente para registrar merma. Stock actual: {ingredient.current_stock}{ingredient.unit.value}, Merma: {waste_qty}{ingredient.unit.value}"
        )

    # 3. Descontar la merma del stock
    ingredient.current_stock = ingredient.current_stock - waste_qty

    # 4. Guardar en WasteLog
    waste_log = WasteLog(
        waste_type=WasteType.PROCESO,
        ingredient_id=ingredient.id,
        gross_quantity=data.gross_quantity,
        net_quantity=data.net_quantity,
        waste_quantity=waste_qty,
        waste_percentage=round(waste_pct, 2),
        unit=ingredient.unit,
        reason=data.reason or "Merma por proceso / preparación de lote",
        registered_by=data.registered_by,
    )
    db.add(waste_log)

    # 5. Guardar en Kardex
    movement = StockMovement(
        movement_type=MovementType.MERMA,
        ingredient_id=ingredient.id,
        quantity=-waste_qty,
        balance_after=ingredient.current_stock,
        unit=ingredient.unit,
        note=f"Merma proceso ({waste_log.waste_percentage}%): {data.reason or 'Preparación de lote'}",
    )
    db.add(movement)

    db.commit()
    db.refresh(waste_log)
    return waste_log


def register_general_waste(db: Session, data: GeneralWasteCreate) -> WasteLog:
    """
    Registra mermas directas (caducidad, error humano, rechazo, falta de calidad).
    Descuenta directamente la cantidad especificada.
    """
    item_unit = None
    balance_after = Decimal("0.000")

    if data.ingredient_id:
        ingredient = db.query(Ingredient).filter(Ingredient.id == data.ingredient_id).with_for_update().first()
        if not ingredient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insumo no encontrado.")
        if ingredient.current_stock < data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente. Disponible: {ingredient.current_stock}{ingredient.unit.value}"
            )
        ingredient.current_stock = ingredient.current_stock - data.quantity
        balance_after = ingredient.current_stock
        item_unit = ingredient.unit

    elif data.subrecipe_id:
        subrecipe_stock = db.query(SubrecipeStock).filter(SubrecipeStock.recipe_id == data.subrecipe_id).with_for_update().first()
        if not subrecipe_stock:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock de subreceta no encontrado.")
        if subrecipe_stock.current_stock < data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente. Disponible: {subrecipe_stock.current_stock}{subrecipe_stock.unit.value}"
            )
        subrecipe_stock.current_stock = subrecipe_stock.current_stock - data.quantity
        balance_after = subrecipe_stock.current_stock
        item_unit = subrecipe_stock.unit

    # Registrar WasteLog
    waste_log = WasteLog(
        waste_type=data.waste_type,
        ingredient_id=data.ingredient_id,
        subrecipe_id=data.subrecipe_id,
        waste_quantity=data.quantity,
        waste_percentage=Decimal("100.00"),
        unit=item_unit,
        reason=data.reason,
        registered_by=data.registered_by,
    )
    db.add(waste_log)

    # Registrar Kardex
    movement = StockMovement(
        movement_type=MovementType.MERMA,
        ingredient_id=data.ingredient_id,
        subrecipe_id=data.subrecipe_id,
        quantity=-data.quantity,
        balance_after=balance_after,
        unit=item_unit,
        note=f"Merma ({data.waste_type.value}): {data.reason or 'Sin nota'}",
    )
    db.add(movement)

    db.commit()
    db.refresh(waste_log)
    return waste_log


# ============================================================================
# 4. RECETAS Y PRODUCCIÓN DE SUBRECETAS (MISE EN PLACE)
# ============================================================================

def create_recipe(db: Session, data: RecipeCreate) -> Recipe:
    """
    Crea una Receta o Subreceta con su lista de ingredientes.
    Si es tipo SUBRECETA, crea automáticamente su registro de SubrecipeStock.
    """
    recipe = Recipe(
        name=data.name.strip(),
        recipe_type=data.recipe_type,
        description=data.description,
        yield_quantity=data.yield_quantity,
        yield_unit=data.yield_unit,
        is_active=True,
    )
    db.add(recipe)
    db.flush()

    # Agregar los items
    for item_data in data.items:
        item = RecipeItem(
            recipe_id=recipe.id,
            ingredient_id=item_data.ingredient_id,
            subrecipe_id=item_data.subrecipe_id,
            quantity=item_data.quantity,
            unit=item_data.unit,
        )
        db.add(item)

    # Si es subreceta, inicializar su stock en 0
    if data.recipe_type == RecipeType.SUBRECETA:
        sub_stock = SubrecipeStock(
            recipe_id=recipe.id,
            current_stock=Decimal("0.000"),
            min_stock=Decimal("0.000"),
            unit=data.yield_unit,
        )
        db.add(sub_stock)

    db.commit()
    db.refresh(recipe)
    return recipe


def produce_subrecipe(db: Session, data: SubrecipeProductionCreate) -> ProductionLog:
    """
    Ejecuta un lote de preparación de subreceta (Mise en place):
    1. Calcula los insumos necesarios de forma proporcional al rendimiento.
    2. Bloquea y valida que haya suficiente stock de cada ingrediente.
    3. Descuenta los ingredientes crudos del inventario (Kardex: PRODUCCION_CONSUMO).
    4. Suma la cantidad producida al stock de la subreceta (Kardex: PRODUCCION_ENTRADA).
    5. Guarda el registro en ProductionLog.
    ¡Todo en UNA sola transacción atómica ACID!
    """
    recipe = db.query(Recipe).filter(Recipe.id == data.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada.")
    if recipe.recipe_type != RecipeType.SUBRECETA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden producir recetas clasificadas como SUBRECETA."
        )

    # Factor de escala (ej. si la receta rinde 1000ml y preparamos 5000ml, factor = 5)
    factor = data.quantity_to_produce / recipe.yield_quantity

    # 1. Validar y descontar cada insumo
    for item in recipe.items:
        required_qty = item.quantity * factor

        if item.ingredient_id:
            ingredient = db.query(Ingredient).filter(Ingredient.id == item.ingredient_id).with_for_update().first()
            if not ingredient:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Insumo {item.ingredient_id} no existe.")
            if ingredient.current_stock < required_qty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock insuficiente para preparar {recipe.name}. Falta insumo: '{ingredient.name}'. Requerido: {required_qty}{ingredient.unit.value}, Disponible: {ingredient.current_stock}{ingredient.unit.value}"
                )
            # Descontar
            ingredient.current_stock = ingredient.current_stock - required_qty
            # Registrar Kardex
            db.add(StockMovement(
                movement_type=MovementType.PRODUCCION_CONSUMO,
                ingredient_id=ingredient.id,
                quantity=-required_qty,
                balance_after=ingredient.current_stock,
                unit=ingredient.unit,
                note=f"Consumo para producción de {data.quantity_to_produce}{recipe.yield_unit.value} de {recipe.name}",
            ))

        elif item.subrecipe_id:
            child_stock = db.query(SubrecipeStock).filter(SubrecipeStock.recipe_id == item.subrecipe_id).with_for_update().first()
            if not child_stock:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subreceta intermedia no encontrada.")
            if child_stock.current_stock < required_qty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock insuficiente para preparar {recipe.name}. Falta subreceta intermedia. Requerido: {required_qty}, Disponible: {child_stock.current_stock}"
                )
            child_stock.current_stock = child_stock.current_stock - required_qty
            db.add(StockMovement(
                movement_type=MovementType.PRODUCCION_CONSUMO,
                subrecipe_id=item.subrecipe_id,
                quantity=-required_qty,
                balance_after=child_stock.current_stock,
                unit=child_stock.unit,
                note=f"Consumo para producción de {recipe.name}",
            ))

    # 2. Sumar stock a la subreceta producida
    subrecipe_stock = db.query(SubrecipeStock).filter(SubrecipeStock.recipe_id == recipe.id).with_for_update().first()
    if not subrecipe_stock:
        subrecipe_stock = SubrecipeStock(
            recipe_id=recipe.id,
            current_stock=Decimal("0.000"),
            min_stock=Decimal("0.000"),
            unit=recipe.yield_unit,
        )
        db.add(subrecipe_stock)
        db.flush()

    subrecipe_stock.current_stock = subrecipe_stock.current_stock + data.quantity_to_produce
    subrecipe_stock.last_production_at = datetime.utcnow()

    # Kardex para la entrada de subreceta
    db.add(StockMovement(
        movement_type=MovementType.PRODUCCION_ENTRADA,
        subrecipe_id=recipe.id,
        quantity=data.quantity_to_produce,
        balance_after=subrecipe_stock.current_stock,
        unit=subrecipe_stock.unit,
        note=f"Lote producido: {data.notes or 'Mise en place'}",
    ))

    # 3. Registrar log de producción
    prod_log = ProductionLog(
        recipe_id=recipe.id,
        quantity_produced=data.quantity_to_produce,
        unit=recipe.yield_unit,
        notes=data.notes,
        produced_by=data.produced_by,
    )
    db.add(prod_log)

    db.commit()
    db.refresh(prod_log)
    return prod_log


# ============================================================================
# 5. ALERTAS DE STOCK BAJO (LOW STOCK)
# ============================================================================

def get_low_stock_alerts(db: Session) -> List[LowStockAlertResponse]:
    """
    Busca todos los insumos y subrecetas que tienen stock menor o igual a su stock mínimo.
    """
    alerts = []

    # 1. Alertas de Insumos Base
    ingredients = db.query(Ingredient).filter(
        Ingredient.is_active == True,
        Ingredient.current_stock <= Ingredient.min_stock
    ).all()

    for ing in ingredients:
        status_str = "CRITICO" if ing.current_stock <= Decimal("0.000") else "BAJO"
        alerts.append(LowStockAlertResponse(
            item_id=ing.id,
            name=ing.name,
            item_type="ingredient",
            current_stock=ing.current_stock,
            min_stock=ing.min_stock,
            unit=ing.unit,
            status=status_str,
        ))

    # 2. Alertas de Subrecetas
    subrecipes = db.query(SubrecipeStock).join(Recipe).filter(
        SubrecipeStock.current_stock <= SubrecipeStock.min_stock
    ).all()

    for sub in subrecipes:
        status_str = "CRITICO" if sub.current_stock <= Decimal("0.000") else "BAJO"
        alerts.append(LowStockAlertResponse(
            item_id=sub.recipe_id,
            name=sub.recipe.name,
            item_type="subrecipe",
            current_stock=sub.current_stock,
            min_stock=sub.min_stock,
            unit=sub.unit,
            status=status_str,
        ))

    return alerts
