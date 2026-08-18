"""Workflow integration, wiring, and HTTP surface tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent


def test_agent_discovery():
    from orchestrator.graph import _discover_agents

    agents = _discover_agents()
    expected = {
        "user-question-intake",
        "question-routing",
        "sql-query-chain",
        "evidence-reconciliation",
        "conflict-detection",
        "answer-consolidation",
        "evidence-sufficiency-gate",
        "response-delivery",
    }
    assert expected.issubset(set(agents.keys()))


def test_manifest_matches_graph():
    manifest = json.loads((ROOT / "workflow_manifest.json").read_text(encoding="utf-8"))
    workflow = json.loads((ROOT / "workflow.json").read_text(encoding="utf-8"))
    graph_nodes = {n["id"] for n in workflow["plan"]["graph"]["nodes"]}
    manifest_nodes = {n["id"] for n in manifest["nodes"]}
    assert manifest_nodes == graph_nodes
    assert len(manifest["runtime_order"]) == len(graph_nodes)


def test_configuration_error_on_missing_openai(monkeypatch):
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_BASE", raising=False)
    from config.settings import ConfigurationError, Settings

    settings = Settings()
    with pytest.raises(ConfigurationError):
        settings.require_azure_openai()


def test_routing_heuristic_dry_run():
    from agents.generated.question_routing.agent import execute

    out = execute(
        {
            "user_question": "What is the return policy in the email archive?",
            "session_context": {"allowed_document_ids": ["*"], "allowed_tables": ["*"]},
        },
        dry_run=True,
    )
    decision = out["routing_decision"]
    assert decision["run_document"] is False
    assert decision["run_sql"] is False
    assert decision["refusal_reason"] == "unsupported_question_type"


def test_routing_heuristic_sql_only():
    from agents.generated.question_routing.agent import execute

    out = execute(
        {
            "user_question": "What were total sales last quarter?",
            "session_context": {"allowed_tables": ["*"]},
        },
        dry_run=True,
    )
    decision = out["routing_decision"]
    assert decision["run_sql"] is True
    assert decision["run_document"] is False
    assert decision["analysis_type"] == "SQL-based"
    assert decision["refusal_reason"] is None


def test_reconciliation_with_fixture_evidence():
    from agents.generated.evidence_reconciliation.agent import execute

    out = execute(
        {
            "document_result": {"llm_answer": "Policy allows 30-day returns [Doc excerpt].", "question": "q"},
            "sql_result": {
                "query": "SELECT SUM(sales) FROM Mars_Sales_Data",
                "query_answer": "Total sales were 1.2M",
                "query_results": '[{"sales": 1200000}]',
            },
            "routing_decision": {"run_document": True, "run_sql": True},
            "session_context": {"allowed_document_ids": ["*"], "allowed_tables": ["*"]},
        },
        dry_run=True,
    )
    evidence = out["normalized_cross_source_evidence_set"]
    assert len(evidence["items"]) == 2
    assert evidence["coverage"] in {"full", "partial"}


def test_conflict_detection_numeric_disagreement():
    from agents.generated.conflict_detection.agent import execute

    evidence_set = {
        "items": [
            {"citation_id": "Doc-1", "source_type": "document", "text": "Revenue was 100 units", "status": "ok"},
            {"citation_id": "SQL-1", "source_type": "sql", "text": "Revenue was 500 units", "status": "ok"},
        ],
        "coverage": "full",
    }
    out = execute({"normalized_cross_source_evidence_set": evidence_set}, dry_run=True)
    conflicts = out["evidence_plus_conflict_annotations"]["conflicts"]
    assert len(conflicts) >= 1
    assert conflicts[0]["show_both_and_flag"] is True


def test_gate_refuses_empty_evidence():
    from agents.generated.evidence_sufficiency_gate.agent import execute

    out = execute(
        {
            "draft_answer": "",
            "normalized_cross_source_evidence_set": {"items": [], "coverage": "none"},
            "evidence_plus_conflict_annotations": {"evidence_set": {}, "conflicts": []},
            "routing_decision": {"run_document": True, "run_sql": True},
            "session_context": {},
        },
        dry_run=True,
    )
    assert out["approved_answer_or_refusal_payload"]["status"] == "refused"


def test_gate_approves_cited_draft():
    from agents.generated.evidence_sufficiency_gate.agent import execute

    out = execute(
        {
            "draft_answer": "Total sales were 1.2M per [SQL-1].",
            "normalized_cross_source_evidence_set": {
                "items": [
                    {"citation_id": "SQL-1", "source_type": "sql", "text": "1.2M", "status": "ok"},
                ],
                "coverage": "full",
                "document_status": "empty",
                "sql_status": "ok",
            },
            "evidence_plus_conflict_annotations": {"evidence_set": {}, "conflicts": []},
            "routing_decision": {"run_sql": True, "run_document": False},
            "session_context": {},
        },
        dry_run=True,
    )
    assert out["approved_answer_or_refusal_payload"]["status"] == "approved"


def test_delivery_formats_refusal():
    from agents.generated.response_delivery.agent import execute

    out = execute(
        {
            "approved_answer_or_refusal_payload": {
                "status": "refused",
                "message": "Insufficient evidence.",
                "citations": [],
                "conflicts": [],
                "refusal_reason": "insufficient_evidence",
            }
        },
        dry_run=True,
    )
    assert "Unable to provide" in out["natural_language_answers"]


def test_dry_run_cli():
    proc = subprocess.run(
        [sys.executable, "main.py", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_full_pipeline_dry_run():
    from orchestrator.graph import run_workflow_from_node, set_dry_run

    set_dry_run(True)
    result = run_workflow_from_node(
        "user-question-intake",
        {
            "user_question": "Compare policy documents with Q1 sales totals",
            "session_context": {"allowed_document_ids": ["*"], "allowed_tables": ["*"]},
        },
    )
    assert "natural_language_answers" in result
    assert result["approved_answer_or_refusal_payload"]["status"] == "refused"
    assert result["approved_answer_or_refusal_payload"]["refusal_reason"] == "unsupported_question_type"
    assert "structured/database" in result["natural_language_answers"]


def test_http_chat_and_health():
    from main import app

    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"user_question": "What is the refund policy?"},
    )
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    body = response.json()
    assert "natural_language_answers" in body
    assert "structured/database" in body["natural_language_answers"]

    health = client.get("/health")
    assert health.status_code in (200, 503)
    assert "integrations" in health.json()
    assert "X-Request-ID" in health.headers


def test_best_table_evidence_prefers_query_results():
    from agents.adapters.reuse_to_reconciliation import _best_table_evidence

    text = _best_table_evidence(
        {
            "query_answer": "I do not have enough information to answer.",
            "query_results": '[{"sales": 99}]',
        }
    )
    assert "sales" in text
