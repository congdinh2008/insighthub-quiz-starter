"""Cosine retrieval scoped to an explicit, validated document set."""

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.deadline import check_deadline
from app.core.errors import SourceSetInvalid
from app.core.index import check_schema, ensure_index_identity
from app.core.metrics import retrieval_candidates_total
from app.services.embeddings import embed
from app.services.reranking import rerank


WORDS_PER_TOKEN = 0.75


def _estimated_tokens(text: str) -> int:
    return max(1, round(len(text.split()) / WORDS_PER_TOKEN))


def _pack_contexts(candidates: list[dict], limit: int) -> list[dict]:
    settings = get_settings()
    selected, per_document, used_tokens = [], {}, 0
    for candidate in candidates:
        document_id = candidate["document_id"]
        if per_document.get(document_id, 0) >= settings.retrieval_max_chunks_per_document:
            continue
        tokens = _estimated_tokens(candidate["chunk_text"])
        if selected and used_tokens + tokens > settings.context_max_tokens:
            continue
        if tokens > settings.context_max_tokens:
            continue
        selected.append({**candidate, "estimated_tokens": tokens})
        used_tokens += tokens
        per_document[document_id] = per_document.get(document_id, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def ready_document_ids(document_ids: list[int] | None) -> list[int]:
    with get_conn() as conn:
        if document_ids is None:
            rows = conn.execute("SELECT id FROM documents WHERE status='ready' ORDER BY id").fetchall()
            return [row[0] for row in rows]
        if not document_ids:
            raise SourceSetInvalid()
        unique = sorted(set(document_ids))
        rows = conn.execute(
            "SELECT id FROM documents WHERE status='ready' AND id = ANY(%s) ORDER BY id",
            (unique,),
        ).fetchall()
    if [row[0] for row in rows] != unique:
        raise SourceSetInvalid()
    return unique


def retrieve(question: str, top_k: int | None = None, document_ids: list[int] | None = None) -> list[dict]:
    settings = get_settings()
    k = settings.retrieval_top_k if top_k is None else top_k
    if not 1 <= k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    selected = ready_document_ids(document_ids)
    if not selected:
        return []
    with get_conn() as conn:
        check_schema(conn)
        if not ensure_index_identity(conn, claim=False):
            return []
    query_vec = embed([question], input_type="query")[0]
    check_deadline()
    with get_conn() as conn:
        check_schema(conn)
        if not ensure_index_identity(conn, claim=False):
            return []
        check_deadline()
        conn.execute("SELECT set_config('hnsw.ef_search', %s, true)", (str(settings.hnsw_ef_search),))
        candidate_k = max(k, settings.retrieval_candidate_k)
        rows = conn.execute(
            """
            SELECT c.id,c.document_id,c.source_segment_id,c.chunk_text,d.filename,
                   c.locator_type,c.locator_value,
                   1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c JOIN documents d ON d.id=c.document_id
            WHERE d.status='ready' AND c.embedding_identity_id=%s AND d.id=ANY(%s)
            ORDER BY c.embedding <=> %s::vector LIMIT %s
            """,
            (query_vec, settings.embedding_identity_id, selected, query_vec, candidate_k),
        ).fetchall()
    dense = [{
        "id": row[0], "context_id": f"chunk:{row[0]}", "document_id": row[1],
        "source_segment_id": row[2], "chunk_text": row[3], "source": row[4],
        "locator": {"type": row[5], "value": row[6]},
        "similarity": round(float(row[7]), 4),
    } for row in rows]
    retrieval_candidates_total.labels("dense").inc(len(dense))
    filtered = [
        candidate
        for candidate in dense
        if candidate["similarity"] >= settings.retrieval_min_similarity
    ]
    retrieval_candidates_total.labels("evidence_filter").inc(len(filtered))
    ranked = rerank(question, filtered)
    final_limit = (
        k
        if settings.reranker_provider == "none"
        else min(k, settings.reranker_top_n)
    )
    packed = _pack_contexts(ranked, final_limit)
    retrieval_candidates_total.labels("context").inc(len(packed))
    return packed


def validate_context_sources(contexts: list[dict]):
    ids = sorted({context["document_id"] for context in contexts})
    if not ids:
        raise SourceSetInvalid()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id FROM documents WHERE status='ready' AND id=ANY(%s)", (ids,)
        ).fetchall()
    if sorted(row[0] for row in rows) != ids:
        raise SourceSetInvalid()
