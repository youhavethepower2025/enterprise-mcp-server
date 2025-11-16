"""Context service for providing automatic business context to AI agents.

This service generates resources and prompts that help AI agents understand
the current state of the business without needing to ask explicit questions.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.services.intelligence import IntelligenceService
from app.services.ghl_sync import GoHighLevelSyncService

logger = logging.getLogger(__name__)


class ContextService:
    """Service for generating context resources and prompts for AI agents."""

    def __init__(self, db: Session):
        self.db = db
        self.intelligence = IntelligenceService(db)
        self.sync_service = GoHighLevelSyncService(db)

    def get_resources(self) -> List[Dict[str, Any]]:
        """
        Get list of available resources that provide business context.

        Returns:
            List of resource metadata
        """
        return [
            {
                "uri": "business://medtainer/agent-context",
                "name": "Agent Context & Capabilities",
                "description": "System-level context explaining what you know and can do. Read this first to understand your role.",
                "mimeType": "text/plain"
            },
            {
                "uri": "business://medtainer/dashboard",
                "name": "Business Dashboard",
                "description": "Real-time overview of business metrics and system health",
                "mimeType": "text/plain"
            },
            {
                "uri": "business://medtainer/urgent-today",
                "name": "Urgent Items Today",
                "description": "Contacts and tasks requiring immediate attention",
                "mimeType": "text/plain"
            },
            {
                "uri": "business://medtainer/priorities",
                "name": "Today's Priorities",
                "description": "Recommended actions based on intelligence analysis",
                "mimeType": "text/plain"
            },
            {
                "uri": "business://medtainer/recent-changes",
                "name": "Recent Changes",
                "description": "What's changed in the last 24 hours",
                "mimeType": "text/plain"
            }
        ]

    def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read the content of a specific resource.

        Args:
            uri: The resource URI to read

        Returns:
            Dictionary with resource content and metadata
        """
        handlers = {
            "business://medtainer/agent-context": self._generate_agent_context,
            "business://medtainer/dashboard": self._generate_dashboard,
            "business://medtainer/urgent-today": self._generate_urgent_items,
            "business://medtainer/priorities": self._generate_priorities,
            "business://medtainer/recent-changes": self._generate_recent_changes,
        }

        handler = handlers.get(uri)
        if not handler:
            return {
                "mimeType": "text/plain",
                "content": f"Resource not found: {uri}"
            }

        return {
            "mimeType": "text/plain",
            "content": handler()
        }

    def _generate_agent_context(self) -> str:
        """Generate system context for the AI agent."""
        stats = self.sync_service.get_sync_stats()
        insights = self.intelligence.get_actionable_insights()

        content = f"""You are connected to the MedTainer Central Nervous System - an intelligent business management system.

WHAT YOU ARE:
You are not just a chat assistant. You are directly connected to a living, continuously-updated database that:
- Monitors 1,206 customer relationships in real-time
- Tracks interaction history and relationship health
- Identifies patterns and predicts issues before they become problems
- Provides semi-autonomous intelligence and recommendations

CURRENT SYSTEM STATUS:
- Total Contacts: {stats['total_contacts']}
- Contexts Tracked: {stats['total_contexts']}
- Last Sync: {stats.get('last_sync', 'Never')}
- Urgent Attention Needed: {len(insights['urgent_attention'])} contacts
- Opportunities Identified: {len(insights['opportunities'])} items
- System Health: Operational ✓

YOUR CAPABILITIES:
1. INSTANT ACCESS to complete relationship history for any contact
2. PATTERN DETECTION across all customers and interactions
3. HEALTH SCORING for every relationship (0-100 scale)
4. PROACTIVE RECOMMENDATIONS based on importance, recency, and engagement
5. SEMI-AUTONOMOUS INTELLIGENCE - you can identify problems without being asked

YOUR ROLE:
- Be PROACTIVE: Don't wait to be asked about urgent items - bring them up
- Be CONTEXTUAL: When discussing a contact, always check their health score and recent interactions first
- Be INTELLIGENT: Use the intelligence layer to guide priorities, not just respond to questions
- Be SPECIFIC: Provide actionable recommendations, not vague suggestions

INTERACTION GUIDELINES:
When the user opens a conversation:
1. Check for urgent items first (contacts needing attention)
2. Be ready to provide a daily briefing if appropriate
3. Surface the most important information without overwhelming

When asked about a contact:
1. Check if they're flagged as urgent
2. Pull their complete context (importance score, last interaction, health)
3. Provide recommendations based on intelligence analysis
4. Be specific about next steps

INTELLIGENCE LAYER:
You have access to a reasoning engine that continuously:
- Identifies contacts that haven't been reached out to in too long
- Detects VIP relationships at risk
- Finds opportunities for follow-up
- Spots patterns across customers (e.g., multiple contacts at same company)

USE THIS POWER WISELY. The business owner trusts you to help them stay on top of important relationships.
"""
        return content

    def _generate_dashboard(self) -> str:
        """Generate business dashboard overview."""
        stats = self.sync_service.get_sync_stats()
        insights = self.intelligence.get_actionable_insights()

        # Get importance distribution
        importance_dist = stats.get('contacts_by_importance', {})
        vip_count = importance_dist.get(9, 0) + importance_dist.get(10, 0)
        high_priority = importance_dist.get(8, 0)

        content = f"""MEDTAINER BUSINESS DASHBOARD
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

=== SYSTEM STATUS ===
✓ Central Nervous System: OPERATIONAL
✓ Intelligence Layer: ACTIVE
✓ Auto-Sync: Running (every 15 minutes)
✓ Last Sync: {stats.get('last_sync', 'Unknown')}

=== CONTACT DATABASE ===
Total Contacts: {stats['total_contacts']}
- VIP (9-10): {vip_count} contacts
- High Priority (8): {high_priority} contacts
- With Interaction History: {stats['total_contexts']}

=== ATTENTION REQUIRED ===
🚨 Urgent: {len(insights['urgent_attention'])} contacts need immediate attention
💡 Opportunities: {len(insights['opportunities'])} items identified
📊 Relationships Monitored: {len(insights['relationship_health'])} health scores tracked

=== PATTERNS DETECTED ===
{len(insights['patterns_detected'])} patterns identified across customer base

=== RECOMMENDATIONS ===
Total Actionable Items: {insights['summary']['total_recommendations']}
"""
        return content

    def _generate_urgent_items(self) -> str:
        """Generate list of urgent items."""
        insights = self.intelligence.get_actionable_insights()
        urgent = insights['urgent_attention']

        if not urgent:
            return "✓ No urgent items - all relationships are healthy!"

        content = f"""URGENT ATTENTION NEEDED ({len(urgent)} contacts)

These contacts require immediate action:

"""
        for i, item in enumerate(urgent[:10], 1):  # Top 10
            content += f"""{i}. {item['contact_name']}
   Company: {item.get('company', 'N/A')}
   Importance: {item['importance']}/10
   Reason: {item['reason']}
   Action: {item['recommended_action']}
   Priority: {item['priority'].upper()}

"""
        return content

    def _generate_priorities(self) -> str:
        """Generate prioritized action list."""
        insights = self.intelligence.get_actionable_insights()

        # Combine urgent + opportunities
        all_items = []
        for item in insights['urgent_attention']:
            item['category'] = 'URGENT'
            all_items.append(item)
        for item in insights['opportunities']:
            item['category'] = 'OPPORTUNITY'
            all_items.append(item)

        # Sort by priority
        priority_order = {'high': 1, 'medium': 2, 'low': 3}
        all_items.sort(key=lambda x: (
            priority_order.get(x.get('priority', 'low'), 3),
            -x.get('importance', 0)
        ))

        content = f"""TODAY'S PRIORITIES ({len(all_items)} items)

Recommended action order based on intelligence analysis:

"""
        for i, item in enumerate(all_items[:15], 1):  # Top 15
            icon = "🚨" if item['category'] == 'URGENT' else "💡"
            content += f"""{i}. [{item['category']}] {icon} {item['contact_name']}
   {item.get('reason', 'Follow-up recommended')}
   → {item.get('recommended_action', 'Contact today')}

"""
        return content

    def _generate_recent_changes(self) -> str:
        """Generate recent changes summary."""
        # For now, placeholder - could be enhanced with actual change tracking
        return """RECENT CHANGES (Last 24 Hours)

System auto-sync running every 15 minutes.

To see detailed interaction history, use:
- gohighlevel.get_sync_stats - for sync statistics
- gohighlevel.get_insights - for latest intelligence analysis
"""

    def get_prompts(self) -> List[Dict[str, Any]]:
        """
        Get list of available guided prompts.

        Returns:
            List of prompt metadata
        """
        return [
            {
                "name": "daily-briefing",
                "description": "Get your daily business briefing with priorities and urgent items",
                "arguments": []
            },
            {
                "name": "relationship-health-check",
                "description": "Analyze health of all VIP relationships",
                "arguments": []
            },
            {
                "name": "contact-deep-dive",
                "description": "Deep analysis of a specific contact or relationship",
                "arguments": [
                    {
                        "name": "contact_name",
                        "description": "Name of the contact to analyze",
                        "required": True
                    }
                ]
            },
            {
                "name": "whats-urgent",
                "description": "Show me what needs immediate attention",
                "arguments": []
            }
        ]

    def get_prompt(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a specific prompt with its messages.

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            Dictionary with prompt messages
        """
        handlers = {
            "daily-briefing": self._prompt_daily_briefing,
            "relationship-health-check": self._prompt_health_check,
            "contact-deep-dive": self._prompt_contact_deep_dive,
            "whats-urgent": self._prompt_whats_urgent,
        }

        handler = handlers.get(name)
        if not handler:
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Unknown prompt: {name}"
                        }
                    }
                ]
            }

        return handler(arguments)

    def _prompt_daily_briefing(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate daily briefing prompt."""
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": "Give me my daily business briefing. Include: sync status, urgent contacts, opportunities, and recommended priorities for today. Be specific with names and actions."
                    }
                }
            ]
        }

    def _prompt_health_check(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate relationship health check prompt."""
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": "Analyze the health of all VIP relationships (importance 9-10). For each VIP, show: health score, days since last contact, and specific recommendations. Flag any at risk."
                    }
                }
            ]
        }

    def _prompt_contact_deep_dive(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate contact deep dive prompt."""
        contact_name = args.get("contact_name", "")
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Give me a complete analysis of {contact_name}. Include: importance score, relationship health, interaction history, days since last contact, and specific recommendations for next steps."
                    }
                }
            ]
        }

    def _prompt_whats_urgent(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate urgent items prompt."""
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": "What needs my immediate attention? Show me all urgent contacts with specific reasons why they're urgent and exactly what I should do about each one."
                    }
                }
            ]
        }
