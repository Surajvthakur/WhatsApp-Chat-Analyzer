import pandas as pd

def chunk_chat_data(df: pd.DataFrame, chunk_size: int = 15) -> list[str]:
    """
    Chunks a pandas DataFrame of chat messages into strings containing multiple messages.
    Reduces the number of embeddings by grouping adjacent messages.
    """
    if df is None or df.empty:
        return []

    chunks = []
    current_chunk = []
    
    # Iterate through the rows of the dataframe
    for index, row in df.iterrows():
        # Format each line as "User: Message" or "[Date] User: Message"
        date_str = str(row['date']) if pd.notna(row.get('date')) else ""
        user = row.get('user', 'Unknown')
        msg = row.get('message', '')
        
        # Omit media omitted messages or system messages if desired, but for now we keep everything
        # just formatting it cleanly.
        if msg == '<Media omitted>' or msg.strip() == '':
            continue
            
        line = f"[{date_str}] {user}: {msg}"
        current_chunk.append(line)
        
        if len(current_chunk) >= chunk_size:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            
    # Add any remaining messages
    if current_chunk:
        chunks.append("\n".join(current_chunk))
        
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

    chunks_metadata = []
    current_chunk = []
    current_speakers = set()
    current_dates = []
    
    for index, row in df.iterrows():
        date_str = str(row['date']) if pd.notna(row.get('date')) else ""
        user = row.get('user', 'Unknown')
        msg = row.get('message', '')
        
        if msg == '<Media omitted>' or msg.strip() == '':
            continue
            
        line = f"[{date_str}] {user}: {msg}"
        current_chunk.append(line)
        if user and user != 'group_notification':
            current_speakers.add(user)
        if pd.notna(row.get('date')):
            current_dates.append(row['date'])
            
        if len(current_chunk) >= chunk_size:
            ts_range = _format_date_range(current_dates)
            speakers = ", ".join(sorted(current_speakers)) if current_speakers else "Unknown"
            
            chunks_metadata.append({
                "text": "\n".join(current_chunk),
                "speaker": speakers,
                "timestamp_range": ts_range
            })
            current_chunk = []
            current_speakers = set()
            current_dates = []
            
    # Add any remaining messages
    if current_chunk:
        ts_range = _format_date_range(current_dates)
        speakers = ", ".join(sorted(current_speakers)) if current_speakers else "Unknown"
        
        chunks_metadata.append({
            "text": "\n".join(current_chunk),
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
