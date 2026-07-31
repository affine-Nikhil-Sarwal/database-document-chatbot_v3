"""Maps reuse agent outputs into reconciliation inputs."""

from __future__ import annotations

from typing import Any


def _best_table_evidence(sql_result: dict[str, Any]) -> str:
    """Prefer non-empty query_results over insufficiency-flagged NL summaries."""
    query_results = str(sql_result.get("query_results", "")).strip()
    if query_results and not query_results.lower().startswith("an error occurred"):
        return query_results
    query_answer = str(sql_result.get("query_answer", "")).strip()
    inference = str(sql_result.get("inference", "")).strip()
    insufficient_markers = (
        "do not have enough",
        "insufficient",
        "no rows",
        "cannot answer",
    )
    lower = query_answer.lower()
    if any(m in lower for m in insufficient_markers) and query_results:
        return query_results
    if query_answer:
        return query_answer
    return inference


def adapt_eryl_output(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    return {
        "llm_answer": raw.get("llm_answer", ""),
        "analysis_type": raw.get("analysis_type"),
        "updated_question": raw.get("updated_question"),
        "question": raw.get("question"),
    }


def adapt_quin_output(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    enriched = dict(raw)
    enriched["query_results"] = _best_table_evidence(raw)
    return enriched


def to_reconciliation_inputs(
    document_result: dict[str, Any] | None,
    sql_result: dict[str, Any] | None,
    routing_decision: dict[str, Any],
    session_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "document_result": adapt_eryl_output(document_result),
        "sql_result": adapt_quin_output(sql_result),
        "routing_decision": routing_decision,
        "session_context": session_context,
    }
