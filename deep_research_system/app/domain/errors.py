"""Domain errors for the research system.

All errors are categorized for proper retry routing and terminal state mapping.
"""

from __future__ import annotations

from app.domain.enums import ErrorCategory


class ResearchError(Exception):
    """Base error for all research-related exceptions."""

    category: ErrorCategory = ErrorCategory.BUG
    retryable: bool = False

    def __init__(self, message: str, category: ErrorCategory | None = None) -> None:
        super().__init__(message)
        if category:
            self.category = category


class TransientError(ResearchError):
    """Temporary error that can be retried."""

    category = ErrorCategory.TRANSIENT
    retryable = True


class RateLimitError(ResearchError):
    """Rate limit exceeded."""

    category = ErrorCategory.RATE_LIMIT
    retryable = True


class AuthError(ResearchError):
    """Authentication or authorization failure."""

    category = ErrorCategory.AUTH
    retryable = False


class InvalidOutputError(ResearchError):
    """LLM output failed validation."""

    category = ErrorCategory.INVALID_OUTPUT
    retryable = False


class PolicyError(ResearchError):
    """Content policy violation."""

    category = ErrorCategory.POLICY
    retryable = False


class QualityError(ResearchError):
    """Quality gate failure."""

    category = ErrorCategory.QUALITY
    retryable = False


class CancelledError(ResearchError):
    """User cancelled the run."""

    category = ErrorCategory.CANCELLED
    retryable = False


class BudgetExceededError(ResearchError):
    """Budget limit exceeded."""

    category = ErrorCategory.POLICY
    retryable = False


class DeadlineExceededError(ResearchError):
    """Time deadline exceeded."""

    category = ErrorCategory.TRANSIENT
    retryable = False


class ModelUnavailableError(TransientError):
    """No model available for the requested capability."""

    category = ErrorCategory.TRANSIENT
    retryable = True


class SearchProviderError(TransientError):
    """Search provider failed."""

    category = ErrorCategory.TRANSIENT
    retryable = True


class FetchError(TransientError):
    """Document fetch failed."""

    category = ErrorCategory.TRANSIENT
    retryable = True


class EvidenceValidationError(InvalidOutputError):
    """Evidence validation failed."""

    category = ErrorCategory.INVALID_OUTPUT
    retryable = False


class ReportValidationError(InvalidOutputError):
    """Report validation failed."""

    category = ErrorCategory.INVALID_OUTPUT
    retryable = False