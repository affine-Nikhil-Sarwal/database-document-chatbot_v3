"""Question routing — classifies SQL vs unsupported (non-database) questions."""

from __future__ import annotations

import json
import re
from typing import Any

from config.settings import get_settings
from integrations import azure_openai
from workflow.exceptions import PermissionDeniedError

SQL_KEYWORDS = (
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

DOC_KEYWORDS = ("policy", "document", "email", "guideline", "procedure", "memo")


def _heuristic_route(user_question: str, session_context: dict[str, Any]) -> dict[str, Any]:
    q = user_question.lower()
    run_sql = any(word in q for word in SQL_KEYWORDS)
    run_document = any(word in q for word in DOC_KEYWORDS)
    if run_sql and not run_document:
        route = "sql_only"
    else:
        route = "unsupported"
    return _build_decision(user_question, route, session_context, "Heuristic dry-run classification")


def _build_decision(
    user_question: str,
    route: str,
    session_context: dict[str, Any],
    rationale: str,
) -> dict[str, Any]:
    if route == "unsupported":
        return {
            "routing_decision": {
                "run_document": False,
                "run_sql": False,
                "initial_question": user_question,
                "analysis_type": "Semantic-based",
                "rationale": rationale,
                "refusal_reason": "unsupported_question_type",
            }
        }

    run_sql = route == "sql_only"
    if "allowed_tables" in session_context and not session_context.get("allowed_tables"):
        run_sql = False

    if not run_sql:
        return {
            "routing_decision": {
                "run_document": False,
                "run_sql": False,
                "initial_question": user_question,
                "analysis_type": "SQL-based",
                "rationale": rationale,
                "refusal_reason": "permission_denied",
            }
        }

    return {
        "routing_decision": {
            "run_document": False,
            "run_sql": True,
            "initial_question": user_question,
            "analysis_type": "SQL-based",
            "rationale": rationale,
            "refusal_reason": None,
        }
    }


def _llm_route(user_question: str, session_context: dict[str, Any]) -> dict[str, Any]:
    system = (
        "Classify the analyst question into exactly one route: sql_only or unsupported. "
        "Use sql_only only when the question can be answered from structured database tables "
        "without reading documents, policies, emails, or other unstructured sources. "
        "Use unsupported for document-only questions, hybrid document+database questions, "
        "or any question that is not clearly a structured/database query. "
        'Respond with JSON only: {"route": "sql_only|unsupported", "rationale": "..."}.'
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_question},
    ]
    try:
        raw = azure_openai.chat_completion(messages, settings=get_settings())
        cleaned = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(cleaned)
        route = str(parsed.get("route", "unsupported")).strip()
        if route not in {"sql_only", "unsupported"}:
            route = "unsupported"
        rationale = str(parsed.get("rationale", "LLM classification"))
        return _build_decision(user_question, route, session_context, rationale)
    except Exception:
        return _build_decision(
            user_question,
            "unsupported",
            session_context,
            "Classifier failure — question type could not be confirmed as SQL-only",
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
