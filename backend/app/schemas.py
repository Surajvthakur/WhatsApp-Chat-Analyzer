from pydantic import BaseModel


class DateRange(BaseModel):
    start: str | None
    end: str | None


class ChatUploadResponse(BaseModel):
    chat_id: str
    users: list[str]
    message_count: int
    date_range: DateRange


class StatsResponse(BaseModel):
    messages: int
    words: int
    media: int
    links: int


class TimelinePoint(BaseModel):
    time: str
    message: int


class DailyTimelinePoint(BaseModel):
    only_date: str
    message: int


class LabeledCount(BaseModel):
    label: str
    count: int


class HeatmapResponse(BaseModel):
    days: list[str]
    periods: list[str]
    values: list[list[float]]


class BusyUserItem(BaseModel):
    user: str
    count: int


class BusyUserPercent(BaseModel):
    name: str
    percent: float


class BusyUsersResponse(BaseModel):
    top_users: list[BusyUserItem]
    percentages: list[BusyUserPercent]


class WordCount(BaseModel):
    word: str
    count: int


class EmojiCount(BaseModel):
    emoji: str
    count: int
