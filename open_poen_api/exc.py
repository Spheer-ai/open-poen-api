from sqlalchemy.exc import IntegrityError


class CustomException(Exception):
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.status_code}': '{self.message}')"

    def __str__(self):
        return self.__repr__()


class EntityAlreadyExists(CustomException):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class EntityNotFound(CustomException):
    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class UnsupportedFileType(CustomException):
    def __init__(self, message: str):
        super().__init__(message, status_code=415)


class FileTooLarge(CustomException):
    def __init__(self, message: str):
        super().__init__(message, status_code=413)


class PaymentCouplingError(CustomException):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class UnprocessableContent(CustomException):
    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class NotAuthorized(CustomException):
    def __init__(self, message: str):
        super().__init__(message, status_code=403)


def raise_err_if_unique_constraint(constraint_name: str, error: IntegrityError):
    """There seems to be no way to check for this specific case without making
    this check work only for Postgres. SQL-Alchemy does not return consistent
    exceptions for different databases."""
    if constraint_name in str(error):
        raise EntityAlreadyExists(
            message=f"The following unique constraint was violated: '{constraint_name}'."
        )
