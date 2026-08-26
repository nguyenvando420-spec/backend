from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime
from app.infrastructure.database.connection import Base
from app.domain.entities.item import Item


class ItemModel(Base):
    """SQLAlchemy ORM Model for persistence."""
    __tablename__ = "items"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_entity(self) -> Item:
        """Convert ORM model to pure Domain Entity."""
        return Item(
            id=self.id,
            title=self.title,
            description=self.description,
            price=self.price,
            is_active=self.is_active,
            created_at=self.created_at
        )

    @classmethod
    def from_entity(cls, entity: Item) -> "ItemModel":
        """Create ORM model from Domain Entity."""
        return cls(
            id=entity.id,
            title=entity.title,
            description=entity.description,
            price=entity.price,
            is_active=entity.is_active,
            created_at=entity.created_at
        )
