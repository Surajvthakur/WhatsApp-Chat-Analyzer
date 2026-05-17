from pathlib import Path

import emoji
import pandas as pd
from collections import Counter
from urlextract import URLExtract
from wordcloud import WordCloud

extract = URLExtract()
_BACKEND_DIR = Path(__file__).resolve().parent

_WHATSAPP_SKIP_MESSAGES = {
    "<media omitted>",
    "image omitted",
    "video omitted",
    "audio omitted",
    "sticker omitted",
    "gif omitted",
    "document omitted",
    "this message was deleted",
    "you deleted this message",
    "message deleted",
}

_WHATSAPP_NOISE_WORDS = {
    "media",
    "omitted",
    "http",
    "https",
}

_WORDCLOUD_COLORS = [
    "#25D366",
    "#128C7E",
    "#075E54",
    "#00A884",
    "#34B7F1",
    "#53BDEB",
    "#D9FDD3",
    "#8696A0",
]

_stop_words_cache: set[str] | None = None

def fetch_stats(selected_user,df):

    if selected_user != 'Overall':

        df = df[df['user'] == selected_user]
        # 1. fetch no of messages
    num_messages = df.shape[0]
    # 2. number of words
    words = []
    for message in df['message']:
        words.extend(message.split())

    # fetch number of media messages
    num_media_messages = df[df['message']=='<Media omitted>'].shape[0]

    # fetch number of links shared
    links = []
    for message in df['message']:
        links.extend(extract.find_urls(message))

    return num_messages,len(words),num_media_messages,len(links)


def most_busy_users(df):
    x = df['user'].value_counts().head()

    percent_df = (
        round((df['user'].value_counts() / df.shape[0]) * 100, 2)
        .reset_index()
    )
    percent_df.columns = ['name', 'percent']
    return x, percent_df


def _load_stop_words() -> set[str]:
    global _stop_words_cache
    if _stop_words_cache is not None:
        return _stop_words_cache

    path = _BACKEND_DIR / "stop_hinglish.txt"
    with open(path, encoding="utf-8") as f:
        _stop_words_cache = {
            line.strip().lower()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        }
    _stop_words_cache.update(_WHATSAPP_NOISE_WORDS)
    return _stop_words_cache


def _wordcloud_color(word, font_size, position, orientation, random_state=None, **kwargs):
    return random_state.choice(_WORDCLOUD_COLORS)


def _build_word_frequencies(selected_user: str, df: pd.DataFrame) -> Counter:
    if selected_user != "Overall":
        df = df[df["user"] == selected_user]

    stop_words = _load_stop_words()
    words: list[str] = []

    for message in df["message"].astype(str):
        msg = message.strip().lower()
        if not msg or msg in _WHATSAPP_SKIP_MESSAGES:
            continue
        if msg.startswith("http") or msg.startswith("https://"):
            continue

        for raw in msg.split():
            word = "".join(ch for ch in raw if ch.isalnum() or ch in "'")
            if len(word) < 2 or word in stop_words:
                continue
            words.append(word)

    return Counter(words)


def create_wordcloud(selected_user, df):
    frequencies = _build_word_frequencies(selected_user, df)
    if not frequencies:
        frequencies = Counter({"chat": 1})

    wc = WordCloud(
        width=900,
        height=500,
        background_color=None,
        mode="RGBA",
        max_words=150,
        min_font_size=14,
        max_font_size=96,
        relative_scaling=0.55,
        prefer_horizontal=0.8,
        collocations=False,
        color_func=_wordcloud_color,
        random_state=42,
        margin=4,
    )
    return wc.generate_from_frequencies(dict(frequencies))


def most_common_words(selected_user, df):

    f = open('stop_hinglish.txt','r')
    stop_words = f.read()
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    temp = df[df['user'] != 'group_notification']
    temp = temp[temp['message'] != '<Media omitted>']

    words = []

    for message in temp['message']:
        for word in message.lower().split():
            if word not in stop_words:
                words.append(word)

    most_common_df = pd.DataFrame(Counter(words).most_common(20))

    return most_common_df

def emoji_helper(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    emojis = []
    for message in df['message']:
        emojis.extend([c for c in message if c in emoji.EMOJI_DATA])

    emoji_df = pd.DataFrame(Counter(emojis).most_common(len(Counter(emojis))))
    return emoji_df

def monthly_timeline(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    # Group by year, month_num, and month, counting messages
    timeline = df.groupby(['year', 'month', 'month_num']).count()['message'].reset_index()

    # Create a list of time strings in "Month Year" format
    time = []
    for i in range(timeline.shape[0]):
        time.append(str(timeline['month'][i]) + " " + str(timeline['year'][i]))

    timeline['time'] = time

    return timeline
def daily_timeline(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    daily_timeline = df.groupby('only_date').count()['message'].reset_index()

    return daily_timeline


def week_activity_map(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    return df['day_name'].value_counts()

def month_activity_map(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    return df['month'].value_counts()

def activity_heatmap(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]
    user_heatmap = df.pivot_table(index='day_name',columns='period',values='message' , aggfunc='count').fillna(0)
    return user_heatmap
