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
        TimelinePoint(time=str(row["time"]), message=int(row["message"]))
        for _, row in df.iterrows()
    ]


def daily_timeline_to_json(df: pd.DataFrame) -> list[DailyTimelinePoint]:
    points = []
    for _, row in df.iterrows():
        only_date = row["only_date"]
        if hasattr(only_date, "isoformat"):
            only_date = only_date.isoformat()
        else:
            only_date = str(only_date)
        points.append(
            DailyTimelinePoint(only_date=only_date, message=int(row["message"]))
        )
    return points


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
            name=str(row["name"]),
            percent=float(row["percent"]),
        )
        for _, row in percent_df.iterrows()
    ]
    return BusyUsersResponse(top_users=top_users, percentages=percentages)


def common_words_to_json(df: pd.DataFrame) -> list[WordCount]:
    return [
        WordCount(word=str(row[0]), count=int(row[1]))
        for _, row in df.iterrows()
    ]


def emoji_to_json(df: pd.DataFrame) -> list[EmojiCount]:
    return [
        EmojiCount(emoji=str(row[0]), count=int(row[1]))
        for _, row in df.iterrows()
    ]


def wordcloud_to_png(wordcloud) -> bytes:
    image = wordcloud.to_image()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
