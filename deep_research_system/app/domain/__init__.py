"""Domain layer for the research system.

This layer contains:
- Enums: Core vocabulary
- Errors: Categorized exceptions
- Models: Pydantic models for all artifacts
- Policies: Business rules and validation
"""

from app.domain.enums import (
    ArtifactType,
    BudgetLevel,
    ClaimType,
    DebatePosition,
    DepthLevel,
    ErrorCategory,
    EvidenceType,
    QualityDecision,
    ResolutionAction,
    RunStatus,
    ResearchStrategy,
    SourceTier,
    TaskType,
)
from app.domain.errors import (
    AuthError,
    BudgetExceededError,
    CancelledError,
    DeadlineExceededError,
    EvidenceValidationError,
    FetchError,
    InvalidOutputError,
    ModelUnavailableError,
    PolicyError,
    QualityError,
    RateLimitError,
    ReportValidationError,
    ResearchError,
    SearchProviderError,
    TransientError,
)
from app.domain.models import (
    AnalysisRevision,
    Artifact,
    Claim,
    CritiqueRevision,
    Document,
    Evidence,
    Passage,
    PlanArtifact,
    ReportRevision,
    RevisionMeta,
    Source,
    ValidationResult,
)

__all__ = [
    # Enums
    "ArtifactType",
    "BudgetLevel",
    "ClaimType",
    "DebatePosition",
    "DepthLevel",
    "ErrorCategory",
    "EvidenceType",
    "QualityDecision",
    "ResolutionAction",
    "RunStatus",
    "ResearchStrategy",
    "SourceTier",
    "TaskType",
    # Errors
    "AuthError",
    "BudgetExceededError",
    "CancelledError",
    "DeadlineExceededError",
    "EvidenceValidationError",
    "FetchError",
    "InvalidOutputError",
    "ModelUnavailableError",
    "PolicyError",
    "QualityError",
    "RateLimitError",
    "ReportValidationError",
    "ResearchError",
    "SearchProviderError",
    "TransientError",
    # Models
    "AnalysisRevision",
    "Artifact",
    "Claim",
    "CritiqueRevision",
    "Document",
    "Evidence",
    "Passage",
    "PlanArtifact",
    "ReportRevision",
    "RevisionMeta",
    "Source",
    "ValidationResult",
]