"""Maps routing decisions to reuse agent invocations."""

from __future__ import annotations

from typing import Any


def build_eryl_inputs(routing_decision: dict[str, Any]) -> dict[str, Any] | None:
    if not routing_decision.get("run_document"):
        return None
    return {
        "initial_question": routing_decision.get("initial_question", ""),
        "analysis_type": routing_decision.get("analysis_type", "Semantic-based"),
    }


def build_quin_inputs(routing_decision: dict[str, Any]) -> dict[str, Any] | None:
    if not routing_decision.get("run_sql"):
        return None
    return {
        "initial_question": routing_decision.get("initial_question", ""),
        "analysis_type": routing_decision.get("analysis_type", "SQL-based"),
    }


def invoke_eryl(routing_decision: dict[str, Any]) -> dict[str, Any] | None:
    inputs = build_eryl_inputs(routing_decision)
    if inputs is None:
        return None
    from agents.reused.eryl_semantic_rag_agent_chain.agent import ErylChainRunner

    return ErylChainRunner().run(**inputs)


def invoke_quin(routing_decision: dict[str, Any]) -> dict[str, Any] | None:
    inputs = build_quin_inputs(routing_decision)
    if inputs is None:
        return None
    from agents.reused.quin_sql_agent_chain.agent import QuinChainRunner

    return QuinChainRunner().run(**inputs)
