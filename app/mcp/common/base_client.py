from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import httpx


@dataclass
class BaseAPIClient:
    """Lightweight synchronous HTTP client wrapper."""

    base_url: str
    api_key: Optional[str] = None
    timeout: float = 15.0
    default_headers: Dict[str, str] = field(default_factory=dict)

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json", **self.default_headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, headers=self._headers(), timeout=self.timeout)

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        with self._client() as client:
            response = client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    def post(self, path: str, json: Optional[dict] = None, params: Optional[dict] = None) -> dict:
        with self._client() as client:
            response = client.post(path, json=json, params=params)
            response.raise_for_status()
            return response.json()
