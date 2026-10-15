"""Adapters turn a golden-set case into an API call and a normalized output.

ChatAdapter works against the Starter API as shipped. After Auth is added, set
INSIGHTHUB_EVAL_COOKIE or INSIGHTHUB_SESSION_COOKIE (session cookie of test
account A, see scripts/session_cookie.py) in the shell; it is sent as a Cookie
header on upload, chat and cleanup and never written to reports.

SummaryAdapter and QuizAdapter are learner work (LR-16..18, LR-23): implement
`run()` against your own API and return the normalized shape in graders.py.
"""
import json
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from run_aev import call, upload  # noqa: E402

CORPUS = ROOT / "evaluation" / "corpus"


def auth_headers():
    cookie = os.environ.get("INSIGHTHUB_EVAL_COOKIE", "") or os.environ.get("INSIGHTHUB_SESSION_COOKIE", "")
    return {"Cookie": cookie} if cookie else {}


class Adapter:
    tool = ""

    def __init__(self, base):
        self.base = base.rstrip("/")
        self.documents = {}
        self.created = []

    def ensure_sources(self, names):
        for name in names:
            if name in self.documents:
                continue
            status, raw, _ = upload(self.base, CORPUS / name, auth_headers())
            body = json.loads(raw or b"{}")
            identifier = body.get("id") or body.get("document_id")
            if status not in (200, 201) or not identifier:
                raise RuntimeError(f"Upload failed for {name}: HTTP {status}")
            if not body.get("deduplicated", False):
                self.created.append(identifier)
            self.documents[name] = identifier
        return [self.documents[n] for n in names]

    def cleanup(self):
        for identifier in self.created:
            call(self.base, f"/documents/{identifier}", "DELETE",
                 headers={"Idempotency-Key": "eval-delete-" + uuid.uuid4().hex, **auth_headers()})

    def run(self, case, document_ids):
        raise NotImplementedError


class ChatAdapter(Adapter):
    tool = "chat"

    def run(self, case, document_ids):
        payload = json.dumps({"question": case["input"], "document_ids": document_ids}, ensure_ascii=False).encode()
        start = time.perf_counter()
        status, raw, headers = call(self.base, "/chat", "POST", payload, {
            "Content-Type": "application/json", "Idempotency-Key": "eval-chat-" + uuid.uuid4().hex, **auth_headers()})
        body = json.loads(raw or b"{}")
        return {
            "http_status": status,
            "request_id": next((v for k, v in headers.items() if k.lower() == "x-request-id"), None),
            "status": body.get("status"),
            "text": body.get("answer") or "",
            "claims": body.get("claims") or [],
            "citations": body.get("citations") or [],
            "meta": {"latency_ms": int((time.perf_counter() - start) * 1000),
                     "prompt_version": body.get("prompt_version"), "model": body.get("model"),
                     "usage": body.get("usage") or {}},
        }


class SummaryAdapter(Adapter):
    tool = "summary"

    def run(self, case, document_ids):
        raise NotImplementedError(
            "LR-23: gọi API Summary của bài làm với document_ids và case['config'] (length), "
            "chờ tác vụ kết thúc, trả output theo shape trong graders.py (text, claims, citations, meta)."
        )


class QuizAdapter(Adapter):
    tool = "quiz"

    def run(self, case, document_ids):
        raise NotImplementedError(
            "LR-23: gọi API Quiz của bài làm với document_ids và case['config'] (question_count), "
            "đọc bản nội bộ có đáp án bằng quyền phù hợp, trả output có quiz.questions theo graders.py."
        )


ADAPTERS = {cls.tool: cls for cls in (ChatAdapter, SummaryAdapter, QuizAdapter)}
