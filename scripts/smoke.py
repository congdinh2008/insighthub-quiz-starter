"""Local fixture smoke. Deletes only documents created by this invocation.

Sau khi khóa endpoint bằng phiên (LR-12), đặt INSIGHTHUB_SESSION_COOKIE (xem scripts/session_cookie.py);
smoke gửi cookie này kèm mọi request. Không đặt thì chạy như Starter gốc (endpoint demo công khai).
"""
import argparse
import json
import os
import uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

parser = argparse.ArgumentParser()
parser.add_argument("--api-url", default="http://127.0.0.1:8107")
parser.add_argument("--web-url", default="http://127.0.0.1:3107")
args = parser.parse_args()

SESSION_COOKIE = os.environ.get("INSIGHTHUB_SESSION_COOKIE", "")

def call(base, path, method="GET", data=None, headers=None):
    headers = dict(headers or {})
    if SESSION_COOKIE:
        headers.setdefault("Cookie", SESSION_COOKIE)
    req = Request(base + path, data=data, method=method, headers=headers)
    try:
        with urlopen(req, timeout=130) as res:
            return res.status, res.read()
    except HTTPError as exc:
        return exc.code, exc.read()

def upload(filename, content, origin=None):
    boundary = "----sdlc" + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: text/plain\r\n\r\n').encode() + content + f"\r\n--{boundary}--\r\n".encode()
    headers = {"Content-Type": "multipart/form-data; boundary=" + boundary}
    headers["Idempotency-Key"] = "smoke-upload-" + uuid.uuid4().hex
    if origin:
        headers["Origin"] = origin
    return call(args.api_url, "/documents", "POST", body, headers)

created = []
try:
    for base, path in [(args.api_url, "/healthz"), (args.api_url, "/readyz"), (args.web_url, "/api/health")]:
        assert call(base, path)[0] == 200, path
    status, body = call(args.web_url, "/")
    assert status == 200 and b"InsightHub SDLC" in body and b"DO2603" not in body
    status, body = call(args.api_url, "/")
    assert status == 200 and json.loads(body)["mode"] == "fixture", "Smoke requires fixture mode"
    name = "sdlc-smoke-" + uuid.uuid4().hex + ".md"
    status, body = upload(name, b"InsightHub accepts text documents up to 10 MB.")
    assert status == 201, (status, body)
    document = json.loads(body)
    created.append(document["id"])
    pdf_path = Path(__file__).resolve().parents[1] / "evaluation/corpus/03_reference.pdf"
    pdf_name = "sdlc-smoke-" + uuid.uuid4().hex + ".pdf"
    status, body = upload(pdf_name, pdf_path.read_bytes())
    assert status == 201, (status, body)
    pdf_document = json.loads(body)
    created.append(pdf_document["id"])
    status, body = call(args.api_url, "/documents")
    found = next(item for item in json.loads(body) if item["id"] == created[0])
    assert status == 200 and found["status"] == "ready" and found["chunk_count"] > 0
    status, body = call(args.api_url, "/chat", "POST", json.dumps({"question": "What is the file limit?", "document_ids": [document["id"]]}).encode(), {"Content-Type": "application/json", "Idempotency-Key": "smoke-chat-" + uuid.uuid4().hex})
    answer = json.loads(body)
    assert status == 200 and answer["status"] == "Answered" and "FIXTURE" in answer["answer"] and name in answer["sources"] and answer["citations"]
    citation = answer["citations"][0]
    status, body = call(args.api_url, f"/documents/{citation['document_id']}/source?segment_id={citation['source_segment_id']}")
    assert status == 200 and json.loads(body)["content"], "Citation source cannot be opened"
    assert upload("bad.exe", b"invalid")[0] == 400
    assert upload("foreign.md", b"blocked", "https://foreign.example")[0] == 403
    assert call(args.web_url, "/api/proxy?target=chat", "POST", b'{"question":"test"}', {"Content-Type": "application/json", "Origin": "https://foreign.example"})[0] == 403
    print("PASS: health, web, MD/PDF upload, source locator, chat, validation and origin guards")
finally:
    for document_id in created:
        status, _ = call(args.api_url, f"/documents/{document_id}", "DELETE", headers={"Idempotency-Key": "smoke-delete-" + uuid.uuid4().hex})
        assert status == 204, "Smoke cleanup failed"
