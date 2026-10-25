class ServiceError(Exception):
    """A request that can't be completed, with a message that is safe to show the user.

    Raised by services and turned into an HTTP response by the handler in main.py.
    """

    status_code = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class NotFound(ServiceError):
    status_code = 404


class Forbidden(ServiceError):
    status_code = 403


class Conflict(ServiceError):
    status_code = 409
