"""Domain errors raised by services. Mapped to HTTP responses in app.main."""


class AppError(Exception):
    status_code = 400
    headers: dict[str, str] | None = None

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class BadRequestError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401
    headers = {"WWW-Authenticate": "Bearer"}


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class PayloadTooLargeError(AppError):
    status_code = 413


class UnsupportedFileTypeError(AppError):
    status_code = 415
