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
    ForeignKey,
    Enum as SQLEnum,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


# ============================================================================
# 1. ENUMS (Listas cerradas de opciones válidas)
# ============================================================================

class UnitType(str, Enum):
    """
    Unidades de medida base para el inventario.
    Usamos unidades estándar mínimas para evitar errores de redondeo.
    """
    G = "g"      # Gramos (para peso)
    ML = "ml"    # Mililitros (para volumen)
    PZA = "pza"  # Piezas / unidades (para conteo)


class WasteType(str, Enum):
    """
    Tipos de merma rescatados del estándar de restaurantes (Brote).
    """
    NATURAL = "natural"                  # Limpieza habitual (cáscaras, huesos)
    VIDA_UTIL = "vida_util"              # Caducidad / expiración en refrigeración
    ERROR_HUMANO = "error_humano"        # Se cayó al piso, se quemó en la plancha
    FALTA_CALIDAD = "falta_calidad"      # Llegó en mal estado del proveedor
    RECHAZO_CLIENTE = "rechazo_cliente"  # Devolución por parte del cliente
    PROCESO = "proceso"                  # Merma operativa durante preparación (descongelación, limpieza)


class MovementType(str, Enum):
    """
    Tipos de movimientos para el Kardex / Ledger contable de stock.
    Cada cambio de inventario DEBE tener un tipo registrado para trazabilidad.
    """
    ENTRADA_MANUAL = "entrada_manual"        # Compra o carga manual de stock
    SALIDA_VENTA = "salida_venta"            # Venta cobrada en la caja registradora
    MERMA = "merma"                          # Salida por desperdicio o merma
    PRODUCCION_CONSUMO = "produccion_consumo"# Insumos crudos consumidos al preparar una subreceta
    PRODUCCION_ENTRADA = "produccion_entrada"# Subreceta terminada que entra al stock
    AJUSTE_INVENTARIO = "ajuste_inventario"  # Cuadre físico al contar el almacén


class RecipeType(str, Enum):
    """
    Clasificación de recetas:
    - RECETA: Platillo final que se vende al comensal (ej. Pasta Alfredo).
    - SUBRECETA: Preparación intermedia / mise en place que genera stock (ej. Salsa de Jitomate).
    """
    RECETA = "receta"
    SUBRECETA = "subreceta"


# ============================================================================
# 2. MODELOS ORM (Tablas en PostgreSQL)
# ============================================================================

class Ingredient(Base):
    """
    Representa un Insumo Base o Producto Directo de Venta.
    Ejemplos: Jitomate crudo, Pechuga de pollo congelada, Lata de refresco.
    """
    __tablename__ = "ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), unique=True, index=True, nullable=False)
    category = Column(String(50), nullable=True)  # abarrotes, verduras, carnes, bebidas...
    unit = Column(SQLEnum(UnitType, name="unit_type_enum"), nullable=False, default=UnitType.G)

    # Inventario: Numeric(12, 3) = hasta 999,999,999.999 (3 decimales de precisión para gramos/ml)
    current_stock = Column(Numeric(12, 3), nullable=False, default=Decimal("0.000"))
    min_stock = Column(Numeric(12, 3), nullable=False, default=Decimal("0.000"))
    cost_per_unit = Column(Numeric(10, 2), nullable=True)  # Costo por unidad base

    # Merma teórica estimada (%) para costeo o cálculo estándar
    waste_percentage = Column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relaciones
    movements = relationship("StockMovement", back_populates="ingredient")
    waste_logs = relationship("WasteLog", back_populates="ingredient")


class Recipe(Base):
    """
    Receta o Subreceta culinaria.
    Define cómo se compone un platillo final o una preparación de mise en place.
    """
    __tablename__ = "recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), index=True, nullable=False)
    recipe_type = Column(SQLEnum(RecipeType, name="recipe_type_enum"), nullable=False, default=RecipeType.RECETA)
    description = Column(Text, nullable=True)

    # Rendimiento esperado: ej. 5000 ml de salsa, o 1 pza de hamburguesa
    yield_quantity = Column(Numeric(10, 3), nullable=False, default=Decimal("1.000"))
    yield_unit = Column(SQLEnum(UnitType, name="unit_type_enum"), nullable=False, default=UnitType.PZA)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relaciones
    items = relationship("RecipeItem", back_populates="recipe", foreign_keys="RecipeItem.recipe_id", cascade="all, delete-orphan")
    stock = relationship("SubrecipeStock", back_populates="recipe", uselist=False, cascade="all, delete-orphan")
    production_logs = relationship("ProductionLog", back_populates="recipe")


