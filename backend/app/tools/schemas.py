from pydantic import BaseModel, Field
from typing import Any

class ToolStep(BaseModel):
    name: str
    params: dict[str, Any] = Field(default_factory=dict)

class RoutingResult(BaseModel):
    tools: list[ToolStep] = Field(default_factory=list)
    chain: bool = False
    fallback_to_rag: bool = False
    reasoning: str | None = None

    @property
    def has_tools(self) -> bool:
        return len(self.tools) > 0 and not self.fallback_to_rag

# --- Pydantic validation schemas for individual tools ---

class DateFilterInput(BaseModel):
    date: str | None = None          # Expected format: YYYY-MM-DD
    start_date: str | None = None    # Expected format: YYYY-MM-DD
    end_date: str | None = None      # Expected format: YYYY-MM-DD
    relative: str | None = None      # e.g., "last week", "yesterday", "last month"

class UserFilterInput(BaseModel):
    username: str
    limit: int = 50

class MessageSearchInput(BaseModel):
    query: str
    limit: int = 50

class ConversationContextInput(BaseModel):
    message_id: str | None = None
    timestamp: str | None = None
    user: str | None = None
    window_size: int = 5             # Number of messages before and after

class StatisticsInput(BaseModel):
    user: str = "Overall"

class ActiveUsersInput(BaseModel):
    limit: int = 5

class EmojiAnalysisInput(BaseModel):
    user: str = "Overall"
    limit: int = 10

class MediaAnalysisInput(BaseModel):
    user: str = "Overall"

class LinkAnalysisInput(BaseModel):
    user: str = "Overall"

class ResponseTimeInput(BaseModel):
    user_a: str | None = None
    user_b: str | None = None

class TopicSearchInput(BaseModel):
    query: str
    top_k: int = 5

class SummaryInput(BaseModel):
    limit: int = 50
    aspect: str | None = None        # e.g., "conflict", "work", "general"
