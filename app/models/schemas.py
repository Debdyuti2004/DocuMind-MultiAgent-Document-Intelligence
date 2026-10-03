"""Pydantic schemas and data exchange models for DocuMind."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class DocumentMetadata(BaseModel):
    """Metadata representing an uploaded and processed document."""
    document_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    num_pages: int
    num_chunks: int = 0
    num_tables: int = 0
    title: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    document_type: str = "General"
    domain: str = "General"
    classification_confidence: float = 0.0
    storage_filename: Optional[str] = None


class DocumentChunk(BaseModel):
    """Structured text chunk retaining strict lineage and citation metadata."""
    chunk_id: str
    document_id: str
    filename: str
    page: int
    section: str = "Main"
    text: str
    chunk_index: int = 0
    token_count: int = 0


class ExtractedTable(BaseModel):
    """Structured tabular data extracted from a document page."""
    table_id: str
    document_id: str
    filename: str
    page: int
    title: Optional[str] = "Table"
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)
    structured_data: Optional[List[Dict[str, Any]]] = None


class AgentActionLog(BaseModel):
    """Safe, user-facing agent activity log entry without raw internal prompt leakage."""
    agent_name: str
    action: str
    detail: str
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    status: str = "completed"  # running, completed, warning, error
    execution_time_ms: Optional[float] = None


class ClaimVerification(BaseModel):
    """Verification output evaluating factual claims against retrieved evidence."""
    claim: str
    supported: bool
    confidence: float
    source_pages: List[int] = Field(default_factory=list)
    source_filenames: List[str] = Field(default_factory=list)
    evidence_text: Optional[str] = None
    reasoning: Optional[str] = None


class SourceCitation(BaseModel):
    """Explicit citation pointing directly to source document and page number."""
    document_name: str
    document_id: str
    page: int
    section: str = "Content"
    snippet: str


class ComparisonMetric(BaseModel):
    """Side-by-side metric comparison between two documents or periods."""
    metric: str
    doc1_name: str
    doc1_value: Optional[float] = None
    doc1_text: str = "N/A"
    doc2_name: str
    doc2_value: Optional[float] = None
    doc2_text: str = "N/A"
    change_absolute: Optional[float] = None
    change_percent: Optional[float] = None
    interpretation: str = ""


class DocumentSummary(BaseModel):
    """Comprehensive automatic summary generated upon document ingestion."""
    document_id: str
    filename: str
    document_type: str
    executive_summary: str
    key_facts: List[str] = Field(default_factory=list)
    key_entities: Dict[str, List[str]] = Field(default_factory=dict)
    key_topics: List[str] = Field(default_factory=list)
    important_findings: List[str] = Field(default_factory=list)
    potential_risks: List[str] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)
    summary_version: int = 2


class QueryRequest(BaseModel):
    """User query request payload."""
    query: str = Field(min_length=1, max_length=4000)
    document_ids: Optional[List[str]] = Field(default=None, max_length=50)
    enable_research: bool = False
    enable_verification: bool = True
    session_id: Optional[str] = Field(default=None, min_length=1, max_length=120)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Query cannot be empty.")
        return value


class QueryResponse(BaseModel):
    """Structured response synthesized by DocuMind agent network."""
    query: str
    answer: str
    document_ids: List[str]
    intent: str
    plan: List[str]
    explicit_facts: List[str] = Field(default_factory=list)
    derived_calculations: List[Dict[str, Any]] = Field(default_factory=list)
    interpretations: List[str] = Field(default_factory=list)
    external_research: List[Dict[str, Any]] = Field(default_factory=list)
    verified_claims: List[ClaimVerification] = Field(default_factory=list)
    sources: List[SourceCitation] = Field(default_factory=list)
    confidence: str = "High"  # High, Medium, Low
    confidence_score: float = 0.95
    execution_time_seconds: float = 0.0
    agent_logs: List[AgentActionLog] = Field(default_factory=list)


class CompareRequest(BaseModel):
    """Request payload to compare multiple documents."""
    doc1_id: str = Field(min_length=1, max_length=120)
    doc2_id: str = Field(min_length=1, max_length=120)
    focus_areas: Optional[List[str]] = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def require_distinct_documents(self):
        if self.doc1_id == self.doc2_id:
            raise ValueError("Choose two different documents to compare.")
        return self


class CompareResponse(BaseModel):
    """Structured comparison response."""
    doc1_id: str
    doc1_name: str
    doc2_id: str
    doc2_name: str
    comparison_summary: str
    metrics: List[ComparisonMetric] = Field(default_factory=list)
    key_differences: List[str] = Field(default_factory=list)
    citations: List[SourceCitation] = Field(default_factory=list)
    agent_logs: List[AgentActionLog] = Field(default_factory=list)
