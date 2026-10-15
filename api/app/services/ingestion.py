"""Synchronous, retry-safe ingestion with source provenance."""

import hashlib
import io
import json
import logging
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.deadline import check_deadline, operation_deadline, remaining_timeout
from app.core.errors import DocumentConflict, DocumentNotFound, InvalidDocument, ServiceError
from app.core.index import check_schema, ensure_index_identity
from app.core.metrics import ingestion_errors_total
from app.services.chunking import chunk_text
from app.services.embeddings import embed, validate_vectors

logger = logging.getLogger("insighthub.ingestion")


@dataclass(frozen=True)
class SourceSegment:
    locator_type: str
    locator_value: str
    heading: str | None
    text: str


@dataclass(frozen=True)
class ExtractedSource:
    text: str
    mime_type: str
    segments: list[SourceSegment]
    metadata: dict


def _normalized_text(raw: str) -> str:
    text = unicodedata.normalize("NFC", raw)
    if not text.strip() or "\x00" in text:
        raise InvalidDocument()
    return text


def _text_segments(text: str, markdown: bool) -> list[SourceSegment]:
    if markdown:
        segments, headings, lines = [], [], []
        fence = None

        def flush():
            if lines:
                value = "\n".join(lines).strip()
                if value:
                    path = " / ".join(title for _, title in headings) or None
                    segments.append(SourceSegment("section", str(len(segments) + 1), path, value))
                lines.clear()

        for line in text.splitlines():
            marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
            if marker:
                token = marker[1]
                if fence is None:
                    fence = token
                elif token[0] == fence[0] and len(token) >= len(fence):
                    fence = None
                lines.append(line)
                continue
            match = re.match(r"^ {0,3}(#{1,6})(?:[ \t]+|$)(.*)$", line) if fence is None else None
            if match:
                flush()
                level = len(match[1])
                title = re.sub(r"[ \t]+#+[ \t]*$", "", match[2]).strip()
                headings[:] = [(depth, value) for depth, value in headings if depth < level]
                headings.append((level, title))
                # Include the entire heading path in source segment and indexed text.
                lines.extend("#" * depth + " " + value for depth, value in headings)
            else:
                lines.append(line)
        flush()
        if segments:
            return segments
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    return [SourceSegment("paragraph", str(i + 1), None, part) for i, part in enumerate(paragraphs)]


def extract_source(filename: str, content: bytes) -> ExtractedSource:
    settings = get_settings()
    try:
        if not content:
            raise InvalidDocument()
        lower = filename.lower()
        if lower.endswith((".txt", ".md")):
            if content.startswith(b"%PDF-"):
                raise InvalidDocument()
            text = _normalized_text(content.decode("utf-8-sig"))
            if len(text) > settings.max_extracted_chars:
                raise InvalidDocument()
            segments = _text_segments(text, lower.endswith(".md"))
            mime = "text/markdown" if lower.endswith(".md") else "text/plain"
            return ExtractedSource(text, mime, segments, {"segment_count": len(segments)})
        if lower.endswith(".pdf"):
            if not content.startswith(b"%PDF-"):
                raise InvalidDocument()
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            if reader.is_encrypted or len(reader.pages) > settings.max_pdf_pages:
                raise InvalidDocument()
            pages, total = [], 0
            for number, page in enumerate(reader.pages, 1):
                check_deadline()
                extracted = page.extract_text() or ""
                piece = _normalized_text(extracted) if extracted.strip() else ""
                total += len(piece)
                if total > settings.max_extracted_chars:
                    raise InvalidDocument()
                if piece:
                    pages.append(SourceSegment("page", str(number), None, piece))
            if not pages:
                raise InvalidDocument()
            text = "\n".join(page.text for page in pages)
            return ExtractedSource(text, "application/pdf", pages, {"page_count": len(reader.pages), "segment_count": len(pages)})
        raise InvalidDocument()
    except ServiceError:
        raise
    except Exception:
        raise InvalidDocument() from None


def extract_text(filename: str, content: bytes) -> str:
    """Compatibility helper retained for unit tests and learning exercises."""
    return extract_source(filename, content).text


def _pipeline_id() -> str:
    settings = get_settings()
    return hashlib.sha256(json.dumps({
        "version": "extract-segment-chunk-v3",
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "embedding_identity": settings.embedding_identity_id,
        "unicode": "NFC",
    }, sort_keys=True).encode()).hexdigest()


def _attempt_start(conn, document_id: int, operation_key: str, request_fingerprint: str) -> int:
    previous = conn.execute(
        "SELECT id FROM ingestion_attempts WHERE document_id=%s ORDER BY started_at DESC LIMIT 1",
        (document_id,),
    ).fetchone()
    deadline = datetime.now(timezone.utc) + timedelta(seconds=remaining_timeout(get_settings().ingestion_timeout_seconds))
    return conn.execute(
        "INSERT INTO ingestion_attempts(document_id,previous_attempt_id,operation_key,request_fingerprint,status,deadline_at) "
        "VALUES (%s,%s,%s,%s,'processing',%s) RETURNING id",
        (document_id, previous[0] if previous else None, operation_key, request_fingerprint, deadline),
    ).fetchone()[0]


def process_document(document_id: int, filename: str, content: bytes, *, operation_key=None, request_fingerprint=None) -> int:
    with get_conn(read_only=True) as lock_conn:
        lock_conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"document:{document_id}",))
        return _process_document(document_id, filename, content, operation_key=operation_key, request_fingerprint=request_fingerprint)


