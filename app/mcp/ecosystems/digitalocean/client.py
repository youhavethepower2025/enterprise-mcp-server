"""DigitalOcean API client for droplet management."""

import logging
from typing import Dict, Any, List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class DigitalOceanClient:
    """Client for interacting with DigitalOcean API."""

    def __init__(self):
        self.api_token = getattr(settings, 'digitalocean_api_token', None)
        self.base_url = "https://api.digitalocean.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to DigitalOcean API."""
        url = f"{self.base_url}{endpoint}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=json_data,
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"DigitalOcean API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request."""
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, json_data: Dict) -> Dict[str, Any]:
        """POST request."""
        return self._request("POST", endpoint, json_data=json_data)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request."""
        return self._request("DELETE", endpoint)

    def put(self, endpoint: str, json_data: Dict) -> Dict[str, Any]:
        """PUT request."""
        return self._request("PUT", endpoint, json_data=json_data)

    # Droplet Operations

    def list_droplets(self) -> List[Dict]:
        """List all droplets."""
        response = self.get("/droplets")
        return response.get("droplets", [])

    def get_droplet(self, droplet_id: int) -> Dict:
        """Get droplet details."""
        response = self.get(f"/droplets/{droplet_id}")
        return response.get("droplet", {})

    def create_droplet(
        self,
        name: str,
        region: str,
        size: str,
        image: str,
        ssh_keys: Optional[List[int]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict:
        """Create a new droplet."""
        data = {
            "name": name,
            "region": region,
            "size": size,
            "image": image,
            "backups": False,
            "ipv6": False,
            "monitoring": True,
            "tags": tags or []
        }

        if ssh_keys:
            data["ssh_keys"] = ssh_keys

        response = self.post("/droplets", data)
        return response.get("droplet", {})

    def delete_droplet(self, droplet_id: int) -> bool:
        """Delete a droplet."""
        try:
            self.delete(f"/droplets/{droplet_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete droplet: {e}")
            return False

    def power_on_droplet(self, droplet_id: int) -> Dict:
        """Power on a droplet."""
        data = {"type": "power_on"}
        response = self.post(f"/droplets/{droplet_id}/actions", data)
        return response.get("action", {})

    def power_off_droplet(self, droplet_id: int) -> Dict:
        """Power off a droplet."""
        data = {"type": "power_off"}
        response = self.post(f"/droplets/{droplet_id}/actions", data)
        return response.get("action", {})

    def reboot_droplet(self, droplet_id: int) -> Dict:
        """Reboot a droplet."""
        data = {"type": "reboot"}
        response = self.post(f"/droplets/{droplet_id}/actions", data)
        return response.get("action", {})

    # SSH Key Operations

    def list_ssh_keys(self) -> List[Dict]:
        """List SSH keys."""
        response = self.get("/account/keys")
        return response.get("ssh_keys", [])

    def add_ssh_key(self, name: str, public_key: str) -> Dict:
        """Add SSH key."""
        data = {
            "name": name,
            "public_key": public_key
        }
        response = self.post("/account/keys", data)
        return response.get("ssh_key", {})

    # Account Operations

    def get_account(self) -> Dict:
        """Get account information."""
        response = self.get("/account")
        return response.get("account", {})

    # Region and Size Information

    def list_regions(self) -> List[Dict]:
        """List available regions."""
        response = self.get("/regions")
        return response.get("regions", [])

    def list_sizes(self) -> List[Dict]:
        """List available droplet sizes."""
        response = self.get("/sizes")
        return response.get("sizes", [])
