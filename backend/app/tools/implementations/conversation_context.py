import logging
import pandas as pd
from typing import Any
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.registry import register_tool
from app.tools.schemas import ConversationContextInput

logger = logging.getLogger(__name__)

@register_tool
class ConversationContextTool(BaseTool):
    """Retrieves conversation context (messages before and after) around a specific message or point in time."""

    @property
    def name(self) -> str:
        return "conversation_context"

    @property
    def description(self) -> str:
        return (
            "Retrieves surrounding chat messages (context) before and after a specific message. "
            "Use this when the query asks about the context of a message, what happened before/after "
            "a link was shared, or what led up to a statement.\n"
            "Parameters:\n"
            "- timestamp: Specific message timestamp to find (format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD)\n"
            "- user: Sender of target message\n"
            "- query: Optional search text to identify the target message\n"
            "- window_size: Number of messages to fetch before and after (default: 5)"
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SEARCH

    @property
    def triggers(self) -> list[str]:
        return ["context", "surrounding", "before", "after", "happened when", "led up to", "why did they say", "what was the reply to"]

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        validated = ConversationContextInput(**params)
        return validated.model_dump(exclude_none=True)

    def execute(self, df: pd.DataFrame, params: dict[str, Any]) -> ToolResult:
        if df.empty:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"context_messages": []},
                message_count=0
            )

        window_size = params.get("window_size", 5)
        timestamp_str = params.get("timestamp")
        user = params.get("user")
        query = params.get("query")

        # Ensure sorted chronologically
        sorted_df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(sorted_df['date']):
            sorted_df['date'] = pd.to_datetime(sorted_df['date'], errors='coerce')
        sorted_df = sorted_df.dropna(subset=['date']).sort_values('date').reset_index(drop=True)

        target_idx = None

        # 1. Search by timestamp and user
        if timestamp_str:
            try:
                target_dt = pd.to_datetime(timestamp_str)
                # Exact or closest match
                time_diffs = (sorted_df['date'] - target_dt).abs()
                closest_idx = time_diffs.idxmin()
                
                # Verify closest is within reasonable window (e.g. 5 minutes)
                if time_diffs[closest_idx] < pd.Timedelta(minutes=5):
                    target_idx = closest_idx
            except Exception as e:
                logger.warning(f"Error parsing timestamp in ConversationContextTool: {e}")

        # 2. If index not found yet, search by text query and optional user
        if target_idx is None and query:
            mask = sorted_df['message'].str.contains(query, case=False, na=False)
            if user:
                mask = mask & (sorted_df['user'].str.lower() == user.lower())
            
            matching_indices = sorted_df[mask].index
            if not matching_indices.empty:
                # Get the first match
                target_idx = matching_indices[0]

        # 3. Fallback to middle of the chat if absolutely nothing matches
        if target_idx is None:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="Could not locate the target message in chat history."
            )

        # Retrieve window slice
        start_idx = max(0, target_idx - window_size)
        end_idx = min(len(sorted_df) - 1, target_idx + window_size)

        context_slice = sorted_df.iloc[start_idx : end_idx + 1]

        messages_list = []
        for idx, row in context_slice.iterrows():
            date_formatted = row['date'].strftime('%Y-%m-%d %H:%M:%S')
            messages_list.append({
                "date": date_formatted,
                "user": str(row['user']),
                "message": str(row['message']),
                "is_target": idx == target_idx
            })

        result_data = {
            "target_message": messages_list[target_idx - start_idx] if target_idx is not None else None,
            "context_messages": messages_list,
            "window_size": window_size,
            "start_index": int(start_idx),
            "end_index": int(end_idx),
            "total_chat_messages": len(sorted_df)
        }

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=result_data,
            message_count=len(context_slice)
        )
