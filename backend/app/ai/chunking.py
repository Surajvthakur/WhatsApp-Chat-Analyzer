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
