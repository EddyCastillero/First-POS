from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import schemas.pos as schemas
import services.pos_service as service
from models.pos import Order

router = APIRouter(prefix="/pos", tags=["Punto de Venta (Caja)"])


# ============================================================================
# 1. ENDPOINTS DE TURNOS Y CORTES DE CAJA
# ============================================================================

@router.post(
    "/shifts/open",
    response_model=schemas.CashCutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Abrir turno de caja con fondo fijo obligatorio (1000, 2000 o 3000 MXN)",
)
def open_shift_endpoint(
    data: schemas.ShiftOpenRequest,
    db: Session = Depends(get_db)
):
    """
    Inicia un turno de caja para un cajero.
    Regla estricta: Solo permite fondos iniciales fijos de 1000, 2000 o 3000 pesos.
    """
    return service.open_shift(db, data)


@router.get(
    "/shifts/current",
    response_model=Optional[schemas.CashCutResponse],
    summary="Consultar el turno actualmente abierto en caja",
)
def get_current_shift_endpoint(
    db: Session = Depends(get_db)
):
    """Devuelve el turno activo si existe, o null si la caja está cerrada."""
    return service.get_current_shift(db)


@router.post(
    "/shifts/{shift_id}/close",
    response_model=schemas.CashCutResponse,
    summary="Cerrar turno de caja y realizar corte / arqueo de efectivo",
)
def close_shift_endpoint(
    shift_id: UUID,
    data: schemas.ShiftCloseRequest,
    db: Session = Depends(get_db)
):
    """
    Cierra el turno de caja. Compara el efectivo físico contado con las ventas
    del sistema y calcula automáticamente la diferencia (sobrante o faltante).
    """
    return service.close_shift(db, shift_id, data)


# ============================================================================
# 2. ENDPOINTS DEL MENÚ
# ============================================================================

@router.post(
    "/menu",
    response_model=schemas.MenuItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dar de alta un platillo en el menú (asociado a su receta)",
)
def create_menu_item_endpoint(
    data: schemas.MenuItemCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un platillo a la venta.
    Requiere obligatoriamente un `recipe_id` para saber de dónde descontar el stock al venderse.
    """
    return service.create_menu_item(db, data)


@router.get(
    "/menu",
    response_model=List[schemas.MenuItemResponse],
    summary="Listar los platillos disponibles para venta",
)
def list_menu_items_endpoint(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    return service.get_menu_items(db, active_only=active_only)


# ============================================================================
# 3. ENDPOINTS DE COBRO (CHECKOUT ATÓMICO)
# ============================================================================

@router.post(
    "/orders/checkout",
    response_model=schemas.OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cobrar orden en caja con descuento atómico de inventario",
)
def checkout_order_endpoint(
    data: schemas.OrderCheckoutRequest,
    db: Session = Depends(get_db)
):
    """
    **El Flujo Dorado del POS:**
    1. Verifica que haya un turno de caja abierto.
    2. Bloquea y verifica el stock de todos los ingredientes requeridos.
    3. Si falta algún insumo, rechaza la venta completa (ROLLBACK).
    4. Si hay stock, descuenta de bodega, genera Kardex, calcula cambio y registra el cobro.
    """
    return service.checkout_order(db, data)


@router.get(
    "/orders",
    response_model=List[schemas.OrderResponse],
    summary="Historial de órdenes cobradas",
)
def list_orders_endpoint(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    return db.query(Order).order_by(Order.created_at.desc()).limit(limit).all()
