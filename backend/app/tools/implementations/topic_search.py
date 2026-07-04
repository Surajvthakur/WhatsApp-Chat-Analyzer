import logging
import pandas as pd
from typing import Any
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.registry import register_tool
from app.tools.schemas import TopicSearchInput
from app.ai.embeddings import generate_embeddings
from app.ai.qdrant_store import search_qdrant_embeddings

logger = logging.getLogger(__name__)

@register_tool
class TopicSearchTool(BaseTool):
    """Performs semantic vector search on chat embeddings in Qdrant."""

    @property
    def name(self) -> str:
        return "topic_search"

    @property
    def description(self) -> str:
        return (
            "Performs a semantic search on chat messages. Use this when the query asks about "
            "topics, concepts, opinions, or general questions (e.g. 'what did they say about the trip?') "
            "where keywords might not match exactly.\n"
            "Parameters:\n"
            "- query: Semantic search question or topic string\n"
            "- top_k: Number of relevant messages to return (default: 5)"
        )

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SEARCH

    @property
    def triggers(self) -> list[str]:
        return ["topic", "semantic", "opinions", "about", "feel about", "discussing", "discuss"]

    def validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        validated = TopicSearchInput(**params)
        return validated.model_dump(exclude_none=True)

    async def execute(self, df: pd.DataFrame, params: dict[str, Any]) -> ToolResult:
        query = params.get("query", "").strip()
        top_k = params.get("top_k", 5)
        session_id = params.get("session_id")

        if not query:
            return ToolResult(tool_name=self.name, success=False, error="Parameter 'query' is required.")
        if not session_id:
            return ToolResult(tool_name=self.name, success=False, error="Session ID not provided in execution context.")

        try:
            # 1. Embed the query
            logger.info(f"Generating embedding for query: '{query}'...")
            query_embedding = (await generate_embeddings([query]))[0]
            if hasattr(query_embedding, "tolist"):
                query_embedding = query_embedding.tolist()

            # 2. Search Qdrant
            logger.info(f"Searching Qdrant for top {top_k} matches under workspace {session_id}...")
            retrieved_chunks = search_qdrant_embeddings(
                workspace_id=session_id,
                query_embedding=query_embedding,
                top_k=top_k
            )

            result_data = {
                "semantic_query": query,
                "matches": retrieved_chunks,
                "count": len(retrieved_chunks)
            }

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=result_data,
                message_count=len(retrieved_chunks)
            )

        except Exception as e:
            logger.error(f"Semantic search failed: {e}", exc_info=True)
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Semantic search failed: {str(e)}"
            )
