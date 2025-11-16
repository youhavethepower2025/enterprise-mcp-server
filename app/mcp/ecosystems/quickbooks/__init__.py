from __future__ import annotations

from typing import List

from app.mcp.ecosystems.quickbooks.client import QuickBooksClient
from app.mcp.ecosystems.quickbooks.tools import (
    QuickBooksDraftInvoiceTool,
    QuickBooksLedgerSummaryTool,
)


def build_tools() -> List[object]:
    client = QuickBooksClient()
    return [
        QuickBooksLedgerSummaryTool(client=client),
        QuickBooksDraftInvoiceTool(client=client),
    ]
