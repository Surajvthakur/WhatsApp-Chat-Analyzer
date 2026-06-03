import io
from datetime import date, datetime

import pandas as pd
from pydantic import TypeAdapter

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

# Initialize TypeAdapters for Pydantic list validation
timeline_adapter = TypeAdapter(list[TimelinePoint])
daily_timeline_adapter = TypeAdapter(list[DailyTimelinePoint])
labeled_count_adapter = TypeAdapter(list[LabeledCount])
busy_user_adapter = TypeAdapter(list[BusyUserItem])
busy_percent_adapter = TypeAdapter(list[BusyUserPercent])
word_count_adapter = TypeAdapter(list[WordCount])
emoji_count_adapter = TypeAdapter(list[EmojiCount])


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
    if df.empty:
        return []
    records = df.to_dict(orient="records")
    return timeline_adapter.validate_python(records)


def daily_timeline_to_json(df: pd.DataFrame) -> list[DailyTimelinePoint]:
    if df.empty:
        return []
    df_copy = df.copy()
    df_copy["only_date"] = df_copy["only_date"].apply(
        lambda x: x.isoformat() if hasattr(x, "isoformat") else str(x)
    )
    records = df_copy.to_dict(orient="records")
    return daily_timeline_adapter.validate_python(records)


def series_to_labeled_counts(series: pd.Series) -> list[LabeledCount]:
    if series.empty:
        return []
    df = series.reset_index()
    df.columns = ["label", "count"]
    df["label"] = df["label"].astype(str)
    records = df.to_dict(orient="records")
    return labeled_count_adapter.validate_python(records)


def heatmap_to_json(heatmap: pd.DataFrame) -> HeatmapResponse:
    days = [str(d) for d in heatmap.index.tolist()]
    periods = [str(p) for p in heatmap.columns.tolist()]
    values = heatmap.values.tolist()
    return HeatmapResponse(days=days, periods=periods, values=values)


def busy_users_to_json(x: pd.Series, percent_df: pd.DataFrame) -> BusyUsersResponse:
    df_users = x.reset_index()
    df_users.columns = ["user", "count"]
    df_users["user"] = df_users["user"].astype(str)
    top_users_records = df_users.to_dict(orient="records")
    top_users = busy_user_adapter.validate_python(top_users_records)

    percentages_records = percent_df.to_dict(orient="records")
    percentages = busy_percent_adapter.validate_python(percentages_records)

    return BusyUsersResponse(top_users=top_users, percentages=percentages)


def common_words_to_json(df: pd.DataFrame) -> list[WordCount]:
    if df.empty:
        return []
    df_copy = df.copy()
    df_copy.columns = ["word", "count"]
    df_copy["word"] = df_copy["word"].astype(str)
    records = df_copy.to_dict(orient="records")
    return word_count_adapter.validate_python(records)


def emoji_to_json(df: pd.DataFrame) -> list[EmojiCount]:
    if df.empty:
        return []
    df_copy = df.copy()
    df_copy.columns = ["emoji", "count"]
    df_copy["emoji"] = df_copy["emoji"].astype(str)
    records = df_copy.to_dict(orient="records")
    return emoji_count_adapter.validate_python(records)


def wordcloud_to_png(wordcloud) -> bytes:
    image = wordcloud.to_image()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
