import pandas as pd
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

class ToolCategory(str, Enum):
    FILTER = "filter"          # Narrows down messages (e.g. date_filter, user_filter)
    ANALYSIS = "analysis"      # Computes analytics (e.g. active_users, emoji_analysis)
    SEARCH = "search"          # Searches content (e.g. message_search, topic_search)
    SUMMARY = "summary"        # Generates summaries (e.g. summary)

class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Any = None
    message_count: int | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class BaseTool(ABC):
    """Abstract base class that all chat tools must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier of the tool (e.g., 'date_filter')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A detailed description of what the tool does and what parameters it accepts.
        Used by the LLM for function-calling/routing.
        """
        pass

    @property
    @abstractmethod
    def category(self) -> ToolCategory:
        """The category of the tool, defining its role in the execution pipeline."""
        pass

    @property
    @abstractmethod
    def triggers(self) -> list[str]:
        """A list of keyword triggers or phrases used for quick heuristics matching."""
        pass

    @abstractmethod
    def execute(self, df: pd.DataFrame, params: dict[str, Any]) -> ToolResult:
        """Execute the tool's logic against the provided chat DataFrame.
        
        Args:
            df: The pandas DataFrame representing the active workspace's chat messages.
            params: Parameters parsed from the user query.
            
        Returns:
            A ToolResult object containing the structured data or error message.
        """
        pass

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate and clean parameters before execution. Override if needed."""
        return params
