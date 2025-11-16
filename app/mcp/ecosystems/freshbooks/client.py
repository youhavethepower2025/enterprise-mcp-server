from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from app.core.config import settings
from app.mcp.common.base_client import BaseAPIClient
from app.mcp.common.mock_data import sample_freshbooks_clients, sample_freshbooks_invoices

logger = logging.getLogger(__name__)


class FreshBooksClient(BaseAPIClient):
    """Client wrapper for FreshBooks Accounting API."""

    def __init__(self) -> None:
        account_id = settings.freshbooks_account_id
        base_url = settings.freshbooks_base_url.rstrip("/") if settings.freshbooks_base_url else ""
        if account_id:
            base_url = f"{base_url}/{account_id}"
        super().__init__(
            base_url=base_url or "https://api.freshbooks.com/accounting/account",
            api_key=settings.freshbooks_access_token,
            default_headers={"Accept": "application/json"},
        )
        self.account_id = account_id

    def _credentials_ready(self) -> bool:
        return bool(self.api_key and self.account_id)

    def list_invoices(self, params: Dict[str, Any] | None = None) -> List[dict]:
        fallback = sample_freshbooks_invoices()
        if not self._credentials_ready():
            logger.warning("FreshBooks credentials missing, returning sample invoices")
            return fallback
        try:
            response = self.get("/invoices/invoices", params=params)
            invoices = response.get("response", {}).get("result", {}).get("invoices", [])
            normalized = [self._normalize_invoice(inv) for inv in invoices]
            logger.info("Fetched %s FreshBooks invoices", len(normalized))
            return normalized or fallback
        except httpx.HTTPStatusError as exc:
            logger.error("FreshBooks invoice API error: %s - %s", exc.response.status_code, exc.response.text)
            return fallback
        except httpx.RequestError as exc:
            logger.error("FreshBooks invoice network error: %s", exc)
            return fallback

    def create_invoice(self, invoice: Dict[str, Any]) -> dict:
        if not self._credentials_ready():
            logger.warning("FreshBooks credentials missing, returning mock invoice payload")
            return {"invoice_id": "FB-MOCK", "status": "mock_created", "payload": invoice}
        try:
            response = self.post("/invoices/invoices", json={"invoice": invoice})
            created = response.get("response", {}).get("result", {}).get("invoice", {})
            logger.info("Created FreshBooks invoice %s", created.get("invoiceid"))
            return {
                "invoice_id": created.get("invoiceid"),
                "status": created.get("status"),
                "amount": created.get("amount", {}).get("amount"),
                "raw": created,
            }
        except httpx.HTTPStatusError as exc:
            logger.error("FreshBooks invoice create error: %s - %s", exc.response.status_code, exc.response.text)
            return {"invoice_id": "ERROR", "status": "failed", "error": exc.response.text}

    def list_clients(self, params: Dict[str, Any] | None = None) -> List[dict]:
        fallback = sample_freshbooks_clients()
        if not self._credentials_ready():
            logger.warning("FreshBooks credentials missing, returning sample clients")
            return fallback
        try:
            response = self.get("/users/clients", params=params)
            clients = response.get("response", {}).get("result", {}).get("clients", [])
            normalized = [self._normalize_client(client) for client in clients]
            logger.info("Fetched %s FreshBooks clients", len(normalized))
            return normalized or fallback
        except httpx.HTTPStatusError as exc:
            logger.error("FreshBooks client API error: %s - %s", exc.response.status_code, exc.response.text)
            return fallback
        except httpx.RequestError as exc:
            logger.error("FreshBooks client network error: %s", exc)
            return fallback

    def create_client(self, client: Dict[str, Any]) -> dict:
        if not self._credentials_ready():
            logger.warning("FreshBooks credentials missing, returning mock client payload")
            return {"client_id": "FB-MOCK-CLIENT", "status": "mock_created", "payload": client}
        try:
            response = self.post("/users/clients", json={"client": client})
            created = response.get("response", {}).get("result", {}).get("client", {})
            logger.info("Created FreshBooks client %s", created.get("id"))
            return {"client_id": created.get("id"), "organization": created.get("organization"), "raw": created}
        except httpx.HTTPStatusError as exc:
            logger.error("FreshBooks client create error: %s - %s", exc.response.status_code, exc.response.text)
            return {"client_id": "ERROR", "status": "failed", "error": exc.response.text}

    @staticmethod
    def _normalize_invoice(invoice: dict) -> dict:
        return {
            "invoice_id": invoice.get("invoiceid"),
            "status": invoice.get("status"),
            "amount": float(invoice.get("amount", {}).get("amount", 0)),
            "client": invoice.get("organization") or invoice.get("customerid"),
        }

    @staticmethod
    def _normalize_client(client: dict) -> dict:
        return {
            "id": client.get("id"),
            "organization": client.get("organization"),
            "email": client.get("email"),
            "first_name": client.get("first_name"),
            "last_name": client.get("last_name"),
        }
