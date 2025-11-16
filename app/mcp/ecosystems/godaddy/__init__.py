from __future__ import annotations

from typing import List

from app.mcp.ecosystems.godaddy.client import GoDaddyClient
from app.mcp.ecosystems.godaddy.tools import (
    GoDaddyDomainCatalogTool,
    GoDaddyDomainDetailsTool,
    GoDaddyDnsRecordsTool,
    GoDaddyMxRecordsTool,
    GoDaddySubdomainsTool,
    GoDaddyDomainContactsTool,
    GoDaddyDomainAvailabilityTool,
    GoDaddyDnsPlanTool,  # DEPRECATED but kept for backwards compatibility
)


def build_tools() -> List[object]:
    """
    Build and register all GoDaddy tools with a shared client instance.

    Returns:
        List of instantiated GoDaddy tool objects
    """
    client = GoDaddyClient()
    return [
        # Core domain management
        GoDaddyDomainCatalogTool(client=client),
        GoDaddyDomainDetailsTool(client=client),

        # DNS and subdomain discovery
        GoDaddyDnsRecordsTool(client=client),
        GoDaddyMxRecordsTool(client=client),
        GoDaddySubdomainsTool(client=client),

        # Domain information
        GoDaddyDomainContactsTool(client=client),
        GoDaddyDomainAvailabilityTool(client=client),

        # Deprecated tools (kept for backwards compatibility)
        GoDaddyDnsPlanTool(client=client),
    ]
