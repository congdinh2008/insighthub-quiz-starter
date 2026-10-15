"""InsightHub synchronous starter API."""

import logging
import json
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.db import close_pool, get_conn, initialize_database
from app.core.errors import ServiceError
from app.core.metrics import documents_total, http_requests_total
from app.core.upload_limit import UploadLimitMiddleware
from app.routers import ai_jobs, auth, chat, documents, health, operations, system

settings = get_settings()
logging.basicConfig(level=settings.log_level)
request_logger = logging.getLogger("insighthub.requests")
# SDK/transport debugging can expose URLs and headers. Keep it out of lab logs.
for name in ("httpx", "httpcore", "pypdf", "psycopg.pool"):
    logging.getLogger(name).setLevel(logging.CRITICAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await run_in_threadpool(initialize_database)
        yield
    finally:
        await run_in_threadpool(close_pool)


app = FastAPI(title=settings.app_name, version="1.0.0-rc.3", lifespan=lifespan)
app.add_middleware(UploadLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def error_response(request: Request, status: int, code: str, message: str, *,
                   fields: list[dict] | None = None, retry_after_seconds: int | None = None) -> JSONResponse:
    """Envelope lỗi chung (SRS mục 3.3.1). Client đọc `code`, không phân tích chuỗi tiếng Việt.
    `detail` giữ lại để tương thích với web rc.3, cùng giá trị với `message`."""
    request_id = getattr(request.state, "request_id", None)
    body = {"code": code, "message": message, "detail": message, "request_id": request_id, "fields": fields or []}
    headers = {"X-Request-ID": request_id} if request_id else {}
    if retry_after_seconds is not None:
        body["retry_after_seconds"] = retry_after_seconds
        headers["Retry-After"] = str(retry_after_seconds)
    return JSONResponse(body, status_code=status, headers=headers)


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    return error_response(request, exc.status_code, exc.code, exc.message,
                          fields=exc.fields, retry_after_seconds=exc.retry_after_seconds)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    # HTTPException của route cũ (ví dụ documents.py) cũng theo envelope chung, code dạng http_<status>.
    message = exc.detail if isinstance(exc.detail, str) else "Không thể xử lý yêu cầu."
    response = error_response(request, exc.status_code, f"http_{exc.status_code}", message)
    for name, value in (exc.headers or {}).items():
        response.headers[name] = value
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # Chỉ trả vị trí trường và mã lỗi; không trả lại giá trị đầu vào hay thông điệp nội bộ của pydantic.
    fields = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", ())]
        if location and location[0] in {"body", "query", "path", "header", "cookie"}:
            location = location[1:]
        fields.append({"field": ".".join(location) or "request", "code": str(error.get("type", "invalid"))})
    return error_response(request, 422, "validation_error", "Dữ liệu yêu cầu không hợp lệ.", fields=fields)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.perf_counter()
    status = 500
    try:
        origin = request.headers.get("origin")
        if (request.method in {"POST", "PUT", "PATCH", "DELETE"}
                and origin is not None and origin not in settings.cors_origins):
            status = 403
            return error_response(request, 403, "origin_not_allowed", "Origin không được phép.")
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request.state.request_id
        return response
    except Exception:
        # Never expose uncaught driver/provider exception text to clients.
        return error_response(request, 500, "internal_error", "Không thể xử lý yêu cầu.")
    finally:
        route = request.scope.get("route")
        endpoint = getattr(route, "path", "__unmatched__")
        method = (
            request.method
            if request.method
            in {
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
                "HEAD",
                "OPTIONS",
                "TRACE",
                "CONNECT",
            }
            else "OTHER"
        )
        http_requests_total.labels(method, endpoint, str(status)).inc()
        request_logger.info(json.dumps({
            "event": "http_request",
            "request_id": request.state.request_id,
            "method": method,
            "endpoint": endpoint,
            "status": status,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "rag_mode": settings.rag_mode,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.resolved_chat_model,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.resolved_embedding_model,
            "reranker_provider": settings.reranker_provider,
        }, ensure_ascii=True, separators=(",", ":")))


@app.get("/metrics")
def metrics():
    with get_conn() as conn:
        counts = dict(
            conn.execute(
                "SELECT status, count(*) FROM documents GROUP BY status"
            ).fetchall()
        )
    for status in ("pending", "ready", "failed"):
        documents_total.labels(status).set(counts.get(status, 0))
    return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(operations.router)
app.include_router(ai_jobs.router)
app.include_router(system.router)


@app.get("/")
def root():
    return {
        "service": settings.app_name,
        "version": "1.0.0-rc.3",
        "docs": "/docs",
        "mode": settings.rag_mode,
    }
