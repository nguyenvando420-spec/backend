from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from app.domain.entities.item import Item


class ItemRepository(ABC):
    """
    Abstract interface for Item persistence operations.
    Use Cases depend on this abstraction, adhering to Dependency Inversion Principle.
    """

    @abstractmethod
    async def create(self, item: Item) -> Item:
        """Persist a new Item domain entity."""
        pass

    @abstractmethod
    async def get_by_id(self, item_id: str) -> Optional[Item]:
        """Find an Item domain entity by ID."""
        pass

    @abstractmethod
    async def get_by_title(self, title: str) -> Optional[Item]:
        """Find an Item domain entity by title."""
        pass

    @abstractmethod
    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Item]:
        """List Item domain entities with pagination and optional date range filtering."""
        pass

    @abstractmethod
    async def update(self, item: Item) -> Item:
        """Update an existing Item domain entity."""
        pass

    @abstractmethod
    async def delete(self, item_id: str) -> bool:
        """Delete an Item domain entity by ID."""
        pass
