"""Document lifecycle API for the synchronous starter."""

import hashlib

from fastapi import APIRouter, Header, HTTPException, Query, Response, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.deadline import operation_deadline
from app.core.errors import DocumentConflict, DocumentNotFound, InvalidDocument, ServiceError, OperationInProgress
from app.core.operations import complete_operation, fingerprint, serialized_operation, validate_key
from app.services.ingestion import ingest_document_sync

router = APIRouter(prefix="/documents", tags=["documents"])
ALLOWED_EXT = (".txt", ".md", ".pdf")


def _read_upload(file: UploadFile) -> tuple[str, bytes]:
    try:
        if not file.filename or not file.filename.lower().endswith(ALLOWED_EXT):
            raise HTTPException(400, "Chỉ chấp nhận: .txt, .md, .pdf")
        if len(file.filename) > 255 or "\x00" in file.filename:
            raise HTTPException(422, "Tên file không hợp lệ.")
        content = file.file.read(get_settings().max_upload_bytes + 1)
    finally:
        file.file.close()
    if len(content) > get_settings().max_upload_bytes:
        raise HTTPException(413, "File vượt quá giới hạn upload.")
    if not content:
        raise InvalidDocument()
    return file.filename, content


def _document_body(document_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id,filename,mime_type,size_bytes,status,chunk_count,content_sha256,"
            "embedding_identity_id,error_code,created_at,updated_at FROM documents WHERE id=%s",
            (document_id,),
        ).fetchone()
    if row is None:
        raise DocumentNotFound()
    return {
        "id": row[0], "filename": row[1], "mime_type": row[2], "size_bytes": row[3],
        "status": row[4], "chunk_count": row[5], "content_sha256": row[6],
        "embedding_identity_id": row[7], "error_code": row[8],
        "created_at": row[9].isoformat(), "updated_at": row[10].isoformat(),
    }


def _upload_document(file: UploadFile, idempotency_key: str | None):
    key = validate_key(idempotency_key)
    filename, content = _read_upload(file)
    digest = hashlib.sha256(content).hexdigest()
    request_fingerprint = fingerprint({"filename": filename, "sha256": digest})
    with serialized_operation("upload", key, request_fingerprint) as operation:
        if operation["replay"]:
            return JSONResponse(operation["body"], status_code=operation["status"])
        document_id = None
        try:
            with get_conn() as conn:
                with conn.transaction():
                    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"document:{digest}",))
                    existing = conn.execute(
                        "SELECT id FROM documents WHERE content_sha256=%s ORDER BY id LIMIT 1", (digest,)
                    ).fetchone()
                    if existing:
                        document_id = existing[0]
                    else:
                        document_id = conn.execute(
                            "INSERT INTO documents(filename,status,content_sha256,size_bytes) VALUES (%s,'pending',%s,%s) RETURNING id",
                            (filename, digest, len(content)),
                        ).fetchone()[0]
            if existing is None:
                ingest_document_sync(
                    document_id, filename, content,
                    operation_key=key, request_fingerprint=request_fingerprint,
                )
            body = _document_body(document_id)
            if body["status"] != "ready":
                error = OperationInProgress() if body["status"] == "pending" else DocumentConflict("Tài liệu đã có nhưng xử lý thất bại. Dùng thao tác Thử lại trên tài liệu này.")
                failure = {"detail": error.message, "code": error.code, "document_id": document_id, "status": body["status"], "deduplicated": True}
                complete_operation(operation["id"], error.status_code, failure, error_code=error.code)
                return JSONResponse(failure, status_code=error.status_code)
            body["mode"] = get_settings().rag_mode
            body["deduplicated"] = existing is not None
            complete_operation(operation["id"], 201, body)
            return JSONResponse(body, status_code=201)
        except ServiceError as exc:
            body = {"detail": exc.message, "code": exc.code, "document_id": document_id, "operation_id": operation["id"]}
            complete_operation(operation["id"], exc.status_code, body, error_code=exc.code)
            return JSONResponse(body, status_code=exc.status_code)


