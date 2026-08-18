"""Detect tabular content in answers and build CSV attachments."""

from __future__ import annotations

import base64
import csv
import io
import json
import re
from typing import Any


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-+:?", cell.replace(" ", "")) for cell in cells)


def _split_markdown_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or "|" not in stripped[1:]:
        return None
    if stripped.endswith("|"):
        stripped = stripped[1:-1]
    else:
        stripped = stripped[1:]
    return [cell.strip() for cell in stripped.split("|")]


def extract_markdown_tables(text: str) -> list[list[list[str]]]:
    """Return markdown tables as row/cell matrices."""
    tables: list[list[list[str]]] = []
    block: list[str] = []

    def flush_block() -> None:
        nonlocal block
        if len(block) < 2:
            block = []
            return
        rows: list[list[str]] = []
        for line in block:
            parsed = _split_markdown_row(line)
            if parsed is None:
                block = []
                return
            rows.append(parsed)
        if len(rows) >= 2 and _is_separator_row(rows[1]):
            rows.pop(1)
        if rows and all(len(row) == len(rows[0]) for row in rows):
            tables.append(rows)
        block = []

    for line in text.splitlines():
        if _split_markdown_row(line) is not None:
            block.append(line)
        else:
            flush_block()
    flush_block()
    return tables


def extract_json_record_tables(text: str) -> list[list[dict[str, Any]]]:
    """Return JSON arrays of objects embedded in ``text``."""
    tables: list[list[dict[str, Any]]] = []
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(text):
        start = text.find("[", idx)
        if start < 0:
            break
        try:
            value, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            idx = start + 1
            continue
        if isinstance(value, list) and value and all(isinstance(row, dict) for row in value):
            tables.append(value)
        idx = end
    return tables


def _matrix_to_csv(rows: list[list[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def _records_to_csv(records: list[dict[str, Any]]) -> str:
    fieldnames: list[str] = []
    seen: set[str] = set()
    for record in records:
        for key in record:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        writer.writerow({key: record.get(key, "") for key in fieldnames})
    return buffer.getvalue()


def tables_to_csv(
    markdown_tables: list[list[list[str]]],
    json_tables: list[list[dict[str, Any]]],
) -> tuple[str, int, list[str]]:
    """Merge detected tables into one CSV document."""
    sections: list[str] = []
    row_count = 0
    column_names: list[str] = []

    for table in markdown_tables:
        if not table:
            continue
        column_names = table[0]
        row_count += max(len(table) - 1, 0)
        sections.append(_matrix_to_csv(table))

    for records in json_tables:
        if not records:
            continue
        keys: list[str] = []
        seen: set[str] = set()
        for record in records:
            for key in record:
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        column_names = keys or column_names
        row_count += len(records)
        sections.append(_records_to_csv(records))

    if not sections:
        return "", 0, []

    csv_text = "\n".join(section.rstrip("\n") for section in sections)
    if len(sections) > 1:
        csv_text = "\n\n".join(section.rstrip("\n") for section in sections)
    return csv_text, row_count, column_names


def build_csv_attachment(
    text: str,
    *,
    filename: str = "answer_tables.csv",
) -> dict[str, Any] | None:
    """Build a downloadable CSV attachment when ``text`` contains tabular data."""
    if not text or not text.strip():
        return None

    markdown_tables = extract_markdown_tables(text)
    json_tables = extract_json_record_tables(text)
    if not markdown_tables and not json_tables:
        return None

    csv_text, row_count, column_names = tables_to_csv(markdown_tables, json_tables)
    if not csv_text.strip():
        return None

    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")
    return {
        "filename": filename,
        "media_type": "text/csv; charset=utf-8",
        "content_base64": encoded,
        "row_count": row_count,
        "column_names": column_names,
        "table_count": len(markdown_tables) + len(json_tables),
    }
