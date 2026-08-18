"""Tests for tabular CSV export from final answers."""

from __future__ import annotations

import base64
import csv
import io

from agents.generated.response_delivery.agent import execute as deliver
from workflow.table_export import (
    build_csv_attachment,
    extract_json_record_tables,
    extract_markdown_tables,
)


def test_extract_markdown_table():
    text = (
        "Summary below:\n\n"
        "| Region | Sales |\n"
        "| --- | ---: |\n"
        "| North | 100 |\n"
        "| South | 200 |\n"
    )
    tables = extract_markdown_tables(text)
    assert len(tables) == 1
    assert tables[0][0] == ["Region", "Sales"]
    assert tables[0][1:] == [["North", "100"], ["South", "200"]]


def test_extract_json_record_table():
    text = 'Top rows: [{"region": "North", "sales": 100}, {"region": "South", "sales": 200}]'
    tables = extract_json_record_tables(text)
    assert len(tables) == 1
    assert tables[0][0]["region"] == "North"


def test_build_csv_attachment_from_markdown():
    text = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    attachment = build_csv_attachment(text)
    assert attachment is not None
    assert attachment["filename"] == "answer_tables.csv"
    decoded = base64.b64decode(attachment["content_base64"]).decode("utf-8")
    rows = list(csv.reader(io.StringIO(decoded)))
    assert rows == [["A", "B"], ["1", "2"]]
    assert attachment["row_count"] == 1
    assert attachment["column_names"] == ["A", "B"]


def test_build_csv_attachment_returns_none_for_prose_only():
    assert build_csv_attachment("Revenue grew 12% year over year.") is None


def test_delivery_attaches_csv_for_tabular_answer():
    out = deliver(
        {
            "approved_answer_or_refusal_payload": {
                "status": "approved",
                "message": "Quarterly totals:\n\n| Quarter | Total |\n| --- | --- |\n| Q1 | 1.2M |\n",
                "citations": ["SQL-1"],
                "conflicts": [],
            }
        },
        dry_run=True,
    )
    assert "natural_language_answers" in out
    assert "csv_attachment" in out
    assert out["csv_attachment"]["row_count"] == 1


def test_delivery_omits_csv_for_non_tabular_answer():
    out = deliver(
        {
            "approved_answer_or_refusal_payload": {
                "status": "approved",
                "message": "Total sales were 1.2M per [SQL-1].",
                "citations": ["SQL-1"],
                "conflicts": [],
            }
        },
        dry_run=True,
    )
    assert "csv_attachment" not in out


def test_delivery_omits_csv_for_refusal():
    out = deliver(
        {
            "approved_answer_or_refusal_payload": {
                "status": "refused",
                "message": "| A | B |\n| --- | --- |\n| 1 | 2 |",
                "citations": [],
                "conflicts": [],
                "refusal_reason": "insufficient_evidence",
            }
        },
        dry_run=True,
    )
    assert "csv_attachment" not in out


def _csv_test_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.routes import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_http_csv_download_endpoint():
    from api.routes import _register_csv_download

    client = _csv_test_client()
    attachment = build_csv_attachment("| X | Y |\n| --- | --- |\n| 9 | 8 |\n")
    assert attachment is not None

    token = _register_csv_download(dict(attachment))
    assert token

    response = client.get(f"/download/csv/{token}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers.get("content-disposition", "").lower()
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows == [["X", "Y"], ["9", "8"]]


def test_http_csv_download_rejects_tampered_token():
    from api.routes import _register_csv_download

    client = _csv_test_client()
    attachment = build_csv_attachment("| X | Y |\n| --- | --- |\n| 9 | 8 |\n")
    assert attachment is not None
    token = _register_csv_download(dict(attachment))
    assert token
    tampered = token[:-2] + ("A" if token[-2] != "A" else "B") + token[-1]
    response = client.get(f"/download/csv/{tampered}")
    assert response.status_code == 404


def test_http_csv_download_rejects_expired_token(monkeypatch):
    from api import routes

    client = _csv_test_client()
    attachment = build_csv_attachment("| X | Y |\n| --- | --- |\n| 9 | 8 |\n")
    assert attachment is not None
    token = routes._register_csv_download(dict(attachment))
    assert token
    monkeypatch.setattr(routes.time, "time", lambda: 10**12)
    response = client.get(f"/download/csv/{token}")
    assert response.status_code == 404
