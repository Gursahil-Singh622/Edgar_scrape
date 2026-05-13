from __future__ import annotations

import logging
import time
from typing import Any

import requests

from config import settings


LOGGER = logging.getLogger(__name__)


class SECClient:
    """Small responsible HTTP client for SEC public endpoints."""

    def __init__(self, user_agent: str | None = None, request_delay_seconds: float | None = None) -> None:
        self.user_agent = user_agent or settings.sec_user_agent
        self.request_delay_seconds = request_delay_seconds or settings.request_delay_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Host": "www.sec.gov",
            }
        )
        self._last_request_at = 0.0

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        self._throttle()
        headers = kwargs.pop("headers", {})
        if url.startswith(settings.sec_data_url):
            headers = {"Host": "data.sec.gov", **headers}
        response = self.session.get(url, headers=headers, timeout=30, **kwargs)
        if response.status_code in {429, 503}:
            retry_after = int(response.headers.get("Retry-After", "2"))
            LOGGER.warning("SEC rate limited request to %s; retrying after %s seconds", url, retry_after)
            time.sleep(retry_after)
            self._throttle()
            response = self.session.get(url, headers=headers, timeout=30, **kwargs)
        response.raise_for_status()
        return response

    def get_json(self, url: str) -> dict[str, Any]:
        return self.get(url).json()

    def get_text(self, url: str) -> str:
        return self.get(url).text

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.request_delay_seconds:
            time.sleep(self.request_delay_seconds - elapsed)
        self._last_request_at = time.monotonic()
