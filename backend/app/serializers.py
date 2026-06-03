import io
from datetime import date, datetime

import pandas as pd

from app.schemas import (
    BusyUserItem,
    BusyUserPercent,
    BusyUsersResponse,
    DailyTimelinePoint,
    EmojiCount,
    HeatmapResponse,
    LabeledCount,
    TimelinePoint,
    WordCount,
)


def build_user_list(df: pd.DataFrame) -> list[str]:
    user_list = df["user"].unique().tolist()
    if "System" in user_list:
        user_list.remove("System")
    user_list.sort()
    user_list.insert(0, "Overall")
    return user_list


def get_date_range(df: pd.DataFrame) -> tuple[str | None, str | None]:
    if df.empty or "date" not in df.columns:
        return None, None
    valid = df["date"].dropna()
    if valid.empty:
        return None, None
    start = valid.min()
    end = valid.max()
    return _to_iso(start), _to_iso(end)


def _to_iso(value) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def monthly_timeline_to_json(df: pd.DataFrame) -> list[TimelinePoint]:
    return [
        TimelinePoint(time=str(time), message=int(message))
        for time, message in zip(df["time"], df["message"])
    ]


def daily_timeline_to_json(df: pd.DataFrame) -> list[DailyTimelinePoint]:
    if df.empty:
        return []
    only_dates = df["only_date"].apply(lambda x: x.isoformat() if hasattr(x, "isoformat") else str(x))
    return [
        DailyTimelinePoint(only_date=str(d), message=int(m))
        for d, m in zip(only_dates, df["message"])
    ]


def series_to_labeled_counts(series: pd.Series) -> list[LabeledCount]:
    return [
        LabeledCount(label=str(idx), count=int(val))
        for idx, val in series.items()
    ]


def heatmap_to_json(heatmap: pd.DataFrame) -> HeatmapResponse:
    days = [str(d) for d in heatmap.index.tolist()]
    periods = [str(p) for p in heatmap.columns.tolist()]
    values = heatmap.values.tolist()
    return HeatmapResponse(days=days, periods=periods, values=values)


def busy_users_to_json(x: pd.Series, percent_df: pd.DataFrame) -> BusyUsersResponse:
    top_users = [
        BusyUserItem(user=str(name), count=int(count))
        for name, count in x.items()
    ]
    percentages = [
        BusyUserPercent(
            name=str(name),
            percent=float(percent),
        )
        for name, percent in zip(percent_df["name"], percent_df["percent"])
    ]
    return BusyUsersResponse(top_users=top_users, percentages=percentages)


def common_words_to_json(df: pd.DataFrame) -> list[WordCount]:
    if df.empty:
        return []
    return [
        WordCount(word=str(word), count=int(count))
        for word, count in zip(df.iloc[:, 0], df.iloc[:, 1])
    ]


def emoji_to_json(df: pd.DataFrame) -> list[EmojiCount]:
    if df.empty:
        return []
    return [
        EmojiCount(emoji=str(emoji), count=int(count))
        for emoji, count in zip(df.iloc[:, 0], df.iloc[:, 1])
    ]


def wordcloud_to_png(wordcloud) -> bytes:
    image = wordcloud.to_image()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
