"""Price input shared by ingredient administration and shopping persistence."""

from decimal import Decimal, InvalidOperation


def normalize_price(raw: str) -> str | None:
    """Normalize an optional euro price with two decimal places."""
    value = raw.strip().replace(',', '.')
    if not value:
        return None
    try:
        price = Decimal(value)
        cents = price.quantize(Decimal('0.01'))
    except InvalidOperation as error:
        raise ValueError('Enter a price with at most two decimal places') from error
    if not price.is_finite() or price < 0 or price > 1_000_000 or price != cents:
        raise ValueError('Enter a non-negative price with at most two decimal places')
    return format(cents, '.2f')
