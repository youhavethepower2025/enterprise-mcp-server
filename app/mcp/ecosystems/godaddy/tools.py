from __future__ import annotations

from typing import Optional
from app.mcp.base import BaseTool
from app.mcp.ecosystems.godaddy.client import GoDaddyClient
from app.mcp.models import ToolMetadata, ToolResponse

DOCS_PREFIX = "Docs/godaddy"


class GoDaddyDomainCatalogTool(BaseTool):
    """List all registered domains in the GoDaddy account."""

    metadata = ToolMetadata(
        name="godaddy.list_domains",
        description="List all registered domains with registration dates, expiration dates, and status. Essential for DNS management and domain portfolio oversight.",
        ecosystem="godaddy",
        docs_path=f"{DOCS_PREFIX}/connections.md",
        requires_secrets=["GODADDY_API_KEY", "GODADDY_API_SECRET"],
    )

    def __init__(self, client: GoDaddyClient) -> None:
        super().__init__(client=client)

    def run(self, limit: Optional[int] = None) -> ToolResponse:
        """
        List domains from GoDaddy account.

        Args:
            limit: Maximum number of domains to return

        Returns:
            ToolResponse with domain list and metadata
        """
        try:
            domains = self.client.list_domains(limit=limit)
            return ToolResponse(
                status="ok",
                data={"domains": domains, "count": len(domains)},
                metadata={"source": "godaddy_api", "limit": limit},
            )
        except Exception as e:
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "godaddy_api", "error_type": type(e).__name__},
            )


class GoDaddyDomainDetailsTool(BaseTool):
    """Get detailed information about a specific domain."""

    metadata = ToolMetadata(
        name="godaddy.get_domain",
        description="Get comprehensive details for a specific domain including registration date, expiration date, nameservers, renewal settings, and domain lock status.",
        ecosystem="godaddy",
        docs_path=f"{DOCS_PREFIX}/endpoints.md",
        requires_secrets=["GODADDY_API_KEY", "GODADDY_API_SECRET"],
    )

    def __init__(self, client: GoDaddyClient) -> None:
        super().__init__(client=client)

    def run(self, domain: str) -> ToolResponse:
        """
        Get domain details from GoDaddy.

        Args:
            domain: Domain name (e.g., 'medtainer.com')

        Returns:
            ToolResponse with domain details
        """
        try:
            details = self.client.get_domain(domain)
            return ToolResponse(
                status="ok", data=details, metadata={"source": "godaddy_api", "domain": domain}
            )
        except Exception as e:
            return ToolResponse(
                status="error",
                data={"error": str(e), "domain": domain},
                metadata={"source": "godaddy_api", "error_type": type(e).__name__},
            )


class GoDaddyDnsRecordsTool(BaseTool):
    """Get DNS records for a domain."""

    metadata = ToolMetadata(
        name="godaddy.get_dns_records",
        description="Retrieve all DNS records (A, AAAA, CNAME, MX, TXT, SRV, etc.) for a domain. Critical for understanding email routing, subdomains, and service configurations.",
        ecosystem="godaddy",
        docs_path=f"{DOCS_PREFIX}/endpoints.md",
        requires_secrets=["GODADDY_API_KEY", "GODADDY_API_SECRET"],
    )

    def __init__(self, client: GoDaddyClient) -> None:
        super().__init__(client=client)

    def run(self, domain: str, record_type: Optional[str] = None) -> ToolResponse:
        """
        Get DNS records for a domain.

        Args:
            domain: Domain name
            record_type: Optional filter by record type (A, AAAA, CNAME, MX, TXT, etc.)

        Returns:
            ToolResponse with DNS records
        """
        try:
            records = self.client.get_dns_records(domain, record_type)
            return ToolResponse(
                status="ok",
                data={"records": records, "count": len(records), "domain": domain, "type_filter": record_type},
                metadata={"source": "godaddy_api", "domain": domain, "record_type": record_type},
            )
        except Exception as e:
            return ToolResponse(
                status="error",
                data={"error": str(e), "domain": domain},
                metadata={"source": "godaddy_api", "error_type": type(e).__name__},
            )


class GoDaddyMxRecordsTool(BaseTool):
    """Get MX (email) records for a domain."""

    metadata = ToolMetadata(
        name="godaddy.get_mx_records",
        description="Retrieve MX records to understand email routing and identify available email configurations for creating subdomain-based email addresses.",
        ecosystem="godaddy",
        docs_path=f"{DOCS_PREFIX}/workflows.md",
        requires_secrets=["GODADDY_API_KEY", "GODADDY_API_SECRET"],
    )

    def __init__(self, client: GoDaddyClient) -> None:
        super().__init__(client=client)

    def run(self, domain: str) -> ToolResponse:
        """
        Get MX (email) records for a domain.

        Args:
            domain: Domain name

        Returns:
            ToolResponse with MX records
        """
        try:
            records = self.client.get_dns_records(domain, record_type="MX")
            return ToolResponse(
                status="ok",
                data={"mx_records": records, "count": len(records), "domain": domain},
                metadata={"source": "godaddy_api", "domain": domain, "record_type": "MX"},
            )
        except Exception as e:
            return ToolResponse(
                status="error",
                data={"error": str(e), "domain": domain},
                metadata={"source": "godaddy_api", "error_type": type(e).__name__},
            )


