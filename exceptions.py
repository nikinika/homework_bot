class APIStatusNotOk(Exception):
    """Статус ответа сервера не 200."""


class TokenOrDateError(Exception):
    """Ошибка токена или даты."""
