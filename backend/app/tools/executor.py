import time
import logging
import pandas as pd
from typing import Any
from app.tools.base import ToolResult, ToolCategory
from app.tools.schemas import RoutingResult
from app.tools.registry import ToolRegistry
from app.tools.cache import ToolCache

logger = logging.getLogger(__name__)

class ToolExecutor:
    """Orchestrates the sequential execution of tools, supporting pipelined DataFrame chaining."""

    async def execute(self, session_id: str, routing: RoutingResult, df: pd.DataFrame) -> list[ToolResult]:
        """Execute a list of tool steps sequentially.
        
        If a filter tool executes, its filtered DataFrame is propagated downstream to subsequent tools.
        """
        results: list[ToolResult] = []
        current_df = df
        
        logger.info(f"Starting execution of {len(routing.tools)} tools for session {session_id}.")
        
        for step in routing.tools:
            tool_name = step.name
            params = step.params
            
            # Compute lightweight hash signature of the current DataFrame state
            import hashlib
            df_signature = hashlib.md5(str(current_df.index.tolist()).encode("utf-8")).hexdigest()
            
            tool = ToolRegistry.get(tool_name)
            if not tool:
                error_msg = f"Tool '{tool_name}' not found in registry."
                logger.error(error_msg)
                results.append(ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=error_msg
                ))
                continue
                
            # Check cache first with df_signature
            cached_result = ToolCache.get(session_id, tool_name, params, df_signature)
            if cached_result:
                results.append(cached_result)
                if tool.category == ToolCategory.FILTER and "filtered_df" in cached_result.metadata:
                    current_df = cached_result.metadata["filtered_df"]
                continue
                
            start_time = time.time()
            try:
                # Validate/clean parameters
                validated_params = tool.validate_params(params)
                validated_params["session_id"] = session_id
                
                # Execute tool against the (potentially filtered) DataFrame
                logger.debug(f"Running tool '{tool_name}' with params: {validated_params}")
                
                # Check if execute is a coroutine or normal function
                # (All our tools will be synchronous execution, but we'll support both)
                import inspect
                if inspect.iscoroutinefunction(tool.execute):
                    result = await tool.execute(current_df, validated_params)
                else:
                    result = tool.execute(current_df, validated_params)
                
                # Add execution metadata
                execution_time = (time.time() - start_time) * 1000
                result.metadata["execution_time_ms"] = round(execution_time, 2)
                result.metadata["cached"] = False
                
                # If this is a filter tool, propagate the filtered DataFrame
                if result.success and tool.category == ToolCategory.FILTER:
                    filtered_df = result.metadata.get("filtered_df")
                    if isinstance(filtered_df, pd.DataFrame):
                        current_df = filtered_df
                        logger.debug(f"Filter tool '{tool_name}' narrowed DataFrame down to {len(current_df)} rows.")
                    else:
                        logger.warning(f"Filter tool '{tool_name}' did not return 'filtered_df' in metadata.")
                
                # Cache the successful result with df_signature
                ToolCache.set(session_id, tool_name, params, result, df_signature)
                results.append(result)
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                results.append(ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=f"Internal tool error: {str(e)}",
                    metadata={"execution_time_ms": round(execution_time, 2)}
                ))
                
        return results
