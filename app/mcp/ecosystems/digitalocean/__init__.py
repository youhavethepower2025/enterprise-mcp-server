"""DigitalOcean ecosystem for droplet management."""

from typing import List

from app.mcp.ecosystems.digitalocean.client import DigitalOceanClient
from app.mcp.ecosystems.digitalocean.tools import (
    ListDropletsTool,
    CreateDropletTool,
    GetDropletTool,
    DeleteDropletTool,
    RebootDropletTool,
)


def build_tools() -> List[object]:
    """Build DigitalOcean tools."""
    client = DigitalOceanClient()
    return [
        ListDropletsTool(client=client),
        CreateDropletTool(client=client),
        GetDropletTool(client=client),
        DeleteDropletTool(client=client),
        RebootDropletTool(client=client),
    ]
