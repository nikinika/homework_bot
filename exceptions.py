class APIStatusNotOk(Exception):
    """Статус ответа сервера не 200."""

    pass


class TokenOrDateError(Exception):
    """Ошибка токена или даты."""

    pass


class EnviromentVarError(Exception):
    """Ошибка переменных аутентификации."""

    pass
