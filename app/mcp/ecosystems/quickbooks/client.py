from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from app.core.config import settings
from app.mcp.common.base_client import BaseAPIClient
from app.mcp.common.mock_data import sample_invoices

logger = logging.getLogger(__name__)


class QuickBooksClient(BaseAPIClient):
    def __init__(self) -> None:
        base_url = settings.quickbooks_base_url
        if settings.quickbooks_company_id:
            base_url = f"{base_url}/{settings.quickbooks_company_id}"
        super().__init__(
            base_url=base_url,
            api_key=settings.quickbooks_access_token,
            default_headers={"Accept": "application/json"},
        )
        self.company_id = settings.quickbooks_company_id
        self.default_customer_id = settings.quickbooks_default_customer_id

    def ledger_summary(self) -> List[dict]:
        """
        Query QuickBooks for open invoices. Falls back to sample data if credentials are missing.
        """

        fallback = sample_invoices()
        if not self.api_key or not self.company_id:
            logger.warning("QuickBooks credentials incomplete, returning sample invoices")
            return fallback

        query = "SELECT Id, DocNumber, Balance, TotalAmt, DueDate, EmailStatus, CustomerRef FROM Invoice WHERE Balance > '0'"

        try:
            response = self.post(
                "/query",
                params={"minorversion": "65"},
                json={"query": query},
            )
            invoices_raw = response.get("QueryResponse", {}).get("Invoice", [])
            invoices = [self._transform_invoice(invoice) for invoice in invoices_raw]
            logger.info("Successfully fetched %s invoices from QuickBooks", len(invoices))
            return invoices or fallback

        except httpx.HTTPStatusError as exc:
            logger.error(
                "QuickBooks API error: %s - %s",
                exc.response.status_code,
                exc.response.text,
            )
            if exc.response.status_code == 401:
                logger.error("QuickBooks access token may be expired - refresh required")
            return fallback
        except httpx.RequestError as exc:
            logger.error("QuickBooks network error: %s", exc)
            return fallback
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error fetching QuickBooks invoices: %s", exc)
            return fallback

    def create_invoice(self, payload: dict) -> dict:
        """
        Create a draft invoice in QuickBooks, falling back to mock response when credentials are missing.
        """

        if not self.api_key or not self.company_id:
            logger.warning("QuickBooks credentials incomplete, returning mock response")
            return {"invoice_id": "MOCK-INV-001", "status": "mock_created", "echo": payload}

        customer_id = payload.get("customer_id") or self.default_customer_id
        customer_name = payload.get("customer")
        if not customer_id and customer_name:
            customer_id = self._lookup_customer_id(customer_name)

        if not customer_id:
            logger.error("Unable to determine QuickBooks customer ID for payload: %s", payload)
            return {"invoice_id": "ERROR", "status": "failed", "error": "missing_customer_id"}

        qb_payload = self._build_invoice_payload(payload, customer_id)

        try:
            response = self.post(
                "/invoice",
                params={"minorversion": "65"},
                json=qb_payload,
            )
            invoice = response.get("Invoice", {})
            invoice_id = invoice.get("DocNumber") or invoice.get("Id")
            logger.info("Successfully created invoice %s in QuickBooks", invoice_id)
            return {
                "invoice_id": invoice_id,
                "status": invoice.get("EmailStatus") or invoice.get("PrivateNote") or "created",
                "customer": customer_name,
                "amount": invoice.get("TotalAmt"),
            }

        except httpx.HTTPStatusError as exc:
            logger.error(
                "QuickBooks API error creating invoice: %s - %s",
                exc.response.status_code,
                exc.response.text,
            )
            return {"invoice_id": "ERROR", "status": "failed", "error": exc.response.text}
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error creating QuickBooks invoice: %s", exc)
            return {"invoice_id": "ERROR", "status": "failed", "error": str(exc)}

    def _lookup_customer_id(self, customer_name: str) -> Optional[str]:
        """
        Attempt to look up a CustomerRef ID by display name.
        """

        if not customer_name:
            return None

        safe_name = customer_name.replace("'", "''")
        query = f"SELECT Id, DisplayName FROM Customer WHERE DisplayName = '{safe_name}'"
        try:
            response = self.post("/query", params={"minorversion": "65"}, json={"query": query})
            customers = response.get("QueryResponse", {}).get("Customer", [])
            if not customers:
                logger.warning("No QuickBooks customer found for name '%s'", customer_name)
                return None
            customer_id = customers[0].get("Id")
            logger.info("Resolved customer '%s' to ID %s", customer_name, customer_id)
            return customer_id
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to look up QuickBooks customer '%s': %s", customer_name, exc)
            return None

    @staticmethod
    def _transform_invoice(invoice: dict) -> dict:
        return {
            "invoice_id": invoice.get("DocNumber") or invoice.get("Id"),
            "status": invoice.get("EmailStatus") or invoice.get("TxnStatus"),
            "amount": float(invoice.get("Balance") or invoice.get("TotalAmt") or 0),
            "due_date": invoice.get("DueDate"),
            "customer": (
                invoice.get("CustomerRef", {}).get("name")
                or invoice.get("CustomerRef", {}).get("value")
            ),
        }

    @staticmethod
    def _build_invoice_payload(payload: dict, customer_id: str) -> dict:
        line_items = payload.get("line_items", [])
        qb_lines = [
            {
                "Amount": item.get("amount"),
                "DetailType": "SalesItemLineDetail",
                "Description": item.get("description"),
                "SalesItemLineDetail": {
                    "ItemRef": {"value": item.get("item_ref", "1")},
                    "Qty": item.get("quantity", 1),
                },
            }
            for item in line_items
        ]

        total_amt = sum(item.get("amount", 0) for item in line_items)

        qb_payload = {
            "Line": qb_lines,
            "CustomerRef": {"value": customer_id},
            "PrivateNote": payload.get("note", "Generated via MCP"),
            "BillEmail": {"Address": payload.get("billing_email")},
            "TxnDate": payload.get("transaction_date"),
            "DueDate": payload.get("due_date"),
            "TotalAmt": total_amt or payload.get("amount"),
        }
        return qb_payload
