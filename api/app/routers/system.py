"""Safe runtime profile disclosure for the Web and evaluation evidence."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/profile")
def get_profile():
    settings = get_settings()
    external = settings.rag_mode == "real" and (
        settings.llm_provider != "ollama"
        or settings.embedding_provider != "ollama"
        or settings.reranker_provider == "cohere"
    )
    return {
        "profile": settings.rag_profile,
        "mode": settings.rag_mode,
        "llm": {
            "provider": settings.llm_provider,
            "model": settings.resolved_chat_model,
        },
        "embedding": {
            "provider": settings.embedding_provider,
            "model": settings.resolved_embedding_model,
            "dimension": settings.embedding_dim,
        },
        "reranker": {
            "provider": settings.reranker_provider,
            "model": settings.resolved_reranker_model,
        },
        "retrieval": {
            "candidate_k": settings.retrieval_candidate_k,
            "top_k": settings.retrieval_top_k,
            "min_similarity": settings.retrieval_min_similarity,
            "context_max_tokens": settings.context_max_tokens,
        },
        "disclosure": {
            "external_data_transfer": external,
            "notice": settings.ai_data_usage_notice,
            "policy_url": settings.ai_data_policy_url or None,
        },
    }
