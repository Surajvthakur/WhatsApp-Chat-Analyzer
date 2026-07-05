import re
import json
import logging
from typing import Any
from groq import Groq
from app.config import settings
from app.tools.base import BaseTool
from app.tools.schemas import RoutingResult, ToolStep
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

class ToolRouter:
    """Classifies user query intent to route it to the appropriate tool chain or fallback to RAG."""

    def __init__(self) -> None:
        self.groq_client = None
        if settings.groq_api_key:
            self.groq_client = Groq(api_key=settings.groq_api_key)

    def route(self, query: str) -> RoutingResult:
        """Determines the execution path for the query.
        
        Uses keyword-based heuristics first for zero-latency routing.
        Falls back to Groq LLM for complex/ambiguous queries.
        """
        available_tools = ToolRegistry.all_tools()
        if not available_tools:
            logger.warning("No tools registered in ToolRegistry. Falling back to RAG.")
            return RoutingResult(fallback_to_rag=True, reasoning="No tools registered")

        # 1. First run fast keyword heuristics
        heuristic_result = self._try_heuristics(query, available_tools)
        if heuristic_result:
            logger.info(f"Heuristics routed query to tool chain: {[t.name for t in heuristic_result.tools]}")
            return heuristic_result

        # 2. Fallback to Groq LLM routing if heuristics are ambiguous or negative
        if not self.groq_client:
            logger.warning("Groq API key not configured. Falling back to RAG.")
            return RoutingResult(fallback_to_rag=True, reasoning="Groq client not initialized")

        try:
            return self._llm_route(query, available_tools)
        except Exception as e:
            logger.error(f"Error during LLM routing: {e}", exc_info=True)
            return RoutingResult(fallback_to_rag=True, reasoning=f"LLM routing failed: {str(e)}")

    def _try_heuristics(self, query: str, available_tools: dict[str, BaseTool]) -> RoutingResult | None:
        """Simple regex/keyword checks for very obvious single-tool tasks to avoid LLM cost/latency.
        
        Returns a RoutingResult if a high-confidence match is found, otherwise None.
        """
        q = query.lower().strip()
        
        # Emoji trigger
        if any(trigger in q for trigger in ["emoji", "emojis", "smileys"]):
            return RoutingResult(
                tools=[ToolStep(name="emoji_analysis", params={"limit": 10})],
                reasoning="Matched keyword trigger for emoji analysis"
            )
            
        # Active users trigger
        if any(trigger in q for trigger in ["most active", "busy user", "who talks the most", "sent the most", "who is active"]):
            return RoutingResult(
                tools=[ToolStep(name="active_users", params={"limit": 5})],
                reasoning="Matched keyword trigger for active users"
            )

        # Statistics / stats trigger
        if q in ["stats", "statistics", "show statistics", "show stats", "overview"]:
            return RoutingResult(
                tools=[ToolStep(name="statistics", params={"user": "Overall"})],
                reasoning="Matched keyword trigger for statistics"
            )
            
        # Message search triggers (look for quotes or "search for ...")
        search_match = re.match(r"^(?:search|find|look for)\s+(?:for\s+)?['\" ]?(.*?)['\" ]?$", q)
        if search_match:
            term = search_match.group(1).strip()
            if term:
                return RoutingResult(
                    tools=[ToolStep(name="message_search", params={"query": term})],
                    reasoning="Matched keyword pattern for message search"
                )

        return None

    def _llm_route(self, query: str, available_tools: dict[str, BaseTool]) -> RoutingResult:
        """Leverages Groq LLM to classify query intent and construct a tool execution plan."""
        tools_metadata = ToolRegistry.get_tool_descriptions()
        
        system_prompt = f"""You are an advanced router for a WhatsApp Chat Analyzer.
Your task is to analyze the user's query and decide which tools should run, in what order, and with what parameters.

Available Tools:
{json.dumps(tools_metadata, indent=2)}

Rules:
1. Return a JSON object matching this schema:
{{
  "tools": [
    {{ "name": "tool_name", "params": {{ ... }} }}
  ],
  "chain": true/false, // Set to true if a filter tool's output should be fed to the next tool in the sequence
  "fallback_to_rag": true/false, // Set to true if none of the tools can answer the query
  "reasoning": "Brief explanation of your choice"
}}
2. Chaining: You can chain tools. E.g., for "Show Rahul's messages from July 5th", chain "date_filter" (params: date="2025-07-05") -> "user_filter" (params: username="Rahul").
3. For open-ended questions like "Why did Rahul say that?" or "What were they arguing about?", set "fallback_to_rag" to true.
4. Parameters extraction: Extract exact parameters where possible (e.g. date formatted as YYYY-MM-DD, clean username).
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {query}"}
        ]

        logger.debug("Requesting tool routing plan from Groq...")
        response = self.groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,  # Deterministic routing
            max_tokens=500
        )
        
        response_text = response.choices[0].message.content
        logger.debug(f"Router response: {response_text}")
        
        data = json.loads(response_text)
        
        # Parse into Pydantic RoutingResult
        steps = []
        for step_data in data.get("tools", []):
            steps.append(ToolStep(
                name=step_data.get("name"),
                params=step_data.get("params", {})
            ))
            
        return RoutingResult(
            tools=steps,
            chain=data.get("chain", False),
            fallback_to_rag=data.get("fallback_to_rag", False),
            reasoning=data.get("reasoning")
        )
