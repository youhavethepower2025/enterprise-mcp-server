from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from app.mcp.models import ToolMetadata, ToolResponse


class BaseTool(ABC):
    """Abstract helper that every ecosystem tool inherits from."""

    metadata: ToolMetadata

    def __init__(self, **kwargs) -> None:
        if not hasattr(self, "metadata"):
            raise ValueError("Tool subclasses must define `metadata`.")
        for key, value in kwargs.items():
            setattr(self, key, value)

    @abstractmethod
    def run(self, **kwargs) -> ToolResponse:
        """Execute the tool with structured kwargs."""

    def requirements(self) -> List[str]:
        return self.metadata.requires_secrets

    def serialize(self) -> Dict[str, object]:
        return self.metadata.model_dump()
