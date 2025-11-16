from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from app.mcp.base import BaseTool
from app.mcp.models import ToolResponse


class ToolNotFoundError(KeyError):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.metadata.name] = tool

    def bulk_register(self, tools: Iterable[BaseTool]) -> None:
        for tool in tools:
            self.register(tool)

    def list_tools(self, ecosystem: Optional[str] = None) -> List[Dict[str, object]]:
        values = self._tools.values()
        if ecosystem:
            values = [tool for tool in values if tool.metadata.ecosystem == ecosystem]
        return [tool.serialize() for tool in values]

    def execute(self, tool_name: str, params: Optional[Dict[str, object]] = None) -> ToolResponse:
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ToolNotFoundError(f"No tool registered with name '{tool_name}'")
        params = params or {}
        return tool.run(**params)


registry = ToolRegistry()
