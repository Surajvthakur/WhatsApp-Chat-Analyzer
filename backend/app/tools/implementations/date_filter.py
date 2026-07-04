import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Any
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.registry import register_tool
from app.tools.schemas import DateFilterInput

logger = logging.getLogger(__name__)

@register_tool
class DateFilterTool(BaseTool):
    """Filters chat messages by a specific date, date range, or relative date expression."""

    @property
    def name(self) -> str:
        return "date_filter"

    @property
    def description(self) -> str:
        return (
            "Filters chat messages by date. Use this when the query asks about events, "
            "messages, or activity on a specific date, date range, or relative time "
            "(e.g., 'yesterday', 'last week', 'July 5th 2025').\n"
            "Parameters:\n"
            "- date: single date string (YYYY-MM-DD)\n"
            "- start_date: range start (YYYY-MM-DD)\n"
            "- end_date: range end (YYYY-MM-DD)\n"
            "- relative: relative time expression (e.g. 'yesterday', 'last week', 'last month')\n"
            "- limit: maximum number of messages to return in structured result (default: 50)"
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILTER

    @property
    def triggers(self) -> list[str]:
        return ["date", "today", "yesterday", "week", "month", "year", "between", "from", "on the", "last"]

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        # Validate using Pydantic schema
        validated = DateFilterInput(**params)
        return validated.model_dump(exclude_none=True)

    def execute(self, df: pd.DataFrame, params: dict[str, Any]) -> ToolResult:
        if df.empty:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"messages": [], "total_found": 0},
                message_count=0
            )

        limit = params.get("limit", 50)
        filtered_df = df.copy()

        # Ensure datetime type
        if not pd.api.types.is_datetime64_any_dtype(filtered_df['date']):
            filtered_df['date'] = pd.to_datetime(filtered_df['date'], errors='coerce')
        filtered_df = filtered_df.dropna(subset=['date'])

        # Reference "now" as maximum date in dataset, or current date if empty
        ref_date = filtered_df['date'].max()
        if pd.isna(ref_date):
            ref_date = datetime.now()

        # Handle filters
        date_str = params.get("date")
        start_date_str = params.get("start_date")
        end_date_str = params.get("end_date")
        relative = params.get("relative")

        if date_str:
            try:
                target_date = pd.to_datetime(date_str).date()
                filtered_df = filtered_df[filtered_df['date'].dt.date == target_date]
            except Exception as e:
                return ToolResult(tool_name=self.name, success=False, error=f"Invalid date format: {e}")

        elif start_date_str or end_date_str:
            try:
                if start_date_str:
                    start_val = pd.to_datetime(start_date_str)
                    filtered_df = filtered_df[filtered_df['date'] >= start_val]
                if end_date_str:
                    end_val = pd.to_datetime(end_date_str) + timedelta(days=1)  # Inclusive of the day
                    filtered_df = filtered_df[filtered_df['date'] < end_val]
            except Exception as e:
                return ToolResult(tool_name=self.name, success=False, error=f"Invalid date range format: {e}")

        elif relative:
            rel = relative.lower().strip()
            if "yesterday" in rel:
                target_date = (ref_date - timedelta(days=1)).date()
                filtered_df = filtered_df[filtered_df['date'].dt.date == target_date]
            elif "last week" in rel or "past week" in rel:
                start_val = ref_date - timedelta(days=7)
                filtered_df = filtered_df[filtered_df['date'] >= start_val]
            elif "last month" in rel or "past month" in rel:
                start_val = ref_date - timedelta(days=30)
                filtered_df = filtered_df[filtered_df['date'] >= start_val]
            else:
                return ToolResult(tool_name=self.name, success=False, error=f"Unsupported relative time expression: '{relative}'")

        # Sort chronologically
        filtered_df = filtered_df.sort_values('date')
        total_found = len(filtered_df)

        # Truncate for the JSON payload, but keep full df in metadata
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
            "date_range": {
                "start": str(filtered_df['date'].min()) if not filtered_df.empty else None,
                "end": str(filtered_df['date'].max()) if not filtered_df.empty else None
            }
        }

        # Pack the full filtered DataFrame into metadata for pipeline chaining
        metadata = {
            "filtered_df": filtered_df,
            "filter_type": "date"
        }

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=result_data,
            message_count=total_found,
            metadata=metadata
        )
