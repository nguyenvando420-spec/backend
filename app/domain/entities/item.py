from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Item:
    """
    Domain Entity representing an Item.
    Contains core business attributes and logic.
    100% independent of databases or web frameworks.
    """
    title: str
    description: Optional[str] = None
    price: float = 0.0
    is_active: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    def validate(self) -> None:
        """Domain validation logic."""
        if not self.title or not self.title.strip():
            raise ValueError("Item title cannot be empty.")
        if self.price < 0:
            raise ValueError("Item price cannot be negative.")
