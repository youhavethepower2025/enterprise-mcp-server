"""GoHighLevel sync service - pulls data and populates the central nervous system.

This service is the core of keeping the MCP server in sync with GoHighLevel.
It pulls all contacts, tags, custom fields, and other data, storing it in PostgreSQL
to create a complete "brain" of the business.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.db.models import Contact, ContactContext, InteractionHistory
from app.mcp.ecosystems.gohighlevel.client import GoHighLevelClient

logger = logging.getLogger(__name__)


class GoHighLevelSyncService:
    """Service for syncing GoHighLevel data into the central nervous system."""

    def __init__(self, db: Session):
        self.db = db
        self.client = GoHighLevelClient()

    def sync_all_contacts(self, full_sync: bool = True) -> Dict[str, Any]:
        """
        Sync all contacts from GoHighLevel to PostgreSQL.

        Args:
            full_sync: If True, pull all contacts. If False, only pull recently updated.

        Returns:
            Dictionary with sync statistics
        """
        logger.info("Starting GoHighLevel contact sync")
        stats = {
            "started_at": datetime.utcnow().isoformat(),
            "contacts_fetched": 0,
            "contacts_created": 0,
            "contacts_updated": 0,
            "errors": [],
        }

        try:
            # Pull all contacts with pagination
            all_contacts = self._fetch_all_contacts()
            stats["contacts_fetched"] = len(all_contacts)

            logger.info(f"Fetched {len(all_contacts)} contacts from GoHighLevel")

            # Process each contact
            for contact_data in all_contacts:
                try:
                    self._upsert_contact(contact_data, stats)
                except Exception as e:
                    error_msg = f"Failed to process contact {contact_data.get('id')}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

            # Commit all changes
            self.db.commit()

            stats["completed_at"] = datetime.utcnow().isoformat()
            logger.info(
                f"Sync complete: {stats['contacts_created']} created, "
                f"{stats['contacts_updated']} updated, "
                f"{len(stats['errors'])} errors"
            )

            return stats

        except Exception as e:
            self.db.rollback()
            error_msg = f"Sync failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            stats["errors"].append(error_msg)
            stats["completed_at"] = datetime.utcnow().isoformat()
            return stats

    def _fetch_all_contacts(self) -> List[Dict[str, Any]]:
        """
        Fetch ALL contacts from GoHighLevel using pagination.

        Returns:
            List of all contact dictionaries
        """
        all_contacts = []
        limit = 100  # Max per page
        start_after = None
        start_after_id = None

        while True:
            try:
                # Build params
                params = {"limit": limit, "locationId": self.client.location_id}
                if start_after:
                    params["startAfter"] = start_after
                if start_after_id:
                    params["startAfterId"] = start_after_id

                # Fetch page
                response = self.client.get("/contacts/", params=params)

                contacts = response.get("contacts", [])
                if not contacts:
                    break

                all_contacts.extend(contacts)
                logger.info(f"Fetched page: {len(contacts)} contacts, total so far: {len(all_contacts)}")

                # Check for next page
                meta = response.get("meta", {})
                if not meta.get("nextPage"):
                    break

                # Update pagination params
                start_after = meta.get("startAfter")
                start_after_id = meta.get("startAfterId")

            except Exception as e:
                logger.error(f"Error fetching contacts page: {str(e)}", exc_info=True)
                break

        return all_contacts

    def _upsert_contact(self, contact_data: Dict[str, Any], stats: Dict[str, Any]) -> None:
        """
        Insert or update a contact in the database.

        Args:
            contact_data: Raw contact data from GoHighLevel API
            stats: Statistics dictionary to update
        """
        contact_id = contact_data.get("id")
        if not contact_id:
            raise ValueError("Contact missing ID")

        # Check if contact exists
        existing = self.db.query(Contact).filter(Contact.id == contact_id).first()

        if existing:
            # Update existing contact
            existing.data = contact_data
            existing.last_synced = datetime.utcnow()
            existing.expires_at = datetime.utcnow() + timedelta(hours=1)  # Cache for 1 hour
            stats["contacts_updated"] += 1
            action = "updated"
        else:
            # Create new contact
            contact = Contact(
                id=contact_id,
                ecosystem="gohighlevel",
                data=contact_data,
                last_synced=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
            self.db.add(contact)
            stats["contacts_created"] += 1
            action = "created"

        # Create or update contact context for intelligent search
        self._upsert_contact_context(contact_data)

        # Record interaction
        self._record_sync_interaction(contact_id, action)

    def _upsert_contact_context(self, contact_data: Dict[str, Any]) -> None:
        """
        Create or update contact context for natural language intelligence.

        Analyzes the contact data and extracts:
        - Possible nicknames
        - Company information
        - Importance signals
        """
        contact_id = contact_data.get("id")
        if not contact_id:
            return

        # Check if context exists
        context = self.db.query(ContactContext).filter(ContactContext.contact_id == contact_id).first()

        # Extract names and possible nicknames
        first_name = contact_data.get("firstName", "")
        last_name = contact_data.get("lastName", "")
        company_name = contact_data.get("companyName", "")
        contact_name = contact_data.get("contactName", "")

        # Build nicknames list
        nicknames = []
        if first_name:
            nicknames.append(first_name.lower())
        if company_name:
            nicknames.append(company_name.lower())
            # Add variations like "John from MedSupply"
            if first_name:
                nicknames.append(f"{first_name.lower()} from {company_name.lower()}")

        # Calculate importance score based on signals
        importance = 5  # Default
        if contact_data.get("tags"):
            importance += 1  # Has tags = slightly more important
        if contact_data.get("type") == "lead":
            importance += 2  # Leads are more important
        if contact_data.get("lastActivity"):
            # Recently active = more important
            last_activity = contact_data.get("lastActivity", 0)
            if last_activity > 0:
                days_ago = (datetime.utcnow().timestamp() * 1000 - last_activity) / (1000 * 60 * 60 * 24)
                if days_ago < 7:
                    importance += 2
                elif days_ago < 30:
                    importance += 1

        importance = min(importance, 10)  # Cap at 10

        if context:
            # Update existing context
            if nicknames:
                # Merge new nicknames with existing
                existing_nicks = set(context.nicknames or [])
                new_nicks = set(nicknames)
                context.nicknames = list(existing_nicks | new_nicks)
            context.contact_name = contact_name or f"{first_name} {last_name}".strip()
            context.company_info = company_name
            context.importance_score = importance
            context.updated_at = datetime.utcnow()
        else:
            # Create new context
            context = ContactContext(
                contact_id=contact_id,
                contact_name=contact_name or f"{first_name} {last_name}".strip(),
                nicknames=nicknames,
                company_info=company_name,
                importance_score=importance,
            )
            self.db.add(context)

    def _record_sync_interaction(self, contact_id: str, action: str) -> None:
        """Record that we synced this contact."""
        interaction = InteractionHistory(
            contact_id=contact_id,
            interaction_type="synced",
            description=f"Contact {action} during sync",
            extra_data={"sync_time": datetime.utcnow().isoformat()},
        )
        self.db.add(interaction)

    def get_sync_stats(self) -> Dict[str, Any]:
        """Get statistics about the current sync state."""
        stats = {
            "total_contacts": self.db.query(func.count(Contact.id)).scalar(),
            "total_contexts": self.db.query(func.count(ContactContext.contact_id)).scalar(),
            "last_sync": None,
            "contacts_by_type": {},
            "contacts_by_importance": {},
        }

        # Get last sync time from most recent contact
        latest = self.db.query(Contact).order_by(Contact.last_synced.desc()).first()
        if latest:
            stats["last_sync"] = latest.last_synced.isoformat()

        # Get contact counts by type
        # Note: For now, skip this aggregation to avoid JSON query complexity
        # Can be added later with proper PostgreSQL JSON operators
        stats["contacts_by_type"] = {"note": "Type aggregation pending implementation"}

        # Get contact counts by importance
        for row in (
            self.db.query(ContactContext.importance_score, func.count(ContactContext.contact_id))
            .group_by(ContactContext.importance_score)
            .order_by(ContactContext.importance_score.desc())
        ):
            stats["contacts_by_importance"][row[0]] = row[1]

        return stats
