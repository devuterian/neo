class NeoError(Exception):
    """Base error for user-facing neoctl failures."""

class NotFoundError(NeoError):
    pass


class ConflictError(NeoError):
    pass


class ValidationError(NeoError):
    pass


class ApprovalRequiredError(NeoError):
    pass


class AutoWakeRejectedError(NeoError):
    """Raised when auto_wake policy blocks automatic day creation."""
