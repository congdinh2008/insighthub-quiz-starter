"""Validated starter configuration. Real providers never fall back to fixtures."""

import hashlib
import json
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        frozen=True,
        hide_input_in_errors=True,
        str_strip_whitespace=True,
    )

    app_name: str = "InsightHub SDLC API"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3107", "http://127.0.0.1:3107"])
    environment: str = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str = Field(
        default="postgresql://insighthub:insighthub@postgres:5432/insighthub",
        repr=False,
    )
    rag_mode: Literal["fixture", "real"] = "fixture"
    rag_profile: str = Field(default="custom", min_length=1, max_length=64)
    llm_provider: Literal["deepseek", "gemini", "anthropic", "ollama", "openai", "fixture"] = (
        "fixture"
    )
    embedding_provider: Literal["gemini", "voyage", "openai", "ollama", "fixture"] = (
        "fixture"
    )
    reranker_provider: Literal["none", "local", "cohere"] = "none"
    deepseek_api_key: str = Field(default="", repr=False)
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_chat_model: str = "deepseek-flash"
    gemini_api_key: str = Field(default="", repr=False)
    gemini_chat_model: str = "gemini-3.1-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-2"
    anthropic_api_key: str = Field(default="", repr=False)
    anthropic_chat_model: str = ""
    voyage_api_key: str = Field(default="", repr=False)
    voyage_embedding_model: str = "voyage-3.5"
    cohere_api_key: str = Field(default="", repr=False)
    cohere_reranker_model: str = "rerank-v4.0-fast"
    local_reranker_url: str = ""
    local_reranker_model: str = "Alibaba-NLP/gte-multilingual-reranker-base"
    openai_api_key: str = Field(default="", repr=False)
    # Required explicitly for OpenAI, including OpenAI-compatible gateways.
    openai_base_url: str = ""
    openai_chat_model: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    ollama_base_url: str = "http://ollama:11434"
    ollama_chat_model: str = ""
    ollama_embedding_model: str = "mxbai-embed-large"
    llm_model: str = ""
    embedding_model: str = ""
    llm_max_tokens: int = Field(default=1024, ge=1, le=32768)
    embedding_dim: int = Field(default=1024, ge=1, le=2000)
    embedding_revision: str = Field(default="1", min_length=1, max_length=128)
    provider_timeout_seconds: float = Field(
        default=60, gt=0, le=300, allow_inf_nan=False
    )
    provider_retry_attempts: int = Field(default=3, ge=1, le=5)
    reranker_timeout_seconds: float = Field(
        default=20, gt=0, le=120, allow_inf_nan=False
    )
    embedding_batch_size: int = Field(default=32, ge=1, le=100)
    chunk_size: int = Field(default=800, ge=2, le=8000)
    chunk_overlap: int = Field(default=100, ge=0)
    retrieval_top_k: int = Field(default=5, ge=1, le=20)
    retrieval_candidate_k: int = Field(default=20, ge=1, le=100)
    retrieval_min_similarity: float = Field(default=-1.0, ge=-1, le=1)
    retrieval_max_chunks_per_document: int = Field(default=3, ge=1, le=20)
    context_max_tokens: int = Field(default=4000, ge=128, le=100000)
    reranker_top_n: int = Field(default=5, ge=1, le=20)
    hnsw_ef_search: int = Field(default=100, ge=20, le=1000)
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=50 * 1024 * 1024)
    max_extracted_chars: int = Field(default=200_000, ge=1, le=2_000_000)
    max_pdf_pages: int = Field(default=100, ge=1, le=500)
    ingestion_timeout_seconds: float = Field(default=120, gt=0, le=300)
    chat_timeout_seconds: float = Field(default=60, gt=0, le=180)
    idempotency_ttl_hours: int = Field(default=24, ge=1, le=168)
    expose_debug_contexts: bool = False
    ai_data_policy_url: str = ""
    ai_data_usage_notice: str = (
        "Nội dung câu hỏi và trích đoạn tài liệu có thể được gửi tới provider đã cấu hình."
    )
    migration_path: str = "/app/migrations"
    # Transactional email (infrastructure only). Defaults target the local Mailpit
    # catcher from the Compose profile "mail"; nothing is sent until code calls it.
    smtp_host: str = "mailpit"
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_timeout_seconds: float = Field(default=10, gt=0, le=60, allow_inf_nan=False)
    mail_from: str = "InsightHub <no-reply@insighthub.local>"

    @model_validator(mode="before")
    @classmethod
    def apply_mode_defaults(cls, values):
        """One mode switch for onboarding; explicit advanced overrides still validate."""
        values = dict(values)
        mode = str(values.get("rag_mode", "fixture")).strip()
        values.setdefault("llm_provider", "deepseek" if mode == "real" else "fixture")
        values.setdefault("embedding_provider", "gemini" if mode == "real" else "fixture")
        classroom = values["embedding_provider"] == "gemini" and values["llm_provider"] in {"gemini", "deepseek"}
        reranker = str(values.get("reranker_provider", "none")).strip()
        profile = "fixture-offline" if mode == "fixture" else "custom"
        if mode == "real" and classroom:
            profile = "classroom-deepseek-gemini" if values["llm_provider"] == "deepseek" else "classroom-gemini"
            profile += {"none": "", "local": "-local-reranker", "cohere": "-cohere"}.get(reranker, "")
        values.setdefault("rag_profile", profile)
        values.setdefault("retrieval_min_similarity", 0.20 if mode == "real" and values["embedding_provider"] == "gemini" else -1.0)
        if mode == "fixture":
            values.setdefault("ai_data_usage_notice", "Fixture offline không gửi dữ liệu tới provider bên ngoài.")
        elif classroom:
            generation = "DeepSeek" if values["llm_provider"] == "deepseek" else "Gemini"
            notice = f"Nội dung tài liệu và câu hỏi dùng tạo embedding được gửi tới Gemini; câu hỏi và các đoạn nguồn được chọn được gửi tới {generation} để trả lời."
            if reranker == "cohere":
                notice += " Câu hỏi và candidate chunks còn được gửi tới Cohere để rerank."
            if generation == "Gemini":
                values.setdefault("ai_data_policy_url", "https://ai.google.dev/gemini-api/terms")
            values.setdefault("ai_data_usage_notice", notice + " Chỉ dùng bộ dữ liệu thực hành được phép; kiểm chính sách dữ liệu của từng provider trước khi sử dụng.")
        return values

    @model_validator(mode="after")
    def validate_configuration(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        if self.retrieval_candidate_k < self.retrieval_top_k:
            raise ValueError("RETRIEVAL_CANDIDATE_K must be >= RETRIEVAL_TOP_K")
        if self.reranker_top_n > self.retrieval_candidate_k:
            raise ValueError("RERANKER_TOP_N must be <= RETRIEVAL_CANDIDATE_K")
        if self.rag_mode == "fixture":
            if self.llm_provider != "fixture" or self.embedding_provider != "fixture":
                raise ValueError("RAG_MODE=fixture requires both providers=fixture")
            if self.reranker_provider != "none":
                raise ValueError("RAG_MODE=fixture requires RERANKER_PROVIDER=none")
            if self.llm_model or self.embedding_model:
                raise ValueError("Fixture model overrides are not supported")
        elif "fixture" in (self.llm_provider, self.embedding_provider):
            raise ValueError("Fixture providers require RAG_MODE=fixture")
        for provider in {self.llm_provider, self.embedding_provider}:
            if provider in {"deepseek", "gemini", "anthropic", "voyage", "openai"}:
                if not getattr(self, f"{provider}_api_key"):
                    raise ValueError(f"{provider.upper()}_API_KEY is required")
            if provider in {"deepseek", "ollama", "openai"}:
                value = getattr(self, f"{provider}_base_url")
                parsed = urlsplit(value)
                if (
                    parsed.scheme not in {"http", "https"}
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or parsed.query
                    or parsed.fragment
                ):
                    raise ValueError(
                        f"{provider.upper()}_BASE_URL must be an explicit HTTP(S) URL without credentials/query"
                    )
                try:
                    parsed.port
                except ValueError:
                    raise ValueError(
                        f"{provider.upper()}_BASE_URL has an invalid port"
                    ) from None
        if self.reranker_provider == "cohere" and not self.cohere_api_key:
            raise ValueError("COHERE_API_KEY is required for Cohere reranking")
        if self.reranker_provider == "local":
            parsed = urlsplit(self.local_reranker_url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.hostname not in {"localhost", "127.0.0.1", "host.docker.internal", "reranker"}
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "LOCAL_RERANKER_URL must target localhost, host.docker.internal or reranker"
                )
            try:
                parsed.port
            except ValueError:
                raise ValueError("LOCAL_RERANKER_URL has an invalid port") from None
        if not self.resolved_chat_model or not self.resolved_embedding_model:
            raise ValueError("Selected providers require nonempty model names")
        if (
            self.embedding_provider == "gemini"
            and self.resolved_embedding_model
            not in {
                "gemini-embedding-001",
                "gemini-embedding-2",
                "gemini-embedding-2-preview",
            }
        ):
            raise ValueError("Unsupported Gemini embedding model")
        if self.embedding_provider == "ollama":
            # This starter supports a tested, dedicated embedding contract.
            if self.resolved_embedding_model.split(":")[0] != "mxbai-embed-large":
                raise ValueError("Ollama embedding requires mxbai-embed-large")
            if self.embedding_dim != 1024:
                raise ValueError("mxbai-embed-large requires EMBEDDING_DIM=1024")
        return self

    @property
    def resolved_chat_model(self) -> str:
        if self.llm_provider == "fixture":
            return "extractive-fixture-v1"
        return self.llm_model or getattr(self, f"{self.llm_provider}_chat_model")

    @property
    def resolved_embedding_model(self) -> str:
        if self.embedding_provider == "fixture":
            return "shake256-fixture-v1"
        return self.embedding_model or getattr(
            self, f"{self.embedding_provider}_embedding_model"
        )

    @property
    def resolved_reranker_model(self) -> str | None:
        if self.reranker_provider == "none":
            return None
        return getattr(self, f"{self.reranker_provider}_reranker_model")

    @property
    def embedding_identity(self) -> dict:
        endpoint = {
            "gemini": "https://generativelanguage.googleapis.com/v1beta",
            "voyage": "https://api.voyageai.com/v1",
            "openai": self.openai_base_url.rstrip("/"),
            "ollama": self.ollama_base_url.rstrip("/"),
            "fixture": "fixture",
        }[self.embedding_provider]
        return {
            "mode": self.rag_mode,
            "provider": self.embedding_provider,
            "model": self.resolved_embedding_model,
            "dimension": self.embedding_dim,
            "endpoint": endpoint,
            "revision": self.embedding_revision,
            "preprocessing": "retrieval-v1",
            "normalization": "l2-v1",
        }

    @property
    def embedding_identity_id(self) -> str:
        return hashlib.sha256(
            json.dumps(self.embedding_identity, sort_keys=True).encode()
        ).hexdigest()


@lru_cache
def get_settings() -> Settings:
    return Settings()
