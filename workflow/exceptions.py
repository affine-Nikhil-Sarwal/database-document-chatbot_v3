"""Workflow-level typed exceptions."""

from config.settings import ConfigurationError


class ValidationError(ValueError):
    """Raised when intake or contract validation fails."""


class PermissionDeniedError(PermissionError):
    """Raised when session_context denies access to requested resources."""


class InsufficientEvidenceError(RuntimeError):
    """Raised when evidence is too weak to produce a safe answer."""


__all__ = [
    "ConfigurationError",
    "InsufficientEvidenceError",
    "PermissionDeniedError",
    "ValidationError",
]