class RecipeItem(Base):
    """
    Ingrediente individual dentro de una Receta o Subreceta.
    Un item puede ser:
    - Un Insumo base (apunta a ingredient_id), O BIEN
    - Otra Subreceta (apunta a subrecipe_id)
    """
    __tablename__ = "recipe_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)

    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=True, index=True)
    subrecipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=True, index=True)

    # Cantidad requerida en la preparación
    quantity = Column(Numeric(10, 3), nullable=False)
    unit = Column(SQLEnum(UnitType, name="unit_type_enum"), nullable=False)

    # Relaciones
    recipe = relationship("Recipe", back_populates="items", foreign_keys=[recipe_id])
    ingredient = relationship("Ingredient")
    subrecipe = relationship("Recipe", foreign_keys=[subrecipe_id])


class SubrecipeStock(Base):
    """
    Control de stock específico para Subrecetas preparadas (ej. 4500 ml de Salsa en refrigerador).
    """
    __tablename__ = "subrecipe_stocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), unique=True, nullable=False)

    current_stock = Column(Numeric(12, 3), nullable=False, default=Decimal("0.000"))
    min_stock = Column(Numeric(12, 3), nullable=False, default=Decimal("0.000"))
    unit = Column(SQLEnum(UnitType, name="unit_type_enum"), nullable=False)

    last_production_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    recipe = relationship("Recipe", back_populates="stock")


class StockMovement(Base):
    """
    Kardex / Libro contable inmutable de inventario.
    Ningún stock se modifica sin dejar un registro en esta tabla.
    """
    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    movement_type = Column(SQLEnum(MovementType, name="movement_type_enum"), nullable=False, index=True)

    # Puede afectar a un Insumo o a una Subreceta
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=True, index=True)
    subrecipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=True, index=True)

    # Cantidad: positiva para entradas, negativa para salidas
    quantity = Column(Numeric(12, 3), nullable=False)
    balance_after = Column(Numeric(12, 3), nullable=False)  # Saldo que quedó después del movimiento
    unit = Column(SQLEnum(UnitType, name="unit_type_enum"), nullable=False)

    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relaciones
    ingredient = relationship("Ingredient", back_populates="movements")
    subrecipe = relationship("Recipe")


class WasteLog(Base):
    """
    Registro detallado de Mermas y Desperdicios.
    Incluye la regla de negocio para Merma de Proceso (Peso Bruto vs Peso Neto).
    """
    __tablename__ = "waste_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    waste_type = Column(SQLEnum(WasteType, name="waste_type_enum"), nullable=False, index=True)

    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=True, index=True)
    subrecipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=True, index=True)

    # Regla de Proceso: Peso Bruto y Peso Neto (opcionales para otras mermas, obligatorios en proceso)
    gross_quantity = Column(Numeric(10, 3), nullable=True)
    net_quantity = Column(Numeric(10, 3), nullable=True)

    # Cantidad total desperdiciada = gross_quantity - net_quantity (o cantidad directa en otras mermas)
    waste_quantity = Column(Numeric(10, 3), nullable=False)
    waste_percentage = Column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    unit = Column(SQLEnum(UnitType, name="unit_type_enum"), nullable=False)

    reason = Column(String(255), nullable=True)
    registered_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relaciones
    ingredient = relationship("Ingredient", back_populates="waste_logs")
    subrecipe = relationship("Recipe")


class ProductionLog(Base):
    """
    Historial de lotes de Subrecetas preparadas en cocina (Mise en place).
    """
    __tablename__ = "production_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity_produced = Column(Numeric(10, 3), nullable=False)
    unit = Column(SQLEnum(UnitType, name="unit_type_enum"), nullable=False)

    notes = Column(String(255), nullable=True)
    produced_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relaciones
    recipe = relationship("Recipe", back_populates="production_logs")
