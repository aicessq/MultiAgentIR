from __future__ import annotations

from pydantic import BaseModel, Field


class SubQuestion(BaseModel):
    id: str
    question: str
    priority: int = 1
    search_queries: list[str] = Field(default_factory=list)
    expected_evidence_type: str = "market_data"


class PlannerOutput(BaseModel):
    research_goal: str = ""
    task_type: str = "general"
    sub_questions: list[SubQuestion] = Field(default_factory=list)
    suggested_topology: str = "hierarchical"


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


class Evidence(BaseModel):
    claim: str = ""
    source_url: str = ""
    quote_or_summary: str = ""
    confidence: float = 0.5


class ReaderOutput(BaseModel):
    sub_question_id: str = ""
    key_findings: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class ReportSection(BaseModel):
    heading: str = ""
    content: str = ""
    citations: list[str] = Field(default_factory=list)


class WriterOutput(BaseModel):
    title: str = ""
    executive_summary: str = ""
    sections: list[ReportSection] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    appendix: str = ""


class CriticOutput(BaseModel):
    issues: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    logic_flaws: list[str] = Field(default_factory=list)
    needs_more_research: bool = False


class DebateBranchOutput(BaseModel):
    branch: str = ""
    position: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    arguments: list[str] = Field(default_factory=list)


class SynthesizerOutput(BaseModel):
    key_disagreements: list[str] = Field(default_factory=list)
    conditional_conclusions: list[str] = Field(default_factory=list)
    consensus_points: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
