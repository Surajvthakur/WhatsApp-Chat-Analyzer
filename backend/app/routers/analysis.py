import os
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

import helper
import preprocessor
from app.config import settings
from app.schemas import (
    BusyUsersResponse,
    ChatUploadResponse,
    DailyTimelinePoint,
    DateRange,
    EmojiCount,
    HeatmapResponse,
    LabeledCount,
    StatsResponse,
    TimelinePoint,
    WordCount,
)
from app.serializers import (
    build_user_list,
    busy_users_to_json,
    common_words_to_json,
    daily_timeline_to_json,
    emoji_to_json,
    get_date_range,
    heatmap_to_json,
    monthly_timeline_to_json,
    series_to_labeled_counts,
    wordcloud_to_png,
)
from app.session_store import SessionStore

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(BACKEND_ROOT)

router = APIRouter(prefix="/api/v1/chats", tags=["analysis"])
store = SessionStore(ttl_seconds=settings.session_ttl_seconds)


def _get_df(chat_id: str):
    df = store.get(chat_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Chat session not found or expired")
    return df


@router.post("", response_model=ChatUploadResponse)
async def upload_chat(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Please upload a .txt WhatsApp export file")

    raw = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_mb} MB",
        )

    try:
        data = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

    df = preprocessor.preprocess(data)
    if df.empty:
        raise HTTPException(
            status_code=422,
            detail="Could not parse chat. Ensure the file is a valid WhatsApp export.",
        )

    chat_id = store.create(df)
    start, end = get_date_range(df)

    return ChatUploadResponse(
        chat_id=chat_id,
        users=build_user_list(df),
        message_count=len(df),
        date_range=DateRange(start=start, end=end),
    )


@router.get("/{chat_id}/users", response_model=list[str])
def get_users(chat_id: str):
    df = _get_df(chat_id)
    return build_user_list(df)


@router.get("/{chat_id}/stats", response_model=StatsResponse)
def get_stats(
    chat_id: str,
    user: str = Query(default="Overall"),
):
    df = _get_df(chat_id)
    num_messages, words, num_media, num_links = helper.fetch_stats(user, df)
    return StatsResponse(
        messages=num_messages,
        words=words,
        media=num_media,
        links=num_links,
    )


@router.get("/{chat_id}/timeline/monthly", response_model=list[TimelinePoint])
def get_monthly_timeline(
    chat_id: str,
    user: str = Query(default="Overall"),
):
    df = _get_df(chat_id)
    timeline = helper.monthly_timeline(user, df)
    return monthly_timeline_to_json(timeline)


@router.get("/{chat_id}/timeline/daily", response_model=list[DailyTimelinePoint])
def get_daily_timeline(
    chat_id: str,
    user: str = Query(default="Overall"),
):
    df = _get_df(chat_id)
    timeline = helper.daily_timeline(user, df)
    return daily_timeline_to_json(timeline)


@router.get("/{chat_id}/activity/week", response_model=list[LabeledCount])
def get_week_activity(
    chat_id: str,
    user: str = Query(default="Overall"),
):
    df = _get_df(chat_id)
    activity = helper.week_activity_map(user, df)
    return series_to_labeled_counts(activity)


@router.get("/{chat_id}/activity/month", response_model=list[LabeledCount])
def get_month_activity(
    chat_id: str,
    user: str = Query(default="Overall"),
):
    df = _get_df(chat_id)
    activity = helper.month_activity_map(user, df)
    return series_to_labeled_counts(activity)


@router.get("/{chat_id}/activity/heatmap", response_model=HeatmapResponse)
def get_activity_heatmap(
    chat_id: str,
    user: str = Query(default="Overall"),
):
    df = _get_df(chat_id)
    heatmap = helper.activity_heatmap(user, df)
    return heatmap_to_json(heatmap)


@router.get("/{chat_id}/users/busy", response_model=BusyUsersResponse)
def get_busy_users(
    chat_id: str,
    user: str = Query(default="Overall"),
):
    if user != "Overall":
        raise HTTPException(
            status_code=400,
            detail="Busy users analysis is only available for Overall",
        )
    df = _get_df(chat_id)
    df_filtered = df[df["user"] != "group_notification"]
    x, percent_df = helper.most_busy_users(df_filtered)
    return busy_users_to_json(x, percent_df)


@router.get("/{chat_id}/words/common", response_model=list[WordCount])
def get_common_words(
    chat_id: str,
    user: str = Query(default="Overall"),
):
    df = _get_df(chat_id)
    words_df = helper.most_common_words(user, df)
    return common_words_to_json(words_df)


@router.get("/{chat_id}/words/cloud")
def get_wordcloud(
    chat_id: str,
    user: str = Query(default="Overall"),
):
    df = _get_df(chat_id)
    wc = helper.create_wordcloud(user, df)
    png_bytes = wordcloud_to_png(wc)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/{chat_id}/emoji", response_model=list[EmojiCount])
def get_emoji(
    chat_id: str,
    user: str = Query(default="Overall"),
):
    df = _get_df(chat_id)
    emoji_df = helper.emoji_helper(user, df)
    return emoji_to_json(emoji_df)
