"""REST API and web UI.

Endpoints: POST /v1/scan, POST /v1/explain, GET /health, GET / (UI).
Policy decisions (including BLOCK) return 200; the caller must honour `decision`.
"""

import time
import uuid
from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from pii_gate import __version__, gate, knowledge
from pii_gate.config import Settings, load_settings
from pii_gate.logging_setup import configure_logging, get_logger
from pii_gate.policy import check_rules

STATIC = Path(__file__).parent / "static"
log = get_logger("api")


class ScanRequest(BaseModel):
    text: str


class ExplainRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Readiness: the policy corpus must load and every rule must cite a real clause.
        try:
            knowledge.default_index.cache_clear()
            index = knowledge.default_index()
            check_rules(index)
            app.state.index, app.state.ready, app.state.not_ready_reason = index, True, None
            log.info("startup", extra={"fields": {"clauses": len(index.clauses)}})
        except Exception as exc:
            app.state.index, app.state.ready = None, False
            app.state.not_ready_reason = type(exc).__name__
            log.error("startup_failed", extra={"fields": {"error_type": type(exc).__name__}})
        yield

    app = FastAPI(title="PII Gate", version=__version__, lifespan=lifespan)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()

        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_body_bytes:
            response = JSONResponse(
                {"error": "PAYLOAD_TOO_LARGE", "decision": "BLOCK"}, status_code=413
            )
        else:
            response = await call_next(request)

        response.headers["x-request-id"] = request_id
        log.info(
            "request",
            extra={"fields": {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }},
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # FastAPI's default echoes the submitted value ("input"), which could be PII.
        detail = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse({"error": "INVALID_REQUEST", "detail": detail}, status_code=422)

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        log.error("unhandled_error", extra={"fields": {
            "request_id": getattr(request.state, "request_id", None),
            "error_type": type(exc).__name__,
        }})
        return JSONResponse({"error": "INTERNAL_ERROR", "decision": "BLOCK"}, status_code=500)

    def not_ready() -> JSONResponse:
        return JSONResponse(
            {"error": "SERVICE_NOT_READY", "decision": "BLOCK"}, status_code=503
        )

    @app.post("/v1/scan")
    def scan(body: ScanRequest, request: Request):
        if not app.state.ready:
            return not_ready()
        result = gate.scan(body.text, max_chars=settings.max_chars)
        log.info("scan", extra={"fields": {
            "request_id": request.state.request_id,
            "decision": result.decision.name,
            "input_chars": len(body.text),
            "entity_counts": dict(Counter(f.entity_type for f in result.findings)),
            "reason_codes": sorted({r.code for r in result.reasons}),
        }})
        return {"request_id": request.state.request_id, **result.to_dict(app.state.index)}

    @app.post("/v1/explain")
    def explain(body: ExplainRequest, request: Request):
        if not app.state.ready:
            return not_ready()
        result = knowledge.explain(body.question, app.state.index)
        log.info("explain", extra={"fields": {
            "request_id": request.state.request_id,
            "answered": result.answered,
            "clauses": [h.clause.id for h in result.hits],
        }})
        return {"request_id": request.state.request_id, **result.to_dict()}

    @app.get("/health")
    def health():
        body = {
            "status": "ok" if app.state.ready else "not_ready",
            "version": __version__,
            "policy_clauses": len(app.state.index.clauses) if app.state.ready else 0,
            "max_chars": settings.max_chars,
        }
        if not app.state.ready:
            body["reason"] = app.state.not_ready_reason
            return JSONResponse(body, status_code=503)
        return body

    @app.get("/", include_in_schema=False)
    def ui():
        return FileResponse(STATIC / "index.html")

    return app


app = create_app()
