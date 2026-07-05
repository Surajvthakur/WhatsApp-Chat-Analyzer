import logging
import pandas as pd
from typing import Any
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.registry import register_tool
from app.tools.schemas import UserFilterInput

logger = logging.getLogger(__name__)

@register_tool
class UserFilterTool(BaseTool):
    """Filters chat messages by a specific sender name (case-insensitive substring match)."""

    @property
    def name(self) -> str:
        return "user_filter"

    @property
    def description(self) -> str:
        return (
            "Filters chat messages by user. Use this when the query asks about messages sent "
            "by a specific user or wants to look at a single person's chat history.\n"
            "Parameters:\n"
            "- username: Name of the sender (performs case-insensitive substring match)\n"
            "- limit: maximum number of messages to return in structured result (default: 50)"
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILTER

    @property
    def triggers(self) -> list[str]:
        return ["user", "sender", "from", "said by", "messages of", "messages by", "sent by"]

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        validated = UserFilterInput(**params)
        return validated.model_dump(exclude_none=True)

    def execute(self, df: pd.DataFrame, params: dict[str, Any]) -> ToolResult:
        if df.empty:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"messages": [], "total_found": 0},
                message_count=0
            )

        username = params.get("username", "").strip()
        limit = params.get("limit", 50)

        if not username:
            return ToolResult(tool_name=self.name, success=False, error="Parameter 'username' is required.")

        # Find matching users in unique users list
        unique_users = df['user'].dropna().unique()
        matching_users = [
            str(u) for u in unique_users 
            if username.lower() in str(u).lower() and str(u) != 'group_notification'
        ]

        if not matching_users:
            # Let's perform a looser check or return empty
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "messages": [],
                    "total_found": 0,
                    "warning": f"No users matching '{username}' found in the chat."
                },
                message_count=0,
                metadata={"filtered_df": df.iloc[0:0]}  # Empty dataframe
            )

        filtered_df = df[df['user'].isin(matching_users)]
        total_found = len(filtered_df)

        # Truncate JSON output
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
            "messages": messages_list,
            "total_found": total_found,
            "truncated": total_found > limit,
            "limit": limit,
            "matched_users": matching_users
        }

        metadata = {
            "filtered_df": filtered_df,
            "filter_type": "user",
            "matched_users": matching_users
        }

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=result_data,
            message_count=total_found,
            metadata=metadata
        )
