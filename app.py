import streamlit as st
from matplotlib import pyplot as plt
import seaborn as sns
import preprocessor
import helper
import plotly.express as px

# Set Seaborn style
sns.set_theme(style="darkgrid")

st.sidebar.title("Whatsapp Chat Analyzer")

uploaded_file = st.sidebar.file_uploader("Choose a file")
if uploaded_file is not None:
    bytes_data = uploaded_file.getvalue()
    data = bytes_data.decode("utf-8")

    df = preprocessor.preprocess(data)

    # Fetch unique users
    user_list = df['user'].unique().tolist()
    if 'System' in user_list:
        user_list.remove('System')
    user_list.sort()
    user_list.insert(0, "Overall")
    selected_user = st.sidebar.selectbox("Show analysis wrt", user_list)

    if st.sidebar.button("Show analysis"):

        # Stats Area
        num_messages, words, num_media_messages, num_links = helper.fetch_stats(selected_user, df)
        st.title("Top Statistics")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.header("Total Messages")
            st.title(num_messages)

        with col2:
            st.header("Total Words")
            st.title(words)

        with col3:
            st.header("Media Shared")
            st.title(num_media_messages)

        with col4:
            st.header("Links Shared")
            st.title(num_links)

        # Monthly timeline
        st.title("Monthly Timeline")
        timeline = helper.monthly_timeline(selected_user, df)
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.lineplot(x='time', y='message', data=timeline, ax=ax, marker='o', color='green', linewidth=2, label='Messages')
        ax.set_title("Monthly Message Timeline", fontsize=16)
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Message Count", fontsize=12)
        plt.xticks(rotation=90)
        ax.legend(title="Legend")  # Added legend
        st.pyplot(fig)

        # Daily timeline
        st.title("Daily Timeline")
        daily_timeline = helper.daily_timeline(selected_user, df)
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.lineplot(x='only_date', y='message', data=daily_timeline, ax=ax, marker='o', color='blue', linewidth=2, label='Messages')
        ax.set_title("Daily Message Timeline", fontsize=16)
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Message Count", fontsize=12)
        plt.xticks(rotation=90)
        ax.legend(title="Legend")  # Added legend
        st.pyplot(fig)

        # Activity map
        st.title("Activity Map")
        col1, col2 = st.columns(2)

        with col1:
            st.header("Most Busy Day")
            busy_day = helper.week_activity_map(selected_user, df)
            fig, ax = plt.subplots()
            sns.barplot(x=busy_day.index, y=busy_day.values, palette="magma", ax=ax, label='Activity')
            ax.set_title("Most Busy Days", fontsize=16)
            ax.set_xlabel("Days", fontsize=12)
            ax.set_ylabel("Message Count", fontsize=12)
            plt.xticks(rotation=90)
            st.pyplot(fig)

        with col2:
            st.header("Most Busy Month")
            busy_month = helper.month_activity_map(selected_user, df)
            fig, ax = plt.subplots()
            sns.barplot(x=busy_month.index, y=busy_month.values, palette="inferno", ax=ax, label='Activity')
            ax.set_title("Most Busy Months", fontsize=16)
            ax.set_xlabel("Months", fontsize=12)
            ax.set_ylabel("Message Count", fontsize=12)
            plt.xticks(rotation=90)
            st.pyplot(fig)

        # Weekly Activity Heatmap
        st.title("Weekly Activity Map")
        user_heatmap = helper.activity_heatmap(selected_user, df)
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(user_heatmap, cmap="YlGnBu", linewidths=.5, annot=True, fmt="g", ax=ax)
        ax.set_title("Weekly Activity Heatmap", fontsize=16)
        st.pyplot(fig)

        # Finding the busiest users in the group
        if selected_user == 'Overall':
            st.title("Most Busy Users")
            df_filtered = df[df['user'] != 'group_notification']
            x, new_df = helper.most_busy_users(df_filtered)
            fig, ax = plt.subplots()
            col1, col2 = st.columns(2)

            with col1:
                sns.barplot(x=x.values, y=x.index, palette="rocket", ax=ax, label='Message Count')
                ax.set_title("Top Active Users", fontsize=16)
                ax.set_xlabel("Message Count", fontsize=12)
                ax.set_ylabel("Users", fontsize=12)
                st.pyplot(fig)

            with col2:
                st.dataframe(new_df)

        # WordCloud
        st.title("WordCloud")
        df_wc = helper.create_wordcloud(selected_user, df)
        fig, ax = plt.subplots()
        ax.imshow(df_wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig)

        # Most common words
        most_common_df = helper.most_common_words(selected_user, df)
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(x=most_common_df[1], y=most_common_df[0], palette="mako", ax=ax, label='Frequency')
        ax.set_title("Most Common Words", fontsize=16)
        ax.set_xlabel("Frequency", fontsize=12)
        ax.set_ylabel("Words", fontsize=12)
        plt.xticks(rotation=45)
        st.pyplot(fig)

        # Emoji analysis
        emoji_df = helper.emoji_helper(selected_user, df)
        st.title("Emoji Analysis")
        col1, col2 = st.columns(2)

        with col1:
            st.dataframe(emoji_df)

        with col2:
            # Create pie chart using Plotly
            fig = px.pie(emoji_df, names=0, values=1, title="Emoji Distribution", color=0,
                         color_discrete_sequence=px.colors.qualitative.Set3)

            # Show the plot
            st.plotly_chart(fig)