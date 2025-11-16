from __future__ import annotations

import logging
from typing import List

import httpx

from app.core.config import settings
from app.mcp.common.base_client import BaseAPIClient
from app.mcp.common.mock_data import sample_contacts

logger = logging.getLogger(__name__)


class GoHighLevelClient(BaseAPIClient):
    def __init__(self) -> None:
        super().__init__(base_url=settings.gohighlevel_base_url, api_key=settings.gohighlevel_api_key)
        self.location_id = settings.gohighlevel_location_id

    def list_contacts(self, limit: int = 10) -> List[dict]:
        """
        Fetch contacts from GoHighLevel API with graceful fallback to mock data.
        """

        fallback = sample_contacts()[:limit]
        if not self.api_key:
            logger.warning("No GoHighLevel API key configured, returning sample data")
            return fallback

        try:
            params = {"limit": limit}
            if self.location_id:
                params["locationId"] = self.location_id

            response = self.get("/contacts/", params=params)
            raw_contacts = response.get("contacts") if isinstance(response, dict) else response
            if raw_contacts is None:
                logger.warning("Unexpected GoHighLevel contact payload: %s", response)
                return fallback

            contacts = [self._transform_contact(contact) for contact in raw_contacts]
            logger.info("Successfully fetched %s contacts from GoHighLevel", len(contacts))
            return contacts[:limit]

        except httpx.HTTPStatusError as exc:
            logger.error(
                "GoHighLevel API error: %s - %s",
                exc.response.status_code,
                exc.response.text,
            )
            return fallback
        except httpx.RequestError as exc:
            logger.error("GoHighLevel network error: %s", exc)
            return fallback
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error fetching GoHighLevel contacts: %s", exc)
            return fallback

    def pipeline_digest(self) -> List[dict]:
        """
        Aggregate pipeline counts by stage, hitting opportunities endpoint when possible.
        """

        if not self.api_key:
            return self._digest_from_contacts(sample_contacts())

        try:
            params = {"limit": 100}
            if self.location_id:
                params["locationId"] = self.location_id
            response = self.get("/opportunities/", params=params)
            items = response.get("opportunities") if isinstance(response, dict) else response
            if not items:
                logger.warning("Empty pipeline response from GoHighLevel, falling back to contacts snapshot")
                return self._digest_from_contacts(self.list_contacts(limit=25))

            summary = {}
            for item in items:
                stage = (
                    item.get("stageName")
                    or item.get("stageId")
                    or item.get("pipelineStage")
                    or "unknown"
                )
                summary[stage] = summary.get(stage, 0) + 1

            digest = [{"stage": stage, "count": count} for stage, count in summary.items()]
            logger.info("Computed GoHighLevel pipeline digest with %s stages", len(digest))
            return digest

        except httpx.HTTPStatusError as exc:
            logger.error(
                "GoHighLevel pipeline API error: %s - %s",
                exc.response.status_code,
                exc.response.text,
            )
            return self._digest_from_contacts(self.list_contacts(limit=25))
        except httpx.RequestError as exc:
            logger.error("GoHighLevel pipeline network error: %s", exc)
            return self._digest_from_contacts(self.list_contacts(limit=25))
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error building pipeline digest: %s", exc)
            return self._digest_from_contacts(self.list_contacts(limit=25))

    @staticmethod
    def _transform_contact(contact: dict) -> dict:
        return {
            "id": contact.get("id") or contact.get("contactId"),
            "name": contact.get("fullName") or contact.get("firstName") or "Unknown",
            "stage": contact.get("stage") or contact.get("pipelineStage") or "Unassigned",
            "last_activity": contact.get("lastActivity") or contact.get("updatedAt"),
        }

    @staticmethod
    def _digest_from_contacts(contacts: List[dict]) -> List[dict]:
        summary = {}
        for contact in contacts:
            stage = contact.get("stage", "unknown")
            summary[stage] = summary.get(stage, 0) + 1
        return [{"stage": stage, "count": count} for stage, count in summary.items()]
