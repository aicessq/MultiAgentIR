"""PostgreSQL database schema for research system.

Tables:
- research_runs: Run metadata and status
- config_snapshots: Frozen configuration snapshots
- research_artifacts: Artifact metadata and content
- sources: Search sources
- documents: Fetched documents
- evidence: Extracted evidence
- claims: Extracted claims
- analysis_revisions: Analysis revisions
- critique_revisions: Critique revisions
- report_revisions: Report revisions
- validation_results: Validation results
- model_call_audits: LLM call audit trail
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)

from app.infrastructure.db.base import Base


class ResearchRun(Base):
    """Research run metadata."""

    __tablename__ = "research_runs"

    run_id = Column(String(64), primary_key=True)
    thread_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=True)

    # Query and task
    query = Column(Text, nullable=False)
    task_type = Column(String(32), nullable=False)
    requested_strategy = Column(String(16), nullable=True)
    selected_strategy = Column(String(16), nullable=True)

    # Status
    status = Column(String(32), nullable=False, default="queued")
    current_phase = Column(String(32), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    deadline_at = Column(DateTime, nullable=True)
    cancel_requested = Column(Boolean, default=False)

    # Config
    config_snapshot_id = Column(String(64), nullable=False)
    config_hash = Column(String(16), nullable=False)

    # Budget
    budget_max_tokens = Column(Integer, default=300000)
    budget_max_cost_usd = Column(Float, default=20.0)
    usage_tokens = Column(Integer, default=0)
    usage_cost_usd = Column(Float, default=0.0)

    # Results
    plan_artifact_id = Column(String(64), nullable=True)
    authoritative_analysis_id = Column(String(64), nullable=True)
    authoritative_critique_id = Column(String(64), nullable=True)
    authoritative_report_id = Column(String(64), nullable=True)
    validation_result_id = Column(String(64), nullable=True)

    # Counters
    research_round = Column(Integer, default=0)
    repair_count = Column(Integer, default=0)

    # Terminal
    terminal_reason = Column(String(64), nullable=True)
    warnings = Column(JSON, default=list)
    errors = Column(JSON, default=list)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_research_runs_status", "status"),
        Index("ix_research_runs_user_status", "user_id", "status"),
    )


class ConfigSnapshot(Base):
    """Frozen configuration snapshot."""

    __tablename__ = "config_snapshots"

    config_snapshot_id = Column(String(64), primary_key=True)
    config_hash = Column(String(16), nullable=False)

    # Config data
    graph_config = Column(JSON, nullable=False)
    concurrency_config = Column(JSON, nullable=False)
    timeout_config = Column(JSON, nullable=False)
    budget_config = Column(JSON, nullable=False)
    quality_config = Column(JSON, nullable=False)
    model_catalog = Column(JSON, default=list)
    prompt_versions = Column(JSON, default=dict)
    topology_version = Column(String(16), default="v1")
    features = Column(JSON, default=dict)

    # Metadata
    source_version = Column(String(16), default="v1")
    created_at = Column(DateTime, default=datetime.utcnow)


class ResearchArtifact(Base):
    """Research artifact (plan, report, etc.)."""

    __tablename__ = "research_artifacts"

    artifact_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id"), nullable=False, index=True)
    artifact_type = Column(String(32), nullable=False)

    # Revision info
    revision_id = Column(String(64), nullable=False)
    revision_number = Column(Integer, nullable=False)
    supersedes_revision_id = Column(String(64), nullable=True)

    # Content
    created_by_node = Column(String(32), nullable=False)
    prompt_version = Column(String(16), nullable=False)
    model_ref = Column(String(64), nullable=False)

    # Storage
    storage_uri = Column(String(256), nullable=True)
    content_hash = Column(String(64), nullable=True)

    # Extra metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    extra_metadata = Column(JSON, default=dict)

    __table_args__ = (
        Index("ix_artifacts_run_type", "run_id", "artifact_type"),
        Index("ix_artifacts_revision", "run_id", "artifact_type", "revision_number"),
    )


class Source(Base):
    """Search source."""

    __tablename__ = "sources"

    source_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id"), nullable=False, index=True)

    url = Column(String(2048), nullable=False)
    canonical_url = Column(String(2048), nullable=True)
    title = Column(String(512), nullable=True)
    publisher = Column(String(256), nullable=True)
    domain = Column(String(256), nullable=True)
    source_tier = Column(String(16), default="unknown")
    reliability = Column(String(16), default="medium")

    publish_date = Column(DateTime, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    content_hash = Column(String(64), nullable=True)
    snippet = Column(Text, nullable=True)

    extra_metadata = Column(JSON, default=dict)


class Document(Base):
    """Fetched document."""

    __tablename__ = "documents"

    document_id = Column(String(64), primary_key=True)
    source_id = Column(String(64), ForeignKey("sources.source_id"), nullable=False)
    run_id = Column(String(64), ForeignKey("research_runs.run_id"), nullable=False, index=True)

    source_url = Column(String(2048), nullable=False)
    canonical_url = Column(String(2048), nullable=False)
    title = Column(String(512), nullable=True)
    content = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=False)

    extracted_at = Column(DateTime, default=datetime.utcnow)
    publish_date = Column(DateTime, nullable=True)
    word_count = Column(Integer, default=0)
    language = Column(String(16), default="unknown")

    extra_metadata = Column(JSON, default=dict)


class Evidence(Base):
    """Extracted evidence."""

    __tablename__ = "evidence"

    evidence_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id"), nullable=False, index=True)
    document_id = Column(String(64), ForeignKey("documents.document_id"), nullable=False)
    source_url = Column(String(2048), nullable=False)
    canonical_url = Column(String(2048), nullable=False)

    title = Column(String(512), nullable=True)
    passage_id = Column(String(64), nullable=False)
    quote = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=False)

    start_offset = Column(Integer, nullable=True)
    end_offset = Column(Integer, nullable=True)
    source_tier = Column(String(16), default="unknown")
    content_hash = Column(String(64), nullable=False)

    evidence_type = Column(String(16), default="quote")
    supports_claims = Column(JSON, default=list)
    contradicts_claims = Column(JSON, default=list)
    confidence = Column(Float, default=0.5)

    retrieved_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)


class Claim(Base):
    """Extracted claim."""

    __tablename__ = "claims"

    claim_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id"), nullable=False, index=True)
    analysis_revision_id = Column(String(64), nullable=True)

    statement = Column(Text, nullable=False)
    claim_type = Column(String(32), nullable=False)

    supporting_evidence_ids = Column(JSON, default=list)
    contradicting_evidence_ids = Column(JSON, default=list)

    confidence = Column(Float, default=0.5)
    uncertainty = Column(String(256), nullable=True)

    subject = Column(String(256), nullable=True)
    metric = Column(String(256), nullable=True)
    value = Column(String(256), nullable=True)
    unit = Column(String(64), nullable=True)
    period = Column(String(128), nullable=True)

    caveats = Column(JSON, default=list)


class AnalysisRevision(Base):
    """Analysis revision (extends ResearchArtifact)."""

    __tablename__ = "analysis_revisions"

    analysis_revision_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id"), nullable=False, index=True)

    revision_number = Column(Integer, nullable=False)
    supersedes_revision_id = Column(String(64), nullable=True)

    claims = Column(JSON, default=list)
    trends = Column(JSON, default=list)
    contradictions = Column(JSON, default=list)
    gaps = Column(JSON, default=list)
    confidence_level = Column(String(16), default="medium")

    created_by_node = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    prompt_version = Column(String(16), nullable=False)
    model_ref = Column(String(64), nullable=False)


class CritiqueRevision(Base):
    """Critique revision."""

    __tablename__ = "critique_revisions"

    critique_revision_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id"), nullable=False, index=True)
    analysis_revision_id = Column(String(64), nullable=True)

    revision_number = Column(Integer, nullable=False)
    supersedes_revision_id = Column(String(64), nullable=True)

    findings = Column(JSON, default=list)
    needs_more_research = Column(Boolean, default=False)
    overall_assessment = Column(Text, nullable=True)

    created_by_node = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    prompt_version = Column(String(16), nullable=False)
    model_ref = Column(String(64), nullable=False)


class ReportRevision(Base):
    """Report revision."""

    __tablename__ = "report_revisions"

    report_revision_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id"), nullable=False, index=True)

    revision_number = Column(Integer, nullable=False)
    supersedes_revision_id = Column(String(64), nullable=True)

    title = Column(String(512), nullable=False)
    as_of_date = Column(String(32), nullable=False)
    executive_summary = Column(Text, nullable=True)
    sections = Column(JSON, default=list)
    risk_register = Column(JSON, default=list)
    limitations = Column(JSON, default=list)

    created_by_node = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    prompt_version = Column(String(16), nullable=False)
    model_ref = Column(String(64), nullable=False)


class ValidationResult(Base):
    """Validation result."""

    __tablename__ = "validation_results"

    validation_result_id = Column(String(64), primary_key=True)
    report_revision_id = Column(String(64), ForeignKey("report_revisions.report_revision_id"), nullable=False)
    run_id = Column(String(64), ForeignKey("research_runs.run_id"), nullable=False, index=True)

    decision = Column(String(16), nullable=False)  # pass, repair, human_review, fail
    score = Column(Float, nullable=False)
    issues = Column(JSON, default=list)
    warnings = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)


class ModelCallAudit(Base):
    """LLM call audit trail."""

    __tablename__ = "model_call_audits"

    audit_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id"), nullable=False, index=True)
    thread_id = Column(String(64), nullable=True, index=True)
    checkpoint_id = Column(String(64), nullable=True)

    node = Column(String(32), nullable=False)
    namespace = Column(JSON, default=list)
    subtask_id = Column(String(64), nullable=True)
    revision_id = Column(String(64), nullable=True)

    provider = Column(String(32), nullable=False)
    model = Column(String(64), nullable=False)
    attempt = Column(Integer, default=1)
    purpose = Column(String(32), nullable=False)
    prompt_version = Column(String(16), nullable=False)

    latency_ms = Column(Float, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)

    success = Column(Boolean, nullable=False)
    error_category = Column(String(32), nullable=True)
    error_message = Column(Text, nullable=True)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_audits_run_node", "run_id", "node"),
    )
