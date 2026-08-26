from typing import Optional
from app.domain.entities.item import Item
from app.domain.exceptions.item_exceptions import ItemAlreadyExistsException, InvalidItemDataException
from app.use_cases.interfaces.item_repository import ItemRepository


class CreateItemUseCase:
    """Use case to handle creation of a new Item."""

    def __init__(self, item_repository: ItemRepository):
        self.item_repository = item_repository

    async def execute(self, title: str, price: float, description: Optional[str] = None) -> Item:
        # Check if item with exact title already exists (sample domain policy)
        existing_item = await self.item_repository.get_by_title(title)
        if existing_item:
            raise ItemAlreadyExistsException(title)

        # Create Domain Entity
        item = Item(
            title=title,
            description=description,
            price=price
        )

        # Validate Entity business logic
        try:
            item.validate()
        except ValueError as err:
            raise InvalidItemDataException(str(err))

        # Persist through repository interface
        return await self.item_repository.create(item)
