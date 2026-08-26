from app.core.exceptions import ApplicationException


class ItemNotFoundException(ApplicationException):
    """Raised when an item with specified ID is not found."""

    def __init__(self, item_id: str):
        super().__init__(f"Item with ID '{item_id}' was not found.")
        self.item_id = item_id


class ItemAlreadyExistsException(ApplicationException):
    """Raised when attempting to create an item that already exists."""

    def __init__(self, title: str):
        super().__init__(f"Item with title '{title}' already exists.")
        self.title = title


class InvalidItemDataException(ApplicationException):
    """Raised when item data violates domain rules."""
    pass
