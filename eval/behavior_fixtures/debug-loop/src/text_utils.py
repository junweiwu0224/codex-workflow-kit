"""Small text helpers used by the behavior-pilot debugging case."""


def canonical_slug(value: str) -> str:
    """Return a lower-case URL slug for a human-entered title."""
    return value.strip().lower().replace(" ", "-")
