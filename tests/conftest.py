"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest


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
