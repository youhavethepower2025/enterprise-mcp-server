"""Static payloads used while real API keys are not configured."""

from __future__ import annotations

from datetime import datetime, timezone


def sample_contacts() -> list[dict]:
    return [
        {
            "id": "lead_1001",
            "name": "Avery Pharma",
            "stage": "Nurture",
            "last_activity": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "lead_1002",
            "name": "Sunrise Clinics",
            "stage": "Qualified",
            "last_activity": datetime.now(timezone.utc).isoformat(),
        },
    ]


def sample_invoices() -> list[dict]:
    return [
        {"invoice_id": "INV-9001", "status": "Draft", "amount": 1250.00},
        {"invoice_id": "INV-9002", "status": "Sent", "amount": 980.50},
    ]


def sample_freshbooks_invoices() -> list[dict]:
    return [
        {"invoice_id": "FB-1001", "status": "sent", "amount": 450.0, "client": "Wellness Labs"},
        {"invoice_id": "FB-1002", "status": "draft", "amount": 780.0, "client": "Sunrise Clinic"},
    ]


def sample_freshbooks_clients() -> list[dict]:
    return [
        {"id": "client_2001", "organization": "Wellness Labs", "email": "ops@wellnesslabs.com"},
        {"id": "client_2002", "organization": "Sunrise Clinic", "email": "finance@sunriseclinic.com"},
    ]


def sample_google_assets() -> dict:
    return {
        "documents": [
            {"id": "doc_abc", "title": "MedTainer Pitch Deck"},
            {"id": "doc_xyz", "title": "Q2 SOP Updates"},
        ],
        "sheets": [
            {"id": "sheet_pipeline", "title": "GoHighLevel Pipeline Sync"},
        ],
    }


def sample_amazon_orders() -> list[dict]:
    return [
        {"order_id": "AMZ-1", "status": "Shipped", "items": 42},
        {"order_id": "AMZ-2", "status": "Pending", "items": 15},
    ]


def sample_cloudflare_records() -> list[dict]:
    return [
        {"type": "A", "name": "api", "content": "203.0.113.10"},
        {"type": "TXT", "name": "_dmarc", "content": "v=DMARC1; p=quarantine"},
    ]


def sample_godaddy_domains() -> list[dict]:
    return [
        {"domain": "medtainer.com", "status": "active", "expires": "2026-01-01"},
        {"domain": "medtainerlabs.com", "status": "active", "expires": "2025-08-15"},
    ]
