"""Domain error for a change that conflicts with saved user data."""


class ConflictError(ValueError):
    """A valid request that conflicts with saved user data."""
