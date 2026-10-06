from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

from models.inventory import UnitType, WasteType, MovementType, RecipeType


# ============================================================================
# 1. SCHEMAS DE INGREDIENTES / INSUMOS
# ============================================================================

class IngredientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="Nombre del insumo")
    category: Optional[str] = Field(None, max_length=50, description="Categoría (abarrotes, carnes, verduras, etc.)")
    unit: UnitType = Field(default=UnitType.G, description="Unidad de medida base (g, ml, pza)")
    min_stock: Decimal = Field(default=Decimal("0.000"), ge=0, description="Stock mínimo para disparar alertas")
    cost_per_unit: Optional[Decimal] = Field(None, ge=0, description="Costo unitario por unidad base")
    waste_percentage: Decimal = Field(default=Decimal("0.00"), ge=0, le=100, description="Merma teórica estimada (%)")


class IngredientCreate(IngredientBase):
    """Schema para registrar un nuevo insumo."""
    initial_stock: Decimal = Field(default=Decimal("0.000"), ge=0, description="Stock inicial al crearlo")


class IngredientUpdate(BaseModel):
    """Schema para editar un insumo existente (campos opcionales)."""
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    category: Optional[str] = None
    min_stock: Optional[Decimal] = Field(None, ge=0)
    cost_per_unit: Optional[Decimal] = Field(None, ge=0)
    waste_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None


class IngredientResponse(IngredientBase):
    """Schema para devolver el insumo en formato JSON."""
    id: UUID
    current_stock: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# 2. ENTRADAS MANUALES DE STOCK
# ============================================================================

class StockEntryCreate(BaseModel):
    """Carga manual de inventario (compras locales, reposición)."""
    ingredient_id: UUID
    quantity: Decimal = Field(..., gt=0, description="Cantidad que entra al almacén")
    cost_per_unit: Optional[Decimal] = Field(None, ge=0, description="Costo por unidad de esta entrada")
    note: Optional[str] = Field(None, max_length=255, description="Motivo o proveedor de la compra")


# ============================================================================
# 3. SCHEMAS DE MERMAS (WASTE)
# ============================================================================

class ProcessWasteCreate(BaseModel):
    """
    Regla de Merma por Proceso:
    Pide Peso Bruto (lo que salió del almacén) y Peso Neto (lo útil resultante).
    """
    ingredient_id: UUID
    gross_quantity: Decimal = Field(..., gt=0, description="Peso Bruto: cantidad retirada del almacén")
    net_quantity: Decimal = Field(..., ge=0, description="Peso Neto: cantidad limpia aprovechable")
    reason: Optional[str] = Field(None, max_length=255, description="Ej. Limpieza de aguacate, descongelación")
    registered_by: Optional[str] = Field(None, max_length=100, description="Nombre o usuario del cocinero")

    @model_validator(mode="after")
    def validate_gross_greater_than_net(self):
        """Valida que el Peso Bruto sea mayor o igual al Peso Neto."""
        if self.gross_quantity < self.net_quantity:
            raise ValueError("El Peso Bruto debe ser mayor o igual al Peso Neto.")
        return self


class GeneralWasteCreate(BaseModel):
    """
    Registro de mermas directas (caducidad, error humano, falta de calidad, etc.).
    """
    ingredient_id: Optional[UUID] = None
    subrecipe_id: Optional[UUID] = None
    waste_type: WasteType
    quantity: Decimal = Field(..., gt=0, description="Cantidad mermada")
    reason: Optional[str] = Field(None, max_length=255)
    registered_by: Optional[str] = Field(None, max_length=100)

    @model_validator(mode="after")
    def validate_target(self):
        """Debe especificar exactamente un insumo o una subreceta, no ambos ni ninguno."""
        if bool(self.ingredient_id) == bool(self.subrecipe_id):
            raise ValueError("Debe especificar exactamente ingredient_id O subrecipe_id.")
        if self.waste_type == WasteType.PROCESO:
            raise ValueError("Para merma de proceso, utiliza el endpoint específico con peso bruto y neto.")
        return self


class WasteResponse(BaseModel):
    """Respuesta con los cálculos de merma aplicados."""
    id: UUID
    waste_type: WasteType
    ingredient_id: Optional[UUID]
    subrecipe_id: Optional[UUID]
    gross_quantity: Optional[Decimal]
    net_quantity: Optional[Decimal]
    waste_quantity: Decimal
    waste_percentage: Decimal
    unit: UnitType
    reason: Optional[str]
    registered_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# 4. SCHEMAS DE RECETAS Y SUBRECETAS
# ============================================================================

class RecipeItemCreate(BaseModel):
    ingredient_id: Optional[UUID] = None
    subrecipe_id: Optional[UUID] = None
    quantity: Decimal = Field(..., gt=0, description="Cantidad requerida")
    unit: UnitType = Field(..., description="Unidad de medida requerida")

    @model_validator(mode="after")
    def validate_item_target(self):
        if bool(self.ingredient_id) == bool(self.subrecipe_id):
            raise ValueError("Un item de receta debe ser o un ingrediente o una subreceta.")
        return self


class RecipeItemResponse(BaseModel):
    id: UUID
    ingredient_id: Optional[UUID]
    subrecipe_id: Optional[UUID]
    quantity: Decimal
    unit: UnitType

    class Config:
        from_attributes = True


class RecipeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    recipe_type: RecipeType = Field(default=RecipeType.RECETA)
    description: Optional[str] = None
    yield_quantity: Decimal = Field(default=Decimal("1.000"), gt=0)
    yield_unit: UnitType = Field(default=UnitType.PZA)
    items: List[RecipeItemCreate] = Field(default_factory=list)


class RecipeResponse(BaseModel):
    id: UUID
    name: str
    recipe_type: RecipeType
    description: Optional[str]
    yield_quantity: Decimal
    yield_unit: UnitType
    is_active: bool
    created_at: datetime
    items: List[RecipeItemResponse]

    class Config:
        from_attributes = True


# ============================================================================
# 5. SCHEMAS DE PRODUCCIÓN DE SUBRECETAS (MISE EN PLACE)
# ============================================================================

class SubrecipeProductionCreate(BaseModel):
    recipe_id: UUID
    quantity_to_produce: Decimal = Field(..., gt=0, description="Cantidad que se preparó (ej. 5000 ml)")
    notes: Optional[str] = Field(None, max_length=255)
    produced_by: Optional[str] = Field(None, max_length=100)


class ProductionLogResponse(BaseModel):
    id: UUID
    recipe_id: UUID
    quantity_produced: Decimal
    unit: UnitType
    notes: Optional[str]
    produced_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SubrecipeStockResponse(BaseModel):
    id: UUID
    recipe_id: UUID
    current_stock: Decimal
    min_stock: Decimal
    unit: UnitType
    last_production_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# 6. SCHEMAS DE MOVIMIENTOS (KARDEX) Y ALERTAS
# ============================================================================

class StockMovementResponse(BaseModel):
    id: UUID
    movement_type: MovementType
    ingredient_id: Optional[UUID]
    subrecipe_id: Optional[UUID]
    quantity: Decimal
    balance_after: Decimal
    unit: UnitType
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class LowStockAlertResponse(BaseModel):
    item_id: UUID
    name: str
    item_type: str  # "ingredient" o "subrecipe"
    current_stock: Decimal
    min_stock: Decimal
    unit: UnitType
    status: str     # "CRITICO" si stock es 0, "BAJO" si stock <= min_stock
