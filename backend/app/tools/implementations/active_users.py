import logging
import pandas as pd
from typing import Any
import helper
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.registry import register_tool
from app.tools.schemas import ActiveUsersInput

logger = logging.getLogger(__name__)

@register_tool
class ActiveUsersTool(BaseTool):
    """Computes the most active/busy users in the chat."""

    @property
    def name(self) -> str:
        return "active_users"

    @property
    def description(self) -> str:
        return (
            "Computes and returns the most active users in the chat based on message count.\n"
            "Parameters:\n"
            "- limit: The number of active users to return (default: 5)"
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYSIS

    @property
    def triggers(self) -> list[str]:
        return ["active", "busy", "most active", "talks the most", "who is the most active", "active user", "sent most", "top users"]

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        validated = ActiveUsersInput(**params)
        return validated.model_dump(exclude_none=True)

    def execute(self, df: pd.DataFrame, params: dict[str, Any]) -> ToolResult:
        if df.empty:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"active_users": []},
                message_count=0
            )

        limit = params.get("limit", 5)

        # Pre-filter group notifications
        df_filtered = df[df["user"] != "group_notification"]
        if df_filtered.empty:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"active_users": []},
                message_count=0
            )

        # Get top users by count
        user_counts = df_filtered['user'].value_counts()
        total_messages = len(df_filtered)

        active_users_list = []
        for name, count in user_counts.head(limit).items():
            percentage = round((count / total_messages) * 100, 2)
            active_users_list.append({
                "username": str(name),
                "message_count": int(count),
                "percentage": float(percentage)
            })

        result_data = {
            "active_users": active_users_list,
            "total_messages_analyzed": total_messages
        }

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=result_data,
            message_count=len(df)
        )
