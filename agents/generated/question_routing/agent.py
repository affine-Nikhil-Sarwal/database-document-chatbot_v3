"""Question routing — classifies document vs SQL vs both paths."""

from __future__ import annotations

import json
import re
from typing import Any

from config.settings import get_settings
from integrations import azure_openai
from workflow.exceptions import PermissionDeniedError


def _heuristic_route(user_question: str, session_context: dict[str, Any]) -> dict[str, Any]:
    q = user_question.lower()
    sql_keywords = (
        "sales",
        "revenue",
        "table",
        "sql",
        "database",
        "count",
        "sum",
        "average",
        "total",
        "inventory",
        "rows",
    )
    doc_keywords = ("policy", "document", "email", "guideline", "procedure", "memo")
    run_sql = any(word in q for word in sql_keywords)
    run_document = any(word in q for word in doc_keywords)
    if run_sql and run_document:
        route = "both"
    elif run_sql:
        route = "sql_only"
    elif run_document:
        route = "document_only"
    else:
        route = "both"
    return _build_decision(user_question, route, session_context, "Heuristic dry-run classification")


def _build_decision(
    user_question: str,
    route: str,
    session_context: dict[str, Any],
    rationale: str,
) -> dict[str, Any]:
    run_document = route in {"document_only", "both"}
    run_sql = route in {"sql_only", "both"}

    if "allowed_document_ids" in session_context and not session_context.get("allowed_document_ids"):
        run_document = False
    if "allowed_tables" in session_context and not session_context.get("allowed_tables"):
        run_sql = False

    if not run_document and not run_sql:
        return {
            "routing_decision": {
                "run_document": False,
                "run_sql": False,
                "initial_question": user_question,
                "analysis_type": "Both-independent",
                "rationale": rationale,
                "refusal_reason": "permission_denied",
            }
        }

    analysis_map = {
        "document_only": "Semantic-based",
        "sql_only": "SQL-based",
        "both": "Both-independent",
    }
    return {
        "routing_decision": {
            "run_document": run_document,
            "run_sql": run_sql,
            "initial_question": user_question,
            "analysis_type": analysis_map[route],
            "rationale": rationale,
            "refusal_reason": None,
        }
    }


def _llm_route(user_question: str, session_context: dict[str, Any]) -> dict[str, Any]:
    system = (
        "Classify the analyst question into exactly one route: document_only, sql_only, or both. "
        "Respond with JSON only: {\"route\": \"document_only|sql_only|both\", \"rationale\": \"...\"}."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_question},
    ]
    try:
        raw = azure_openai.chat_completion(messages, settings=get_settings())
        cleaned = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(cleaned)
        route = str(parsed.get("route", "both")).strip()
        if route not in {"document_only", "sql_only", "both"}:
            route = "both"
        rationale = str(parsed.get("rationale", "LLM classification"))
        return _build_decision(user_question, route, session_context, rationale)
    except Exception:
        return _build_decision(
            user_question,
            "both",
            session_context,
            "Classifier failure — defaulting to both paths when permitted",
        )


def execute(payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    user_question = str(payload.get("user_question", "")).strip()
    session_context = payload.get("session_context") or {}

    if session_context.get("permission_denied") is True:
        raise PermissionDeniedError("Access denied for this analyst session")

    if dry_run:
        return _heuristic_route(user_question, session_context)
    return _llm_route(user_question, session_context)


run = execute
