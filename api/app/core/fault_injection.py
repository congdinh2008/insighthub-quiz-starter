"""Giả lập lỗi nhà cung cấp AI để kiểm retry và fallback mà không gọi dịch vụ thật (AI Job scaffold).

Hai cách dùng, cả hai chỉ dành cho test và chạy thử:

1. Trong test, bọc lời gọi bằng `inject_provider_faults`. Mỗi lần gọi provider lấy một phần tử của kế hoạch:

       with inject_provider_faults({"deepseek": ["timeout", "429", "503"]}):
           executor(job)   # lời gọi deepseek thất bại cả 3 lần, code fallback của học viên phải chuyển provider

   Áp dụng cho `post_json` (đường HTTP thật, kể cả retry có sẵn) và cho nhánh fixture của học viên qua
   `check_fixture_fault(provider)`. Phần tử dạng dict `{"json": {...}}` trả HTTP 200 với body đó.
   Hết kế hoạch thì lời gọi tiếp theo chạy bình thường.

2. Chạy thử thủ công ở chế độ fixture: đặt `AI_FIXTURE_FAULTS=deepseek:timeout` (nhiều provider ngăn bằng dấu phẩy).
   Chỉ có hiệu lực khi RAG_MODE=fixture, provider đó luôn thất bại theo lỗi đã chọn.

Lỗi hỗ trợ: timeout, 429, 500, 502, 503, invalid_json. Không ghi body hay header của request.
"""

import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from urllib.parse import urlsplit

import httpx

from app.core.errors import ProviderError, ProviderRateLimited, ProviderTimeout

FAULTS = {"timeout", "429", "500", "502", "503", "invalid_json"}

# Tên provider theo host mặc định của các adapter trong app/services/llm.py và embeddings.py.
KNOWN_HOSTS = {
    "api.deepseek.com": "deepseek",
    "generativelanguage.googleapis.com": "gemini",
    "api.anthropic.com": "anthropic",
    "api.openai.com": "openai",
    "api.cohere.com": "cohere",
}

_plan: ContextVar[dict[str, list] | None] = ContextVar("provider_fault_plan", default=None)


def _validate(item):
    if isinstance(item, dict) and set(item) == {"json"}:
        return item
    if item in FAULTS:
        return item
    raise ValueError(f"Lỗi giả lập không hỗ trợ: {item!r}. Dùng một trong {sorted(FAULTS)} hoặc {{'json': ...}}")


@contextmanager
def inject_provider_faults(plan: dict[str, list]):
    """Kế hoạch lỗi theo provider (tên như "deepseek" hoặc host như "api.deepseek.com")."""
    copied = {name: [_validate(item) for item in items] for name, items in plan.items()}
    token = _plan.set(copied)
    try:
        yield copied
    finally:
        _plan.reset(token)


def _env_faults() -> dict[str, str]:
    from app.core.config import get_settings

    raw = os.environ.get("AI_FIXTURE_FAULTS", "").strip()
    if not raw or get_settings().rag_mode != "fixture":
        return {}
    faults = {}
    for part in raw.split(","):
        name, _, fault = part.strip().partition(":")
        if name and fault in FAULTS:
            faults[name.strip()] = fault
    return faults


def next_fault(provider: str):
    """Phần tử kế tiếp cho provider, hoặc None nếu không giả lập."""
    plan = _plan.get()
    if plan is not None:
        items = plan.get(provider)
        if items:
            return items.pop(0)
        return None
    return _env_faults().get(provider)


def raise_fault(fault) -> None:
    """Chuyển lỗi giả lập thành đúng lỗi công khai mà adapter thật sẽ ném sau khi hết retry."""
    if fault == "timeout":
        raise ProviderTimeout()
    if fault == "429":
        raise ProviderRateLimited()
    if fault in {"500", "502", "503", "invalid_json"}:
        raise ProviderError()


def check_fixture_fault(provider: str) -> None:
    """Gọi ở đầu nhánh fixture của executor để kiểm fallback khi không có mạng."""
    fault = next_fault(provider)
    if fault is not None and not isinstance(fault, dict):
        raise_fault(fault)


class _FaultTransport(httpx.BaseTransport):
    def __init__(self, fault):
        self.fault = fault

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if self.fault == "timeout":
            raise httpx.ReadTimeout("injected timeout", request=request)
        if self.fault == "invalid_json":
            return httpx.Response(200, content=b"not-json", request=request)
        if isinstance(self.fault, dict):
            return httpx.Response(200, content=json.dumps(self.fault["json"]).encode(), request=request)
        return httpx.Response(int(self.fault), json={"error": "injected"}, request=request)


def transport_for(url: str) -> httpx.BaseTransport | None:
    """Dùng trong providers.post_json: trả transport giả lập nếu kế hoạch có lỗi cho host hoặc provider này."""
    plan = _plan.get()
    if not plan:
        return None
    host = urlsplit(url).hostname or ""
    for name in (host, KNOWN_HOSTS.get(host)):
        if name and plan.get(name):
            return _FaultTransport(plan[name].pop(0))
    return None
