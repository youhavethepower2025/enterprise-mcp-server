#!/usr/bin/env python3
"""
Validate GoHighLevel API schemas against live API.

Run this script to ensure our Pydantic schemas match the real API responses.
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from app.core.config import settings
from app.mcp.ecosystems.gohighlevel.schemas.contact import GHLContactList, GHLContact
import json
from rich.console import Console
from rich.table import Table

console = Console()


def validate_contact_list_schema():
    """Test GET /contacts/ endpoint and validate response schema."""
    console.print("\n[bold cyan]Testing GET /contacts/ endpoint...[/bold cyan]")

    client = httpx.Client(
        base_url="https://rest.gohighlevel.com/v1",
        headers={"Authorization": f"Bearer {settings.gohighlevel_api_key}"},
        timeout=30.0,
    )

    try:
        response = client.get(
            "/contacts/",
            params={"limit": 3, "locationId": settings.gohighlevel_location_id},
        )
        response.raise_for_status()

        data = response.json()

        # Validate with Pydantic schema
        contact_list = GHLContactList(**data)

        console.print("[bold green]✓ Schema validation successful![/bold green]")
        console.print(f"Found {len(contact_list.contacts)} contacts")
        console.print(f"Total contacts in location: {contact_list.meta.total}")

        # Display contacts
        table = Table(title="Sample Contacts")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Email", style="yellow")
        table.add_column("Phone", style="magenta")
        table.add_column("Type", style="blue")

        for contact in contact_list.contacts:
            table.add_row(
                contact.id[:8] + "...",
                contact.contactName or f"{contact.firstName or ''} {contact.lastName or ''}".strip() or "N/A",
                contact.email or "N/A",
                contact.phone or "N/A",
                contact.type or "N/A",
            )

        console.print(table)

        # Check for any extra fields (API changes)
        console.print("\n[bold cyan]Checking for unexpected fields...[/bold cyan]")
        if contact_list.contacts:
            sample_contact = contact_list.contacts[0]
            schema_fields = set(GHLContact.model_fields.keys())
            api_fields = set(data["contacts"][0].keys())

            extra_fields = api_fields - schema_fields
            if extra_fields:
                console.print(f"[bold yellow]⚠ Warning: API returned unexpected fields: {extra_fields}[/bold yellow]")
                console.print("Consider updating the schema to include these fields")
            else:
                console.print("[bold green]✓ No unexpected fields detected[/bold green]")

        return True

    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]✗ HTTP Error: {e.response.status_code}[/bold red]")
        console.print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        console.print(f"[bold red]✗ Validation Error: {str(e)}[/bold red]")
        import traceback

        traceback.print_exc()
        return False
    finally:
        client.close()


def check_api_authentication():
    """Verify API authentication is working."""
    console.print("\n[bold cyan]Testing API Authentication...[/bold cyan]")

    if not settings.gohighlevel_api_key:
        console.print("[bold red]✗ No API key configured[/bold red]")
        return False

    if not settings.gohighlevel_location_id:
        console.print("[bold red]✗ No Location ID configured[/bold red]")
        return False

    console.print(f"API Key: {settings.gohighlevel_api_key[:20]}...")
    console.print(f"Location ID: {settings.gohighlevel_location_id}")

    client = httpx.Client(
        base_url="https://rest.gohighlevel.com/v1",
        headers={"Authorization": f"Bearer {settings.gohighlevel_api_key}"},
        timeout=30.0,
    )

    try:
        response = client.get(
            "/contacts/", params={"limit": 1, "locationId": settings.gohighlevel_location_id}
        )
        response.raise_for_status()
        console.print("[bold green]✓ Authentication successful[/bold green]")
        return True
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]✗ Authentication failed: {e.response.status_code}[/bold red]")
        console.print(f"Response: {e.response.text}")
        return False
    finally:
        client.close()


def main():
    """Run all validation tests."""
    console.print("[bold magenta]═══════════════════════════════════════════[/bold magenta]")
    console.print("[bold magenta]  GoHighLevel API Schema Validation[/bold magenta]")
    console.print("[bold magenta]═══════════════════════════════════════════[/bold magenta]")

    # Test 1: Authentication
    auth_ok = check_api_authentication()

    if not auth_ok:
        console.print("\n[bold red]Authentication failed. Cannot proceed with tests.[/bold red]")
        sys.exit(1)

    # Test 2: Contact list schema
    schema_ok = validate_contact_list_schema()

    # Summary
    console.print("\n[bold magenta]═══════════════════════════════════════════[/bold magenta]")
    console.print("[bold magenta]  Summary[/bold magenta]")
    console.print("[bold magenta]═══════════════════════════════════════════[/bold magenta]")

    if auth_ok and schema_ok:
        console.print("[bold green]✓ All validations passed![/bold green]")
        console.print("\nSchemas are in sync with GoHighLevel API")
        sys.exit(0)
    else:
        console.print("[bold red]✗ Some validations failed[/bold red]")
        console.print("\nPlease review errors above and update schemas")
        sys.exit(1)


if __name__ == "__main__":
    main()
