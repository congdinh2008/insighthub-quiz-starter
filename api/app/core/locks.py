"""Transaction advisory locks fence reads against deletion within the deadline."""
from contextlib import contextmanager
from app.core.db import get_conn

@contextmanager
def shared_document_locks(document_ids: list[int]):
    with get_conn(read_only=True) as conn:
        for document_id in sorted(set(document_ids)):
            conn.execute("SELECT pg_advisory_xact_lock_shared(hashtextextended(%s,0))", (f"document:{document_id}",))
        yield
