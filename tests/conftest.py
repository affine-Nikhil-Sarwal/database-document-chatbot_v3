"""Shared pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def sample_question_pdf(tmp_path: Path) -> Path:
    from tests.pdf_fixtures import write_question_pdf

    return write_question_pdf(
        tmp_path / "sample_question.pdf",
        "Compare policy documents with Q1 sales totals",
    )


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ.keys()):
        if key.startswith(("AZURE_", "SQL_", "DATABASE_", "GPT4_", "EMBEDDING_", "WORKFLOW_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("WORKFLOW_DRY_RUN", "1")
    from orchestrator.graph import set_dry_run

    set_dry_run(True)
    yield
    set_dry_run(False)
