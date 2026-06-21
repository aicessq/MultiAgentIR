"""Domain enums for the research system.

These enums define the core vocabulary used across all layers.
"""

from __future__ import annotations

from enum import Enum


class RunStatus(str, Enum):
    """Terminal states for a research run."""
    QUEUED = "queued"
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED_QUALITY_GATE = "failed_quality_gate"
    FAILED = "failed"


class ResearchStrategy(str, Enum):
    """Research topology strategy."""
    AUTO = "auto"
    HIERARCHICAL = "hierarchical"
    DEBATE = "debate"


class DebatePosition(str, Enum):
    """Unified debate position enum."""
    SUPPORT = "support"
    OPPOSE = "oppose"
    ALTERNATIVE = "alternative"


class ArtifactType(str, Enum):
    """Types of artifacts produced during research."""
    PLAN = "plan"
    SEARCH_RESULT_SET = "search_result_set"
    DOCUMENT = "document"
    EVIDENCE_SET = "evidence_set"
    ANALYSIS_REVISION = "analysis_revision"
    CRITIQUE_REVISION = "critique_revision"
    DEBATE_ROUND = "debate_round"
    REPORT_REVISION = "report_revision"
    VALIDATION_RESULT = "validation_result"


class ClaimType(str, Enum):
    """Types of claims in analysis."""
    FACTUAL = "factual_claim"
    ANALYTICAL = "analytical_claim"
    FORECAST = "forecast_claim"
    RISK = "risk_claim"
    LIMITATION = "research_limitation"


class ResolutionAction(str, Enum):
    """How to handle a critic finding."""
    BLOCK = "blocker"
    DOWNGRADE = "downgrade_required"
    LIMIT_ONLY = "limitations_only"
    ACCEPTABLE = "acceptable_uncertainties"


class QualityDecision(str, Enum):
    """Validator quality decision."""
    PASS = "pass"
    REPAIR = "repair"
    HUMAN_REVIEW = "human_review"
    FAIL = "fail"


class ErrorCategory(str, Enum):
    """Categories of errors for retry routing."""
    TRANSIENT = "transient"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    INVALID_OUTPUT = "invalid_output"
    POLICY = "policy"
    QUALITY = "quality"
    CANCELLED = "cancelled"
    BUG = "bug"


class SourceTier(str, Enum):
    """Quality tier of a source."""
    TIER_1 = "tier_1"  # Official reports, regulatory filings
    TIER_2 = "tier_2"  # News outlets, industry publications
    TIER_3 = "tier_3"  # Blogs, forums, social media
    UNKNOWN = "unknown"


class EvidenceType(str, Enum):
    """Types of evidence extracted from documents."""
    QUOTE = "quote"
    SUMMARY = "summary"
    DATA_POINT = "data_point"
    INFERENCE = "inference"


class TaskType(str, Enum):
    """Types of research tasks."""
    INDUSTRY_REPORT = "industry_report"
    COMPANY_ANALYSIS = "company_analysis"
    TECHNICAL_RESEARCH = "technical_research"
    OPEN_QUESTION = "open_question"
    STRATEGY_DECISION = "strategy_decision"
    GENERAL = "general"


class DepthLevel(str, Enum):
    """Research depth levels."""
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class BudgetLevel(str, Enum):
    """Budget constraint levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"