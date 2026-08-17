"""FastAPI HTTP surface and CLI for the database + document chatbot workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import traceback
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

APP_ROOT = Path(__file__).resolve().parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] request_id=%(request_id)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


for handler in logging.root.handlers:
    handler.addFilter(RequestIdFilter())

logger = logging.getLogger(__name__)

from config.autogen_azure_compat import apply_autogen_azure_compat
from config.settings import ConfigurationError, get_settings
from orchestrator.graph import run_workflow_from_node, set_dry_run

_settings = get_settings()
_settings.export_to_environ()
apply_autogen_azure_compat()

app = FastAPI(title="Database + Document Chatbot")


class RequestIdMiddleware:
    """Pure ASGI request-ID middleware."""

    header_name = b"x-request-id"

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = b""
        for key, value in scope.get("headers") or []:
            if key.lower() == self.header_name:
                incoming = value
                break
        request_id = incoming.decode("latin-1").strip() or str(uuid.uuid4())
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers.append((self.header_name, request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        token = request_id_context.set(request_id)
        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            request_id_context.reset(token)


request_id_context: Any = None
try:
    import contextvars

    request_id_context = contextvars.ContextVar("request_id", default="-")
except ImportError:
    request_id_context = None


app.add_middleware(RequestIdMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "Unhandled exception path=%s request_id=%s",
        request.url.path,
        request_id,
    )
    headers: dict[str, str] = {}
    if request_id:
        headers["X-Request-ID"] = str(request_id)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "request_id": request_id,
            "traceback": traceback.format_exc(),
        },
        headers=headers,
    )


from api.routes import router

app.include_router(router)


def _load_input_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Input JSON must be an object")
    return data


def _build_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_json:
        payload = _load_input_json(Path(args.input_json))
    elif args.file:
        file_path = Path(args.file).resolve()
        payload = {
            "question_pdf": str(file_path),
            "session_context": {
                "user_id": "cli-user",
                "request_id": str(uuid.uuid4()),
                "allowed_document_ids": ["*"],
                "allowed_tables": ["*"],
            },
        }
    else:
        raise ConfigurationError("Provide --file (question PDF) or --input-json")
    return payload


async def _run_health_checks() -> dict[str, Any]:
    from integrations import azure_openai, azure_search, sql_database

    results = await asyncio.gather(
        azure_openai.health_check(),
        azure_search.health_check(),
        sql_database.health_check(),
    )
    integrations = list(results)
    overall = "ok" if all(r.get("status") == "ok" for r in integrations) else "degraded"
    return {"status": overall, "integrations": integrations}


def _cli_health() -> int:
    result = asyncio.run(_run_health_checks())
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 1


def _cli_dry_run() -> int:
    set_dry_run(True)
    sample = {
        "user_question": "What were total sales last quarter?",
        "session_context": {
            "user_id": "dry-run",
            "request_id": "dry-run",
            "allowed_document_ids": ["*"],
            "allowed_tables": ["*"],
        },
    }
    result = run_workflow_from_node("user-question-intake", sample)
    assert "natural_language_answers" in result
    print(json.dumps({"status": "ok", "dry_run": True, "result_keys": sorted(result.keys())}, indent=2))
    return 0


def _cli_run(args: argparse.Namespace) -> int:
    set_dry_run(False)
    payload = _build_payload(args)
    result = run_workflow_from_node("user-question-intake", payload)
    print(json.dumps(result, indent=2, default=str))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Database + document chatbot — grounded QA across documents and SQL tables.",
    )
    parser.add_argument("--health", action="store_true", help="Check integration health and exit")
    parser.add_argument("--dry-run", action="store_true", help="Exercise orchestration without live I/O")
    parser.add_argument("--file", "-f", type=str, help="Path to a PDF containing the analyst question")
    parser.add_argument("--input-json", type=str, help="Path to JSON payload for intake")
    parser.add_argument("--serve", action="store_true", help="Start uvicorn server")
    parser.add_argument("--host", default="0.0.0.0", help="Uvicorn host")
    parser.add_argument("--port", type=int, default=8000, help="Uvicorn port")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.health:
        return _cli_health()
    if args.dry_run:
        return _cli_dry_run()
    if args.serve:
        import uvicorn

        uvicorn.run("main:app", host=args.host, port=args.port, reload=False)
        return 0
    if args.file or args.input_json:
        try:
            return _cli_run(args)
        except ConfigurationError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    parser.print_help()
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        import uvicorn

        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
    else:
        raise SystemExit(main())