@router.post("", status_code=201)
def upload_document(file: UploadFile, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    with operation_deadline(get_settings().ingestion_timeout_seconds):
        return _upload_document(file, idempotency_key)


@router.get("")
def list_documents(response: Response, limit: int = Query(default=100, ge=1, le=100), after_id: int | None = Query(default=None, ge=1)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id,filename,mime_type,size_bytes,status,chunk_count,created_at,updated_at,"
            "embedding_identity_id,error_code FROM documents WHERE (%s::bigint IS NULL OR id < %s) "
            "ORDER BY id DESC LIMIT %s",
            (after_id, after_id, limit + 1),
        ).fetchall()
    if len(rows) > limit:
        response.headers["X-Next-Cursor"] = str(rows[limit - 1][0])
        rows = rows[:limit]
    return [{
        "id": r[0], "filename": r[1], "mime_type": r[2], "size_bytes": r[3],
        "status": r[4], "chunk_count": r[5], "created_at": r[6].isoformat(),
        "updated_at": r[7].isoformat(), "embedding_identity_id": r[8], "error_code": r[9],
    } for r in rows]


@router.get("/{document_id}")
def get_document(document_id: int):
    body = _document_body(document_id)
    with get_conn() as conn:
        attempts = conn.execute(
            "SELECT id,previous_attempt_id,operation_key,status,error_code,started_at,finished_at,deadline_at "
            "FROM ingestion_attempts WHERE document_id=%s ORDER BY started_at DESC",
            (document_id,),
        ).fetchall()
    body["attempts"] = [{
        "id": row[0], "previous_attempt_id": row[1], "operation_key": row[2],
        "status": row[3], "error_code": row[4], "started_at": row[5].isoformat(),
        "finished_at": row[6].isoformat() if row[6] else None, "deadline_at": row[7].isoformat(),
    } for row in attempts]
    return body


@router.get("/{document_id}/source")
def get_document_source(document_id: int, segment_id: int | None = Query(default=None, gt=0)):
    with get_conn() as conn:
        document = conn.execute(
            "SELECT d.filename,s.extracted_text FROM documents d JOIN document_sources s ON s.document_id=d.id WHERE d.id=%s",
            (document_id,),
        ).fetchone()
        if document is None:
            raise DocumentNotFound()
        if segment_id is None:
            return {"document_id": document_id, "filename": document[0], "content": document[1], "locator": None}
        segment = conn.execute(
            "SELECT locator_type,locator_value,heading,segment_text FROM source_segments WHERE id=%s AND document_id=%s",
            (segment_id, document_id),
        ).fetchone()
    if segment is None:
        raise DocumentNotFound("Không tìm thấy đoạn nguồn.")
    return {
        "document_id": document_id, "filename": document[0], "segment_id": segment_id,
        "locator": {"type": segment[0], "value": segment[1]}, "heading": segment[2], "content": segment[3],
    }


@router.post("/{document_id}/retry")
def retry_document(
    document_id: int,
    file: UploadFile,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    with operation_deadline(get_settings().ingestion_timeout_seconds):
        return _retry_document(document_id, file, idempotency_key)


def _retry_document(document_id: int, file: UploadFile, idempotency_key: str | None):
    key = validate_key(idempotency_key)
    filename, content = _read_upload(file)
    request_fingerprint = fingerprint({"document_id": document_id, "filename": filename, "sha256": hashlib.sha256(content).hexdigest()})
    with serialized_operation("retry", key, request_fingerprint) as operation:
        if operation["replay"]:
            return JSONResponse(operation["body"], status_code=operation["status"])
        try:
            with get_conn() as conn:
                state = conn.execute("SELECT status FROM documents WHERE id=%s", (document_id,)).fetchone()
            if state is None:
                raise DocumentNotFound()
            if state[0] != "failed":
                raise DocumentConflict("Chỉ có thể thử lại tài liệu ở trạng thái Failed.")
            ingest_document_sync(
                document_id, filename, content,
                operation_key=key, request_fingerprint=request_fingerprint,
            )
            body = _document_body(document_id)
            complete_operation(operation["id"], 200, body)
            return body
        except ServiceError as exc:
            body = {"detail": exc.message, "code": exc.code, "document_id": document_id, "operation_id": operation["id"]}
            complete_operation(operation["id"], exc.status_code, body, error_code=exc.code)
            return JSONResponse(body, status_code=exc.status_code)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    key = validate_key(idempotency_key)
    with serialized_operation(
        "delete", key, fingerprint({"document_id": document_id})
    ) as operation:
        if operation["replay"]:
            return Response(status_code=operation["status"])
        try:
            with get_conn() as conn:
                with conn.transaction():
                    conn.execute(
                        "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                        (f"document:{document_id}",),
                    )
                    result = conn.execute(
                        "DELETE FROM documents WHERE id=%s RETURNING id", (document_id,)
                    ).fetchone()
            if result is None:
                raise DocumentNotFound()
            complete_operation(
                operation["id"], 204, {"document_id": document_id, "deleted": True}
            )
            return Response(status_code=204)
        except ServiceError as exc:
            complete_operation(
                operation["id"],
                exc.status_code,
                {"detail": exc.message, "code": exc.code},
                error_code=exc.code,
            )
            raise
