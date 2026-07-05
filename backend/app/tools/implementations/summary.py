import logging
import pandas as pd
from typing import Any
from groq import Groq
from app.config import settings
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.registry import register_tool
from app.tools.schemas import SummaryInput

logger = logging.getLogger(__name__)

@register_tool
class SummaryTool(BaseTool):
    """Generates an LLM-powered summary of the chat messages in the active DataFrame."""

    def __init__(self) -> None:
        self.groq_client = None
        if settings.groq_api_key:
            self.groq_client = Groq(api_key=settings.groq_api_key)

    @property
    def name(self) -> str:
        return "summary"

    @property
    def description(self) -> str:
        return (
            "Generates a summary of the messages currently in view. Use this tool when the query "
            "asks to summarize, explain, or get an overview of recent discussions, messages on a "
            "certain day, or chats by a specific user.\n"
            "Parameters:\n"
            "- limit: maximum number of messages to feed into the summarizer (default: 100)\n"
            "- aspect: optional specific aspect to focus the summary on (e.g. 'work', 'conflict', 'plans')"
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SUMMARY

    @property
    def triggers(self) -> list[str]:
        return ["summarize", "summary", "explain", "get an overview", "what happened", "tldr", "tl;dr"]

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        validated = SummaryInput(**params)
        return validated.model_dump(exclude_none=True)

    def execute(self, df: pd.DataFrame, params: dict[str, Any]) -> ToolResult:
        if not self.groq_client:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="Groq API key not configured on the server."
            )

        if df.empty:
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"summary": "No messages found to summarize."},
                message_count=0
            )

        limit = params.get("limit", 100)
        aspect = params.get("aspect")

        # Sort chronologically to maintain context
        sorted_df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(sorted_df['date']):
            sorted_df['date'] = pd.to_datetime(sorted_df['date'], errors='coerce')
        sorted_df = sorted_df.dropna(subset=['date']).sort_values('date')

        total_messages = len(sorted_df)
        analysis_df = sorted_df.head(limit)

        # Format chat history for LLM context
        chat_lines = []
        for idx, row in analysis_df.iterrows():
            # Skip media omitted messages for summarization since they contain no text content
            if row['message'] == '<Media omitted>':
                continue
            date_str = row['date'].strftime('%Y-%m-%d %H:%M') if hasattr(row['date'], 'strftime') else str(row['date'])
            chat_lines.append(f"[{date_str}] {row['user']}: {row['message']}")

        chat_context = "\n".join(chat_lines)
        if not chat_context.strip():
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"summary": "No text messages found to summarize (only media files or empty messages)."},
                message_count=total_messages
            )

        system_instruction = (
            "You are an expert chat summarizer. Summarize the following WhatsApp chat export segment. "
            "Be objective, clear, and highlight key topics, decisions, actions, and who said what. "
            "Keep the summary concise (under 200 words)."
        )
        if aspect:
            system_instruction += f" Pay special attention to and focus the summary on: '{aspect}'."

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"CHAT LOG:\n{chat_context}"}
        ]

        try:
            logger.info(f"Summarizing {len(analysis_df)} messages using Groq LLM...")
            completion = self.groq_client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                temperature=0.3,
                max_tokens=350
            )
            summary_text = completion.choices[0].message.content.strip()

            result_data = {
                "summary": summary_text,
                "total_messages_analyzed": len(analysis_df),
                "total_messages_found": total_messages,
                "truncated": total_messages > limit,
                "focus_aspect": aspect
            }

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=result_data,
                message_count=total_messages
            )
        except Exception as e:
            logger.error(f"Error calling Groq in SummaryTool: {e}", exc_info=True)
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"LLM summarization failed: {str(e)}"
            )
