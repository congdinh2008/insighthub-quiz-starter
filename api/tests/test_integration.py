"""Opt in with RUN_DB_TESTS=1 and mount init.sql as TEST_SCHEMA_PATH in Docker.

Each test run owns a random PostgreSQL schema. Only that schema is truncated/dropped.
No paid providers are called. A missing DB/schema fixture fails an opted-in run.
"""

import concurrent.futures
import os
from pathlib import Path
import threading
import time
import unittest
import uuid
from unittest.mock import patch

from support import configured, real_config
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from fastapi.testclient import TestClient

from app.core import db
from app.core.db import recover_interrupted_operations
from app.core.config import get_settings
from app.core.errors import (
    DocumentConflict,
    IndexIdentityConflict,
    ProviderError,
    SchemaMismatch,
)
from app.core.index import check_schema
from app.core.migrations import run_migrations
from app.main import app
from app.services.embeddings import _local_embed
from app.services.ingestion import process_document
from app.services.retrieval import retrieve


@unittest.skipUnless(
    os.environ.get("RUN_DB_TESTS") == "1",
    "Set RUN_DB_TESTS=1 for isolated PostgreSQL integration tests",
)
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn = os.environ.get("TEST_DATABASE_URL") or get_settings().database_url
        cls.schema = "test_insighthub_" + uuid.uuid4().hex
        source = Path(
            os.environ.get(
                "TEST_SCHEMA_PATH",
                str(Path(__file__).resolve().parents[2] / "infra/db/init.sql"),
            )
        )
        cls.schema_sql = source.read_text()
        cls.old_pool = db._pool
        with psycopg.connect(cls.dsn, autocommit=True) as conn:
            # Extension must be installed by the DB bootstrap, never by the test run.
            if not conn.execute(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ).fetchone():
                raise RuntimeError(
                    "Initialize pgvector using infra/db/init.sql before integration tests"
                )
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(cls.schema)))
        cls.addClassCleanup(cls.cleanup_schema)
        with psycopg.connect(
            cls.dsn, options=f"-csearch_path={cls.schema},public"
        ) as conn:
            conn.execute(cls.schema_sql)
            run_migrations(conn)
        db._pool = ConnectionPool(
            conninfo=cls.dsn,
            min_size=2,
            max_size=10,
            configure=db._configure,
            kwargs={"options": f"-csearch_path={cls.schema},public"},
            open=True,
        )
        db._pool.wait(timeout=15)

    @classmethod
    def cleanup_schema(cls):
        if db._pool is not cls.old_pool:
            db._pool.close()
        db._pool = cls.old_pool
        with psycopg.connect(cls.dsn, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(cls.schema))
            )

    def setUp(self):
        self.config = configured()
        self.config.__enter__()
        self.addCleanup(self.config.__exit__, None, None, None)
        with db.get_conn() as conn:
            conn.execute(
                "TRUNCATE operation_records, chunks, documents, embedding_index RESTART IDENTITY CASCADE"
            )
        self.client = TestClient(app)
        self.key_index = 0

    def headers(self):
        self.key_index += 1
        return {"Idempotency-Key": f"test-{self._testMethodName}-{self.key_index}"}

    def create_document(self, filename="test.txt"):
        with db.get_conn() as conn:
            return conn.execute(
                "INSERT INTO documents(filename) VALUES (%s) RETURNING id",
                (filename,),
            ).fetchone()[0]

    def state(self, document_id):
        with db.get_conn() as conn:
            return conn.execute(
                "SELECT status, chunk_count, content_sha256, error_code, "
                "(SELECT count(*) FROM chunks WHERE document_id = documents.id) "
                "FROM documents WHERE id = %s",
                (document_id,),
            ).fetchone()

    def test_fixture_upload_retrieve_chat_metrics_delete_end_to_end(self):
        self.assertEqual(self.client.get("/readyz").status_code, 200)
        self.assertEqual(
            self.client.post("/chat", headers=self.headers(), json={"question": "RAG?"}).status_code, 422
        )
        response = self.client.post(
            "/documents", headers=self.headers(), files={"file": ("rag.txt", b"RAG uses retrieved documents.")}
        )
        self.assertEqual(response.status_code, 201, response.text)
        document = response.json()
        self.assertEqual(document["mode"], "fixture")
        self.assertEqual(document["chunk_count"], 1)
        self.assertEqual(self.client.get("/documents").json()[0]["status"], "ready")
        chat = self.client.post(
            "/chat", headers=self.headers(), json={"question": "RAG uses retrieved documents."}
        )
        self.assertEqual(chat.status_code, 200, chat.text)
        self.assertIn("FIXTURE", chat.json()["answer"])
        self.assertEqual(chat.json()["sources"], ["rag.txt"])
        self.assertAlmostEqual(chat.json()["contexts"][0]["similarity"], 1, places=3)
        self.assertEqual(chat.json()["usage"]["source"], "unavailable")
        metrics = self.client.get("/metrics")
        self.assertEqual(metrics.status_code, 200)
        self.assertIn('insighthub_documents_total{status="ready"} 1.0', metrics.text)
        self.assertEqual(
            self.client.delete(f"/documents/{document['id']}", headers={"Idempotency-Key": "delete-e2e"}).status_code, 204
        )
        with db.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT count(*) FROM chunks").fetchone()[0], 0
            )
        self.assertIn(
            'insighthub_documents_total{status="ready"} 0.0',
            self.client.get("/metrics").text,
        )

    def test_successful_retry_is_noop_and_conflicting_payload_is_409(self):
        document_id = self.create_document()
        first = process_document(document_id, "test.txt", b"hello world")
        with patch("app.services.ingestion.embed") as provider:
            self.assertEqual(
                process_document(document_id, "test.txt", b"hello world"), first
            )
            provider.assert_not_called()
        for filename, content in (
            ("test.txt", b"changed"),
            ("other.txt", b"hello world"),
        ):
            with self.assertRaises(DocumentConflict):
                process_document(document_id, filename, content)
        state = self.state(document_id)
        self.assertEqual((state[0], state[1], state[4]), ("ready", first, first))
        self.assertIsNotNone(state[2])

    def test_concurrent_successful_retries_call_provider_once(self):
        document_id = self.create_document()
        started, release = threading.Event(), threading.Event()

        def slow_embed(texts, input_type):
            started.set()
            self.assertTrue(release.wait(timeout=5))
            return _local_embed(texts, 1024)

        with patch("app.services.ingestion.embed", side_effect=slow_embed) as provider:
            with concurrent.futures.ThreadPoolExecutor(2) as executor:
                first = executor.submit(
                    process_document, document_id, "test.txt", b"same"
                )
                self.assertTrue(started.wait(timeout=3))
                second = executor.submit(
                    process_document, document_id, "test.txt", b"same"
                )
                release.set()
                self.assertEqual(first.result(timeout=5), second.result(timeout=5))
            self.assertEqual(provider.call_count, 1)
        self.assertEqual(self.state(document_id)[4], 1)

    def test_failed_attempt_and_concurrent_retry_end_ready(self):
        document_id = self.create_document()
        started, release = threading.Event(), threading.Event()
        calls = []

        def fail_once(texts, input_type):
            calls.append(True)
            if len(calls) == 1:
                started.set()
                release.wait(timeout=5)
                raise ProviderError()
            return _local_embed(texts, 1024)

        with patch("app.services.ingestion.embed", side_effect=fail_once):
            with concurrent.futures.ThreadPoolExecutor(2) as executor:
                first = executor.submit(
                    process_document, document_id, "test.txt", b"same"
                )
                self.assertTrue(started.wait(timeout=3))
                second = executor.submit(
                    process_document, document_id, "test.txt", b"same"
                )
                release.set()
                with self.assertRaises(ProviderError):
                    first.result(timeout=5)
                self.assertEqual(second.result(timeout=5), 1)
        self.assertEqual(self.state(document_id)[0], "ready")
        self.assertEqual(self.state(document_id)[4], 1)
        self.assertIsNone(self.state(document_id)[3])

    def test_failed_vectors_are_atomic_and_can_retry(self):
        document_id = self.create_document()
        for invalid in ([], [[float("nan")] * 1024], [[1.0] * 1023]):
            with (
                patch("app.services.ingestion.embed", return_value=invalid),
                self.assertRaises(ProviderError),
            ):
                process_document(document_id, "test.txt", b"content")
            state = self.state(document_id)
            self.assertEqual((state[0], state[1], state[4]), ("failed", 0, 0))
            self.assertEqual(state[3], "provider_error")
            with db.get_conn() as conn:
                self.assertEqual(
                    conn.execute("SELECT count(*) FROM embedding_index").fetchone()[0],
                    0,
                )
        self.assertEqual(process_document(document_id, "test.txt", b"content"), 1)

    def test_mid_insert_database_failure_rolls_back_all_chunks(self):
        document_id = self.create_document()
        with db.get_conn() as conn:
            conn.execute(
                "CREATE FUNCTION reject_second() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN IF NEW.chunk_index = 1 THEN RAISE EXCEPTION 'secret'; END IF; "
                "RETURN NEW; END $$"
            )
            conn.execute(
                "CREATE TRIGGER reject_second BEFORE INSERT ON chunks "
                "FOR EACH ROW EXECUTE FUNCTION reject_second()"
            )
        try:
            with configured(chunk_size=4, chunk_overlap=0):
                with self.assertRaises(Exception) as raised:
                    process_document(document_id, "test.txt", b"a b c d e f")
                self.assertNotIn("secret", str(raised.exception))
        finally:
            with db.get_conn() as conn:
                conn.execute("DROP TRIGGER reject_second ON chunks")
                conn.execute("DROP FUNCTION reject_second()")
        state = self.state(document_id)
        self.assertEqual((state[0], state[1], state[4]), ("failed", 0, 0))

    def test_empty_extracted_text_is_failed_and_422(self):
        response = self.client.post(
            "/documents", headers=self.headers(), files={"file": ("empty.txt", b" \n ")}
        )
        self.assertEqual(response.status_code, 422, response.text)
        document = self.client.get("/documents").json()[0]
        self.assertEqual(document["status"], "failed")
        self.assertEqual(document["chunk_count"], 0)

    def test_index_identity_change_rejects_query_upload_and_readiness(self):
        self.client.post("/documents", headers=self.headers(), files={"file": ("test.txt", b"content")})
        with (
            configured(embedding_revision="2"),
            patch("app.services.retrieval.embed") as provider,
        ):
            with self.assertRaises(IndexIdentityConflict):
                retrieve("question")
            provider.assert_not_called()
            response = self.client.post(
                "/documents", headers=self.headers(), files={"file": ("new.txt", b"new content")}
            )
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(self.client.get("/readyz").status_code, 503)
        with db.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT count(*) FROM chunks").fetchone()[0], 1
            )

    def test_same_dimension_real_provider_cannot_query_fixture_index(self):
        self.client.post("/documents", headers=self.headers(), files={"file": ("test.txt", b"content")})
        with real_config(), patch("app.services.retrieval.embed") as provider:
            with self.assertRaises(IndexIdentityConflict):
                retrieve("question")
        provider.assert_not_called()

    def test_dimension_mismatch_is_rejected_before_provider(self):
        with configured(embedding_dim=768), db.get_conn() as conn:
            with self.assertRaises(SchemaMismatch):
                check_schema(conn)

    def test_real_gateway_full_pipeline_with_mock_http(self):
        def embedding_response(*args, **kwargs):
            return {
                "data": [
                    {"index": i, "embedding": [1.0] * 1024}
                    for i in range(len(kwargs["payload"]["input"]))
                ],
                "usage": {"prompt_tokens": 5},
            }

        with (
            real_config(),
            patch(
                "app.services.embeddings.post_json",
                side_effect=embedding_response,
            ),
            patch(
                "app.services.llm.post_json",
                return_value={
                    "choices": [
                        {"message": {"content": '{"status":"Answered","claims":[{"text":"Supported answer","citation_ids":["chunk:1"]}]}'}}
                    ],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 8},
                },
            ),
        ):
            upload = self.client.post(
                "/documents", headers=self.headers(), files={"file": ("real.txt", b"content")}
            )
            self.assertEqual(upload.status_code, 201, upload.text)
            chat = self.client.post("/chat", headers=self.headers(), json={"question": "question"})
            self.assertEqual(chat.status_code, 200, chat.text)
            self.assertEqual(chat.json()["mode"], "real")
            self.assertEqual(chat.json()["usage"]["input_tokens"], 12)
            self.assertEqual(chat.json()["usage"]["source"], "provider")

    def test_provider_failure_is_502_and_metadata_truthful(self):
        with (
            real_config(),
            patch("app.services.embeddings.post_json", side_effect=ProviderError()),
        ):
            response = self.client.post(
                "/documents", headers=self.headers(), files={"file": ("real.txt", b"content")}
            )
        self.assertEqual(response.status_code, 502, response.text)
        document = self.client.get("/documents").json()[0]
        self.assertEqual(
            (document["status"], document["chunk_count"], document["error_code"]),
            ("failed", 0, "provider_error"),
        )

    def test_upload_idempotency_conflict_and_content_deduplication(self):
        headers = {"Idempotency-Key": "same-upload-key"}
        first = self.client.post("/documents", headers=headers, files={"file": ("same.txt", b"same bytes")})
        replay = self.client.post("/documents", headers=headers, files={"file": ("same.txt", b"same bytes")})
        conflict = self.client.post("/documents", headers=headers, files={"file": ("same.txt", b"different")})
        duplicate = self.client.post(
            "/documents", headers={"Idempotency-Key": "different-key"},
            files={"file": ("renamed.txt", b"same bytes")},
        )
        self.assertEqual((first.status_code, replay.status_code, conflict.status_code, duplicate.status_code), (201, 201, 409, 201))
        self.assertEqual(first.json()["id"], replay.json()["id"])
        self.assertEqual(first.json()["id"], duplicate.json()["id"])
        self.assertTrue(duplicate.json()["deduplicated"])
        self.assertEqual(len(self.client.get("/documents").json()), 1)
        operation = self.client.get("/operations/upload/same-upload-key")
        self.assertEqual(operation.status_code, 200)
        self.assertEqual(operation.json()["response"]["id"], first.json()["id"])
        retry_ready = self.client.post(
            f"/documents/{first.json()['id']}/retry",
            headers={"Idempotency-Key": "retry-ready"},
            files={"file": ("same.txt", b"same bytes")},
        )
        self.assertEqual(retry_ready.status_code, 409)

    def test_evidence_gate_returns_no_evidence_without_llm_call(self):
        document = self.client.post(
            "/documents",
            headers=self.headers(),
            files={"file": ("evidence.txt", b"Only release procedures are documented.")},
        ).json()
        with (
            configured(retrieval_min_similarity=1.0),
            patch("app.routers.chat.generate") as generate,
        ):
            response = self.client.post(
                "/chat",
                headers=self.headers(),
                json={
                    "question": "What is the weather tomorrow?",
                    "document_ids": [document["id"]],
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "NoEvidence")
        self.assertEqual(response.json()["retrieval"]["context_count"], 0)
        generate.assert_not_called()

    def test_delete_is_idempotent_and_reconciled(self):
        first = self.client.post(
            "/documents", headers=self.headers(), files={"file": ("one.txt", b"one")}
        ).json()
        second = self.client.post(
            "/documents", headers=self.headers(), files={"file": ("two.txt", b"two")}
        ).json()
        headers = {"Idempotency-Key": "delete-replay"}
        original = self.client.delete(f"/documents/{first['id']}", headers=headers)
        replay = self.client.delete(f"/documents/{first['id']}", headers=headers)
        conflict = self.client.delete(f"/documents/{second['id']}", headers=headers)
        self.assertEqual((original.status_code, replay.status_code, conflict.status_code), (204, 204, 409))
        operation = self.client.get("/operations/delete/delete-replay").json()
        self.assertEqual(operation["status"], "succeeded")
        self.assertEqual(operation["response"]["document_id"], first["id"])

    def test_delete_waits_until_chat_result_is_committed(self):
        document = self.client.post(
            "/documents", headers=self.headers(), files={"file": ("lock.txt", b"lock evidence")}
        ).json()
        started, release = threading.Event(), threading.Event()

        def blocked_generate(_question, contexts):
            started.set()
            release.wait(timeout=5)
            return {
                "status": "Answered",
                "answer": "supported",
                "claims": [{"text": "supported", "citation_ids": [contexts[0]["context_id"]]}],
                "citation_ids": [contexts[0]["context_id"]],
                "sources": [contexts[0]["source"]],
                "mode": "fixture",
                "provider": "fixture",
                "model": "extractive-fixture-v1",
                "prompt_version": "test",
                "usage": {"input_tokens": None, "output_tokens": None, "source": "unavailable"},
            }

        with patch("app.routers.chat.generate", side_effect=blocked_generate):
            with concurrent.futures.ThreadPoolExecutor(2) as executor:
                chat = executor.submit(
                    self.client.post,
                    "/chat",
                    headers={"Idempotency-Key": "chat-lock"},
                    json={"question": "lock", "document_ids": [document["id"]]},
                )
                self.assertTrue(started.wait(timeout=3))
                delete = executor.submit(
                    self.client.delete,
                    f"/documents/{document['id']}",
                    headers={"Idempotency-Key": "delete-lock"},
                )
                self.assertFalse(delete.done())
                release.set()
                self.assertEqual(chat.result(timeout=5).status_code, 200)
                self.assertEqual(delete.result(timeout=5).status_code, 204)

    def test_expired_operation_key_can_be_reused(self):
        with db.get_conn() as conn:
            conn.execute(
                "INSERT INTO operation_records(operation_type,operation_key,request_fingerprint,status,expires_at) "
                "VALUES ('upload','expired-key','old','failed',now() - interval '1 minute')"
            )
        response = self.client.post(
            "/documents",
            headers={"Idempotency-Key": "expired-key"},
            files={"file": ("fresh.txt", b"fresh")},
        )
        self.assertEqual(response.status_code, 201, response.text)
        with db.get_conn() as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT count(*) FROM operation_records WHERE operation_type='upload' AND operation_key='expired-key'"
                ).fetchone()[0],
                1,
            )

    def test_document_list_has_stable_cursor_pagination(self):
        for index in range(3):
            self.client.post(
                "/documents", headers=self.headers(),
                files={"file": (f"page-{index}.txt", f"content-{index}".encode())},
            )
        first = self.client.get("/documents?limit=2")
        self.assertEqual(len(first.json()), 2)
        cursor = first.headers.get("X-Next-Cursor")
        self.assertIsNotNone(cursor)
        second = self.client.get(f"/documents?limit=2&after_id={cursor}")
        self.assertEqual(len(second.json()), 1)
        self.assertTrue(set(item["id"] for item in first.json()).isdisjoint(item["id"] for item in second.json()))

    def test_startup_recovery_fences_interrupted_attempt_and_operation(self):
        document_id = self.create_document()
        with db.get_conn() as conn:
            conn.execute(
                "INSERT INTO ingestion_attempts(document_id,operation_key,request_fingerprint,status,deadline_at) "
                "VALUES (%s,'crashed','fingerprint','processing',now() + interval '1 minute')",
                (document_id,),
            )
            conn.execute(
                "INSERT INTO operation_records(operation_type,operation_key,request_fingerprint,status) "
                "VALUES ('upload','crashed','fingerprint','processing')"
            )
            recover_interrupted_operations(conn)
        with db.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT status,error_code FROM documents WHERE id=%s", (document_id,)).fetchone(), ("failed", "interrupted"))
            self.assertEqual(conn.execute("SELECT status,error_code FROM ingestion_attempts").fetchone(), ("failed", "interrupted"))
            self.assertEqual(conn.execute("SELECT status,error_code,http_status FROM operation_records").fetchone(), ("failed", "interrupted", 500))

    def _auth_session(self, *, expires_in="1 hour", email=None):
        email = email or f"user-{uuid.uuid4().hex[:8]}@insighthub.test"
        token = uuid.uuid4().hex
        with psycopg.connect(self.dsn, options=f"-csearch_path={self.schema},public") as conn:
            user_id = conn.execute(
                "INSERT INTO auth_user(name,email,email_verified) VALUES('Test',%s,true) RETURNING id::text", (email,)
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO auth_session(expires_at,token,updated_at,user_id) VALUES(now()+%s::interval,%s,now(),%s)",
                (expires_in, token, user_id),
            )
        return user_id, token

    @staticmethod
    def _signed(token, secret):
        import base64, hashlib, hmac
        signature = base64.b64encode(hmac.new(secret.encode(), token.encode(), hashlib.sha256).digest()).decode()
        from urllib.parse import quote
        return quote(f"{token}.{signature}", safe="")

    def test_auth_me_requires_valid_session(self):
        self.assertEqual(self.client.get("/auth/me").status_code, 401)
        user_id, token = self._auth_session()
        with patch.dict(os.environ, {"BETTER_AUTH_SECRET": "test-secret"}):
            cookie = {"insighthub.session_token": self._signed(token, "test-secret")}
            ok = self.client.get("/auth/me", cookies=cookie)
            self.assertEqual(ok.status_code, 200, ok.text)
            self.assertEqual(ok.json()["id"], user_id)
            forged = self.client.get("/auth/me", cookies={"insighthub.session_token": self._signed(token, "other-secret")})
            self.assertEqual(forged.status_code, 401)
            self.assertEqual(forged.json()["code"], "not_authenticated")

    def test_auth_me_rejects_expired_and_revoked_sessions(self):
        _, expired = self._auth_session(expires_in="-1 minute")
        with patch.dict(os.environ, {"BETTER_AUTH_SECRET": "test-secret"}):
            response = self.client.get("/auth/me", cookies={"insighthub.session_token": self._signed(expired, "test-secret")})
            self.assertEqual(response.status_code, 401)
            _, token = self._auth_session()
            cookie = {"insighthub.session_token": self._signed(token, "test-secret")}
            self.assertEqual(self.client.get("/auth/me", cookies=cookie).status_code, 200)
            with psycopg.connect(self.dsn, options=f"-csearch_path={self.schema},public") as conn:
                conn.execute("DELETE FROM auth_session WHERE token=%s", (token,))
            self.assertEqual(self.client.get("/auth/me", cookies=cookie).status_code, 401)

    def test_mcp_readonly_role_reads_documents_but_cannot_write(self):
        with psycopg.connect(self.dsn, options=f"-csearch_path={self.schema},public") as conn:
            conn.execute("SET ROLE insighthub_readonly")
            conn.execute("SELECT count(*) FROM documents").fetchone()
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute("INSERT INTO documents(filename,status) VALUES('x.txt','pending')")
        with psycopg.connect(self.dsn, options=f"-csearch_path={self.schema},public") as conn:
            conn.execute("SET ROLE insighthub_readonly")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute("SELECT count(*) FROM operation_records")

    def test_forward_migration_preserves_legacy_document_and_chunk(self):
        schema = "migration_" + uuid.uuid4().hex
        legacy = (Path(__file__).with_name("legacy_schema.sql")).read_text()
        with psycopg.connect(self.dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            with psycopg.connect(self.dsn, options=f"-csearch_path={schema},public") as conn:
                conn.execute(legacy)
                identity = get_settings().embedding_identity_id
                conn.execute(
                    "INSERT INTO embedding_index(singleton,identity_id,identity,dimension) VALUES(TRUE,%s,%s,1024)",
                    (identity, Jsonb(get_settings().embedding_identity)),
                )
                document_id = conn.execute(
                    "INSERT INTO documents(filename,status,chunk_count,content_sha256,pipeline_id,embedding_identity_id) "
                    "VALUES('legacy.txt','ready',1,'sha','pipeline',%s) RETURNING id", (identity,),
                ).fetchone()[0]
                vector = "[" + ",".join(["1"] + ["0"] * 1023) + "]"
                conn.execute(
                    "INSERT INTO chunks(document_id,chunk_index,chunk_text,embedding,embedding_identity_id) "
                    "VALUES(%s,0,'legacy content',%s::vector,%s)", (document_id, vector, identity),
                )
                run_migrations(conn)
                self.assertEqual(conn.execute("SELECT filename,status,chunk_count FROM documents").fetchone(), ("legacy.txt", "ready", 1))
                self.assertEqual(conn.execute("SELECT chunk_text FROM chunks").fetchone()[0], "legacy content")
                self.assertIsNotNone(conn.execute("SELECT to_regclass('document_sources')").fetchone()[0])
        finally:
            with psycopg.connect(self.dsn, autocommit=True) as admin:
                admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))

    def test_failed_document_retry_preserves_attempt_history_and_source(self):
        with patch("app.services.ingestion.embed", side_effect=ProviderError()):
            failed = self.client.post(
                "/documents", headers={"Idempotency-Key": "failed-upload"},
                files={"file": ("retry.md", b"# Heading\n\nRetry content")},
            )
        self.assertEqual(failed.status_code, 502, failed.text)
        document_id = failed.json()["document_id"]
        retried = self.client.post(
            f"/documents/{document_id}/retry", headers={"Idempotency-Key": "retry-once"},
            files={"file": ("retry.md", b"# Heading\n\nRetry content")},
        )
        self.assertEqual(retried.status_code, 200, retried.text)
        detail = self.client.get(f"/documents/{document_id}").json()
        self.assertEqual(detail["status"], "ready")
        self.assertEqual([item["status"] for item in detail["attempts"]], ["succeeded", "failed"])
        self.assertEqual(detail["attempts"][0]["previous_attempt_id"], detail["attempts"][1]["id"])
        with db.get_conn() as conn:
            segment_id = conn.execute("SELECT id FROM source_segments WHERE document_id=%s", (document_id,)).fetchone()[0]
        source = self.client.get(f"/documents/{document_id}/source?segment_id={segment_id}")
        self.assertEqual(source.status_code, 200)
        self.assertIn("Retry content", source.json()["content"])

    def test_chat_source_scope_and_idempotent_replay(self):
        first = self.client.post("/documents", headers=self.headers(), files={"file": ("one.txt", b"alpha source")}).json()
        second = self.client.post("/documents", headers=self.headers(), files={"file": ("two.txt", b"beta source")}).json()
        headers = {"Idempotency-Key": "chat-replay"}
        payload = {"question": "alpha source", "document_ids": [first["id"]]}
        answer = self.client.post("/chat", headers=headers, json=payload)
        replay = self.client.post("/chat", headers=headers, json=payload)
        conflict = self.client.post("/chat", headers=headers, json={"question": "other", "document_ids": [second["id"]]})
        self.assertEqual((answer.status_code, replay.status_code, conflict.status_code), (200, 200, 409))
        self.assertEqual(answer.json(), replay.json())
        self.assertEqual({item["document_id"] for item in answer.json()["contexts"]}, {first["id"]})
        self.assertEqual(answer.json()["citations"][0]["document_id"], first["id"])


    def test_internal_chat_error_is_terminal_without_restart(self):
        doc = self.client.post('/documents',headers=self.headers(),files={'file':('internal.txt',b'valid source')}).json()
        headers={'Idempotency-Key':'internal-chat'}
        with patch('app.routers.chat.retrieve',side_effect=RuntimeError('private implementation detail')):
            response=TestClient(app,raise_server_exceptions=False).post('/chat',headers=headers,json={'question':'test','document_ids':[doc['id']]})
        self.assertEqual(response.status_code,500)
        operation=self.client.get('/operations/chat/internal-chat').json()
        self.assertEqual((operation['status'],operation['http_status'],operation['error_code']),('failed',500,'internal_error'))
        self.assertNotIn('private implementation',str(operation))

    def test_success_write_cannot_outlive_deadline(self):
        doc=self.client.post('/documents',headers=self.headers(),files={'file':('deadline.txt',b'valid deadline source')}).json()
        with db.get_conn() as conn:
            conn.execute("CREATE FUNCTION delay_success() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.status='succeeded' AND NEW.operation_type='chat' THEN PERFORM pg_sleep(0.6); END IF; RETURN NEW; END $$")
            conn.execute('CREATE TRIGGER slow_success BEFORE UPDATE ON operation_records FOR EACH ROW EXECUTE FUNCTION delay_success()')
        try:
            with configured(chat_timeout_seconds=0.2):
                started=time.perf_counter()
                response=self.client.post('/chat',headers={'Idempotency-Key':'slow-commit'},json={'question':'test','document_ids':[doc['id']]})
                elapsed=time.perf_counter()-started
            self.assertEqual(response.status_code,504,response.text)
            self.assertLess(elapsed,0.55)
            operation=self.client.get('/operations/chat/slow-commit').json()
            self.assertEqual((operation['status'],operation['error_code']),('failed','deadline_exceeded'))
        finally:
            with db.get_conn() as conn:
                conn.execute('DROP TRIGGER slow_success ON operation_records')
                conn.execute('DROP FUNCTION delay_success()')

    def test_document_lock_wait_respects_chat_deadline(self):
        doc=self.client.post('/documents',headers=self.headers(),files={'file':('locked.txt',b'locked source')}).json()
        with configured(chat_timeout_seconds=0.15), db.get_conn() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",(f"document:{doc['id']}",))
            with concurrent.futures.ThreadPoolExecutor(1) as executor:
                future=executor.submit(self.client.post,'/chat',headers={'Idempotency-Key':'locked-chat'},json={'question':'test','document_ids':[doc['id']]})
                response=future.result(timeout=2)
        self.assertEqual(response.status_code,504,response.text)
        self.assertEqual(self.client.get('/operations/chat/locked-chat').json()['status'],'failed')

    def test_expired_processing_is_recovered_by_poll(self):
        with db.get_conn() as conn:
            conn.execute("INSERT INTO operation_records(operation_type,operation_key,request_fingerprint,status,deadline_at) VALUES ('chat','expired-live','fp','processing',now()-interval '1 second')")
        operation=self.client.get('/operations/chat/expired-live').json()
        self.assertEqual((operation['status'],operation['http_status']),('failed',504))

    def test_deleted_source_replay_redacts_excerpt_and_debug_context(self):
        doc=self.client.post('/documents',headers=self.headers(),files={'file':('historical.txt',b'historical source content')}).json()
        payload={'question':'test','document_ids':[doc['id']]}; headers={'Idempotency-Key':'historical-chat'}
        with configured(expose_debug_contexts=True):
            first=self.client.post('/chat',headers=headers,json=payload).json()
            self.client.delete(f"/documents/{doc['id']}",headers=self.headers())
            replay=self.client.post('/chat',headers=headers,json=payload).json()
            polled=self.client.get('/operations/chat/historical-chat').json()['response']
        for result in (replay,polled):
            self.assertEqual(result['answer'],first['answer'])
            self.assertTrue(result['historical_sources_unavailable'])
            self.assertIsNone(result['citations'][0]['excerpt'])
            self.assertFalse(result['citations'][0]['available'])
            self.assertNotIn('chunk_text',result['contexts'][0])

    def test_duplicate_failed_and_pending_are_not_created_success(self):
        first=self.client.post('/documents',headers=self.headers(),files={'file':('blank.txt',b'   ')})
        duplicate=self.client.post('/documents',headers=self.headers(),files={'file':('blank.txt',b'   ')})
        self.assertEqual((first.status_code,duplicate.status_code),(422,409))
        self.assertEqual(duplicate.json()['document_id'],first.json()['document_id'])
        import hashlib
        with db.get_conn() as conn:
            conn.execute("INSERT INTO documents(filename,content_sha256,status) VALUES ('pending.txt',%s,'pending')",(hashlib.sha256(b'pending bytes').hexdigest(),))
        pending=self.client.post('/documents',headers=self.headers(),files={'file':('pending.txt',b'pending bytes')})
        self.assertEqual(pending.status_code,409)
        self.assertEqual(pending.json()['code'],'operation_in_progress')

    def test_markdown_heading_path_tables_and_code_remain_indexed(self):
        content=b'# Release BLUE-17\n## Limits 42\n| item | count |\n| a | 3 |\n```python\n# code comment\nx = 5\n```\n## Only HEADING-99\n'
        doc=self.client.post('/documents',headers=self.headers(),files={'file':('headings.md',content)}).json()
        with db.get_conn() as conn:
            rows=conn.execute('SELECT chunk_text FROM chunks WHERE document_id=%s ORDER BY chunk_index',(doc['id'],)).fetchall()
        indexed='\n'.join(r[0] for r in rows)
        for token in ('BLUE-17','Limits 42','| a | 3 |','# code comment','x = 5','HEADING-99'):
            self.assertIn(token,indexed)
        with db.get_conn() as conn:
            segments=conn.execute('SELECT heading FROM source_segments WHERE document_id=%s ORDER BY segment_index',(doc['id'],)).fetchall()
        self.assertIn('Release BLUE-17 / Limits 42',[r[0] for r in segments])

    def test_late_embedding_never_publishes_chunks_and_can_retry(self):
        from app.services.embeddings import embed as actual_embed
        def late_embed(texts, **kwargs):
            vectors = actual_embed(texts, **kwargs)
            time.sleep(0.25)
            return vectors
        content = b'late embedding source'
        with configured(ingestion_timeout_seconds=0.12), patch('app.services.ingestion.embed', side_effect=late_embed):
            response = self.client.post('/documents', headers={'Idempotency-Key':'late-upload'}, files={'file':('late.txt', content)})
        self.assertEqual(response.status_code, 504, response.text)
        identifier = response.json()['document_id']
        with db.get_conn() as conn:
            self.assertEqual(conn.execute('SELECT status,chunk_count FROM documents WHERE id=%s',(identifier,)).fetchone(), ('failed',0))
            self.assertEqual(conn.execute('SELECT count(*) FROM chunks WHERE document_id=%s',(identifier,)).fetchone()[0],0)
            self.assertEqual(bytes(conn.execute('SELECT original_bytes FROM document_sources WHERE document_id=%s',(identifier,)).fetchone()[0]),content)
        self.assertEqual(self.client.get('/operations/upload/late-upload').json()['status'],'failed')
        retried=self.client.post(f'/documents/{identifier}/retry',headers=self.headers(),files={'file':('late.txt',content)})
        self.assertEqual((retried.status_code,retried.json()['status']),(200,'ready'))

    def test_unexpected_ingestion_error_leaves_terminal_attempt(self):
        with patch('app.services.ingestion.embed',side_effect=RuntimeError('private provider diagnostic')):
            response=self.client.post('/documents',headers={'Idempotency-Key':'unexpected-upload'},files={'file':('unexpected.txt',b'valid source')})
        self.assertEqual(response.status_code,500)
        identifier=response.json()['document_id']
        detail=self.client.get(f'/documents/{identifier}').json()
        self.assertEqual((detail['status'],detail['attempts'][0]['status']),('failed','failed'))
        operation=self.client.get('/operations/upload/unexpected-upload').json()
        self.assertEqual(operation['status'],'failed')
        self.assertNotIn('private provider',str(operation))

    def test_poll_recovers_expired_ingestion_attempt_without_restart(self):
        with db.get_conn() as conn:
            identifier=conn.execute("INSERT INTO documents(filename,status) VALUES('expired.txt','pending') RETURNING id").fetchone()[0]
            conn.execute("INSERT INTO ingestion_attempts(document_id,operation_key,request_fingerprint,status,deadline_at) VALUES(%s,'expired-upload','fp','processing',now()-interval '1 second')",(identifier,))
            conn.execute("INSERT INTO operation_records(operation_type,operation_key,request_fingerprint,status,deadline_at) VALUES('upload','expired-upload','fp','processing',now()-interval '1 second')")
        self.assertEqual(self.client.get('/operations/upload/expired-upload').json()['status'],'failed')
        detail=self.client.get(f'/documents/{identifier}').json()
        self.assertEqual((detail['status'],detail['attempts'][0]['status']),('failed','failed'))

    # AI Job scaffold (learner-r1.3): cơ chế idempotency, LIM-10, LIM-11, publish fence, đọc trạng thái.
    def _job_user(self):
        return self._auth_session()[0]

    def _accept(self, user_id, key, data=None, job_type="summary", **kwargs):
        from app.core.ai_jobs import accept_job
        return accept_job(user_id=user_id, job_type=job_type, idempotency_key=key,
                          normalized_input=data or {"source_ids": [1], "length": "short"}, **kwargs)

    def _allow(self, read=True, publish=True):
        return type("Policy", (), {"can_read": lambda *_: read, "can_publish": lambda *_: publish})()

    def test_ai_job_idempotency_is_scoped_by_user_and_checked_before_quota(self):
        from app.core.errors import AiJobRunning, AiJobNotFound, IdempotencyConflict
        a, b = self._job_user(), self._job_user()
        job, replay = self._accept(a, "k1")
        self.assertFalse(replay)
        self.assertEqual(job.status, "Processing")
        self.assertAlmostEqual((job.deadline_at - job.accepted_at).total_seconds(), 120, delta=1)
        # Gửi lại cùng key cùng dữ liệu: trả job cũ, không tính lượt dù đang có job chạy.
        again, replay = self._accept(a, "k1", policy=self._allow())
        self.assertEqual((again.id, replay), (job.id, True))
        # Policy mặc định từ chối đọc lại.
        with self.assertRaises(AiJobNotFound):
            self._accept(a, "k1")
        with self.assertRaises(IdempotencyConflict):
            self._accept(a, "k1", {"source_ids": [1], "length": "detailed"})
        # Cùng key ở người dùng khác là job khác, không replay chéo.
        other, replay = self._accept(b, "k1")
        self.assertNotEqual(other.id, job.id)
        self.assertFalse(replay)
        # Key mới trong khi còn job chạy: từ chối và không ghi job.
        with self.assertRaises(AiJobRunning) as caught:
            self._accept(a, "k2")
        self.assertGreaterEqual(caught.exception.retry_after_seconds, 1)
        with db.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM ai_jobs WHERE user_id=%s", (a,)).fetchone()[0], 1)

    def test_ai_job_two_concurrent_requests_accept_only_one(self):
        from app.core.errors import AiJobRunning
        user = self._job_user()
        barrier = threading.Barrier(2)

        def attempt(key):
            barrier.wait()
            try:
                return self._accept(user, key)[0].id
            except AiJobRunning:
                return "rejected"

        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(attempt, ["c1", "c2"]))
        self.assertEqual(results.count("rejected"), 1, results)
        with db.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM ai_jobs WHERE user_id=%s AND status='Processing'", (user,)).fetchone()[0], 1)

    def test_ai_job_rate_limit_counts_accepted_jobs_in_sliding_window(self):
        from app.core.errors import AiRateLimited
        user = self._job_user()
        with db.get_conn() as conn:
            for index in range(10):
                conn.execute(
                    "INSERT INTO ai_jobs(user_id,job_type,idempotency_key,request_fingerprint,input_snapshot,status,error_code,"
                    "accepted_at,deadline_at,finished_at,idempotency_expires_at) VALUES(%s,'summary',%s,'fp','{}','Failed','x',"
                    "clock_timestamp()-interval '50 seconds'+%s*interval '1 second',clock_timestamp()+interval '1 minute',clock_timestamp(),clock_timestamp()+interval '1 day')",
                    (user, f"old-{index}", index),
                )
        with self.assertRaises(AiRateLimited) as caught:
            self._accept(user, "eleventh")
        self.assertTrue(1 <= caught.exception.retry_after_seconds <= 11, caught.exception.retry_after_seconds)
        with db.get_conn() as conn:
            conn.execute("UPDATE ai_jobs SET accepted_at=accepted_at-interval '61 seconds' WHERE user_id=%s AND idempotency_key='old-0'", (user,))
        job, _ = self._accept(user, "eleventh")
        self.assertEqual(job.status, "Processing")

    def test_ai_job_expired_after_deadline_frees_slot_and_cannot_publish(self):
        from app.core.ai_jobs import JobOutcome, get_job, publish
        from app.core.errors import DeadlineExceeded
        user = self._job_user()
        job, _ = self._accept(user, "late")
        with db.get_conn() as conn:
            conn.execute("UPDATE ai_jobs SET accepted_at=accepted_at-interval '200 seconds', deadline_at=clock_timestamp()-interval '1 second' WHERE id=%s", (job.id,))
        stale = get_job(user, job_id=job.id, policy=self._allow())
        self.assertEqual((stale.status, stale.error_code), ("Failed", "deadline_exceeded"))
        written = []
        with self.assertRaises(DeadlineExceeded):
            publish(job, JobOutcome("Succeeded"), policy=self._allow(), write_result=lambda *_: written.append(1))
        self.assertEqual(written, [])
        fresh, _ = self._accept(user, "after-late")
        self.assertEqual(fresh.status, "Processing")

    def test_ai_job_publish_fence_uses_policy_and_rolls_back_result(self):
        from app.core.ai_jobs import JobOutcome, get_job, publish, run_job
        from app.core.errors import PublishBlocked
        user = self._job_user()
        with db.get_conn() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS test_outputs(id serial PRIMARY KEY, job_id uuid)")

        def write(conn, job, outcome):
            return conn.execute("INSERT INTO test_outputs(job_id) VALUES(%s) RETURNING id", (job.id,)).fetchone()[0]

        blocked, _ = self._accept(user, "blocked")
        outcome = run_job(blocked, lambda job: JobOutcome("Succeeded", {"text": "fixture"}))
        with self.assertRaises(PublishBlocked):
            publish(blocked, outcome, write_result=write)  # DenyAllPolicy mặc định
        state = get_job(user, job_id=blocked.id, policy=self._allow())
        self.assertEqual((state.status, state.error_code, state.result_ref), ("Failed", "publish_blocked", None))

        ok, _ = self._accept(user, "ok")
        done = publish(ok, run_job(ok, lambda job: JobOutcome("Succeeded")), policy=self._allow(), write_result=write)
        self.assertEqual(done.status, "Succeeded")
        self.assertIsNotNone(done.finished_at)
        with db.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM test_outputs WHERE job_id=%s", (blocked.id,)).fetchone()[0], 0)
            self.assertEqual(str(conn.execute("SELECT id FROM test_outputs WHERE job_id=%s", (ok.id,)).fetchone()[0]), done.result_ref)

        no_evidence, _ = self._accept(user, "noevidence")
        result = publish(no_evidence, JobOutcome("NoEvidence"), policy=self._allow())
        self.assertEqual(result.status, "NoEvidence")

    def test_ai_job_executor_errors_become_stable_failed_codes(self):
        from app.core.ai_jobs import run_job, get_job, job_usage, record_usage
        from app.core.errors import ProviderTimeout, ServiceError
        from app.core.fault_injection import check_fixture_fault, inject_provider_faults
        user = self._job_user()
        job, _ = self._accept(user, "fault")

        def executor(job):
            record_usage(job, {"provider": "deepseek", "model": "m", "attempt": 1, "outcome": "timeout", "latency_ms": 5})
            check_fixture_fault("deepseek")

        with inject_provider_faults({"deepseek": ["timeout"]}), self.assertRaises(ProviderTimeout):
            run_job(job, executor)
        state = get_job(user, job_id=job.id, policy=self._allow())
        self.assertEqual((state.status, state.error_code), ("Failed", "provider_timeout"))
        self.assertEqual(job_usage(job)[0]["provider"], "deepseek")

        crash, _ = self._accept(user, "crash", retry_of=job.id)
        self.assertEqual(crash.retry_of, job.id)
        with self.assertRaises(ServiceError) as caught:
            run_job(crash, lambda job: (_ for _ in ()).throw(RuntimeError("prompt text must not leak")))
        self.assertEqual(caught.exception.code, "internal_error")
        self.assertEqual(get_job(user, job_id=crash.id, policy=self._allow()).error_code, "internal_error")

    def test_ai_job_status_endpoint_checks_session_owner_and_policy(self):
        from app.core.ai_jobs import _POLICIES
        owner_id, owner_token = self._auth_session()
        _, other_token = self._auth_session()
        job, _ = self._accept(owner_id, "endpoint")
        with patch.dict(os.environ, {"BETTER_AUTH_SECRET": "test-secret"}):
            owner = {"insighthub.session_token": self._signed(owner_token, "test-secret")}
            other = {"insighthub.session_token": self._signed(other_token, "test-secret")}
            self.assertEqual(self.client.get(f"/ai-jobs/{job.id}").status_code, 401)
            denied = self.client.get(f"/ai-jobs/{job.id}", cookies=owner)
            self.assertEqual((denied.status_code, denied.json()["code"]), (404, "ai_job_not_found"))
            _POLICIES["summary"] = self._allow()
            try:
                ok = self.client.get(f"/ai-jobs/{job.id}", cookies=owner)
                self.assertEqual((ok.status_code, ok.json()["status"]), (200, "Processing"))
                self.assertNotIn("input_snapshot", ok.json())
                by_key = self.client.get("/ai-jobs/by-key/summary/endpoint", cookies=owner)
                self.assertEqual(by_key.json()["id"], job.id)
                self.assertEqual(self.client.get(f"/ai-jobs/{job.id}", cookies=other).status_code, 404)
                self.assertEqual(self.client.get("/ai-jobs/not-a-uuid", cookies=owner).status_code, 404)
            finally:
                _POLICIES.pop("summary")

    def test_ai_job_processing_is_failed_on_restart_and_key_released_after_ttl(self):
        user = self._job_user()
        job, _ = self._accept(user, "restart")
        with db.get_conn() as conn:
            recover_interrupted_operations(conn)
            self.assertEqual(conn.execute("SELECT status,error_code FROM ai_jobs WHERE id=%s", (job.id,)).fetchone(), ("Failed", "interrupted"))
            conn.execute("UPDATE ai_jobs SET idempotency_expires_at=now()-interval '1 second' WHERE id=%s", (job.id,))
        reused, replay = self._accept(user, "restart", {"source_ids": [2], "length": "short"})
        self.assertFalse(replay)
        self.assertNotEqual(reused.id, job.id)
        with db.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT idempotency_key FROM ai_jobs WHERE id=%s", (job.id,)).fetchone()[0], None)
