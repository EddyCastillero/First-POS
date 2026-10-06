import uuid
from datetime import datetime
from enum import Enum
from decimal import Decimal
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Numeric,
    Integer,
    ForeignKey,
    Enum as SQLEnum,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


# ============================================================================
# 1. ENUMS DEL MÓDULO POS
# ============================================================================

class PaymentMethod(str, Enum):
    """Métodos de pago admitidos para el MVP."""
    CASH = "CASH"  # Efectivo
    CARD = "CARD"  # Tarjeta


class OrderStatus(str, Enum):
    """Estados posibles de una orden."""
    COMPLETED = "COMPLETED"  # Cobrada con éxito
    CANCELLED = "CANCELLED"  # Cancelada / Reversada


class ShiftStatus(str, Enum):
    """Estado del turno de caja."""
    OPEN = "OPEN"      # Turno activo recibiendo ventas
    CLOSED = "CLOSED"  # Turno cerrado con corte efectuado


# ============================================================================
# 2. MODELOS ORM (Tablas en PostgreSQL)
# ============================================================================

class CashCut(Base):
    """
    Control de Turno de Caja (Apertura y Corte de Caja).
    Garantiza que el cajero tenga un fondo inicial y previene descuadres.
    """
    __tablename__ = "cash_cuts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cashier_name = Column(String(100), nullable=False)
    status = Column(SQLEnum(ShiftStatus, name="shift_status_enum"), nullable=False, default=ShiftStatus.OPEN, index=True)

    # Fondo inicial obligatorio: solo 1000, 2000 o 3000
    initial_cash = Column(Numeric(10, 2), nullable=False)

    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    # Acumuladores de ventas durante este turno
    cash_sales_total = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    card_sales_total = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    # Cuadre de caja al cierre
    expected_cash = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))  # initial_cash + cash_sales_total
    actual_cash = Column(Numeric(10, 2), nullable=True)                              # Dinero físico contado por el cajero
    difference = Column(Numeric(10, 2), nullable=True)                               # actual_cash - expected_cash (sobrante o faltante)

    notes = Column(Text, nullable=True)

    # Relaciones
    orders = relationship("Order", back_populates="cash_cut")


class MenuItem(Base):
    """
    Platillo o Producto a la venta en el menú del POS.
    Cada platillo apunta OBLIGATORIAMENTE a una Receta culinaria (Recipe),
    la cual define los ingredientes que se deben descontar al venderlo.
    """
    __tablename__ = "menu_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), index=True, nullable=False, unique=True)
    category = Column(String(50), nullable=True)  # Comidas, Bebidas, Postres...
    price = Column(Numeric(10, 2), nullable=False)  # Precio de venta al público

    # Clave foránea que conecta la venta con el inventario
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False, index=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    recipe = relationship("Recipe")
    order_items = relationship("OrderItem", back_populates="menu_item")


class Order(Base):
    """
    Orden de Venta / Ticket cobrado en la caja.
    """
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(30), unique=True, index=True, nullable=False)  # Ej. "ORD-20261006-0001"

    # Turno al que pertenece la venta
    cash_cut_id = Column(UUID(as_uuid=True), ForeignKey("cash_cuts.id", ondelete="RESTRICT"), nullable=False, index=True)

    status = Column(SQLEnum(OrderStatus, name="order_status_enum"), nullable=False, default=OrderStatus.COMPLETED, index=True)
    payment_method = Column(SQLEnum(PaymentMethod, name="payment_method_enum"), nullable=False)

    subtotal = Column(Numeric(10, 2), nullable=False)
    tax = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total_amount = Column(Numeric(10, 2), nullable=False)

    # Control de efectivo (si aplica)
    cash_given = Column(Numeric(10, 2), nullable=True)
    change_given = Column(Numeric(10, 2), nullable=True)

    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relaciones
    cash_cut = relationship("CashCut", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """
    Detalle de platillos vendidos dentro de una orden.
    """
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = Column(UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)  # Precio al momento de la venta
    subtotal = Column(Numeric(10, 2), nullable=False)    # quantity * unit_price

    notes = Column(String(255), nullable=True)

    # Relaciones
    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")
