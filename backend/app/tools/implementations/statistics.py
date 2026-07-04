import logging
import pandas as pd
from typing import Any
import helper
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.registry import register_tool
from app.tools.schemas import StatisticsInput

logger = logging.getLogger(__name__)

@register_tool
class StatisticsTool(BaseTool):
    """Computes overall statistics: message counts, word counts, media, and link sharing counts."""

    @property
    def name(self) -> str:
        return "statistics"

    @property
    def description(self) -> str:
        return (
            "Computes basic metrics for a user or the entire chat, including the total number of "
            "messages, total words, number of media files, and shared links.\n"
            "Parameters:\n"
            "- user: 'Overall' or a specific username (default: 'Overall')"
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYSIS

    @property
    def triggers(self) -> list[str]:
        return ["stats", "statistics", "count", "metrics", "number of", "how many", "volume", "summary stats"]

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        validated = StatisticsInput(**params)
        return validated.model_dump(exclude_none=True)

    def execute(self, df: pd.DataFrame, params: dict[str, Any]) -> ToolResult:
        user = params.get("user", "Overall")

        # Respect upstream pipeline filtering
        df_to_analyze = df
        if user != "Overall" and len(df['user'].unique()) > 1:
            df_to_analyze = df[df['user'].str.lower() == user.lower()]

        if df_to_analyze.empty:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "messages": 0,
                    "words": 0,
                    "media": 0,
                    "links": 0,
                    "analyzed_user": user
                },
                message_count=0
            )

        # Call existing fetch_stats helper. Passing "Overall" since we already pre-filtered df_to_analyze.
        num_messages, word_count, num_media_messages, num_links = helper.fetch_stats("Overall", df_to_analyze)

        result_data = {
            "messages_count": num_messages,
            "words_count": word_count,
            "media_count": num_media_messages,
            "links_count": num_links,
            "average_words_per_message": round(word_count / num_messages, 2) if num_messages > 0 else 0,
            "analyzed_user": user
        }

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=result_data,
            message_count=num_messages
        )
