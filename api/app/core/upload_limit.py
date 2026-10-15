"""Bound the entire multipart body before parsing, including chunked HTTP requests."""

import re

from fastapi.responses import JSONResponse

from app.core.config import get_settings


class UploadLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or not (
                scope["path"].rstrip("/") == "/documents"
                or re.fullmatch(r"/documents/[1-9][0-9]*/retry/?", scope["path"])
            )
        ):
            return await self.app(scope, receive, send)
        # Allow multipart headers/boundaries in addition to the actual file limit.
        limit = get_settings().max_upload_bytes + 64 * 1024
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
            if length < 0:
                raise ValueError
        except ValueError:
            return await JSONResponse({"detail": "Content-Length không hợp lệ.", "code": "invalid_content_length"}, 400)(
                scope, receive, send
            )
        if length > limit:
            return await JSONResponse({"detail": "Upload quá lớn.", "code": "upload_too_large"}, 413)(
                scope, receive, send
            )
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            data = message.get("body", b"")
            if len(body) + len(data) > limit:
                return await JSONResponse({"detail": "Upload quá lớn.", "code": "upload_too_large"}, 413)(
                    scope, receive, send
                )
            body.extend(data)
            if not message.get("more_body", False):
                break
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        return await self.app(scope, bounded_receive, send)
