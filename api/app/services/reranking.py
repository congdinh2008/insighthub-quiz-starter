"""Optional reranking with a strict local TEI or Cohere contract."""

import math

from app.core.config import get_settings
from app.core.errors import ProviderError
from app.core.metrics import reranker_call_latency
from app.core.providers import post_json


def _validated_results(data: dict | list, candidate_count: int) -> list[tuple[int, float]]:
    # TEI returns a top-level array; Cohere returns {"results": [...]}.
    items = data if isinstance(data, list) else data.get("results")
    if not isinstance(items, list) or not items:
        raise ProviderError()
    ranked: list[tuple[int, float]] = []
    seen: set[int] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ProviderError()
        index = item.get("index")
        score = item.get("relevance_score", item.get("score"))
        if type(index) is not int or index < 0 or index >= candidate_count or index in seen:
            raise ProviderError()
        if type(score) not in (int, float) or not math.isfinite(float(score)):
            raise ProviderError()
        seen.add(index)
        ranked.append((index, float(score)))
    return sorted(ranked, key=lambda pair: pair[1], reverse=True)


def rerank(question: str, candidates: list[dict]) -> list[dict]:
    """Return candidates in relevance order. Configured failures never silently fallback."""
    settings = get_settings()
    if not candidates:
        return []
    if settings.reranker_provider == "none":
        return [
            {**candidate, "rerank_score": None}
            for candidate in sorted(
                candidates, key=lambda item: item["similarity"], reverse=True
            )
        ]

    texts = [candidate["chunk_text"] for candidate in candidates]
    provider = settings.reranker_provider
    with reranker_call_latency.labels(provider).time():
        if provider == "local":
            data = post_json(
                settings.local_reranker_url.rstrip("/") + "/rerank",
                headers={},
                payload={"query": question, "texts": texts, "return_text": False},
                timeout_seconds=settings.reranker_timeout_seconds,
                response_type=list,
            )
        elif provider == "cohere":
            data = post_json(
                "https://api.cohere.com/v2/rerank",
                headers={"Authorization": f"Bearer {settings.cohere_api_key}"},
                payload={
                    "model": settings.cohere_reranker_model,
                    "query": question,
                    "documents": texts,
                    "top_n": min(settings.reranker_top_n, len(texts)),
                },
                timeout_seconds=settings.reranker_timeout_seconds,
            )
        else:
            raise ProviderError()
    ranked = _validated_results(data, len(candidates))
    return [
        {**candidates[index], "rerank_score": round(score, 6)}
        for index, score in ranked
    ]
