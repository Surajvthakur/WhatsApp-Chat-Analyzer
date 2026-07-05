import logging
import pandas as pd
from collections import Counter
from typing import Any
from urlextract import URLExtract
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.registry import register_tool
from app.tools.schemas import LinkAnalysisInput

logger = logging.getLogger(__name__)

@register_tool
class LinkAnalysisTool(BaseTool):
    """Analyzes hyperlinks shared in the chat messages."""

    def __init__(self) -> None:
        self.extractor = URLExtract()

    @property
    def name(self) -> str:
        return "link_analysis"

    @property
    def description(self) -> str:
        return (
            "Analyzes links/URLs shared in the chat. Use this when the query asks about "
            "links, websites, URLs shared, or who shared the most links.\n"
            "Parameters:\n"
            "- user: 'Overall' or a specific username (default: 'Overall')\n"
            "- limit: maximum number of top links to return (default: 10)"
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYSIS

    @property
    def triggers(self) -> list[str]:
        return ["link", "links", "url", "urls", "website", "websites", "http", "https", "shared most links"]

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        validated = LinkAnalysisInput(**params)
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
                data={"total_links": 0, "links_by_user": [], "top_links": []},
                message_count=0
            )

        # Pre-filter messages that look like they contain links for performance
        url_like_mask = df_to_analyze['message'].str.contains(r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', regex=True, na=False)
        link_messages_df = df_to_analyze[url_like_mask]

        all_extracted_urls = []
        user_link_counts = Counter()
        url_frequency = Counter()

        for idx, row in link_messages_df.iterrows():
            sender = str(row['user'])
            msg_text = str(row['message'])
            
            if sender == 'group_notification':
                continue
                
            urls = self.extractor.find_urls(msg_text)
            if urls:
                user_link_counts[sender] += len(urls)
                for url in urls:
                    # Normalize URL slightly (remove trailing slash or query params if desired, but raw is fine)
                    all_extracted_urls.append(url)
                    url_frequency[url] += 1

        total_links = len(all_extracted_urls)

        # Format user breakdown
        links_by_user = [
            {"username": sender, "link_count": count}
            for sender, count in user_link_counts.most_common()
        ]

        # Format top links
        top_links = [
            {"url": url, "count": count}
            for url, count in url_frequency.most_common(limit)
        ]

        result_data = {
            "total_links_count": total_links,
            "links_by_user": links_by_user,
            "top_links": top_links,
            "analyzed_user": user
        }

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=result_data,
            message_count=len(df_to_analyze)
        )
