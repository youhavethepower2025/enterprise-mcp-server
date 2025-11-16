from __future__ import annotations
import httpx
from typing import Optional
from app.core.config import settings


class GoDaddyClient:
    """Client for interacting with GoDaddy API for domain and DNS management."""

    def __init__(self) -> None:
        self.base_url = "https://api.godaddy.com"
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"sso-key {settings.godaddy_api_key}:{settings.godaddy_api_secret}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def list_domains(self, limit: Optional[int] = None) -> list[dict]:
        """
        List all domains in the GoDaddy account.

        Args:
            limit: Maximum number of domains to return

        Returns:
            List of domain objects with details
        """
        params = {}
        if limit:
            params["limit"] = limit

        response = self.client.get("/v1/domains", params=params)
        response.raise_for_status()
        return response.json()

    def get_domain(self, domain: str) -> dict:
        """
        Get detailed information about a specific domain.

        Args:
            domain: The domain name (e.g., 'medtainer.com')

        Returns:
            Domain details including registration, expiration, nameservers
        """
        response = self.client.get(f"/v1/domains/{domain}")
        response.raise_for_status()
        return response.json()

    def get_dns_records(self, domain: str, record_type: Optional[str] = None) -> list[dict]:
        """
        Get DNS records for a domain.

        Args:
            domain: The domain name
            record_type: Optional filter by type (A, AAAA, CNAME, MX, TXT, etc.)

        Returns:
            List of DNS records
        """
        url = f"/v1/domains/{domain}/records"
        if record_type:
            url += f"/{record_type}"

        response = self.client.get(url)
        response.raise_for_status()
        return response.json()

    def update_dns_records(self, domain: str, records: list[dict], record_type: Optional[str] = None) -> None:
        """
        Update DNS records for a domain.

        Args:
            domain: The domain name
            records: List of DNS record objects to update
            record_type: Optional - update only specific record type
        """
        url = f"/v1/domains/{domain}/records"
        if record_type:
            url += f"/{record_type}"

        response = self.client.put(url, json=records)
        response.raise_for_status()

    def check_domain_availability(self, domain: str) -> dict:
        """
        Check if a domain is available for purchase.

        Args:
            domain: The domain name to check

        Returns:
            Availability information
        """
        response = self.client.get(f"/v1/domains/available", params={"domain": domain})
        response.raise_for_status()
        return response.json()

    def get_domain_contacts(self, domain: str) -> dict:
        """
        Get contact information for a domain.

        Args:
            domain: The domain name

        Returns:
            Contact information (registrant, admin, tech, billing)
        """
        response = self.client.get(f"/v1/domains/{domain}/contacts")
        response.raise_for_status()
        return response.json()

    def dns_plan(self, domain: str) -> dict:
        """
        DEPRECATED: Use get_dns_records() instead.
        Returns actual DNS records from GoDaddy API.

        Args:
            domain: The domain name

        Returns:
            DNS records wrapped in a plan structure
        """
        records = self.get_dns_records(domain)
        return {"domain": domain, "records": records}
