from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
import schemas.inventory as schemas
import services.inventory_service as service

router = APIRouter(prefix="/inventory", tags=["Inventario y Mermas"])


# ============================================================================
# 1. ENDPOINTS DE INSUMOS
# ============================================================================

@router.post(
    "/ingredients",
    response_model=schemas.IngredientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo insumo base o producto directo",
)
def create_ingredient_endpoint(
    data: schemas.IngredientCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un insumo en el almacén.
    Si se indica `initial_stock > 0`, se registra de forma automática
    la entrada en el Kardex contable.
    """
    return service.create_ingredient(db, data)


@router.get(
    "/ingredients",
    response_model=List[schemas.IngredientResponse],
    summary="Listar todos los insumos",
)
def list_ingredients_endpoint(
    category: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Obtiene el inventario de insumos, con opción a filtrar por categoría."""
    return service.get_ingredients(db, category=category, active_only=active_only)


@router.get(
    "/ingredients/{ingredient_id}",
    response_model=schemas.IngredientResponse,
    summary="Consultar un insumo por su ID",
)
def get_ingredient_endpoint(
    ingredient_id: UUID,
    db: Session = Depends(get_db)
):
    return service.get_ingredient_by_id(db, ingredient_id)


# ============================================================================
# 2. ENTRADA MANUAL DE STOCK (COMPRAS / REPOSICIÓN)
# ============================================================================

@router.post(
    "/stock/entry",
    response_model=schemas.StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar entrada manual de stock (compras locales)",
)
def add_stock_endpoint(
    data: schemas.StockEntryCreate,
    db: Session = Depends(get_db)
):
    """
    Aumenta el stock del insumo y genera un registro inmutable en el Kardex.
    """
    return service.add_stock_manual(db, data)


# ============================================================================
# 3. MERMAS (WASTE) — REGLA BRUTO/NETO Y GENERALES
# ============================================================================

@router.post(
    "/waste/process",
    response_model=schemas.WasteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar merma por proceso (Peso Bruto vs Peso Neto)",
)
def register_process_waste_endpoint(
    data: schemas.ProcessWasteCreate,
    db: Session = Depends(get_db)
):
    """
    **Regla Operativa para Cocina:**
    - Recibe `gross_quantity` (Peso Bruto retirado de almacén).
    - Recibe `net_quantity` (Peso Neto aprovechable).
    - El backend calcula automáticamente:
      - Merma = Bruto - Neto
      - % de merma = (Merma / Bruto) * 100
    - Descuenta la merma del inventario y genera el log de auditoría.
    """
    return service.register_process_waste(db, data)


@router.post(
    "/waste/general",
    response_model=schemas.WasteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar merma directa (caducidad, error humano, rechazo)",
)
def register_general_waste_endpoint(
    data: schemas.GeneralWasteCreate,
    db: Session = Depends(get_db)
):
    """
    Registra mermas puntuales para insumos o subrecetas (caducidad, quemado, caído al piso).
    """
    return service.register_general_waste(db, data)


# ============================================================================
# 4. RECETAS Y PRODUCCIÓN DE SUBRECETAS (MISE EN PLACE)
# ============================================================================

@router.post(
    "/recipes",
    response_model=schemas.RecipeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una receta o subreceta con sus ingredientes",
)
def create_recipe_endpoint(
    data: schemas.RecipeCreate,
    db: Session = Depends(get_db)
):
    """
    Define una receta o subreceta. Si es `SUBRECETA`, inicializa
    automáticamente su control de stock disponible en refrigeración.
    """
    return service.create_recipe(db, data)


@router.post(
    "/subrecipes/produce",
    response_model=schemas.ProductionLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Preparar lote de subreceta (descuenta crudos y suma stock)",
)
def produce_subrecipe_endpoint(
    data: schemas.SubrecipeProductionCreate,
    db: Session = Depends(get_db)
):
    """
    **Mise en place en Cocina:**
    Ej. Preparar 5 Litros de Salsa de Tomate.
    - Valida que haya jitomates, cebolla, etc., suficientes.
    - Descuenta los insumos crudos del inventario.
    - Suma los 5 Litros a la bodega de subrecetas.
    - Todo ocurre en una única transacción atómica ACID.
    """
    return service.produce_subrecipe(db, data)


# ============================================================================
# 5. ALERTAS DE STOCK MÍNIMO
# ============================================================================

@router.get(
    "/alerts/low-stock",
    response_model=List[schemas.LowStockAlertResponse],
    summary="Alertas de stock bajo o crítico (insumos y subrecetas)",
)
def get_low_stock_alerts_endpoint(
    db: Session = Depends(get_db)
):
    """
    Devuelve los insumos y subrecetas cuyo stock actual es menor o igual
    a su stock mínimo configurado, para saber qué comprar o preparar.
    """
    return service.get_low_stock_alerts(db)
