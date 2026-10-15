"""Idempotent RAG API with explicit source selection and validated citations."""

import time
import unicodedata
from typing import Literal

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import get_settings
from app.core.deadline import check_deadline, operation_deadline
from app.core.errors import ServiceError, SourceSetInvalid
from app.core.locks import shared_document_locks
from app.core.metrics import llm_call_latency, llm_tokens_total, rag_query_latency
from app.core.operations import complete_operation, fingerprint, serialized_operation, validate_key
from app.services.llm import generate
from app.services.retrieval import ready_document_ids, retrieve, validate_context_sources

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    document_ids: list[int] | None = Field(default=None, max_length=100)

    @field_validator("question", mode="before")
    @classmethod
    def normalize_question(cls, value):
        return unicodedata.normalize("NFC", value) if isinstance(value, str) else value

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, value):
        if value is not None and (not value or any(item <= 0 for item in value)):
            raise ValueError("document_ids must contain positive IDs")
        return sorted(set(value)) if value is not None else None


class TokenUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    source: Literal["provider", "unavailable"]


class ChatResponse(BaseModel):
    status: Literal["Answered", "NoEvidence"]
    answer: str | None
    claims: list[dict]
    citations: list[dict]
    sources: list[str]
    contexts: list[dict]
    latency_ms: int
    mode: Literal["fixture", "real"]
    provider: str
    model: str
    prompt_version: str
    profile: str
    retrieval: dict
    usage: TokenUsage


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    with operation_deadline(get_settings().chat_timeout_seconds):
        return _chat(req, idempotency_key)


def _chat(req: ChatRequest, idempotency_key: str | None):
    start = time.perf_counter()
    key = validate_key(idempotency_key)
    request_fingerprint = fingerprint(req.model_dump())
    with serialized_operation("chat", key, request_fingerprint) as operation:
        if operation["replay"]:
            return JSONResponse(operation["body"], status_code=operation["status"])
        try:
            selected = ready_document_ids(req.document_ids)
            if not selected:
                raise SourceSetInvalid("Chưa có tài liệu nào sẵn sàng. Hãy upload tài liệu trước.")
            with shared_document_locks(selected), rag_query_latency.time():
                contexts = retrieve(req.question, top_k=req.top_k, document_ids=selected)
                settings = get_settings()
                if contexts:
                    with llm_call_latency.time():
                        result = generate(req.question, contexts)
                    validate_context_sources(contexts)
                else:
                    result = {
                        "status": "NoEvidence",
                        "answer": None,
                        "claims": [],
                        "citation_ids": [],
                        "sources": [],
                        "mode": settings.rag_mode,
                        "provider": settings.llm_provider,
                        "model": settings.resolved_chat_model,
                        "prompt_version": "evidence-gate-v1",
                        "usage": {
                            "input_tokens": None,
                            "output_tokens": None,
                            "source": "unavailable",
                        },
                    }
                for direction in ("input", "output"):
                    value = result["usage"].get(f"{direction}_tokens")
                    if value is not None:
                        llm_tokens_total.labels(result["provider"], direction).inc(value)
                by_id = {context["context_id"]: context for context in contexts}
                citations = [{
                    "citation_id": citation_id,
                    "document_id": by_id[citation_id]["document_id"],
                    "source_segment_id": by_id[citation_id]["source_segment_id"],
                    "source": by_id[citation_id]["source"],
                    "locator": by_id[citation_id]["locator"],
                    "excerpt": by_id[citation_id]["chunk_text"][:500],
                } for citation_id in result.pop("citation_ids")]
                public_contexts = contexts if settings.expose_debug_contexts else [{
                    "context_id": context["context_id"],
                    "document_id": context["document_id"],
                    "source_segment_id": context["source_segment_id"],
                    "source": context["source"],
                    "locator": context["locator"],
                    "similarity": context["similarity"],
                    "rerank_score": context.get("rerank_score"),
                    "estimated_tokens": context.get("estimated_tokens"),
                } for context in contexts]
                check_deadline()
                body = ChatResponse(
                    **result, citations=citations, contexts=public_contexts,
                    profile=settings.rag_profile,
                    retrieval={
                        "embedding_provider": settings.embedding_provider,
                        "embedding_model": settings.resolved_embedding_model,
                        "reranker_provider": settings.reranker_provider,
                        "reranker_model": settings.resolved_reranker_model,
                        "min_similarity": settings.retrieval_min_similarity,
                        "candidate_k": settings.retrieval_candidate_k,
                        "context_count": len(contexts),
                    },
                    latency_ms=int((time.perf_counter() - start) * 1000),
                ).model_dump()
                complete_operation(operation["id"], 200, body, started=start)
                return body
        except ServiceError as exc:
            complete_operation(operation["id"], exc.status_code, {"detail": exc.message, "code": exc.code}, error_code=exc.code)
            raise
