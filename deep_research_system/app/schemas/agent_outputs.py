from __future__ import annotations

from pydantic import BaseModel, Field


# ── Planner ──

class SubQuestion(BaseModel):
    id: str
    question: str
    priority: int = 1
    search_queries: list[str] = Field(default_factory=list)
    expected_evidence_type: str = "market_data"
    # P1-1 fields
    scope: str = ""
    hypothesis: str = ""
    assumptions: list[str] = Field(default_factory=list)
    counter_evidence_needed: list[str] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    research_goal: str = ""
    task_type: str = "general"
    sub_questions: list[SubQuestion] = Field(default_factory=list)
    suggested_topology: str = "hierarchical"
    hypotheses: list[str] = Field(default_factory=list)


# ── Searcher ──

class SearchSource(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    source_type: str = "unknown"
    publish_date: str | None = None
    credibility_score: float = 0.5


class SearcherOutput(BaseModel):
    sub_question_id: str = ""
    queries_used: list[str] = Field(default_factory=list)
    sources: list[SearchSource] = Field(default_factory=list)
    insufficient_evidence: bool = False
    insufficient_evidence_reason: str = ""


# ── Evidence ──

class Evidence(BaseModel):
    evidence_id: str = ""
    claim: str = ""
    source_url: str = ""
    quote_or_summary: str = ""
    confidence: float = 0.5
    supports: str = "supports"  # "supports" | "contradicts" | "neutral"
    relevance_score: float = 0.5
    credibility_score: float = 0.5
    freshness_score: float = 0.5
    limitations: list[str] = Field(default_factory=list)


# ── Reader ──

class ReaderOutput(BaseModel):
    sub_question_id: str = ""
    key_findings: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    atomic_facts: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    insufficient_evidence: bool = False
    insufficient_evidence_reason: str = ""


# ── Analyzer ──

class AnalyzerClaim(BaseModel):
    claim_id: str = ""
    claim_text: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    caveats: list[str] = Field(default_factory=list)
    supporting_count: int = 0
    contradicting_count: int = 0


class AnalyzerOutput(BaseModel):
    claims: list[AnalyzerClaim] = Field(default_factory=list)
    trends: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    confidence_level: str = "medium"
    insufficient_evidence: bool = False
    insufficient_evidence_reason: str = ""


# ── Critic ──

class CriticFinding(BaseModel):
    severity: str = "medium"  # "critical" | "high" | "medium" | "low"
    target_type: str = "claim"  # "claim" | "section" | "overall"
    target_id: str = ""
    issue_description: str = ""
    fix_instruction: str = ""
    suggested_search_queries: list[str] = Field(default_factory=list)


class CriticOutput(BaseModel):
    findings: list[CriticFinding] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    logic_flaws: list[str] = Field(default_factory=list)
    needs_more_research: bool = False
    overall_assessment: str = ""  # "pass" | "needs_revision" | "needs_research"


# ── Writer ──

class ReportSection(BaseModel):
    heading: str = ""
    content: str = ""
    citations: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class WriterOutput(BaseModel):
    title: str = ""
    executive_summary: str = ""
    sections: list[ReportSection] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    appendix: str = ""


# ── Debate ──

class DebateBranchOutput(BaseModel):
    branch: str = ""
    hypothesis: str = ""
    position: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    arguments: list[str] = Field(default_factory=list)
    supporting_claims: list[str] = Field(default_factory=list)
    contradicting_claims: list[str] = Field(default_factory=list)


class SynthesizerOutput(BaseModel):
    key_disagreements: list[str] = Field(default_factory=list)
    conditional_conclusions: list[str] = Field(default_factory=list)
    consensus_points: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


# ── Source Registry ──

class SourceRegistry(BaseModel):
    sources: dict[str, SearchSource] = Field(default_factory=dict)

    def register(self, source: SearchSource) -> None:
        if source.url:
            self.sources[source.url] = source

    def is_registered(self, url: str) -> bool:
        return url in self.sources

    def get_all_urls(self) -> list[str]:
        return list(self.sources.keys())
