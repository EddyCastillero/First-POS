from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

from models.pos import PaymentMethod, OrderStatus, ShiftStatus


# ============================================================================
# 1. SCHEMAS DE TURNOS / CORTES DE CAJA (CASH CUT)
# ============================================================================

ALLOWED_INITIAL_CASH = {Decimal("1000.00"), Decimal("2000.00"), Decimal("3000.00")}

class ShiftOpenRequest(BaseModel):
    """
    Apertura obligatoria de turno.
    Regla estricta: solo se permite fondo inicial de 1000, 2000 o 3000 MXN.
    """
    cashier_name: str = Field(..., min_length=2, max_length=100, description="Nombre del cajero en turno")
    initial_cash: Decimal = Field(..., description="Fondo fijo para cambio (solo 1000, 2000 o 3000)")

    @model_validator(mode="after")
    def validate_fixed_initial_cash(self):
        val = self.initial_cash.quantize(Decimal("0.01"))
        if val not in ALLOWED_INITIAL_CASH:
            raise ValueError(
                f"Monto inicial no permitido ({self.initial_cash}). "
                f"Las únicas opciones válidas para fondo de caja son: 1000, 2000 o 3000."
            )
        return self


class ShiftCloseRequest(BaseModel):
    """Cierre de turno y arqueo de caja física."""
    actual_cash: Decimal = Field(..., ge=0, description="Efectivo físico contado en el cajón")
    notes: Optional[str] = Field(None, max_length=500, description="Observaciones o notas del cajero")


class CashCutResponse(BaseModel):
    """Resumen completo del turno / corte de caja."""
    id: UUID
    cashier_name: str
    status: ShiftStatus
    initial_cash: Decimal
    opened_at: datetime
    closed_at: Optional[datetime]
    cash_sales_total: Decimal
    card_sales_total: Decimal
    expected_cash: Decimal
    actual_cash: Optional[Decimal]
    difference: Optional[Decimal]
    notes: Optional[str]

    class Config:
        from_attributes = True


# ============================================================================
# 2. SCHEMAS DEL MENÚ (PLATILLOS / PRODUCTOS DE VENTA)
# ============================================================================

class MenuItemCreate(BaseModel):
    """Alta de platillo en el menú, enlazado a su Receta obligatoria."""
    name: str = Field(..., min_length=1, max_length=150, description="Nombre público del platillo")
    category: Optional[str] = Field(None, max_length=50, description="Categoría (Comidas, Bebidas, etc.)")
    price: Decimal = Field(..., gt=0, description="Precio de venta al comensal")
    recipe_id: UUID = Field(..., description="Receta de la que se descontarán los ingredientes")


class MenuItemResponse(BaseModel):
    id: UUID
    name: str
    category: Optional[str]
    price: Decimal
    recipe_id: Optional[UUID]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# 3. SCHEMAS DE ÓRDENES Y COBRO (CHECKOUT)
# ============================================================================

class OrderItemCreate(BaseModel):
    menu_item_id: UUID
    quantity: int = Field(default=1, ge=1, description="Cantidad a ordenar")
    notes: Optional[str] = Field(None, max_length=255, description="Instrucciones especiales (sin cebolla, etc.)")


class OrderCheckoutRequest(BaseModel):
    """
    Solicitud de cobro de una orden en la caja registradora.
    """
    items: List[OrderItemCreate] = Field(..., min_length=1, description="Platillos a ordenar")
    payment_method: PaymentMethod = Field(..., description="CASH (Efectivo) o CARD (Tarjeta)")
    cash_given: Optional[Decimal] = Field(None, ge=0, description="Monto con el que paga el cliente en efectivo")
    notes: Optional[str] = Field(None, max_length=255, description="Nota de la orden o mesa")


class OrderItemResponse(BaseModel):
    id: UUID
    menu_item_id: UUID
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    notes: Optional[str]

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: UUID
    order_number: str
    cash_cut_id: UUID
    status: OrderStatus
    payment_method: PaymentMethod
    subtotal: Decimal
    tax: Decimal
    total_amount: Decimal
    cash_given: Optional[Decimal]
    change_given: Optional[Decimal]
    notes: Optional[str]
    created_at: datetime
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True


# ============================================================================
# 4. SCHEMAS DE REPORTES DE VENTAS POR DÍA
# ============================================================================

class DailyOrderSummary(BaseModel):
    id: UUID
    order_number: str
    created_at: datetime
    cashier_name: str
    payment_method: PaymentMethod
    total_amount: Decimal
    items_count: int
    notes: Optional[str]


class DailySalesReport(BaseModel):
    date: str  # YYYY-MM-DD
    total_sales: Decimal
    cash_sales: Decimal
    card_sales: Decimal
    orders_count: int
    average_ticket: Decimal
    orders: List[DailyOrderSummary]

