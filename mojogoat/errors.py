"""Exceptions raised when resolving a goat by name (ADR-016)."""


class GoatNotFound(Exception):
    """The goat name is invalid or is not in the registry."""

    def __init__(self, name):
        super().__init__(f"Goat '{name}' not found")
        self.name = name


class GoatUnavailable(Exception):
    """The goat is registered but cannot be opened (missing driver, bad path, ...)."""
