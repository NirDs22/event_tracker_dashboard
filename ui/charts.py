"""Chart and visualization components."""

import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path
import re
from wordcloud import WordCloud


HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
DEFAULT_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

SOURCE_ICONS = {
    "reddit": "👽",
    "news": "📰", 
    "instagram": "📷",
    "facebook": "📘",
    "photos": "🖼️",
    "youtube": "📺",
}


def create_time_series_chart(df: pd.DataFrame, topic_color: str, title: str = "📅 Mentions Over Time") -> None:
    """Create a time series chart showing mentions over time."""
    daily = df.groupby("date").size().reset_index(name="mentions")
    
    fig = px.line(
        daily, 
        x="date", 
        y="mentions", 
        title=title,
        color_discrete_sequence=[topic_color]
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Oxygen, Ubuntu, Cantarell, Open Sans, Helvetica Neue, sans-serif",
            size=12,
            color="#0F172A"
        ),
        title=dict(
            font=dict(
                family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Oxygen, Ubuntu, Cantarell, Open Sans, Helvetica Neue, sans-serif",
                size=16,
                color="#0F172A"
            )
        )
    )
    st.plotly_chart(fig, use_container_width=True)


def create_source_distribution_chart(df: pd.DataFrame, title: str = "📊 Posts by Source") -> None:
    """Create a pie chart showing post distribution by source."""
    source_dist = df.groupby("source").size().reset_index(name="count")
    source_dist["icon"] = source_dist["source"].map(SOURCE_ICONS)
    source_dist["display"] = source_dist["icon"] + " " + source_dist["source"].str.title()
    
    fig = px.pie(
        source_dist, 
        values="count", 
        names="display",
        title=title
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Oxygen, Ubuntu, Cantarell, Open Sans, Helvetica Neue, sans-serif",
            size=12,
            color="#0F172A"
        ),
        title=dict(
            font=dict(
                family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Oxygen, Ubuntu, Cantarell, Open Sans, Helvetica Neue, sans-serif",
                size=16,
                color="#0F172A"
            )
        )
    )
    st.plotly_chart(fig, use_container_width=True)


def create_mini_analytics_chart(posts: list, topic_color: str) -> None:
    """Create a mini analytics chart for topic overview."""
    df_mini = pd.DataFrame([{"posted_at": p.posted_at} for p in posts])
    df_mini["date"] = df_mini["posted_at"].dt.date
    daily_mini = df_mini.groupby("date").size()
    
    # Create a simple line chart with better styling
    fig_mini = px.line(
        x=daily_mini.index, 
        y=daily_mini.values,
        title=None,
        color_discrete_sequence=[topic_color]
    )
    fig_mini.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=80,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        xaxis=dict(showgrid=False, showticklabels=False, title=""),
        yaxis=dict(showgrid=False, showticklabels=False, title=""),
        font=dict(
            family="SF Pro Text, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, system-ui, sans-serif",
            size=10,
            color="#1C1C1E"
        )
    )
    st.plotly_chart(fig_mini, use_container_width=True, config={'displayModeBar': False})


def create_word_cloud(text: str) -> None:
    """Create and display a word cloud from the given text."""
    if not text.strip():
        st.info("No text available for word cloud generation.")
        return
    
    try:
        font = str(DEFAULT_FONT) if DEFAULT_FONT.exists() else None
        wc = WordCloud(
            width=800,
            height=400,
            background_color="white",
            max_words=50,
            colormap="viridis",
            font_path=font,
        ).generate(text)
        st.image(wc.to_array(), use_column_width=True)
    except Exception as e:
        st.error(f"Could not generate word cloud: {e}")


def create_source_badges(posts: list) -> str:
    """Create HTML badges showing source breakdown."""
    sources = pd.DataFrame([{"source": p.source} for p in posts])
    source_counts = sources.groupby("source").size()
    
    source_badges = ""
    for source, count in source_counts.items():
        icon = SOURCE_ICONS.get(source, "📄")
        badge_class = f"{source}-badge"
        source_badges += f'<span class="source-badge {badge_class}">{icon} {count}</span> '
    
    return source_badges
