"""Shared Pydantic models for workflow I/O."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SessionContext(BaseModel):
    user_id: str = "anonymous"
    request_id: str | None = None
    roles: list[str] = Field(default_factory=list)
    allowed_document_ids: list[str] = Field(default_factory=list)
    allowed_tables: list[str] = Field(default_factory=list)
    permission_denied: bool = False
    document_references: list[str] = Field(default_factory=list)
    sql_scope: dict[str, Any] = Field(default_factory=dict)


class RoutingDecision(BaseModel):
    run_document: bool
    run_sql: bool
    initial_question: str
    analysis_type: Literal[
        "Semantic-based",
        "SQL-based",
        "Both-independent",
        "Both-dependent",
    ]
    rationale: str = ""
    refusal_reason: str | None = None


class EvidenceItem(BaseModel):
    citation_id: str
    source_type: Literal["document", "sql"]
    text: str
    provenance: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    status: Literal["empty", "ok", "failed", "insufficient"] = "ok"


class NormalizedEvidenceSet(BaseModel):
    items: list[EvidenceItem] = Field(default_factory=list)
    coverage: Literal["none", "partial", "full"] = "none"
    document_status: str = "empty"
    sql_status: str = "empty"


class ConflictAnnotation(BaseModel):
    severity: Literal["low", "medium", "high"]
    summary: str
    doc_claim: str
    sql_claim: str
    citation_ids: list[str] = Field(default_factory=list)
    show_both_and_flag: bool = True


class EvidenceWithConflicts(BaseModel):
    evidence_set: NormalizedEvidenceSet
    conflicts: list[ConflictAnnotation] = Field(default_factory=list)
    warning: str | None = None


class GateDecision(BaseModel):
    status: Literal["approved", "refused"]
    message: str
    citations: list[str] = Field(default_factory=list)
    conflicts: list[ConflictAnnotation] = Field(default_factory=list)
    refusal_reason: str | None = None


class CsvAttachment(BaseModel):
    filename: str
    media_type: str = "text/csv; charset=utf-8"
    content_base64: str
    row_count: int = 0
    column_names: list[str] = Field(default_factory=list)
    table_count: int = 1


class WorkflowResult(BaseModel):
    natural_language_answers: str
    csv_attachment: CsvAttachment | None = None
    gate_decision: GateDecision | None = None
    routing_decision: RoutingDecision | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
