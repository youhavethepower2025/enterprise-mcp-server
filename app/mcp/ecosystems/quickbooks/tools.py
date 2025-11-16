from __future__ import annotations

from app.mcp.base import BaseTool
from app.mcp.ecosystems.quickbooks.client import QuickBooksClient
from app.mcp.models import ToolMetadata, ToolResponse

DOCS_PREFIX = "Docs/quickbooks"


class QuickBooksLedgerSummaryTool(BaseTool):
    metadata = ToolMetadata(
        name="quickbooks.ledger_summary",
        description="Summarize outstanding invoices for finance reviews.",
        ecosystem="quickbooks",
        docs_path=f"{DOCS_PREFIX}/endpoints.md",
        requires_secrets=["QUICKBOOKS_ACCESS_TOKEN"],
    )

    def __init__(self, client: QuickBooksClient) -> None:
        super().__init__(client=client)

    def run(self) -> ToolResponse:
        invoices = self.client.ledger_summary()
        source = "live" if self.client.api_key else "sample"
        total = sum(invoice["amount"] for invoice in invoices)
        return ToolResponse(
            status="ok",
            data={"invoices": invoices, "total_open": total},
            metadata={"source": source},
        )


class QuickBooksDraftInvoiceTool(BaseTool):
    metadata = ToolMetadata(
        name="quickbooks.create_draft_invoice",
        description="Create a draft invoice for MedTainer wholesale partners.",
        ecosystem="quickbooks",
        docs_path=f"{DOCS_PREFIX}/workflows.md",
        requires_secrets=["QUICKBOOKS_ACCESS_TOKEN"],
    )

    def __init__(self, client: QuickBooksClient) -> None:
        super().__init__(client=client)

    def run(
        self,
        customer_name: str | None = None,
        amount: float | None = None,
        customer_id: str | None = None,
        line_items: list[dict] | None = None,
        note: str | None = None,
    ) -> ToolResponse:
        if not line_items and amount is None:
            return ToolResponse(
                status="error",
                data={},
                metadata={"message": "Provide either `amount` or explicit `line_items`."},
            )

        payload_line_items = line_items or [{"description": "Custom order", "amount": amount}]
        payload = {
            "customer": customer_name,
            "customer_id": customer_id,
            "line_items": payload_line_items,
            "note": note or "Generated via MCP QuickBooks draft tool",
        }
        invoice = self.client.create_invoice(payload)
        status = "ok" if invoice.get("status") not in {"failed", "error"} else "error"
        return ToolResponse(status=status, data={"invoice": invoice}, metadata={"customer": customer_name or customer_id})
