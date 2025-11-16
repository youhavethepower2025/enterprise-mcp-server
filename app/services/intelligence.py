"""Intelligence and reasoning layer for the MCP agent.

This service continuously monitors data, identifies patterns, generates insights,
and recommends actions. It does NOT execute actions - it's semi-autonomous,
providing intelligence that external agents (like Claude Desktop) can act upon.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.db.models import Contact, ContactContext, InteractionHistory
from app.core.config import settings

logger = logging.getLogger(__name__)


class IntelligenceService:
    """Semi-autonomous intelligence layer that monitors, analyzes, and recommends."""

    def __init__(self, db: Session):
        self.db = db

    def get_actionable_insights(self) -> Dict[str, Any]:
        """
        Get current actionable insights across all contacts.

        This is the main "agentic" function that analyzes the entire database
        and generates recommendations. Called when user engages with Claude Desktop.

        Returns:
            Dictionary with categorized insights and recommendations
        """
        logger.info("Generating actionable insights across all contacts")

        insights = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {},
            "urgent_attention": [],
            "opportunities": [],
            "relationship_health": [],
            "patterns_detected": [],
        }

        # Analyze different categories
        insights["urgent_attention"] = self._identify_urgent_contacts()
        insights["opportunities"] = self._identify_opportunities()
        insights["relationship_health"] = self._assess_relationship_health()
        insights["patterns_detected"] = self._detect_patterns()

        # Generate summary
        insights["summary"] = {
            "total_recommendations": (
                len(insights["urgent_attention"])
                + len(insights["opportunities"])
                + len(insights["relationship_health"])
            ),
            "urgent_count": len(insights["urgent_attention"]),
            "opportunity_count": len(insights["opportunities"]),
        }

        logger.info(
            f"Generated {insights['summary']['total_recommendations']} recommendations"
        )
        return insights

    def _identify_urgent_contacts(self) -> List[Dict[str, Any]]:
        """
        Identify contacts that need URGENT attention.

        Criteria:
        - High importance (8+) but no contact in 14+ days
        - VIP (9+) with no contact in 7+ days
        """
        urgent = []
        cutoff_14_days = datetime.utcnow() - timedelta(days=14)
        cutoff_7_days = datetime.utcnow() - timedelta(days=7)

        # High importance, no recent contact
        high_importance_stale = (
            self.db.query(ContactContext)
            .filter(
                and_(
                    ContactContext.importance_score >= 8,
                    or_(
                        ContactContext.last_interaction < cutoff_14_days,
                        ContactContext.last_interaction.is_(None),
                    ),
                )
            )
            .limit(10)
            .all()
        )

        for context in high_importance_stale:
            contact = self.db.query(Contact).filter(Contact.id == context.contact_id).first()
            if not contact:
                continue

            days_since = (
                (datetime.utcnow() - context.last_interaction).days
                if context.last_interaction
                else 999
            )

            urgent.append(
                {
                    "contact_id": context.contact_id,
                    "contact_name": context.contact_name,
                    "company": context.company_info,
                    "importance": context.importance_score,
                    "reason": f"No contact in {days_since} days (importance: {context.importance_score}/10)",
                    "recommended_action": "Re-engage - Check in and assess current needs",
                    "priority": "high" if context.importance_score >= 9 else "medium",
                    "days_since_contact": days_since,
                }
            )

        # Sort by importance + days since contact
        urgent.sort(
            key=lambda x: (
                -x["importance"],  # Higher importance first
                -x["days_since_contact"],  # More days first
            )
        )

        return urgent

    def _identify_opportunities(self) -> List[Dict[str, Any]]:
        """
        Identify positive opportunities (not problems).

        Criteria:
        - Contacts that recently became high importance
        - Contacts with increasing engagement
        - VIP contacts that ARE being contacted (good!)
        """
        opportunities = []

        # VIP contacts that have been contacted recently (keep momentum)
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        vip_active = (
            self.db.query(ContactContext)
            .filter(
                and_(
                    ContactContext.importance_score >= 9,
                    ContactContext.last_interaction >= recent_cutoff,
                )
            )
            .limit(5)
            .all()
        )

        for context in vip_active:
            days_since = (
                (datetime.utcnow() - context.last_interaction).days
                if context.last_interaction
                else 0
            )

            opportunities.append(
                {
                    "contact_id": context.contact_id,
                    "contact_name": context.contact_name,
                    "company": context.company_info,
                    "importance": context.importance_score,
                    "reason": f"VIP contact with recent engagement ({days_since} days ago)",
                    "recommended_action": "Maintain momentum - Schedule next touchpoint",
                    "priority": "medium",
                }
            )

        return opportunities

    def _assess_relationship_health(self) -> List[Dict[str, Any]]:
        """
        Overall relationship health assessment.

        Provides a health score and trend for relationships.
        """
        health_assessments = []

        # Get contacts with interaction history
        contacts_with_history = (
            self.db.query(ContactContext)
            .filter(ContactContext.interaction_count > 0)
            .order_by(ContactContext.importance_score.desc())
            .limit(20)
            .all()
        )

        for context in contacts_with_history:
            days_since = (
                (datetime.utcnow() - context.last_interaction).days
                if context.last_interaction
                else 999
            )

            # Calculate health score
            health_score = self._calculate_health_score(context, days_since)

            health_assessments.append(
                {
                    "contact_id": context.contact_id,
                    "contact_name": context.contact_name,
                    "company": context.company_info,
                    "health_score": health_score["score"],
                    "health_status": health_score["status"],
                    "reason": health_score["reason"],
                    "trend": health_score["trend"],
                }
            )

        return health_assessments

    def _calculate_health_score(self, context: ContactContext, days_since_contact: int) -> Dict[str, Any]:
        """Calculate relationship health score (0-100)."""
        score = 100

        # Deduct points for staleness
        if days_since_contact > 60:
            score -= 50
            status = "cold"
            trend = "declining"
        elif days_since_contact > 30:
            score -= 30
            status = "cooling"
            trend = "declining"
        elif days_since_contact > 14:
            score -= 15
            status = "stable"
            trend = "stable"
        else:
            status = "warm"
            trend = "stable"

        # Add points for importance
        score += (context.importance_score - 5) * 5

        # Add points for interaction frequency
        if context.interaction_count > 10:
            score += 10
        elif context.interaction_count > 5:
            score += 5

        score = max(0, min(100, score))  # Clamp to 0-100

        return {
            "score": score,
            "status": status,
            "trend": trend,
            "reason": self._generate_health_reason(status, days_since_contact, context),
        }

    def _generate_health_reason(
        self, status: str, days_since: int, context: ContactContext
    ) -> str:
        """Generate human-readable health reason."""
        if status == "cold":
            return f"No contact in {days_since} days - relationship has gone cold"
        elif status == "cooling":
            return f"Last contact {days_since} days ago - relationship cooling"
        elif status == "warm":
            return f"Recent contact ({days_since} days ago) - relationship is warm"
        else:
            return f"Last contact {days_since} days ago"

    def _detect_patterns(self) -> List[Dict[str, Any]]:
        """
        Detect patterns across contacts.

        Examples:
        - Contacts clustering in certain companies/industries
        - Time-based patterns (e.g., "Fridays have fewer interactions")
        - Engagement patterns
        """
        patterns = []

        # Pattern 1: Company clustering
        company_distribution = (
            self.db.query(
                ContactContext.company_info, func.count(ContactContext.contact_id).label("count")
            )
            .filter(ContactContext.company_info.isnot(None))
            .group_by(ContactContext.company_info)
            .having(func.count(ContactContext.contact_id) >= 2)
            .order_by(func.count(ContactContext.contact_id).desc())
            .limit(5)
            .all()
        )

        if company_distribution:
            for company, count in company_distribution:
                patterns.append(
                    {
                        "type": "company_clustering",
                        "pattern": f"Multiple contacts at {company}",
                        "insight": f"{count} contacts work at {company} - consider account-based approach",
                        "data": {"company": company, "contact_count": count},
                    }
                )

        # Pattern 2: Importance distribution
        vip_count = self.db.query(ContactContext).filter(ContactContext.importance_score >= 9).count()
        high_count = self.db.query(ContactContext).filter(ContactContext.importance_score == 8).count()
        total_count = self.db.query(ContactContext).count()

        patterns.append(
            {
                "type": "importance_distribution",
                "pattern": "Contact importance distribution",
                "insight": f"{vip_count} VIP contacts ({vip_count/total_count*100:.1f}%), {high_count} high priority ({high_count/total_count*100:.1f}%)",
                "data": {
                    "vip_count": vip_count,
                    "high_priority_count": high_count,
                    "total_count": total_count,
                },
            }
        )

        return patterns

    def analyze_contact(self, contact_id: str) -> Dict[str, Any]:
        """
        Deep analysis of a single contact.

        This is called when user asks about a specific contact.
        Provides comprehensive insights about that relationship.
        """
        contact = self.db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            return {"error": "Contact not found"}

        context = self.db.query(ContactContext).filter(ContactContext.contact_id == contact_id).first()

        interactions = (
            self.db.query(InteractionHistory)
            .filter(InteractionHistory.contact_id == contact_id)
            .order_by(InteractionHistory.timestamp.desc())
            .limit(10)
            .all()
        )

        days_since = (
            (datetime.utcnow() - context.last_interaction).days if context and context.last_interaction else 999
        )

        health = self._calculate_health_score(context, days_since) if context else None

        return {
            "contact_id": contact_id,
            "basic_info": {
                "name": context.contact_name if context else contact.data.get("contactName"),
                "company": context.company_info if context else contact.data.get("companyName"),
                "email": contact.data.get("email"),
                "phone": contact.data.get("phone"),
                "type": contact.data.get("type"),
            },
            "intelligence": {
                "importance_score": context.importance_score if context else 5,
                "nicknames": context.nicknames if context else [],
                "interaction_count": context.interaction_count if context else 0,
                "last_interaction": context.last_interaction.isoformat() if context and context.last_interaction else None,
                "days_since_contact": days_since,
            },
            "relationship_health": health,
            "recent_interactions": [
                {
                    "type": interaction.interaction_type,
                    "description": interaction.description,
                    "timestamp": interaction.timestamp.isoformat(),
                }
                for interaction in interactions
            ],
            "recommendations": self._generate_contact_recommendations(contact, context, days_since),
        }

    def _generate_contact_recommendations(
        self, contact: Contact, context: Optional[ContactContext], days_since: int
    ) -> List[str]:
        """Generate specific recommendations for a contact."""
        recommendations = []

        if days_since > 30:
            recommendations.append("⚠️ No contact in 30+ days - Re-engage immediately")
        elif days_since > 14:
            recommendations.append("⏰ Contact within next few days to maintain relationship")

        if context and context.importance_score >= 9:
            recommendations.append("⭐ VIP contact - Prioritize high-touch engagement")

        if contact.data.get("type") == "lead":
            recommendations.append("🎯 Active lead - Follow up on pipeline status")

        if not contact.data.get("email"):
            recommendations.append("📧 Missing email address - Collect contact info")

        if not recommendations:
            recommendations.append("✅ Relationship healthy - Continue current engagement pattern")

        return recommendations
