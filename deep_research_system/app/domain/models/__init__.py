"""Core domain models for the research system.

These models are the building blocks for all research artifacts.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import ArtifactType, ClaimType, EvidenceType, SourceTier


class RevisionMeta(BaseModel):
    """Metadata for an immutable revision."""

    revision_id: str
    revision_number: int
    supersedes_revision_id: str | None = None
    created_by_node: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    prompt_version: str
    model_ref: str


class Source(BaseModel):
    """A source from search results."""

    source_id: str
    url: str
    canonical_url: str | None = None
    title: str | None = None
    publisher: str | None = None
    domain: str | None = None
    source_tier: SourceTier = SourceTier.UNKNOWN
    reliability: str = "medium"
    publish_date: datetime | None = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    content_hash: str | None = None
    snippet: str | None = None


class Document(BaseModel):
    """A fetched document with extracted content."""

    document_id: str
    source_id: str
    source_url: str
    canonical_url: str
    title: str | None = None
    content: str
    content_hash: str
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    publish_date: datetime | None = None
    word_count: int = 0
    language: str = "unknown"
    metadata: dict = Field(default_factory=dict)


class Passage(BaseModel):
    """A specific passage within a document."""

    passage_id: str
    document_id: str
    start_offset: int | None = None
    end_offset: int | None = None
    text: str
    context_before: str | None = None
    context_after: str | None = None


class Evidence(BaseModel):
    """Evidence extracted from a document passage."""

    evidence_id: str
    run_id: str
    document_id: str
    source_url: str
    canonical_url: str
    title: str | None = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: datetime | None = None
    passage_id: str
    quote: str
    normalized_text: str
    start_offset: int | None = None
    end_offset: int | None = None
    source_tier: SourceTier = SourceTier.UNKNOWN
    content_hash: str
    evidence_type: EvidenceType = EvidenceType.QUOTE
    supports_claims: list[str] = Field(default_factory=list)
    contradicts_claims: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class Claim(BaseModel):
    """A claim extracted from analysis."""

    claim_id: str
    statement: str
    claim_type: ClaimType = ClaimType.FACTUAL
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    uncertainty: str | None = None
    subject: str | None = None
    metric: str | None = None
    value: str | None = None
    unit: str | None = None
    period: str | None = None
    caveats: list[str] = Field(default_factory=list)


class Artifact(BaseModel):
    """Base class for all research artifacts."""

    artifact_id: str
    run_id: str
    artifact_type: ArtifactType
    revision: RevisionMeta
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlanArtifact(Artifact):
    """Research plan artifact."""

    artifact_type: ArtifactType = ArtifactType.PLAN
    research_goal: str
    sub_questions: list[dict] = Field(default_factory=list)
    suggested_strategy: str = "hierarchical"
    hypotheses: list[str] = Field(default_factory=list)


class AnalysisRevision(Artifact):
    """Immutable analysis revision."""

    artifact_type: ArtifactType = ArtifactType.ANALYSIS_REVISION
    claims: list[Claim] = Field(default_factory=list)
    trends: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    confidence_level: str = "medium"


class CritiqueRevision(Artifact):
    """Immutable critique revision."""

    artifact_type: ArtifactType = ArtifactType.CRITIQUE_REVISION
    findings: list[dict] = Field(default_factory=list)
    needs_more_research: bool = False
    overall_assessment: str = ""


class ReportRevision(Artifact):
    """Immutable report revision."""

    artifact_type: ArtifactType = ArtifactType.REPORT_REVISION
    title: str
    as_of_date: str
    executive_summary: str
    sections: list[dict] = Field(default_factory=list)
    risk_register: list[dict] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ValidationResult(Artifact):
    """Validation result artifact."""

    artifact_type: ArtifactType = ArtifactType.VALIDATION_RESULT
    decision: str = "pass"
    score: float = 100.0
    issues: list[dict] = Field(default_factory=list)
    warnings: list[dict] = Field(default_factory=list)