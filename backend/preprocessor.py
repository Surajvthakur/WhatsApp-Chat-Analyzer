# OverAll Parsing

import pandas as pd
import re


def preprocess(chat_data):
    # Regex pattern to match Android and iOS date formats (AM/PM, 24-hour, iOS with seconds)
    date_pattern = r"""
    (\d{2}/\d{2}/(?:\d{2}|\d{4}),\s?\d{1,2}:\d{2}:\d{2}\s?[apAP][mM])  # iOS format with seconds
    |(\d{2}/\d{2}/(?:\d{2}|\d{4}),\s?\d{1,2}:\d{2}\s?[apAP][mM])       # Android format with AM/PM
    |(\d{2}/\d{2}/(?:\d{2}|\d{4}),\s?\d{1,2}:\d{2})                    # Android 24-hour format
    """

    def clean_date(raw_date):
        """
        Cleans the date by removing unwanted characters and ensuring proper formatting.
        """
        if raw_date:
            # Remove narrow no-break spaces (Unicode \u202f) and any extra spaces
            raw_date = re.sub(r'[\u202f]', '', raw_date.strip())
            # Ensure no spaces before AM/PM
            raw_date = re.sub(r'(\d{1,2}:\d{2})(\s?)([apAP]{2})', r'\1\3', raw_date)
            return raw_date
        return None

    # Extract all dates (considering all three date formats)
    dates = re.findall(date_pattern, chat_data, re.VERBOSE)
    dates = [clean_date(date[0] or date[1] or date[2]) for date in dates]  # Flatten and clean

    # Extract messages
    messages = re.split(date_pattern, chat_data, flags=re.VERBOSE)[1:]  # Skip the first split (empty)
    messages = [msg.strip() for i, msg in enumerate(messages) if i % 4 == 3]  # Keep every fourth item (actual messages)

    # Ensure equal lengths and that we parsed at least one message
    if len(dates) != len(messages) or len(dates) == 0:
        return pd.DataFrame()  # Return empty DataFrame if there's a mismatch or no messages parsed

    # Create DataFrame
    df = pd.DataFrame({'date': dates, 'message': messages})

    # Clean date and convert 'date' to datetime with multiple formats
    df['date'] = df['date'].apply(clean_date)

    # Try parsing the dates with flexible parsing
    df['date'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce', format='mixed')

    # Remove unwanted patterns like '\n[', '\n‎[', or '‎[' from messages
    df['message'] = df['message'].str.replace(r'[\n‎]*\[$', '', regex=True)

    # Extract user and clean message
    df['user'] = df['message'].str.extract(r"^(.*?):", expand=False).fillna("System")

    # Clean message
    df['message'] = df['message'].str.split(':', n=1).str[1].fillna(df['message']).str.strip()
    df['user'] = df['user'].str.strip()

    # Remove leading ']' from the 'user' column
    df['user'] = df['user'].str.replace(r'^\]', '', regex=True)

    # Add year, month, day, hour, minute only if 'date' is valid
    if df['date'].notna().all():
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day'] = df['date'].dt.day
        df['hour'] = df['date'].dt.hour
        df['minute'] = df['date'].dt.minute
        df['only_date'] = df['date'].dt.date
        df['month_num'] = df['date'].dt.month
        df['day_name'] = df['date'].dt.day_name()

        h = df['hour']
        h_next = h + 1
        h_str = h.astype(str).where(h != 0, '00')
        h_next_str = h_next.astype(str).where(h != 23, '00')
        df['period'] = h_str + '-' + h_next_str

    return df