def _process_document(document_id: int, filename: str, content: bytes, *, operation_key=None, request_fingerprint=None) -> int:
    settings = get_settings()
    digest, pipeline_id = hashlib.sha256(content).hexdigest(), _pipeline_id()
    operation_key = operation_key or f"legacy-{uuid.uuid4()}"
    request_fingerprint = request_fingerprint or digest
    # Persist the attempt and original bytes before external work, so polling can
    # distinguish an active operation from a crash or an expired attempt.
    with get_conn() as conn:
        row = conn.execute("SELECT filename,status,chunk_count,content_sha256,pipeline_id FROM documents WHERE id=%s FOR UPDATE", (document_id,)).fetchone()
        if row is None:
            raise DocumentNotFound()
        if row[0] != filename or row[3] not in (None, digest) or (row[1] == "ready" and row[4] not in (None, pipeline_id)):
            raise DocumentConflict()
        if row[1] == "ready":
            ensure_index_identity(conn, claim=False)
            return row[2]
        attempt_id = _attempt_start(conn, document_id, operation_key, request_fingerprint)
        conn.execute("UPDATE documents SET status='pending',content_sha256=%s,pipeline_id=%s,size_bytes=%s,updated_at=clock_timestamp() WHERE id=%s", (digest,pipeline_id,len(content),document_id))
        conn.execute("INSERT INTO document_sources(document_id,original_bytes) VALUES (%s,%s) ON CONFLICT(document_id) DO UPDATE SET original_bytes=EXCLUDED.original_bytes,updated_at=clock_timestamp()", (document_id,content))
    try:
        with get_conn() as conn:
            check_schema(conn)
            if conn.execute("SELECT id FROM documents WHERE id=%s FOR UPDATE", (document_id,)).fetchone() is None:
                raise DocumentNotFound()
            check_deadline()
            ensure_index_identity(conn, claim=False)
            if len(content) > settings.max_upload_bytes:
                raise InvalidDocument()
            source = extract_source(filename, content)
            conn.execute("UPDATE documents SET mime_type=%s WHERE id=%s", (source.mime_type,document_id))
            conn.execute("UPDATE document_sources SET extracted_text=%s,extraction_metadata=%s,updated_at=clock_timestamp() WHERE document_id=%s", (source.text,Jsonb(source.metadata),document_id))
            conn.execute("DELETE FROM chunks WHERE document_id=%s", (document_id,))
            conn.execute("DELETE FROM source_segments WHERE document_id=%s", (document_id,))
            chunk_rows = []
            for segment_index, segment in enumerate(source.segments):
                segment_id = conn.execute("INSERT INTO source_segments(document_id,segment_index,locator_type,locator_value,heading,segment_text) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id", (document_id,segment_index,segment.locator_type,segment.locator_value,segment.heading,segment.text)).fetchone()[0]
                for chunk in chunk_text(segment.text):
                    chunk_rows.append((len(chunk_rows),chunk,segment_id,segment.locator_type,segment.locator_value))
            if not chunk_rows:
                raise InvalidDocument()
            ensure_index_identity(conn, claim=True)
            vectors = validate_vectors(embed([row[1] for row in chunk_rows], input_type="document"), len(chunk_rows), settings.embedding_dim)
            check_deadline()
            conn.execute("UPDATE documents SET embedding_identity_id=%s WHERE id=%s", (settings.embedding_identity_id,document_id))
            for item,vector in zip(chunk_rows,vectors,strict=True):
                conn.execute("INSERT INTO chunks(document_id,source_segment_id,chunk_index,chunk_text,locator_type,locator_value,embedding,embedding_identity_id) VALUES (%s,%s,%s,%s,%s,%s,%s::vector,%s)", (document_id,item[2],item[0],item[1],item[3],item[4],vector,settings.embedding_identity_id))
            conn.execute("UPDATE documents SET status='ready',chunk_count=%s,error_code=NULL,updated_at=clock_timestamp() WHERE id=%s", (len(chunk_rows),document_id))
            completed = conn.execute("UPDATE ingestion_attempts SET status='succeeded',finished_at=clock_timestamp() WHERE id=%s AND status='processing' AND deadline_at>clock_timestamp() RETURNING id", (attempt_id,)).fetchone()
            if completed is None:
                from app.core.errors import DeadlineExceeded
                raise DeadlineExceeded()
        return len(chunk_rows)
    except Exception as exc:
        failure = exc if isinstance(exc, ServiceError) else ServiceError()
        with operation_deadline(5), get_conn() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id=%s", (document_id,))
            conn.execute("DELETE FROM source_segments WHERE document_id=%s", (document_id,))
            conn.execute("UPDATE documents SET status='failed',chunk_count=0,embedding_identity_id=NULL,error_code=%s,updated_at=clock_timestamp() WHERE id=%s", (failure.code,document_id))
            conn.execute("UPDATE ingestion_attempts SET status='failed',error_code=%s,finished_at=clock_timestamp() WHERE id=%s", (failure.code,attempt_id))
        ingestion_errors_total.inc()
        logger.warning("Document processing failed: id=%s code=%s",document_id,failure.code)
        raise failure from None


def ingest_document_sync(document_id: int, filename: str, content: bytes, **kwargs) -> int:
    return process_document(document_id, filename, content, **kwargs)
