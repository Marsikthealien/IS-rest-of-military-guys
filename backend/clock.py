from datetime import datetime


def now() -> datetime:
    """Поточний час; у тестах підміняється."""
    return datetime.now()
