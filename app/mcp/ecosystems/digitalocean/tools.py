"""DigitalOcean MCP tools for droplet management."""

import logging
from typing import Optional

from app.mcp.base import BaseTool
from app.mcp.models import ToolMetadata, ToolResponse
from app.mcp.ecosystems.digitalocean.client import DigitalOceanClient

logger = logging.getLogger(__name__)


class ListDropletsTool(BaseTool):
    """List all DigitalOcean droplets."""

    metadata = ToolMetadata(
        name="digitalocean.list_droplets",
        description="List all droplets in the DigitalOcean account with their IPs and status.",
        ecosystem="digitalocean",
        requires_secrets=["DIGITALOCEAN_API_TOKEN"],
    )

    def __init__(self, client: DigitalOceanClient) -> None:
        super().__init__(client=client)

    def run(self) -> ToolResponse:
        """List all droplets."""
        try:
            droplets = self.client.list_droplets()

            return ToolResponse(
                status="success",
                data={
                    "count": len(droplets),
                    "droplets": [
                        {
                            "id": d["id"],
                            "name": d["name"],
                            "status": d["status"],
                            "region": d["region"]["slug"],
                            "size": d["size"]["slug"],
                            "ip_address": d["networks"]["v4"][0]["ip_address"] if d["networks"]["v4"] else None,
                            "created_at": d["created_at"]
                        }
                        for d in droplets
                    ]
                },
                metadata={"source": "live"}
            )
        except Exception as e:
            logger.error(f"Error listing droplets: {e}")
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "error"}
            )


class CreateDropletTool(BaseTool):
    """Create a new DigitalOcean droplet."""

    metadata = ToolMetadata(
        name="digitalocean.create_droplet",
        description=(
            "Create a new droplet on DigitalOcean. "
            "Specify name, region (e.g., nyc1, sfo3), size (e.g., s-2vcpu-4gb), "
            "and image (e.g., ubuntu-22-04-x64)."
        ),
        ecosystem="digitalocean",
        requires_secrets=["DIGITALOCEAN_API_TOKEN"],
    )

    def __init__(self, client: DigitalOceanClient) -> None:
        super().__init__(client=client)

    def run(
        self,
        name: str,
        region: str = "sfo3",
        size: str = "s-2vcpu-4gb",
        image: str = "ubuntu-22-04-x64",
        tags: Optional[list] = None
    ) -> ToolResponse:
        """Create a new droplet."""
        try:
            logger.info(f"Creating droplet: {name} in {region}")

            droplet = self.client.create_droplet(
                name=name,
                region=region,
                size=size,
                image=image,
                tags=tags or ["medtainer", "mcp"]
            )

            return ToolResponse(
                status="success",
                data={
                    "droplet_id": droplet["id"],
                    "name": droplet["name"],
                    "status": droplet["status"],
                    "region": droplet["region"]["slug"],
                    "message": f"Droplet {name} created successfully. It will be available in 1-2 minutes."
                },
                metadata={"source": "live", "operation": "create"}
            )
        except Exception as e:
            logger.error(f"Error creating droplet: {e}")
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "error"}
            )


class GetDropletTool(BaseTool):
    """Get droplet details by ID."""

    metadata = ToolMetadata(
        name="digitalocean.get_droplet",
        description="Get detailed information about a specific droplet by ID, including IP address.",
        ecosystem="digitalocean",
        requires_secrets=["DIGITALOCEAN_API_TOKEN"],
    )

    def __init__(self, client: DigitalOceanClient) -> None:
        super().__init__(client=client)

    def run(self, droplet_id: int) -> ToolResponse:
        """Get droplet details."""
        try:
            droplet = self.client.get_droplet(droplet_id)

            ip_address = None
            if droplet["networks"]["v4"]:
                ip_address = droplet["networks"]["v4"][0]["ip_address"]

            return ToolResponse(
                status="success",
                data={
                    "id": droplet["id"],
                    "name": droplet["name"],
                    "status": droplet["status"],
                    "ip_address": ip_address,
                    "region": droplet["region"]["slug"],
                    "size": droplet["size"]["slug"],
                    "created_at": droplet["created_at"],
                    "memory": droplet["memory"],
                    "vcpus": droplet["vcpus"],
                    "disk": droplet["disk"]
                },
                metadata={"source": "live"}
            )
        except Exception as e:
            logger.error(f"Error getting droplet: {e}")
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "error"}
            )


class DeleteDropletTool(BaseTool):
    """Delete a DigitalOcean droplet."""

    metadata = ToolMetadata(
        name="digitalocean.delete_droplet",
        description="Delete a droplet by ID. This is permanent and cannot be undone!",
        ecosystem="digitalocean",
        requires_secrets=["DIGITALOCEAN_API_TOKEN"],
    )

    def __init__(self, client: DigitalOceanClient) -> None:
        super().__init__(client=client)

    def run(self, droplet_id: int) -> ToolResponse:
        """Delete a droplet."""
        try:
            logger.info(f"Deleting droplet: {droplet_id}")

            success = self.client.delete_droplet(droplet_id)

            if success:
                return ToolResponse(
                    status="success",
                    data={
                        "message": f"Droplet {droplet_id} deleted successfully"
                    },
                    metadata={"source": "live", "operation": "delete"}
                )
            else:
                return ToolResponse(
                    status="error",
                    data={"error": "Failed to delete droplet"},
                    metadata={"source": "error"}
                )
        except Exception as e:
            logger.error(f"Error deleting droplet: {e}")
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "error"}
            )


class RebootDropletTool(BaseTool):
    """Reboot a DigitalOcean droplet."""

    metadata = ToolMetadata(
        name="digitalocean.reboot_droplet",
        description="Reboot a droplet by ID. This will restart the server gracefully.",
        ecosystem="digitalocean",
        requires_secrets=["DIGITALOCEAN_API_TOKEN"],
    )

    def __init__(self, client: DigitalOceanClient) -> None:
        super().__init__(client=client)

    def run(self, droplet_id: int) -> ToolResponse:
        """Reboot a droplet."""
        try:
            logger.info(f"Rebooting droplet: {droplet_id}")

            action = self.client.reboot_droplet(droplet_id)

            return ToolResponse(
                status="success",
                data={
                    "action_id": action["id"],
                    "status": action["status"],
                    "message": f"Droplet {droplet_id} is rebooting"
                },
                metadata={"source": "live", "operation": "reboot"}
            )
        except Exception as e:
            logger.error(f"Error rebooting droplet: {e}")
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "error"}
            )
