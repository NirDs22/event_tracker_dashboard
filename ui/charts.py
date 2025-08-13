"""Chart and visualization components."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from pathlib import Path
import re
from wordcloud import WordCloud
from collections import Counter
from datetime import datetime, timedelta
import html as py_html


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


def filter_last_3_months(df: pd.DataFrame) -> pd.DataFrame:
    """Filter DataFrame to show only data from the last 3 months."""
    if df.empty:
        return df
    
    # Get the cutoff date (3 months ago)
    cutoff_date = datetime.now() - timedelta(days=90)
    
    # Convert date column to datetime if it's not already
    if 'date' in df.columns:
        if df['date'].dtype == 'object':
            df = df.copy()
            df['date'] = pd.to_datetime(df['date'])
        # Filter to last 3 months
        df = df[df['date'] >= cutoff_date]
    elif 'posted_at' in df.columns:
        if df['posted_at'].dtype == 'object':
            df = df.copy()
            df['posted_at'] = pd.to_datetime(df['posted_at'])
        # Filter to last 3 months
        df = df[df['posted_at'] >= cutoff_date]
    
    return df


def create_time_series_chart(df: pd.DataFrame, topic_color: str, title: str = "📅 Mentions Over Time (Last 3 Months)") -> None:
    """Create a time series chart showing mentions over time (last 3 months only)."""
    # Filter to last 3 months
    df_filtered = filter_last_3_months(df)
    
    if df_filtered.empty:
        st.info("📅 No data available in the last 3 months")
        return
    
    daily = df_filtered.groupby("date").size().reset_index(name="mentions")
    
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


def create_source_distribution_chart(df: pd.DataFrame, title: str = "📊 Posts by Source (Last 3 Months)") -> None:
    """Create a pie chart showing post distribution by source (last 3 months only)."""
    # Filter to last 3 months
    df_filtered = filter_last_3_months(df)
    
    if df_filtered.empty:
        st.info("📊 No data available in the last 3 months")
        return
    
    source_dist = df_filtered.groupby("source").size().reset_index(name="count")
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
    """Create a mini analytics chart for topic overview (last 3 months only)."""
    df_mini = pd.DataFrame([{"posted_at": p.posted_at} for p in posts])
    
    # Filter to last 3 months
    cutoff_date = datetime.now() - timedelta(days=90)
    df_mini = df_mini[df_mini["posted_at"] >= cutoff_date]
    
    if df_mini.empty:
        # Show empty chart if no data in last 3 months
        fig_mini = go.Figure()
        fig_mini.add_annotation(
            text="No data (3mo)",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=10, color="#6B7280")
        )
        fig_mini.update_layout(
            height=80,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
            xaxis=dict(showgrid=False, showticklabels=False, title="", visible=False),
            yaxis=dict(showgrid=False, showticklabels=False, title="", visible=False),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_mini, use_container_width=True)
        return
    
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


def extract_keywords_and_hashtags(posts_data, min_length=3, max_keywords=20):
    """Extract trending keywords and hashtags from posts (last 3 months only)."""
    import nltk
    from collections import defaultdict
    
    # Filter posts to last 3 months
    cutoff_date = datetime.now() - timedelta(days=90)
    filtered_posts = []
    for post in posts_data:
        post_date = post.get('posted_at')
        if post_date:
            if isinstance(post_date, str):
                try:
                    post_date = pd.to_datetime(post_date)
                except:
                    continue
            if post_date.date() >= cutoff_date.date():
                filtered_posts.append(post)
    
    if not filtered_posts:
        return {}, {}
    
    # Download required NLTK data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            nltk.download('punkt', quiet=True)
        except:
            pass
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        try:
            nltk.download('stopwords', quiet=True)
        except:
            pass
    
    try:
        from nltk.corpus import stopwords
        from nltk.tokenize import word_tokenize
        stop_words = set(stopwords.words('english'))
    except:
        # Fallback to basic stopwords
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'a', 'an', 'as', 'if', 'so', 'than', 'too', 'very', 'just', 'now'}
        word_tokenize = str.split
    
    keywords_by_date = defaultdict(Counter)
    hashtags_by_date = defaultdict(Counter)
    
    for post in filtered_posts:
        if not post.get('content'):
            continue
            
        content = post['content'].lower()
        post_date = post['posted_at'].date() if post.get('posted_at') else datetime.now().date()
        
        # Extract hashtags
        hashtags = re.findall(r'#(\w+)', content)
        for hashtag in hashtags:
            if len(hashtag) >= min_length:
                hashtags_by_date[post_date][f"#{hashtag}"] += 1
        
        # Extract keywords (remove HTML, URLs, mentions, hashtags)
        clean_content = re.sub(r'<[^>]+>', ' ', content)  # Remove HTML
        clean_content = re.sub(r'http[s]?://\S+', ' ', clean_content)  # Remove URLs
        clean_content = re.sub(r'@\w+', ' ', clean_content)  # Remove mentions
        clean_content = re.sub(r'#\w+', ' ', clean_content)  # Remove hashtags
        clean_content = re.sub(r'[^\w\s]', ' ', clean_content)  # Remove punctuation
        
        try:
            words = word_tokenize(clean_content)
        except:
            words = clean_content.split()
        
        for word in words:
            word = word.strip()
            if (len(word) >= min_length and 
                word not in stop_words and 
                not word.isdigit() and
                not re.match(r'^\w*\d\w*$', word)):  # Skip words with numbers
                keywords_by_date[post_date][word] += 1
    
    return keywords_by_date, hashtags_by_date


def create_trending_keywords_chart(posts_data, topic_color, time_window_days=7, max_keywords=5):
    """Create a simplified trending keywords chart showing only top keywords (last 3 months only)."""
    if not posts_data:
        st.info("📝 No data available for trending analysis")
        return
    
    keywords_by_date, hashtags_by_date = extract_keywords_and_hashtags(posts_data, max_keywords=max_keywords*3)
    
    if not keywords_by_date and not hashtags_by_date:
        st.info("📝 No keywords or hashtags found in the last 3 months")
        return
    
    # Get top keywords overall (reduced number)
    all_keywords = Counter()
    for date_counter in keywords_by_date.values():
        all_keywords.update(date_counter)
    
    all_hashtags = Counter()
    for date_counter in hashtags_by_date.values():
        all_hashtags.update(date_counter)
    
    top_keywords = [word for word, count in all_keywords.most_common(max_keywords)]
    top_hashtags = [tag for tag, count in all_hashtags.most_common(max_keywords)]
    
    # Only show the most relevant data - split into two separate, simpler charts
    if top_keywords:
        st.markdown("#### 📈 Top Keywords")
        
        # Create simple line chart for keywords only
        all_dates = sorted(set(keywords_by_date.keys()))
        fig_keywords = go.Figure()
        
        # Use a simple, distinct color palette
        colors = ['#007AFF', '#34C759', '#FF9500', '#FF3B30', '#AF52DE']
        
        for i, keyword in enumerate(top_keywords):
            keyword_counts = []
            for date in all_dates:
                keyword_counts.append(keywords_by_date[date].get(keyword, 0))
            
            fig_keywords.add_trace(
                go.Scatter(
                    x=all_dates,
                    y=keyword_counts,
                    name=keyword,
                    mode='lines+markers',
                    line=dict(color=colors[i % len(colors)], width=3),
                    marker=dict(size=8),
                    hovertemplate=f"<b>{keyword}</b><br>%{{x}}: %{{y}} mentions<extra></extra>"
                )
            )
        
        fig_keywords.update_layout(
            height=350,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2),
            margin=dict(l=50, r=50, t=30, b=80),
            xaxis_title="Date",
            yaxis_title="Mentions",
            font=dict(size=12)
        )
        
        st.plotly_chart(fig_keywords, use_container_width=True)
    
    # Show hashtags in a separate, simpler chart
    if top_hashtags:
        st.markdown("#### 🏷️ Top Hashtags")
        
        all_dates = sorted(set(hashtags_by_date.keys()))
        fig_hashtags = go.Figure()
        
        colors = ['#5856D6', '#FF2D92', '#30B0C7', '#32D74B', '#FF9F0A']
        
        for i, hashtag in enumerate(top_hashtags):
            hashtag_counts = []
            for date in all_dates:
                hashtag_counts.append(hashtags_by_date[date].get(hashtag, 0))
            
            fig_hashtags.add_trace(
                go.Scatter(
                    x=all_dates,
                    y=hashtag_counts,
                    name=hashtag,
                    mode='lines+markers',
                    line=dict(color=colors[i % len(colors)], width=3),
                    marker=dict(size=8),
                    hovertemplate=f"<b>{hashtag}</b><br>%{{x}}: %{{y}} mentions<extra></extra>"
                )
            )
        
        fig_hashtags.update_layout(
            height=350,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2),
            margin=dict(l=50, r=50, t=30, b=80),
            xaxis_title="Date",
            yaxis_title="Mentions",
            font=dict(size=12)
        )
        
        st.plotly_chart(fig_hashtags, use_container_width=True)


def create_keyword_momentum_chart(posts_data, topic_color):
    """Create a chart showing keyword momentum (trending up/down)."""
    if not posts_data:
        return
    
    keywords_by_date, hashtags_by_date = extract_keywords_and_hashtags(posts_data)
    
    if not keywords_by_date:
        return
    
    # Calculate momentum for keywords
    all_dates = sorted(set(keywords_by_date.keys()))
    if len(all_dates) < 2:
        st.info("📊 Need more data points to calculate momentum trends")
        return
    
    # Get recent vs previous period
    mid_point = len(all_dates) // 2
    recent_dates = all_dates[mid_point:]
    previous_dates = all_dates[:mid_point]
    
    recent_keywords = Counter()
    previous_keywords = Counter()
    
    for date in recent_dates:
        recent_keywords.update(keywords_by_date[date])
    
    for date in previous_dates:
        previous_keywords.update(keywords_by_date[date])
    
    # Calculate momentum
    momentum_data = []
    for keyword in set(list(recent_keywords.keys()) + list(previous_keywords.keys())):
        recent_count = recent_keywords.get(keyword, 0)
        previous_count = previous_keywords.get(keyword, 0)
        
        if recent_count > 0 or previous_count > 0:
            if previous_count == 0:
                momentum = 100  # New keyword
            else:
                momentum = ((recent_count - previous_count) / previous_count) * 100
            
            momentum_data.append({
                'keyword': keyword,
                'recent_count': recent_count,
                'previous_count': previous_count,
                'momentum': momentum,
                'total_mentions': recent_count + previous_count
            })
    
    # Sort by momentum and filter
    momentum_data.sort(key=lambda x: x['momentum'], reverse=True)
    top_momentum = momentum_data[:15]  # Top 15 trending
    
    if not top_momentum:
        return
    
    # Create momentum chart
    keywords = [item['keyword'] for item in top_momentum]
    momentums = [item['momentum'] for item in top_momentum]
    colors = ['#34C759' if m > 0 else '#FF3B30' for m in momentums]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=momentums,
        y=keywords,
        orientation='h',
        marker_color=colors,
        text=[f"{m:+.0f}%" for m in momentums],
        textposition='outside',
        hovertemplate="<b>%{y}</b><br>Momentum: %{x:.1f}%<extra></extra>"
    ))
    
    fig.update_layout(
        title="🚀 Keyword Momentum (Recent vs Previous Period)",
        xaxis_title="Momentum (%)",
        yaxis_title="Keywords",
        height=400 + len(top_momentum) * 20,
        showlegend=False,
        margin=dict(l=120, r=100, t=60, b=40)
    )
    
    st.plotly_chart(fig, use_container_width=True)
