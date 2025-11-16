from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolMetadata(BaseModel):
    name: str
    description: str
    ecosystem: str
    version: str = "0.1.0"
    requires_secrets: List[str] = Field(default_factory=list)
    docs_path: Optional[str] = None
    enabled: bool = True


class ToolResponse(BaseModel):
    status: str
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
