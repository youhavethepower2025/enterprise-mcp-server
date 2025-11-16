"""GoHighLevel action tools - Write/modify operations."""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from app.mcp.base import BaseTool
from app.mcp.models import ToolMetadata, ToolResponse
from app.mcp.ecosystems.gohighlevel.client import GoHighLevelClient

logger = logging.getLogger(__name__)


class CreateContactTool(BaseTool):
    """
    Create a new contact in GoHighLevel.

    Allows the agent to add new contacts to the CRM with full details
    including name, email, phone, tags, and custom fields.
    """

    metadata = ToolMetadata(
        name="gohighlevel.create_contact",
        description=(
            "Create a new contact in GoHighLevel CRM. "
            "Provide contact details like name, email, phone, tags, and custom fields. "
            "Returns the created contact with ID."
        ),
        ecosystem="gohighlevel",
        requires_secrets=["GOHIGHLEVEL_API_KEY", "GOHIGHLEVEL_LOCATION_ID"],
    )

    def __init__(self, client: GoHighLevelClient) -> None:
        super().__init__(client=client)

    def run(
        self,
        first_name: str,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        tags: Optional[list] = None,
        source: Optional[str] = None,
        country: str = "US",
        **custom_fields
    ) -> ToolResponse:
        """
        Create a new contact.

        Args:
            first_name: Contact's first name (required)
            last_name: Contact's last name
            email: Email address
            phone: Phone number
            tags: List of tags to apply
            source: Source of the contact
            country: Country code (default: US)
            **custom_fields: Additional custom fields
        """
        logger.info(f"Creating contact: {first_name} {last_name}")

        payload = {
            "firstName": first_name,
            "locationId": self.client.location_id,
            "country": country,
        }

        if last_name:
            payload["lastName"] = last_name
        if email:
            payload["email"] = email
        if phone:
            payload["phone"] = phone
        if tags:
            payload["tags"] = tags if isinstance(tags, list) else [tags]
        if source:
            payload["source"] = source

        # Add custom fields
        if custom_fields:
            payload["customFields"] = [
                {"key": k, "value": v}
                for k, v in custom_fields.items()
            ]

        try:
            response = self.client.post("/contacts/", json=payload)
            contact = response.get("contact", response)

            return ToolResponse(
                status="success",
                data={
                    "contact_id": contact.get("id"),
                    "contact": contact,
                    "message": f"Created contact: {first_name} {last_name or ''}"
                },
                metadata={"source": "live", "operation": "create"}
            )
        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "error", "operation": "create"}
            )


class UpdateContactTool(BaseTool):
    """
    Update an existing contact in GoHighLevel.

    Modify contact information, add tags, update custom fields.
    """

    metadata = ToolMetadata(
        name="gohighlevel.update_contact",
        description=(
            "Update an existing contact in GoHighLevel. "
            "Can modify name, email, phone, tags, and any custom fields. "
            "Requires contact_id."
        ),
        ecosystem="gohighlevel",
        requires_secrets=["GOHIGHLEVEL_API_KEY"],
    )

    def __init__(self, client: GoHighLevelClient) -> None:
        super().__init__(client=client)

    def run(
        self,
        contact_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        tags: Optional[list] = None,
        **custom_fields
    ) -> ToolResponse:
        """
        Update a contact.

        Args:
            contact_id: ID of the contact to update (required)
            first_name: New first name
            last_name: New last name
            email: New email address
            phone: New phone number
            tags: Tags to add
            **custom_fields: Custom fields to update
        """
        logger.info(f"Updating contact: {contact_id}")

        payload = {}
        if first_name:
            payload["firstName"] = first_name
        if last_name:
            payload["lastName"] = last_name
        if email:
            payload["email"] = email
        if phone:
            payload["phone"] = phone
        if tags:
            payload["tags"] = tags if isinstance(tags, list) else [tags]

        if custom_fields:
            payload["customFields"] = [
                {"key": k, "value": v}
                for k, v in custom_fields.items()
            ]

        try:
            response = self.client.put(f"/contacts/{contact_id}", json=payload)
            contact = response.get("contact", response)

            return ToolResponse(
                status="success",
                data={
                    "contact_id": contact_id,
                    "contact": contact,
                    "message": f"Updated contact: {contact_id}"
                },
                metadata={"source": "live", "operation": "update"}
            )
        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "error", "operation": "update"}
            )


class SendSMSTool(BaseTool):
    """
    Send an SMS message to a contact via GoHighLevel.

    Enables the agent to send text messages to contacts for follow-up,
    notifications, or customer service.
    """

    metadata = ToolMetadata(
        name="gohighlevel.send_sms",
        description=(
            "Send an SMS message to a contact in GoHighLevel. "
            "Provide contact_id and message text. "
            "Message will be sent from the location's configured phone number."
        ),
        ecosystem="gohighlevel",
        requires_secrets=["GOHIGHLEVEL_API_KEY"],
    )

    def __init__(self, client: GoHighLevelClient) -> None:
        super().__init__(client=client)

    def run(self, contact_id: str, message: str) -> ToolResponse:
        """
        Send SMS to a contact.

        Args:
            contact_id: ID of the contact to message (required)
            message: Text message to send (required)
        """
        logger.info(f"Sending SMS to contact: {contact_id}")

        payload = {
            "contactId": contact_id,
            "message": message,
            "type": "SMS"
        }

        try:
            response = self.client.post("/conversations/messages", json=payload)

            return ToolResponse(
                status="success",
                data={
                    "message_id": response.get("messageId"),
                    "contact_id": contact_id,
                    "message": f"SMS sent to {contact_id}",
                    "response": response
                },
                metadata={"source": "live", "operation": "send_sms"}
            )
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "error", "operation": "send_sms"}
            )


