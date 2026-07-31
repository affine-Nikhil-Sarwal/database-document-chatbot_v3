"""SQLAlchemy database client wrapper."""

from __future__ import annotations

import urllib.parse
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import Settings, get_settings


def build_connection_string(settings: Settings) -> str:
    if settings.database_url.strip():
        return settings.database_url.strip()
    settings.require_database()
    odbc_connect = (
        f"DRIVER={{{settings.sql_driver}}};"
        f"SERVER={settings.sql_server};"
        f"DATABASE={settings.sql_database};"
        f"UID={settings.sql_username};"
        f"PWD={settings.sql_password}"
    )
    return f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(odbc_connect)}"


@lru_cache(maxsize=1)
def get_engine(settings: Settings | None = None) -> Engine:
    cfg = settings or get_settings()
    return create_engine(build_connection_string(cfg))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def execute_scalar(query: str, *, settings: Settings | None = None) -> int:
    engine = get_engine(settings)
    with engine.connect() as conn:
        result = conn.execute(text(query))
        row = result.fetchone()
        return int(row[0]) if row else 0


async def health_check(settings: Settings | None = None) -> dict[str, str]:
    cfg = settings or get_settings()
    try:
        cfg.require_database()
        value = execute_scalar("SELECT 1", settings=cfg)
        return {"status": "ok", "integration": "sql_database", "select_one": str(value)}
    except Exception as exc:
        return {"status": "error", "integration": "sql_database", "reason": str(exc)}
