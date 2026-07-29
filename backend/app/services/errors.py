"""Domain errors translated to HTTP responses at the application boundary."""


class ServiceError(Exception):
    """Base class for expected business errors."""

    status_code = 400
    code = "SERVICE_ERROR"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class AuthenticationError(ServiceError):
    """Authentication or credential failure."""

    status_code = 401
    code = "AUTHENTICATION_FAILED"


class AuthorizationError(ServiceError):
    """Authenticated user lacks access to a resource."""

    status_code = 403
    code = "FORBIDDEN"


class NotFoundError(ServiceError):
    """Requested domain resource does not exist."""

    status_code = 404
    code = "NOT_FOUND"


class ConflictError(ServiceError):
    """Request conflicts with an existing unique resource."""

    status_code = 409
    code = "CONFLICT"


class ExternalServiceError(ServiceError):
    """An optional upstream integration could not satisfy the request."""

    status_code = 503
    code = "EXTERNAL_SERVICE_UNAVAILABLE"
