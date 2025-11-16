"""Contact context service for natural language intelligence.

This service provides:
- Fuzzy search across contact names, nicknames, and companies
- Context storage (nicknames, notes, relationships)
- Interaction tracking
- Intelligence for natural language queries
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.db.models import ContactContext, InteractionHistory, Contact
import logging

logger = logging.getLogger(__name__)


class ContactContextService:
    """Service for managing contact context and enabling natural language search."""

    def __init__(self, db: Session):
        self.db = db

    def search_contacts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Intelligent contact search with fuzzy matching.

        Searches across:
        - Contact names (fuzzy)
        - Nicknames in context
        - Company info
        - Personal notes

        Args:
            query: Natural language search query
            limit: Maximum results to return

        Returns:
            List of contact matches with relevance scoring
        """
        query_lower = query.lower().strip()
        results = []

        # Strategy 1: Search contact_context table (nicknames, notes)
        context_matches = (
            self.db.query(ContactContext)
            .filter(
                or_(
                    ContactContext.contact_name.ilike(f"%{query}%"),
                    ContactContext.company_info.ilike(f"%{query}%"),
                    ContactContext.personal_notes.ilike(f"%{query}%"),
                    ContactContext.nicknames.op("&&")(func.array([query_lower]))  # Array overlap
                )
            )
            .order_by(ContactContext.importance_score.desc())
            .limit(limit)
            .all()
        )

        for ctx in context_matches:
            # Get the actual contact data
            contact = self.db.query(Contact).filter(Contact.id == ctx.contact_id).first()
            if contact:
                results.append({
                    "contact_id": ctx.contact_id,
                    "contact": contact.data,
                    "context": {
                        "nicknames": ctx.nicknames or [],
                        "personal_notes": ctx.personal_notes,
                        "company_info": ctx.company_info,
                        "importance_score": ctx.importance_score,
                        "last_interaction": ctx.last_interaction.isoformat() if ctx.last_interaction else None,
                    },
                    "match_type": "context",
                })

        # Strategy 2: Search cached contacts table directly (fallback)
        if len(results) < limit:
            cached_contacts = (
                self.db.query(Contact)
                .filter(
                    func.lower(func.cast(Contact.data, func.TEXT)).like(f"%{query_lower}%")
                )
                .limit(limit - len(results))
                .all()
            )

            existing_ids = {r["contact_id"] for r in results}
            for contact in cached_contacts:
                if contact.id not in existing_ids:
                    results.append({
                        "contact_id": contact.id,
                        "contact": contact.data,
                        "context": None,
                        "match_type": "direct",
                    })

        return results[:limit]

    def save_context(
        self,
        contact_id: str,
        contact_name: str,
        nicknames: Optional[List[str]] = None,
        personal_notes: Optional[str] = None,
        company_info: Optional[str] = None,
        importance_score: Optional[int] = None,
    ) -> ContactContext:
        """
        Save or update context for a contact.

        Args:
            contact_id: GoHighLevel contact ID
            contact_name: Full name of contact
            nicknames: List of nicknames/aliases
            personal_notes: Free-form notes
            company_info: Company background
            importance_score: 1-10 importance rating

        Returns:
            ContactContext object
        """
        # Check if context already exists
        context = self.db.query(ContactContext).filter(ContactContext.contact_id == contact_id).first()

        if context:
            # Update existing
            if nicknames is not None:
                # Merge new nicknames with existing, keeping unique
                existing = set(context.nicknames or [])
                new_nicks = set([n.lower().strip() for n in nicknames])
                context.nicknames = list(existing | new_nicks)
            if personal_notes is not None:
                context.personal_notes = personal_notes
            if company_info is not None:
                context.company_info = company_info
            if importance_score is not None:
                context.importance_score = importance_score
            context.updated_at = datetime.utcnow()
        else:
            # Create new
            context = ContactContext(
                contact_id=contact_id,
                contact_name=contact_name,
                nicknames=[n.lower().strip() for n in (nicknames or [])],
                personal_notes=personal_notes,
                company_info=company_info,
                importance_score=importance_score or 5,
            )
            self.db.add(context)

        self.db.commit()
        self.db.refresh(context)
        logger.info(f"Saved context for contact {contact_id}: {contact_name}")
        return context

    def get_context(self, contact_id: str) -> Optional[ContactContext]:
        """Get context for a specific contact."""
        return self.db.query(ContactContext).filter(ContactContext.contact_id == contact_id).first()

    def record_interaction(
        self,
        contact_id: str,
        interaction_type: str,
        description: Optional[str] = None,
        extra_data: Optional[Dict] = None,
    ) -> InteractionHistory:
        """
        Record an interaction with a contact.

        Args:
            contact_id: GoHighLevel contact ID
            interaction_type: Type of interaction (viewed, updated, called, emailed, sms)
            description: Human-readable description
            extra_data: Additional context

        Returns:
            InteractionHistory object
        """
        interaction = InteractionHistory(
            contact_id=contact_id,
            interaction_type=interaction_type,
            description=description,
            extra_data=extra_data,
        )
        self.db.add(interaction)

        # Update contact_context last_interaction and count
        context = self.db.query(ContactContext).filter(ContactContext.contact_id == contact_id).first()
        if context:
            context.last_interaction = datetime.utcnow()
            context.interaction_count += 1
            context.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(interaction)
        logger.info(f"Recorded {interaction_type} interaction for contact {contact_id}")
        return interaction

    def get_interaction_history(
        self,
        contact_id: str,
        limit: int = 10,
        interaction_type: Optional[str] = None,
    ) -> List[InteractionHistory]:
        """
        Get interaction history for a contact.

        Args:
            contact_id: GoHighLevel contact ID
            limit: Maximum interactions to return
            interaction_type: Filter by type (optional)

        Returns:
            List of interactions, most recent first
        """
        query = self.db.query(InteractionHistory).filter(InteractionHistory.contact_id == contact_id)

        if interaction_type:
            query = query.filter(InteractionHistory.interaction_type == interaction_type)

        return query.order_by(InteractionHistory.timestamp.desc()).limit(limit).all()

    def get_important_contacts(self, min_score: int = 7, limit: int = 20) -> List[ContactContext]:
        """Get most important contacts."""
        return (
            self.db.query(ContactContext)
            .filter(ContactContext.importance_score >= min_score)
            .order_by(ContactContext.importance_score.desc(), ContactContext.interaction_count.desc())
            .limit(limit)
            .all()
        )

    def get_contacts_needing_followup(self, days_since_interaction: int = 7, limit: int = 20) -> List[ContactContext]:
        """Get contacts that haven't been interacted with recently."""
        cutoff_date = datetime.utcnow() - func.make_interval(days=days_since_interaction)
        return (
            self.db.query(ContactContext)
            .filter(
                or_(
                    ContactContext.last_interaction < cutoff_date,
                    ContactContext.last_interaction.is_(None),
                )
            )
            .filter(ContactContext.importance_score >= 5)  # Only important contacts
            .order_by(ContactContext.importance_score.desc())
            .limit(limit)
            .all()
        )
