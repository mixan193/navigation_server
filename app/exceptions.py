class AppException(Exception):
    """
    Базовый класс для всех исключений приложения.
    """
    pass


class NotFoundError(AppException):
    """
    Ресурс не найден (например, при поиске в БД).
    """
    pass


class ValidationError(AppException):
    """
    Ошибка валидации входных данных.
    """
    pass


class ServiceError(AppException):
    """
    Ошибка на уровне бизнес-логики (сервисов).
    """
    pass