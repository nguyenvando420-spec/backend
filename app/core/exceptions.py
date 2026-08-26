class ApplicationException(Exception):
    """Base exception class for application-level errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
