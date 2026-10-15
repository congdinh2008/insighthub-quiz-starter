"""Durable operation records, bounded execution and source-aware replay."""
import copy
import hashlib
import json
import logging
import time
from contextlib import contextmanager
from psycopg.types.json import Jsonb
from app.core.config import get_settings
from app.core.db import get_conn
from app.core.deadline import operation_deadline, remaining_timeout
from app.core.errors import DeadlineExceeded, IdempotencyConflict, IdempotencyKeyRequired, OperationInProgress, ServiceError

logger = logging.getLogger('insighthub.operations')


def validate_key(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 128:
        raise IdempotencyKeyRequired()
    return value.strip()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def public_response(operation_type, body):
    """Historical answers survive deletion; revoked source text does not."""
    if operation_type != 'chat' or not isinstance(body, dict) or not body.get('citations'):
        return body
    result = copy.deepcopy(body)
    ids = sorted({c['document_id'] for c in result['citations']})
    with get_conn() as conn:
        available = {r[0] for r in conn.execute("SELECT id FROM documents WHERE status='ready' AND id=ANY(%s)", (ids,))}
    unavailable = set(ids) - available
    if unavailable:
        result['historical_sources_unavailable'] = True
        for citation in result['citations']:
            if citation['document_id'] in unavailable:
                citation['available'] = False
                citation['excerpt'] = None
        for context in result.get('contexts', []):
            if context.get('document_id') in unavailable:
                context['available'] = False
                context.pop('chunk_text', None)
    return result


def recover_expired_operations():
    """Polling fences overdue work while the process is still running."""
    error = DeadlineExceeded()
    with operation_deadline(5), get_conn() as conn:
        conn.execute(
            "UPDATE operation_records SET status='failed',http_status=%s,response_body=%s,error_code=%s,updated_at=clock_timestamp() "
            "WHERE status='processing' AND deadline_at<=clock_timestamp()",
            (error.status_code, Jsonb({'detail': error.message, 'code': error.code}), error.code),
        )
        stale = conn.execute(
            "UPDATE ingestion_attempts SET status='failed',error_code='deadline_exceeded',finished_at=clock_timestamp() "
            "WHERE status='processing' AND deadline_at<=clock_timestamp() RETURNING document_id"
        ).fetchall()
        if stale:
            conn.execute("UPDATE documents SET status='failed',chunk_count=0,error_code='deadline_exceeded',updated_at=clock_timestamp() WHERE status='pending' AND id=ANY(%s)", ([r[0] for r in stale],))


def complete_operation(operation_id, status, body, *, error_code=None, started=None):
    # Error persistence has its own short cleanup budget after an expired request.
    if status >= 400:
        with operation_deadline(5), get_conn() as conn:
            conn.execute("UPDATE operation_records SET status='failed',http_status=%s,response_body=%s,error_code=%s,updated_at=clock_timestamp() WHERE id=%s AND status='processing'", (status, Jsonb(body), error_code, operation_id))
        return body
    with get_conn() as conn:
        changed = conn.execute(
            "UPDATE operation_records SET status='succeeded',http_status=%s,response_body=%s,error_code=NULL,updated_at=clock_timestamp() "
            "WHERE id=%s AND status='processing' AND deadline_at>clock_timestamp() RETURNING id",
            (status, Jsonb(body), operation_id),
        ).fetchone()
        if changed is None:
            raise DeadlineExceeded()
        if started is not None:
            body['latency_ms'] = int((time.perf_counter() - started) * 1000)
            conn.execute("UPDATE operation_records SET response_body=%s,updated_at=clock_timestamp() WHERE id=%s", (Jsonb(body), operation_id))
    return body


@contextmanager
def serialized_operation(operation_type, key, request_fingerprint):
    key = validate_key(key)
    created = None
    settings = get_settings()
    seconds = settings.ingestion_timeout_seconds if operation_type in {'upload', 'retry'} else settings.chat_timeout_seconds
    try:
        with operation_deadline(remaining_timeout(seconds)):
            # A separate transaction holds only the key lock. The processing record
            # commits before yield so reconciliation can observe it during execution.
            with get_conn(read_only=True) as lock_conn:
                lock_conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f'insighthub:{operation_type}:{key}',))
                with get_conn() as conn:
                    row = conn.execute("SELECT id,request_fingerprint,status,http_status,response_body FROM operation_records WHERE operation_type=%s AND operation_key=%s AND expires_at>now() FOR UPDATE", (operation_type, key)).fetchone()
                    if row:
                        if row[1] != request_fingerprint:
                            raise IdempotencyConflict()
                        if row[2] == 'processing':
                            raise OperationInProgress()
                        replay = {'replay': True, 'id': row[0], 'status': row[3], 'body': row[4]}
                    else:
                        conn.execute("DELETE FROM operation_records WHERE operation_type=%s AND operation_key=%s AND expires_at<=now()", (operation_type, key))
                        created = conn.execute(
                            "INSERT INTO operation_records(operation_type,operation_key,request_fingerprint,status,expires_at,deadline_at) VALUES (%s,%s,%s,'processing',now()+(%s*interval '1 hour'),clock_timestamp()+(%s*interval '1 second')) RETURNING id",
                            (operation_type,key,request_fingerprint,settings.idempotency_ttl_hours,remaining_timeout(seconds)),
                        ).fetchone()[0]
                if created is None:
                    replay['body'] = public_response(operation_type, replay['body'])
                    yield replay
                else:
                    yield {'replay': False, 'id': created}
    except Exception as exc:
        if created is not None:
            error = exc if isinstance(exc, ServiceError) else ServiceError()
            try:
                complete_operation(created,error.status_code,{'detail':error.message,'code':error.code},error_code=error.code)
            except Exception:
                # Polling recovery retries persistence if the database was unavailable.
                logger.warning('Operation error persistence deferred: id=%s', created)
        raise
