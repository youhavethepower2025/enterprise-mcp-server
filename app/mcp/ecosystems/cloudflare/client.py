from __future__ import annotations

from app.core.config import settings
from app.mcp.common.mock_data import sample_cloudflare_records


class CloudflareClient:
    def __init__(self) -> None:
        self.account_id = settings.cloudflare_account_id

    def list_dns_records(self) -> list[dict]:
        return sample_cloudflare_records()

    def plan_audit(self) -> dict:
        records = self.list_dns_records()
        auth = bool(settings.cloudflare_api_token)
        return {"records": records, "has_credentials": auth}
