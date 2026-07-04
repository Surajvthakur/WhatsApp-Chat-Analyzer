import logging
import pandas as pd
from typing import Any
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.registry import register_tool
from app.tools.schemas import ResponseTimeInput

logger = logging.getLogger(__name__)

@register_tool
class ResponseTimeTool(BaseTool):
    """Calculates response times between chat participants (how fast users reply to each other)."""

    @property
    def name(self) -> str:
        return "response_time"

    @property
    def description(self) -> str:
        return (
            "Calculates the response times between participants in the chat. Use this when the query "
            "asks about who replies fastest, response delays, or how long it takes for users to respond.\n"
            "Parameters:\n"
            "- user_a: Optional sender name to analyze specific pairwise interaction\n"
            "- user_b: Optional recipient name to analyze specific pairwise interaction"
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYSIS

    @property
    def triggers(self) -> list[str]:
        return ["response time", "reply speed", "how fast", "who replies first", "respond time", "reply time", "average reply"]

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        validated = ResponseTimeInput(**params)
        return validated.model_dump(exclude_none=True)

    def execute(self, df: pd.DataFrame, params: dict[str, Any]) -> ToolResult:
        if df.empty or len(df) < 2:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"average_response_times": []},
                message_count=len(df)
            )

        # Sort chronologically
        sorted_df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(sorted_df['date']):
            sorted_df['date'] = pd.to_datetime(sorted_df['date'], errors='coerce')
        sorted_df = sorted_df.dropna(subset=['date']).sort_values('date')

        # Filter out system notifications
        sorted_df = sorted_df[sorted_df['user'] != 'group_notification']
        if len(sorted_df) < 2:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"average_response_times": []},
                message_count=len(sorted_df)
            )

        # Shift to align consecutive messages
        sorted_df['prev_user'] = sorted_df['user'].shift(1)
        sorted_df['prev_date'] = sorted_df['date'].shift(1)

        # We care about transitions where the sender changes
        # E.g. User A sends, then User B replies
        transitions = sorted_df[
            (sorted_df['user'] != sorted_df['prev_user']) & 
            (sorted_df['prev_user'].notna())
        ].copy()

        if transitions.empty:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"average_response_times": []},
                message_count=0
            )

        # Calculate difference in seconds
        transitions['delay_seconds'] = (transitions['date'] - transitions['prev_date']).dt.total_seconds()

        # Filter out responses that took more than 12 hours (43200 seconds)
        # These are likely new conversation threads, not replies
        transitions = transitions[transitions['delay_seconds'] <= 43200]

        if transitions.empty:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"average_response_times": []},
                message_count=0
            )

        # Calculate averages/medians grouped by (prev_user, current_user)
        # E.g. (User A, User B) represents how fast B responds to A
        grouped = transitions.groupby(['prev_user', 'user'])['delay_seconds'].agg(['mean', 'median', 'count']).reset_index()

        response_times_list = []
        for idx, row in grouped.iterrows():
            prompt_user = str(row['prev_user'])
            reply_user = str(row['user'])
            
            # Filter if specific users were requested
            user_a = params.get("user_a")
            user_b = params.get("user_b")
            
            if user_a and prompt_user.lower() != user_a.lower() and reply_user.lower() != user_a.lower():
                continue
            if user_b and prompt_user.lower() != user_b.lower() and reply_user.lower() != user_b.lower():
                continue

            response_times_list.append({
                "prompted_by": prompt_user,
                "replied_by": reply_user,
                "replied_in_avg_str": self._format_duration(row['mean']),
                "replied_in_median_str": self._format_duration(row['median']),
                "avg_seconds": round(float(row['mean']), 1),
                "median_seconds": round(float(row['median']), 1),
                "response_count": int(row['count'])
            })

        # Sort by average response time ascending (fastest first)
        response_times_list.sort(key=lambda x: x['avg_seconds'])

        result_data = {
            "average_response_times": response_times_list,
            "max_delay_threshold_hours": 12
        }

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=result_data,
            message_count=len(transitions)
        )

    def _format_duration(self, seconds: float) -> str:
        """Converts float seconds to a readable string like '2m 14s' or '1h 5m'."""
        if pd.isna(seconds):
            return "N/A"
            
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        
        if minutes < 60:
            return f"{minutes}m {remaining_seconds}s"
            
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        return f"{hours}h {remaining_minutes}m"
