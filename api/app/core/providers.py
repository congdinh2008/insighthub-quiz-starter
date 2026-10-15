"""Small REST adapters share bounded timeouts and sanitized transport errors."""

import logging
import random
import time
import httpx

from app.core.config import get_settings
from app.core.errors import ProviderError, ProviderRateLimited, ProviderTimeout
from app.core.deadline import check_deadline, remaining_timeout
from app.core.fault_injection import transport_for

logger = logging.getLogger("insighthub.providers")


def post_json(
    url: str,
    *,
    headers: dict,
    payload: dict,
    timeout_seconds: float | None = None,
    response_type: type = dict,
) -> dict | list:
    settings = get_settings()
    configured_timeout = timeout_seconds or settings.provider_timeout_seconds
    retryable_status = {429, 502, 503, 504}
    last_rate_limited = False
    for attempt in range(settings.provider_retry_attempts):
        try:
            # Do not inherit proxies, follow redirects, or log bodies, headers or URLs.
            # transport_for chỉ khác None trong test có inject_provider_faults (app/core/fault_injection.py).
            with httpx.Client(
                timeout=remaining_timeout(configured_timeout),
                trust_env=False,
                follow_redirects=False,
                transport=transport_for(url),
            ) as client:
                response = client.post(url, headers=headers, json=payload)
                last_rate_limited = response.status_code == 429
                response.raise_for_status()
                data = response.json()
                if response_type not in (dict, list) or not isinstance(data, response_type):
                    raise ValueError("Invalid JSON response type")
                return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in retryable_status:
                logger.warning("AI provider request failed: non-retryable status")
                raise ProviderError() from None
        except httpx.TimeoutException:
            logger.warning("AI provider request timed out")
            check_deadline()
        except httpx.RequestError:
            logger.warning("AI provider transport failed")
        except ValueError:
            logger.warning("AI provider returned invalid JSON")
            raise ProviderError() from None
        if attempt + 1 < settings.provider_retry_attempts:
            delay = min(0.25 * (2**attempt) + random.uniform(0, 0.1), 1.0)
            time.sleep(min(delay, remaining_timeout(delay)))
    if last_rate_limited:
        raise ProviderRateLimited() from None
    raise ProviderTimeout() from None


def token_count(value) -> int | None:
    return value if type(value) is int and value >= 0 else None


def indexed_embeddings(data: dict, count: int) -> list:
    items = data["data"]
    if len(items) != count or any(type(item.get("index")) is not int for item in items):
        raise ProviderError()
    if sorted(item["index"] for item in items) != list(range(count)):
        raise ProviderError()
    return [item["embedding"] for item in sorted(items, key=lambda item: item["index"])]
