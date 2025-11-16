"""Agentic intelligence tools for GoHighLevel.

These tools expose the semi-autonomous intelligence layer via MCP protocol.
When Claude Desktop calls these tools, it gets rich, context-aware responses
with insights, recommendations, and proactive guidance.
"""

from app.mcp.base import BaseTool
from app.mcp.models import ToolMetadata, ToolResponse
from app.db.session import SessionLocal
from app.services.intelligence import IntelligenceService
import logging

logger = logging.getLogger(__name__)


class GetActionableInsightsTool(BaseTool):
    """
    Get actionable insights and recommendations from the MCP agent.

    This is the main "agentic" tool - it analyzes all data and tells you
    what needs attention, what opportunities exist, and what actions to take.
    """

    metadata = ToolMetadata(
        name="gohighlevel.get_insights",
        description=(
            "Get intelligent insights and recommendations from the MCP agent. "
            "This analyzes all contacts and identifies: urgent attention needed, "
            "opportunities, relationship health issues, and detected patterns. "
            "Use this to get proactive guidance on what to do next."
        ),
        ecosystem="gohighlevel",
        requires_secrets=[],
    )

    def __init__(self) -> None:
        super().__init__(client=None)

    def run(self) -> ToolResponse:
        """Get insights and recommendations."""
        logger.info("Generating actionable insights via MCP tool")

        db = SessionLocal()
        try:
            intelligence = IntelligenceService(db)
            insights = intelligence.get_actionable_insights()

            # Generate human-friendly summary
            summary_text = self._generate_summary_text(insights)

            return ToolResponse(
                status="ok",
                data=insights,
                metadata={
                    "source": "intelligence_layer",
                    "message": summary_text,
                },
            )

        except Exception as e:
            logger.error(f"Failed to generate insights: {str(e)}", exc_info=True)
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "intelligence_layer"},
            )
        finally:
            db.close()

    def _generate_summary_text(self, insights: dict) -> str:
        """Generate human-readable summary."""
        urgent_count = len(insights["urgent_attention"])
        opp_count = len(insights["opportunities"])

        parts = []
        if urgent_count > 0:
            parts.append(f"{urgent_count} contacts need urgent attention")
        if opp_count > 0:
            parts.append(f"{opp_count} opportunities identified")

        if parts:
            return "Intelligence analysis complete: " + ", ".join(parts)
        else:
            return "All relationships healthy - no urgent actions needed"


class AnalyzeContactTool(BaseTool):
    """
    Deep analysis of a specific contact.

    Provides comprehensive insights about a single relationship including
    health score, interaction history, and personalized recommendations.
    """

    metadata = ToolMetadata(
        name="gohighlevel.analyze_contact",
        description=(
            "Get deep intelligence analysis for a specific contact. "
            "Provides relationship health score, interaction patterns, "
            "days since last contact, and personalized recommendations. "
            "Use when user asks about a specific person or company."
        ),
        ecosystem="gohighlevel",
        requires_secrets=[],
    )

    def __init__(self) -> None:
        super().__init__(client=None)

    def run(self, contact_id: str) -> ToolResponse:
        """Analyze a specific contact."""
        logger.info(f"Analyzing contact: {contact_id}")

        db = SessionLocal()
        try:
            intelligence = IntelligenceService(db)
            analysis = intelligence.analyze_contact(contact_id)

            if "error" in analysis:
                return ToolResponse(
                    status="error",
                    data=analysis,
                    metadata={"source": "intelligence_layer"},
                )

            # Generate summary
            name = analysis["basic_info"]["name"]
            health_score = analysis["relationship_health"]["score"] if analysis["relationship_health"] else 0
            days_since = analysis["intelligence"]["days_since_contact"]

            summary = f"{name}: Health score {health_score}/100, last contact {days_since} days ago"

            return ToolResponse(
                status="ok",
                data=analysis,
                metadata={
                    "source": "intelligence_layer",
                    "message": summary,
                },
            )

        except Exception as e:
            logger.error(f"Failed to analyze contact: {str(e)}", exc_info=True)
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "intelligence_layer"},
            )
        finally:
            db.close()


class GetContactRecommendationsTool(BaseTool):
    """
    Get prioritized list of contacts that need action.

    Returns contacts sorted by urgency/priority with specific
    recommended actions for each.
    """

    metadata = ToolMetadata(
        name="gohighlevel.get_recommendations",
        description=(
            "Get prioritized action recommendations for contacts. "
            "Returns a sorted list of contacts that need attention with "
            "specific recommended actions. Perfect for 'what should I do today?' queries."
        ),
        ecosystem="gohighlevel",
        requires_secrets=[],
    )

    def __init__(self) -> None:
        super().__init__(client=None)

    def run(self, limit: int = 10) -> ToolResponse:
        """Get prioritized recommendations."""
        logger.info(f"Generating top {limit} recommendations")

        db = SessionLocal()
        try:
            intelligence = IntelligenceService(db)
            insights = intelligence.get_actionable_insights()

            # Combine urgent + opportunities, sort by priority
            all_recommendations = []

            for item in insights["urgent_attention"]:
                item["category"] = "urgent"
                all_recommendations.append(item)

            for item in insights["opportunities"]:
                item["category"] = "opportunity"
                all_recommendations.append(item)

            # Sort by priority
            priority_order = {"high": 1, "medium": 2, "low": 3}
            all_recommendations.sort(key=lambda x: (
                priority_order.get(x.get("priority", "low"), 3),
                -x.get("importance", 0)
            ))

            # Limit
            top_recommendations = all_recommendations[:limit]

            summary = f"Generated {len(top_recommendations)} prioritized recommendations"

            return ToolResponse(
                status="ok",
                data={
                    "recommendations": top_recommendations,
                    "total_available": len(all_recommendations),
                },
                metadata={
                    "source": "intelligence_layer",
                    "message": summary,
                },
            )

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}", exc_info=True)
            return ToolResponse(
                status="error",
                data={"error": str(e)},
                metadata={"source": "intelligence_layer"},
            )
        finally:
            db.close()
