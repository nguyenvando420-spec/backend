from app.domain.entities.item import Item
from app.domain.exceptions.item_exceptions import ItemNotFoundException
from app.use_cases.interfaces.item_repository import ItemRepository


class GetItemUseCase:
    """Use case to retrieve an Item by its unique ID."""

    def __init__(self, item_repository: ItemRepository):
        self.item_repository = item_repository

    async def execute(self, item_id: str) -> Item:
        item = await self.item_repository.get_by_id(item_id)
        if not item:
            raise ItemNotFoundException(item_id)
        return item
