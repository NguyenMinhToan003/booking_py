class DomainException(Exception):
    """Exception nghiệp vụ có status code + code string cho FE, không phải lỗi hệ thống.
    Dùng trong service, raise thẳng; exception_handler map sang HTTP response."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(DomainException):
    def __init__(self, message: str = "Not found", code: str = "NOT_FOUND") -> None:
        super().__init__(status_code=404, code=code, message=message)


class ConflictError(DomainException):
    def __init__(self, message: str, code: str = "CONFLICT", details: dict | None = None) -> None:
        super().__init__(status_code=409, code=code, message=message, details=details)


class BadRequestError(DomainException):
    def __init__(self, message: str, code: str = "BAD_REQUEST", details: dict | None = None) -> None:
        super().__init__(status_code=400, code=code, message=message, details=details)


class ForbiddenError(DomainException):
    def __init__(self, message: str = "Forbidden", code: str = "FORBIDDEN") -> None:
        super().__init__(status_code=403, code=code, message=message)
