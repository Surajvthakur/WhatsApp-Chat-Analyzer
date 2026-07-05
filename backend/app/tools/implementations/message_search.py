import logging
import pandas as pd
from typing import Any
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.registry import register_tool
from app.tools.schemas import MessageSearchInput

logger = logging.getLogger(__name__)

@register_tool
class MessageSearchTool(BaseTool):
    """Searches messages containing a specific text query/keyword."""

    @property
    def name(self) -> str:
        return "message_search"

    @property
    def description(self) -> str:
        return (
            "Searches chat history for messages containing a specific keyword or phrase.\n"
            "Parameters:\n"
            "- query: The search term or phrase (case-insensitive)\n"
            "- limit: maximum number of matching messages to return (default: 50)"
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SEARCH

    @property
    def triggers(self) -> list[str]:
        return ["search", "find", "mention", "say", "talk about", "look for", "who said"]

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        validated = MessageSearchInput(**params)
        return validated.model_dump(exclude_none=True)

    def execute(self, df: pd.DataFrame, params: dict[str, Any]) -> ToolResult:
        query = params.get("query", "").strip()
        limit = params.get("limit", 50)

        if not query:
            return ToolResult(tool_name=self.name, success=False, error="Parameter 'query' is required.")

        if df.empty:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"messages": [], "total_matches": 0},
                message_count=0
            )

        # Case-insensitive substring match
        mask = df['message'].str.contains(re_escape_query := re_escape(query), case=False, na=False)
        filtered_df = df[mask]
        total_matches = len(filtered_df)

        # Truncate result
        truncated_df = filtered_df.head(limit)
        messages_list = []
        for idx, row in truncated_df.iterrows():
            date_formatted = row['date'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row['date'], 'strftime') else str(row['date'])
            messages_list.append({
                "date": date_formatted,
                "user": str(row['user']),
                "message": str(row['message'])
            })

        result_data = {
            "search_query": query,
            "messages": messages_list,
            "total_matches": total_matches,
            "truncated": total_matches > limit,
            "limit": limit
        }

        # Keep matching messages in pipeline chaining metadata
        metadata = {
            "filtered_df": filtered_df,
            "filter_type": "search",
            "query": query
        }

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=result_data,
            message_count=total_matches,
            metadata=metadata
        )

# Simple re.escape replacement since we aren't importing re
def re_escape(text: str) -> str:
    import re
    return re.escape(text)
