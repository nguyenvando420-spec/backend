import pytest
from app.domain.entities.item import Item
from app.domain.exceptions.item_exceptions import ItemAlreadyExistsException, ItemNotFoundException
from app.use_cases.item.create_item import CreateItemUseCase
from app.use_cases.item.get_item import GetItemUseCase
from app.use_cases.interfaces.item_repository import ItemRepository


class InMemoryItemRepository(ItemRepository):
    """In-memory mock repository for testing Use Cases independently of any DB."""

    def __init__(self):
        self.items = {}

    async def create(self, item: Item) -> Item:
        self.items[item.id] = item
        return item

    async def get_by_id(self, item_id: str) -> Item:
        return self.items.get(item_id)

    async def get_by_title(self, title: str) -> Item:
        for item in self.items.values():
            if item.title == title:
                return item
        return None

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Item]:
        return list(self.items.values())[skip: skip + limit]

    async def update(self, item: Item) -> Item:
        self.items[item.id] = item
        return item

    async def delete(self, item_id: str) -> bool:
        if item_id in self.items:
            del self.items[item_id]
            return True
        return False


@pytest.mark.asyncio
async def test_create_item_use_case_success():
    repo = InMemoryItemRepository()
    use_case = CreateItemUseCase(repo)

    item = await use_case.execute(title="Laptop", price=1200.0, description="Gaming laptop")

    assert item.id is not None
    assert item.title == "Laptop"
    assert item.price == 1200.0
    assert item.description == "Gaming laptop"


@pytest.mark.asyncio
async def test_create_duplicate_item_raises_exception():
    repo = InMemoryItemRepository()
    use_case = CreateItemUseCase(repo)

    await use_case.execute(title="Phone", price=800.0)

    with pytest.raises(ItemAlreadyExistsException):
        await use_case.execute(title="Phone", price=900.0)


@pytest.mark.asyncio
async def test_get_nonexistent_item_raises_exception():
    repo = InMemoryItemRepository()
    use_case = GetItemUseCase(repo)

    with pytest.raises(ItemNotFoundException):
        await use_case.execute("non-existent-id")
