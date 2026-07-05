import logging
import pandas as pd
from typing import Any
import helper
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.registry import register_tool
from app.tools.schemas import EmojiAnalysisInput

logger = logging.getLogger(__name__)

@register_tool
class EmojiAnalysisTool(BaseTool):
    """Analyzes frequently used emojis in chat messages."""

    @property
    def name(self) -> str:
        return "emoji_analysis"

    @property
    def description(self) -> str:
        return (
            "Analyzes the emojis used in the chat. Use this when the query asks about "
            "emoji usage, most common emojis, or what emojis someone uses.\n"
            "Parameters:\n"
            "- user: 'Overall' or a specific username (default: 'Overall')\n"
            "- limit: maximum number of top emojis to return (default: 10)"
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYSIS

    @property
    def triggers(self) -> list[str]:
        return ["emoji", "emojis", "smileys", "smiley", "icons"]

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        validated = EmojiAnalysisInput(**params)
        return validated.model_dump(exclude_none=True)

    def execute(self, df: pd.DataFrame, params: dict[str, Any]) -> ToolResult:
        user = params.get("user", "Overall")
        limit = params.get("limit", 10)

        # Respect upstream pipeline filtering
        df_to_analyze = df
        if user != "Overall" and len(df['user'].unique()) > 1:
            df_to_analyze = df[df['user'].str.lower() == user.lower()]

        if df_to_analyze.empty:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"emojis": [], "total_emojis_found": 0},
                message_count=0
            )

        # Call the existing helper function
        # Since we pre-filtered the df_to_analyze, we pass "Overall" to prevent helper from re-filtering
        emoji_df = helper.emoji_helper("Overall", df_to_analyze)

        emojis_list = []
        total_count = 0
        if not emoji_df.empty:
            emoji_df.columns = ["emoji", "count"]
            total_count = int(emoji_df["count"].sum())
            for idx, row in emoji_df.head(limit).iterrows():
                emojis_list.append({
                    "emoji": str(row["emoji"]),
                    "count": int(row["count"])
                })

        result_data = {
            "emojis": emojis_list,
            "total_emojis_found": total_count,
            "analyzed_user": user
        }

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=result_data,
            message_count=len(df_to_analyze)
        )
