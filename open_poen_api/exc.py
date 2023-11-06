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


class PaymentCouplingOrder(CustomException):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)
