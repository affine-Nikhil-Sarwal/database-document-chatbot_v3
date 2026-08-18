"""Workflow graph orchestration."""

from __future__ import annotations

import json
import os
from importlib import import_module
from pathlib import Path
from typing import Any, Callable

from config.autogen_azure_compat import apply_autogen_azure_compat
from config.settings import ConfigurationError, get_settings

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRY_RUN = False

_EARLY_REFUSAL_REASONS = frozenset({"permission_denied", "unsupported_question_type"})


def set_dry_run(enabled: bool) -> None:
    global _DRY_RUN
    _DRY_RUN = enabled
    if enabled:
        os.environ["WORKFLOW_DRY_RUN"] = "1"
    else:
        os.environ.pop("WORKFLOW_DRY_RUN", None)


def is_dry_run() -> bool:
    return _DRY_RUN or os.environ.get("WORKFLOW_DRY_RUN") == "1"


def _discover_agents() -> dict[str, dict[str, Any]]:
    agents: dict[str, dict[str, Any]] = {}
    for root_name in ("reused", "generated"):
        base = _REPO_ROOT / "agents" / root_name
        if not base.is_dir():
            continue
        for agent_dir in base.iterdir():
            if not agent_dir.is_dir():
                continue
            contract_path = agent_dir / "contract.json"
            if not contract_path.is_file():
                continue
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            node_id = contract.get("node_id") or agent_dir.name.replace("_", "-")
            module_path = contract.get("module") or f"agents.{root_name}.{agent_dir.name}.agent"
            entrypoint = contract.get("entrypoint", "run")
            agents[node_id] = {
                "module": module_path,
                "entrypoint": entrypoint,
                "contract": contract,
                "kind": root_name,
            }
    agents["sql-query-chain"] = {
        "module": "agents.reused.quin_sql_agent_chain.agent",
        "entrypoint": "QuinChainRunner.run",
        "kind": "reuse",
    }
    return agents


def _load_runner(node_id: str) -> Callable[..., dict[str, Any]]:
    catalog = _discover_agents()
    if node_id not in catalog:
        raise KeyError(f"Unknown node_id: {node_id}")
    spec = catalog[node_id]
    module = import_module(spec["module"])
    if node_id == "sql-query-chain":
        return lambda payload, **kw: _run_quin(payload, dry_run=kw.get("dry_run", False))
    fn = getattr(module, spec["entrypoint"])
    return fn


def _run_build(node_id: str, payload: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    runner = _load_runner(node_id)
    return runner(payload, dry_run=dry_run)


def _run_quin(payload: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    routing = payload.get("routing_decision") or payload
    from agents.adapters.routing_to_reuse import invoke_quin

    if dry_run or not routing.get("run_sql"):
        return {"skipped": True, "sql_result": None}
    result = invoke_quin(routing)
    return {"sql_result": result}


def _run_sql_retrieval(
    routing_decision: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any] | None:
    if dry_run or not routing_decision.get("run_sql"):
        return None
    return _run_quin({"routing_decision": routing_decision}, dry_run=False).get("sql_result")


def _prepare_live_run() -> None:
    settings = get_settings()
    settings.export_to_environ()
    apply_autogen_azure_compat()


def _deliver_refusal(
    routing_decision: dict[str, Any],
    session_context: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    gate_out = _run_build(
        "evidence-sufficiency-gate",
        {
            "draft_answer": "",
            "normalized_cross_source_evidence_set": {"items": [], "coverage": "none"},
            "evidence_plus_conflict_annotations": {"evidence_set": {}, "conflicts": []},
            "routing_decision": routing_decision,
            "session_context": session_context,
        },
        dry_run=dry_run,
    )
    delivery_out = _run_build(
        "response-delivery",
        {"approved_answer_or_refusal_payload": gate_out["approved_answer_or_refusal_payload"]},
        dry_run=dry_run,
    )
    return {
        "natural_language_answers": delivery_out["natural_language_answers"],
        "routing_decision": routing_decision,
        "approved_answer_or_refusal_payload": gate_out["approved_answer_or_refusal_payload"],
    }


def run_full_pipeline(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    dry_run = is_dry_run()

    intake_out = _run_build("user-question-intake", payload, dry_run=dry_run)
    user_question = intake_out["user_question"]
    session_context = intake_out["session_context"]

    routing_out = _run_build(
        "question-routing",
        {"user_question": user_question, "session_context": session_context},
        dry_run=dry_run,
    )
    routing_decision = routing_out["routing_decision"]

    if routing_decision.get("refusal_reason") in _EARLY_REFUSAL_REASONS:
        return _deliver_refusal(routing_decision, session_context, dry_run=dry_run)

    if not dry_run:
        _prepare_live_run()

    sql_result = _run_sql_retrieval(routing_decision, dry_run=dry_run)

    from agents.adapters.reuse_to_reconciliation import to_reconciliation_inputs

    recon_in = to_reconciliation_inputs(
        None, sql_result, routing_decision, session_context
    )
    recon_out = _run_build("evidence-reconciliation", recon_in, dry_run=dry_run)

    conflict_out = _run_build(
        "conflict-detection",
        {"normalized_cross_source_evidence_set": recon_out["normalized_cross_source_evidence_set"]},
        dry_run=dry_run,
    )

    consolidation_out = _run_build(
        "answer-consolidation",
        {
            "evidence_plus_conflict_annotations": conflict_out["evidence_plus_conflict_annotations"],
            "user_question": user_question,
        },
        dry_run=dry_run,
    )

    from agents.adapters.consolidation_to_gate import bundle_for_gate

    gate_in = bundle_for_gate(
        consolidation_out,
        conflict_out["evidence_plus_conflict_annotations"],
        routing_decision,
        session_context,
    )
    gate_out = _run_build("evidence-sufficiency-gate", gate_in, dry_run=dry_run)

    delivery_out = _run_build(
        "response-delivery",
        {"approved_answer_or_refusal_payload": gate_out["approved_answer_or_refusal_payload"]},
        dry_run=dry_run,
    )

    return {
        "natural_language_answers": delivery_out["natural_language_answers"],
        "routing_decision": routing_decision,
        "normalized_cross_source_evidence_set": recon_out["normalized_cross_source_evidence_set"],
        "approved_answer_or_refusal_payload": gate_out["approved_answer_or_refusal_payload"],
        "evidence_plus_conflict_annotations": conflict_out["evidence_plus_conflict_annotations"],
    }


def run_workflow_from_node(node_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run the workflow graph starting at ``node_id`` and return the terminal output."""
    payload = dict(payload or {})
    dry_run = is_dry_run()

    if node_id == "user-question-intake":
        return run_full_pipeline(payload)

    if node_id in _discover_agents():
        if not dry_run and node_id == "sql-query-chain":
            _prepare_live_run()
        runner = _load_runner(node_id)
        if node_id == "sql-query-chain":
            return runner(payload, dry_run=dry_run)
        return runner(payload, dry_run=dry_run)

    raise KeyError(f"Unsupported start node: {node_id}")
