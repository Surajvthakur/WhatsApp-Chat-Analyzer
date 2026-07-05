import logging
from typing import Type
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Registry pattern to keep track of available chat analysis tools."""
    _tools: dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool_class: Type[BaseTool]):
        """Decorator to register a tool class into the registry."""
        try:
            instance = tool_class()
            name = instance.name
            cls._tools[name] = instance
            logger.debug(f"Registered tool: {name} ({tool_class.__name__})")
        except Exception as e:
            logger.error(f"Failed to register tool class {tool_class.__name__}: {e}")
        return tool_class

    @classmethod
    def get(cls, name: str) -> BaseTool | None:
        """Fetch a tool instance by its registered name."""
        return cls._tools.get(name)

    @classmethod
    def all_tools(cls) -> dict[str, BaseTool]:
        """Fetch all registered tools."""
        return cls._tools

    @classmethod
    def get_tool_descriptions(cls) -> list[dict]:
        """Format descriptions of all tools in a clean JSON format for the LLM router."""
        descriptions = []
        for name, tool in cls._tools.items():
            descriptions.append({
                "name": name,
                "description": tool.description,
                "category": tool.category.value,
                "triggers": tool.triggers
            })
        return descriptions

# Decorator shortcut
register_tool = ToolRegistry.register
