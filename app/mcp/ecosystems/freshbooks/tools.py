from __future__ import annotations

from typing import Any, Dict

from app.mcp.base import BaseTool
from app.mcp.ecosystems.freshbooks.client import FreshBooksClient
from app.mcp.models import ToolMetadata, ToolResponse

DOCS_PREFIX = "Docs/freshbooks"


class FreshBooksListInvoicesTool(BaseTool):
    metadata = ToolMetadata(
        name="freshbooks.list_invoices",
        description="List invoices stored in FreshBooks.",
        ecosystem="freshbooks",
        docs_path=f"{DOCS_PREFIX}/endpoints.md",
        requires_secrets=["FRESHBOOKS_ACCESS_TOKEN", "FRESHBOOKS_ACCOUNT_ID"],
    )

    def __init__(self, client: FreshBooksClient) -> None:
        super().__init__(client=client)

    def run(self, **filters: Any) -> ToolResponse:
        params = filters or None
        invoices = self.client.list_invoices(params)
        source = "live" if self.client._credentials_ready() else "sample"
        return ToolResponse(status="ok", data={"invoices": invoices}, metadata={"source": source})


class FreshBooksCreateInvoiceTool(BaseTool):
    metadata = ToolMetadata(
        name="freshbooks.create_invoice",
        description="Create a FreshBooks invoice from MCP inputs.",
        ecosystem="freshbooks",
        docs_path=f"{DOCS_PREFIX}/workflows.md",
        requires_secrets=["FRESHBOOKS_ACCESS_TOKEN", "FRESHBOOKS_ACCOUNT_ID"],
    )

    def __init__(self, client: FreshBooksClient) -> None:
        super().__init__(client=client)

    def run(self, invoice: Dict[str, Any]) -> ToolResponse:
        response = self.client.create_invoice(invoice)
        status = "ok" if response.get("status") not in {"failed", "error"} else "error"
        return ToolResponse(status=status, data={"invoice": response})


class FreshBooksListClientsTool(BaseTool):
    metadata = ToolMetadata(
        name="freshbooks.list_clients",
        description="List FreshBooks clients for syncing account data.",
        ecosystem="freshbooks",
        docs_path=f"{DOCS_PREFIX}/endpoints.md",
        requires_secrets=["FRESHBOOKS_ACCESS_TOKEN", "FRESHBOOKS_ACCOUNT_ID"],
    )

    def __init__(self, client: FreshBooksClient) -> None:
        super().__init__(client=client)

    def run(self, **filters: Any) -> ToolResponse:
        params = filters or None
        clients = self.client.list_clients(params)
        source = "live" if self.client._credentials_ready() else "sample"
        return ToolResponse(status="ok", data={"clients": clients}, metadata={"source": source})


class FreshBooksCreateClientTool(BaseTool):
    metadata = ToolMetadata(
        name="freshbooks.create_client",
        description="Create a FreshBooks client record tied to MedTainer CRM data.",
        ecosystem="freshbooks",
        docs_path=f"{DOCS_PREFIX}/workflows.md",
        requires_secrets=["FRESHBOOKS_ACCESS_TOKEN", "FRESHBOOKS_ACCOUNT_ID"],
    )

    def __init__(self, client: FreshBooksClient) -> None:
        super().__init__(client=client)

    def run(self, client_payload: Dict[str, Any]) -> ToolResponse:
        response = self.client.create_client(client_payload)
        status = "ok" if response.get("client_id") != "ERROR" else "error"
        return ToolResponse(status=status, data={"client": response})


def build_tools() -> list[BaseTool]:
    client = FreshBooksClient()
    return [
        FreshBooksListInvoicesTool(client=client),
        FreshBooksCreateInvoiceTool(client=client),
        FreshBooksListClientsTool(client=client),
        FreshBooksCreateClientTool(client=client),
    ]
