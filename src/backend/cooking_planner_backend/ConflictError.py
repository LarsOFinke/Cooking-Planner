"""Domain errors translated by the HTTP layer."""


class ConflictError(ValueError):
    """A valid request that conflicts with saved user data."""