class GoDaddySubdomainsTool(BaseTool):
    """Identify all subdomains configured in DNS."""

    metadata = ToolMetadata(
        name="godaddy.get_subdomains",
        description="List all subdomains by analyzing DNS records (A, AAAA, CNAME). Shows which subdomains are in use and available for new services or email addresses.",
        ecosystem="godaddy",
        docs_path=f"{DOCS_PREFIX}/workflows.md",
        requires_secrets=["GODADDY_API_KEY", "GODADDY_API_SECRET"],
    )

    def __init__(self, client: GoDaddyClient) -> None:
        super().__init__(client=client)

    def run(self, domain: str) -> ToolResponse:
        """
        Get all subdomains for a domain by analyzing DNS records.

        Args:
            domain: Domain name

        Returns:
            ToolResponse with subdomain list
        """
        try:
            # Get A, AAAA, and CNAME records to identify subdomains
            all_records = self.client.get_dns_records(domain)

            # Extract unique subdomain names
            subdomains = set()
            for record in all_records:
                name = record.get("name", "")
                record_type = record.get("type", "")

                # Include A, AAAA, CNAME, MX records
                if record_type in ["A", "AAAA", "CNAME", "MX"] and name not in ["@", ""]:
                    subdomains.add(name)

            subdomain_list = sorted(list(subdomains))

            return ToolResponse(
                status="ok",
                data={
                    "domain": domain,
                    "subdomains": subdomain_list,
                    "count": len(subdomain_list),
                    "available_for_email": subdomain_list,  # These can be used for email addresses
                },
                metadata={"source": "godaddy_api", "domain": domain},
            )
        except Exception as e:
            return ToolResponse(
                status="error",
                data={"error": str(e), "domain": domain},
                metadata={"source": "godaddy_api", "error_type": type(e).__name__},
            )


class GoDaddyDomainContactsTool(BaseTool):
    """Get contact information for a domain."""

    metadata = ToolMetadata(
        name="godaddy.get_domain_contacts",
        description="Retrieve registrant, administrative, technical, and billing contact information for a domain.",
        ecosystem="godaddy",
        docs_path=f"{DOCS_PREFIX}/endpoints.md",
        requires_secrets=["GODADDY_API_KEY", "GODADDY_API_SECRET"],
    )

    def __init__(self, client: GoDaddyClient) -> None:
        super().__init__(client=client)

    def run(self, domain: str) -> ToolResponse:
        """
        Get contact information for a domain.

        Args:
            domain: Domain name

        Returns:
            ToolResponse with contact details
        """
        try:
            contacts = self.client.get_domain_contacts(domain)
            return ToolResponse(
                status="ok", data=contacts, metadata={"source": "godaddy_api", "domain": domain}
            )
        except Exception as e:
            return ToolResponse(
                status="error",
                data={"error": str(e), "domain": domain},
                metadata={"source": "godaddy_api", "error_type": type(e).__name__},
            )


class GoDaddyDomainAvailabilityTool(BaseTool):
    """Check if a domain is available for registration."""

    metadata = ToolMetadata(
        name="godaddy.check_domain_availability",
        description="Check if a domain name is available for purchase. Useful for identifying new domains for services or email accounts.",
        ecosystem="godaddy",
        docs_path=f"{DOCS_PREFIX}/endpoints.md",
        requires_secrets=["GODADDY_API_KEY", "GODADDY_API_SECRET"],
    )

    def __init__(self, client: GoDaddyClient) -> None:
        super().__init__(client=client)

    def run(self, domain: str) -> ToolResponse:
        """
        Check domain availability.

        Args:
            domain: Domain name to check

        Returns:
            ToolResponse with availability status
        """
        try:
            availability = self.client.check_domain_availability(domain)
            return ToolResponse(
                status="ok", data=availability, metadata={"source": "godaddy_api", "domain": domain}
            )
        except Exception as e:
            return ToolResponse(
                status="error",
                data={"error": str(e), "domain": domain},
                metadata={"source": "godaddy_api", "error_type": type(e).__name__},
            )


# DEPRECATED: Use GoDaddyDnsRecordsTool instead
class GoDaddyDnsPlanTool(BaseTool):
    """DEPRECATED: Use godaddy.get_dns_records instead."""

    metadata = ToolMetadata(
        name="godaddy.dns_plan",
        description="DEPRECATED: Use godaddy.get_dns_records for actual DNS record retrieval.",
        ecosystem="godaddy",
        docs_path=f"{DOCS_PREFIX}/workflows.md",
        requires_secrets=["GODADDY_API_KEY", "GODADDY_API_SECRET"],
    )

    def __init__(self, client: GoDaddyClient) -> None:
        super().__init__(client=client)

    def run(self, domain: str) -> ToolResponse:
        """Returns actual DNS records (deprecated method)."""
        try:
            plan = self.client.dns_plan(domain)
            return ToolResponse(status="ok", data=plan, metadata={"domain": domain, "deprecated": True})
        except Exception as e:
            return ToolResponse(
                status="error",
                data={"error": str(e), "domain": domain},
                metadata={"error_type": type(e).__name__, "deprecated": True},
            )
