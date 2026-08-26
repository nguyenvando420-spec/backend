from datetime import datetime
from typing import List, Optional, Dict
from app.domain.entities.item import Item
from app.use_cases.interfaces.item_repository import ItemRepository
from app.infrastructure.mock.item_mock_data import MOCK_ITEMS


class InMemoryItemRepository(ItemRepository):
    """
    In-Memory Implementation of ItemRepository.
    Loads mockup data from app.infrastructure.mock.item_mock_data.
    Does NOT require any Database connection.
    """

    def __init__(self, seed_data: Optional[List[Item]] = None):
        self._items: Dict[str, Item] = {}
        # Load mock data by default
        initial_data = seed_data if seed_data is not None else MOCK_ITEMS
        for item in initial_data:
            self._items[item.id] = item

    async def create(self, item: Item) -> Item:
        self._items[item.id] = item
        return item

    async def get_by_id(self, item_id: str) -> Optional[Item]:
        return self._items.get(item_id)

    async def get_by_title(self, title: str) -> Optional[Item]:
        for item in self._items.values():
            if item.title == title:
                return item
        return None

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Item]:
        filtered = list(self._items.values())
        if start_date:
            filtered = [item for item in filtered if item.created_at >= start_date]
        if end_date:
            filtered = [item for item in filtered if item.created_at <= end_date]

        return filtered[skip : skip + limit]

    async def update(self, item: Item) -> Item:
        self._items[item.id] = item
        return item

    async def delete(self, item_id: str) -> bool:
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False


# Singleton instance for mock repository when running in-memory
_in_memory_repo_instance = InMemoryItemRepository()


def get_in_memory_item_repository() -> InMemoryItemRepository:
    """Returns singleton instance of InMemoryItemRepository."""
    return _in_memory_repo_instance