class AddNoteTool(BaseTool):
    """
    Add a note to a contact in GoHighLevel.

    Allows the agent to log notes, observations, or follow-up items
    directly to a contact's record.
    """

    metadata = ToolMetadata(
        name="gohighlevel.add_note",
        description=(
            "Add a note to a contact's record in GoHighLevel. "
            "Use this to log interactions, observations, or next steps. "
            "Notes are visible in the contact's timeline."
        ),
        ecosystem="gohighlevel",
        requires_secrets=["GOHIGHLEVEL_API_KEY"],
    )

    def __init__(self, client: GoHighLevelClient) -> None:
        super().__init__(client=client)

    def run(self, contact_id: str, note: str) -> ToolResponse:
        """
        Add a note to a contact.

        Args:
            contact_id: ID of the contact (required)
            note: Note text to add (required)
        """
        logger.info(f"Adding note to contact: {contact_id}")

        payload = {
            "contactId": contact_id,
            "body": note,
            "userId": "mcp-agent"  # Identifier for notes added by AI
        }

        try:
            response = self.client.post("/contacts/notes/", json=payload)

            return ToolResponse(
                status="success",
                data={
                    "note_id": response.get("id"),
                    "contact_id": contact_id,
                    "message": f"Note added to {contact_id}",
                    "response": response
                },
                metadata={"source": "live", "operation": "add_note"}
            )
        except Exception as e:
            logger.error(f"Error adding note: {e}")
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "error", "operation": "add_note"}
            )


class AddTagsTool(BaseTool):
    """
    Add tags to a contact in GoHighLevel.

    Tags are used for segmentation, automation triggers, and organization.
    """

    metadata = ToolMetadata(
        name="gohighlevel.add_tags",
        description=(
            "Add one or more tags to a contact in GoHighLevel. "
            "Tags are useful for segmentation and triggering automations. "
            "Provide contact_id and list of tags to add."
        ),
        ecosystem="gohighlevel",
        requires_secrets=["GOHIGHLEVEL_API_KEY"],
    )

    def __init__(self, client: GoHighLevelClient) -> None:
        super().__init__(client=client)

    def run(self, contact_id: str, tags: list) -> ToolResponse:
        """
        Add tags to a contact.

        Args:
            contact_id: ID of the contact (required)
            tags: List of tag names to add (required)
        """
        logger.info(f"Adding tags to contact: {contact_id}")

        if isinstance(tags, str):
            tags = [tags]

        payload = {"tags": tags}

        try:
            response = self.client.post(f"/contacts/{contact_id}/tags", json=payload)

            return ToolResponse(
                status="success",
                data={
                    "contact_id": contact_id,
                    "tags_added": tags,
                    "message": f"Added {len(tags)} tag(s) to {contact_id}",
                    "response": response
                },
                metadata={"source": "live", "operation": "add_tags"}
            )
        except Exception as e:
            logger.error(f"Error adding tags: {e}")
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "error", "operation": "add_tags"}
            )


class RemoveTagsTool(BaseTool):
    """
    Remove tags from a contact in GoHighLevel.
    """

    metadata = ToolMetadata(
        name="gohighlevel.remove_tags",
        description=(
            "Remove one or more tags from a contact in GoHighLevel. "
            "Provide contact_id and list of tags to remove."
        ),
        ecosystem="gohighlevel",
        requires_secrets=["GOHIGHLEVEL_API_KEY"],
    )

    def __init__(self, client: GoHighLevelClient) -> None:
        super().__init__(client=client)

    def run(self, contact_id: str, tags: list) -> ToolResponse:
        """
        Remove tags from a contact.

        Args:
            contact_id: ID of the contact (required)
            tags: List of tag names to remove (required)
        """
        logger.info(f"Removing tags from contact: {contact_id}")

        if isinstance(tags, str):
            tags = [tags]

        try:
            # GHL uses DELETE with tags in query params
            response = self.client.delete(
                f"/contacts/{contact_id}/tags",
                params={"tags": ",".join(tags)}
            )

            return ToolResponse(
                status="success",
                data={
                    "contact_id": contact_id,
                    "tags_removed": tags,
                    "message": f"Removed {len(tags)} tag(s) from {contact_id}",
                    "response": response
                },
                metadata={"source": "live", "operation": "remove_tags"}
            )
        except Exception as e:
            logger.error(f"Error removing tags: {e}")
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "error", "operation": "remove_tags"}
            )
