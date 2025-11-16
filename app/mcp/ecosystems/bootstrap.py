from __future__ import annotations

from app.mcp.tool_registry import ToolRegistry

from . import amazon, cloudflare, digitalocean, godaddy, gohighlevel, google_workspace, quickbooks, freshbooks

BUNDLES = [
    gohighlevel,
    quickbooks,
    google_workspace,
    amazon,
    cloudflare,
    godaddy,
    freshbooks,
    digitalocean,
]


def register_all_bundles(registry: ToolRegistry) -> None:
    for bundle in BUNDLES:
        registry.bulk_register(bundle.build_tools())
