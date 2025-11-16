from __future__ import annotations

from typing import Any, Dict, List

from app.mcp.tool_registry import registry


class QAgentPlanner:
    """High-level orchestrator outline for the future voice-driven agent."""

    def __init__(self) -> None:
        self.available_tools = registry.list_tools()

    def describe_tools(self) -> List[Dict[str, Any]]:
        return self.available_tools

    def plan_for_goal(self, goal: str) -> Dict[str, Any]:
        """Return a toy plan aligning goals to tool calls."""
        relevant = [tool for tool in self.available_tools if tool["ecosystem"] in goal.lower()]
        return {
            "goal": goal,
            "steps": [
                {"tool": tool["name"], "reason": f"Matches ecosystem {tool['ecosystem']}"} for tool in relevant
            ]
            or [{"tool": "research", "reason": "No direct tool matched goal"}],
        }
