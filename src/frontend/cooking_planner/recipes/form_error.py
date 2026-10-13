"""A recipe editor validation error suitable for display to the user."""


class FormError(ValueError):
    """A localized message that the editor can show without changing its form."""
