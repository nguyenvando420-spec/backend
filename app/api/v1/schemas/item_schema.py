from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ItemCreateRequest(BaseModel):
    """Schema for creating a new Item."""
    title: str = Field(..., min_length=1, max_length=200, description="Item title", json_schema_extra={"example": "MacBook Pro M3"})
    description: Optional[str] = Field(None, max_length=1000, description="Optional description", json_schema_extra={"example": "Apple Laptop 16 inch"})
    price: float = Field(..., ge=0, description="Price must be non-negative", json_schema_extra={"example": 2499.99})


class ItemResponse(BaseModel):
    """Schema for Item API response."""
    id: str
    title: str
    description: Optional[str] = None
    price: float
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
