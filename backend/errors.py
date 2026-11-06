class ApiError(Exception):
    """Помилка домену: статус HTTP + тіло відповіді."""

    def __init__(self, status: int, body: dict):
        self.status, self.body = status, body


def detail(status: int, text: str) -> ApiError:
    return ApiError(status, {"detail": text})
