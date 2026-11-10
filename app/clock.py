from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def get_now() -> datetime:
    """FastAPI dependency for the current time, so tests can freeze it."""
    return utcnow()
