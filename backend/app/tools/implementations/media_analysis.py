import logging
import pandas as pd
from typing import Any
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.registry import register_tool
from app.tools.schemas import MediaAnalysisInput

logger = logging.getLogger(__name__)

@register_tool
class MediaAnalysisTool(BaseTool):
    """Analyzes media messages (omitted media attachments) shared in the chat."""

    @property
    def name(self) -> str:
        return "media_analysis"

    @property
    def description(self) -> str:
        return (
            "Analyzes media sharing. Use this when the query asks about media shared, "
            "who shared the most photos/videos/audio, or the volume of media files.\n"
            "Parameters:\n"
            "- user: 'Overall' or a specific username (default: 'Overall')"
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYSIS

    @property
    def triggers(self) -> list[str]:
        return ["media", "image", "photo", "video", "audio", "file", "attachment", "shared the most media", "sent the most photos"]

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        validated = MediaAnalysisInput(**params)
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
                data={"total_media": 0, "media_by_user": []},
                message_count=0
            )

        # In WhatsApp exports, media attachments are parsed as '<Media omitted>'
        media_df = df_to_analyze[df_to_analyze['message'] == '<Media omitted>']
        total_media = len(media_df)

        # Breakdown by user
        media_counts = media_df['user'].value_counts()
        media_by_user_list = []
        for name, count in media_counts.items():
            if name != 'group_notification':
                media_by_user_list.append({
                    "username": str(name),
                    "media_count": int(count)
                })

        result_data = {
            "total_media_count": total_media,
            "media_by_user": media_by_user_list,
            "analyzed_user": user
        }

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=result_data,
            message_count=len(df_to_analyze)
        )
