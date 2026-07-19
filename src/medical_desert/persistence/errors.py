class PersistenceError(Exception):
    """Base persistence error."""


class RecordNotFound(PersistenceError):
    pass


class VersionConflict(PersistenceError):
    def __init__(self, expected: int, current: int) -> None:
        super().__init__(f"Expected version {expected}, current version is {current}")
        self.expected = expected
        self.current = current


class IdempotencyConflict(PersistenceError):
    pass
