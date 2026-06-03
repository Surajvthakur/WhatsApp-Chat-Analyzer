import pandas as pd

def chunk_chat_data(df: pd.DataFrame, chunk_size: int = 15) -> list[str]:
    """
    Chunks a pandas DataFrame of chat messages into strings containing multiple messages.
    Reduces the number of embeddings by grouping adjacent messages.
    """
    if df is None or df.empty:
        return []

    dates = df['date'] if 'date' in df.columns else pd.Series(pd.NaT, index=df.index)
    users = df['user'] if 'user' in df.columns else pd.Series('Unknown', index=df.index)
    messages = df['message'] if 'message' in df.columns else pd.Series('', index=df.index)

    messages = messages.astype(str)
    users = users.astype(str)

    # Vectorized date string conversion
    date_strs = dates.astype(str).where(dates.notna(), "")

    # Vectorized line formatting
    lines = "[" + date_strs + "] " + users + ": " + messages

    # Vectorized message filtering
    valid_mask = (messages != '<Media omitted>') & (messages.str.strip() != '')
    filtered_lines = lines[valid_mask].tolist()

    # Chunking using list comprehension
    chunks = [
        "\n".join(filtered_lines[i : i + chunk_size])
        for i in range(0, len(filtered_lines), chunk_size)
    ]
    return chunks

def get_chunks_metadata(df: pd.DataFrame, chunk_size: int = 15) -> list[dict]:
    """
    Groups chat data into chunks of size 15, returning a list of dicts containing:
    - text: The formatted chunk text
    - speaker: Comma-separated unique speakers in the chunk
    - timestamp_range: Formatted date range of messages in the chunk (e.g. "Jan", "Jan-Feb", "15 Jan - 22 Feb")
    """
    if df is None or df.empty:
        return []

    dates = df['date'] if 'date' in df.columns else pd.Series(pd.NaT, index=df.index)
    users = df['user'] if 'user' in df.columns else pd.Series('Unknown', index=df.index)
    messages = df['message'] if 'message' in df.columns else pd.Series('', index=df.index)

    messages = messages.astype(str)
    users = users.astype(str)

    # Vectorized date string conversion
    date_strs = dates.astype(str).where(dates.notna(), "")

    # Vectorized line formatting
    lines = "[" + date_strs + "] " + users + ": " + messages

    # Vectorized message filtering
    valid_mask = (messages != '<Media omitted>') & (messages.str.strip() != '')

    filtered_lines = lines[valid_mask].tolist()
    filtered_users = users[valid_mask].tolist()
    filtered_dates = dates[valid_mask].tolist()

    chunks_metadata = []
    num_items = len(filtered_lines)

    for i in range(0, num_items, chunk_size):
        chunk_lines = filtered_lines[i : i + chunk_size]
        chunk_users = filtered_users[i : i + chunk_size]
        chunk_dates = filtered_dates[i : i + chunk_size]

        # Get unique speakers, omitting group_notification and falsy/None
        speakers_set = {u for u in chunk_users if u and u != 'group_notification'}
        speakers = ", ".join(sorted(speakers_set)) if speakers_set else "Unknown"

        # Format date range for valid dates
        valid_dates = [d for d in chunk_dates if pd.notna(d)]
        ts_range = _format_date_range(valid_dates)

        chunks_metadata.append({
            "text": "\n".join(chunk_lines),
            "speaker": speakers,
            "timestamp_range": ts_range
        })

    return chunks_metadata

def _format_date_range(dates) -> str:
    """
    Helper to format a list of datetime values into a human-readable range like "Jan" or "Jan-Feb".
    """
    if not dates:
        return "Unknown"
        
    try:
        first_date = pd.to_datetime(dates[0])
        last_date = pd.to_datetime(dates[-1])
        
        m1 = first_date.strftime("%b")
        m2 = last_date.strftime("%b")
        
        if m1 == m2:
            return m1
        return f"{m1}-{m2}"
    except Exception:
        return "Unknown"
