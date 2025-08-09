import os
import re
from pathlib import Path
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud

try:
    from dotenv import load_dotenv
    ENV_LOADED = load_dotenv()
except Exception:
    ENV_LOADED = False

from monitoring.database import init_db, SessionLocal, Topic, Post
from monitoring.collectors import collect_topic, collect_all_topics_efficiently
from monitoring.scheduler import start_scheduler, send_test_digest
from monitoring.summarizer import summarize, strip_think


def time_ago(dt: datetime | None) -> str:
    if not dt:
        return "never"
    diff = datetime.utcnow() - dt
    if diff.days > 0:
        return f"{diff.days}d ago"
    hours = diff.seconds // 3600
    if hours:
        return f"{hours}h ago"
    minutes = diff.seconds // 60
    if minutes:
        return f"{minutes}m ago"
    return "just now"


SOURCE_ICONS = {
    "reddit": "👽",
    "news": "📰", 
    "instagram": "📷",
    "facebook": "📘",
    "photos": "🖼️",
    "youtube": "📺",
}


HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
DEFAULT_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def contains_hebrew(text: str) -> bool:
    return bool(HEBREW_RE.search(text))


def clean_content(raw: str) -> str:
    """Return plain text with inline links, stripping any HTML tags."""
    import html as _html
    import re as _re
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except Exception:
        BeautifulSoup = None

    raw_content = _html.unescape(strip_think(str(raw)))

    if BeautifulSoup:
        soup = BeautifulSoup(raw_content, "html.parser")
        for a in soup.find_all("a"):
            href = a.get("href")
            if href:
                a.replace_with(f"{a.get_text(' ', strip=True)} ({href})")
        return soup.get_text(" ", strip=True)

    return _re.sub(r"<[^>]+>", "", raw_content).strip()


@st.dialog("AI Summary")
def show_link_summary(content: str) -> None:
    """Display a modal summarising a post's content."""
    st.write(strip_think(summarize([content])))
    if st.button("Close"):
        st.rerun()


# Initialise database and scheduler
init_db()
try:
    scheduler = start_scheduler()
except Exception:
    scheduler = None

st.set_page_config(
    page_title="Social & News Monitor", 
    layout="wide",
    page_icon="📰",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .topic-card {
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .topic-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
    }
    
    .post-item {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    
    .source-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-left: 0.5rem;
    }
    
    .reddit-badge { background: #ff4500; color: white; }
    .news-badge { background: #0066cc; color: white; }
    .instagram-badge { background: #e4405f; color: white; }
    .facebook-badge { background: #1877f2; color: white; }
    .youtube-badge { background: #ff0000; color: white; }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    
    .sidebar .stSelectbox > div > div > div {
        background-color: #f0f2f6;
    }

    u {
        text-underline-offset: 2px;
        text-decoration-thickness: 2px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>📰 Social & News Monitoring Dashboard</h1><p>Track topics across social media and news sources with AI-powered insights</p></div>', unsafe_allow_html=True)

if not ENV_LOADED:
    st.sidebar.info(
        "No .env file found. Using defaults; some features may be limited. "
        "Copy .env.example to .env to add your own keys."
    )

if not os.getenv("REDDIT_CLIENT_ID") or not os.getenv("REDDIT_CLIENT_SECRET"):
    st.sidebar.warning(
        "Reddit credentials missing. Reddit posts won't be collected. "
        "Create a Reddit app and set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env."
    )

st.sidebar.success(
    "✅ Instagram & Facebook enabled (no accounts required). "
    "Will search for public posts via web search."
)

st.sidebar.success(
    "✅ Photo search enabled - scrapes real images from the web. "
    "No API keys required (though Unsplash/Pexels keys will give better results)."
)

if not os.getenv("NEWSAPI_KEY"):
    st.sidebar.warning(
        "NEWSAPI_KEY not set: using Google News RSS. "
        "Get a free key at newsapi.org and add NEWSAPI_KEY to .env to unlock more sources."
    )

try:
    import instagrapi  # type: ignore  # noqa: F401
except Exception:
    st.sidebar.info(
        "Instagram scraping requires the `instagrapi` package. Install with `pip install instagrapi` to enable."
    )

try:
    import requests
    import bs4  # type: ignore  # noqa: F401
except Exception:
    st.sidebar.info(
        "Photo searching requires `requests` and `beautifulsoup4`. Install with `pip install requests beautifulsoup4` to enable."
    )

if not os.getenv("UNSPLASH_ACCESS_KEY") and not os.getenv("PEXELS_API_KEY"):
    st.sidebar.error(
        "� **No Photo Search Configured**\n\n"
        "To get actual photos of your subjects:\n\n"
        "1. **Unsplash** (recommended): Get free key at unsplash.com/developers\n"
        "2. **Pexels**: Get free key at pexels.com/api\n\n"
        "Add to .env file:\n"
        "```\n"
        "UNSPLASH_ACCESS_KEY=your_key\n"
        "PEXELS_API_KEY=your_key\n"
        "```\n\n"
        "Without API keys, no photos will be collected."
    )

# Facebook scraping now works via web search - no packages needed

if not os.getenv("SMTP_HOST") and not os.getenv("SMTP_SERVER"):
    st.sidebar.info(
        "📧 Email digests disabled. Set SMTP_SERVER, SMTP_PORT, SMTP_USER and SMTP_PASSWORD in .env to enable."
    )
else:
    st.sidebar.success("✅ Email configuration found - digests enabled!")

if not os.getenv("OLLAMA_MODEL"):
    st.sidebar.info(
        "No OLLAMA_MODEL configured; using local transformers summariser. "
        "Install Ollama and run `ollama pull qwen:latest`, then set OLLAMA_MODEL=qwen in .env for higher quality summaries."
    )

if scheduler is None:
    st.sidebar.info(
        "Background scheduler did not start. Scheduled collection won't run; check logs or collect manually."
    )

if "selected_topic" not in st.session_state:
    st.session_state.selected_topic = None

# Initialize database session and topic names
session = SessionLocal()
topic_names = [t.name for t in session.query(Topic).all()]

# Enhanced sidebar styling
st.sidebar.markdown("### 🎛️ **Topic Management**")
st.sidebar.markdown("---")

with st.sidebar.expander("➕ **Add New Topic**", expanded=True):
    name = st.text_input("📝 Topic or Person", placeholder="e.g., AI Technology, Elon Musk")
    
    col1, col2 = st.columns(2)
    with col1:
        icon = st.text_input("🎭 Icon", value="📌", help="Choose an emoji to represent this topic")
    with col2:
        color = st.color_picker("🎨 Color", "#667eea", help="Pick a theme color for this topic")
    
    keywords = st.text_input("🔍 Keywords", placeholder="AI, machine learning, technology", help="Comma-separated keywords to filter content")
    profiles = st.text_input("👥 Social Profiles", placeholder="@username, facebook.com/page", help="Social media profiles to monitor")
    
    if st.button("✨ **Create Topic**", type="primary", use_container_width=True) and name:
        if name not in topic_names:
            with st.spinner(f"Creating topic '{name}'..."):
                topic = Topic(
                    name=name,
                    keywords=keywords,
                    profiles=profiles,
                    color=color,
                    icon=icon,
                )
                session.add(topic)
                session.commit()
                session.refresh(topic)

                def progress(msg: str) -> None:
                    st.sidebar.info(f"{icon} {msg}")

                collect_topic(topic, progress=progress, force=True)
                st.sidebar.success(f"✅ Topic '{name}' created successfully!")
        else:
            st.sidebar.error("⚠️ Topic already exists!")

st.sidebar.markdown("---")

# Add email testing section if SMTP is configured
if os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER"):
    with st.sidebar.expander("📧 **Test Email Digest**"):
        test_email = st.text_input("📧 Test Email", placeholder="your@email.com")
        if topic_names:
            test_topic = st.selectbox("Select Topic", topic_names)
            if st.button("📨 **Send Test Digest**", use_container_width=True) and test_email and test_topic:
                topic_obj = session.query(Topic).filter_by(name=test_topic).first()
                if topic_obj:
                    with st.spinner("Sending test digest..."):
                        success = send_test_digest(topic_obj.id, test_email)
                        if success:
                            st.sidebar.success(f"✅ Test digest sent to {test_email}!")
                        else:
                            st.sidebar.error("❌ Failed to send test digest. Check logs and email configuration.")
        else:
            st.info("Create topics first to test email digests")
            
st.sidebar.markdown("---")

with st.sidebar.expander("🗑️ **Manage Topics**"):
    if topic_names:
        remove_choice = st.selectbox("Select topic to delete", ["None"] + topic_names, help="⚠️ This will permanently delete all data for this topic")
        
        if remove_choice != "None":
            st.warning(f"⚠️ You are about to delete '{remove_choice}' and ALL its data!")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("❌ **Cancel**", use_container_width=True):
                    st.rerun()
            
            with col2:
                if st.button("🗑️ **DELETE**", type="primary", use_container_width=True):
                    # Use session state to track deletion confirmation
                    if f"confirm_delete_{remove_choice}" not in st.session_state:
                        st.session_state[f"confirm_delete_{remove_choice}"] = True
                        st.warning("⚠️ Click DELETE again to confirm!")
                        st.rerun()
                    else:
                        # Actually delete the topic
                        to_del = session.query(Topic).filter_by(name=remove_choice).first()
                        if to_del:
                            # Delete associated posts first (CASCADE)
                            posts_to_delete = session.query(Post).filter_by(topic_id=to_del.id).all()
                            for post in posts_to_delete:
                                session.delete(post)
                            
                            # Delete the topic
                            session.delete(to_del)
                            session.commit()
                            
                            # Clear confirmation state
                            del st.session_state[f"confirm_delete_{remove_choice}"]
                            
                            st.sidebar.success(f"✅ Topic '{remove_choice}' deleted!")
                            st.rerun()
                        else:
                            st.sidebar.error("❌ Topic not found!")
    else:
        st.info("No topics to manage yet")

st.sidebar.markdown("---")

if st.sidebar.button("🔄 **Collect All Topics Now**", type="primary", use_container_width=True):
    with st.sidebar.expander("📊 **Collection Progress**", expanded=True):
        # Show efficiency information
        all_topics = session.query(Topic).all()
        if len(all_topics) > 1:
            st.info(f"⚡ Using efficient collection: Collecting by source first for {len(all_topics)} topics")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        errors: list[str] = []
        
        if len(all_topics) > 1:
            # Use efficient collection for multiple topics
            status_text.text("🚀 Using efficient collection method...")
            progress_bar.progress(0.1)
            
            def progress(msg: str):
                status_text.text(f"⚡ {msg}")
            
            errors.extend(collect_all_topics_efficiently(all_topics, progress=progress))
            progress_bar.progress(1.0)
            
        else:
            # Use traditional method for single topic
            for idx, t in enumerate(all_topics):
                status_text.text(f"Collecting {t.icon} {t.name}...")
                progress_bar.progress((idx + 1) / len(all_topics))
                
                def progress(msg: str, ic=t.icon):
                    status_text.text(f"{ic} {msg}")
                
                errors.extend(collect_topic(t, progress=progress))
        
        if errors:
            st.sidebar.error("⚠️ Some collections failed:")
            for err in errors[:3]:  # Show only first 3 errors
                st.sidebar.error(f"• {err}")
            if len(errors) > 3:
                st.sidebar.error(f"... and {len(errors) - 3} more errors")
        else:
            st.sidebar.success("✅ All collections completed successfully!")
        
        progress_bar.progress(1.0)
        status_text.text("✅ Collection finished!")

session.close()


# Load topics for main view
topics = session.query(Topic).all()

if st.session_state.selected_topic is None:
    if not topics:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; background: #f8f9fa; border-radius: 15px; margin: 2rem 0;">
            <h2>🚀 Welcome to Your Monitoring Dashboard!</h2>
            <p style="font-size: 1.1rem; color: #666;">Start by adding topics to monitor in the sidebar.</p>
            <p>Track conversations about your interests across social media and news sources.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Topic overview with enhanced cards
        st.markdown("## 📊 **Your Topics Overview**")
        
        # Metrics summary
        total_posts = session.query(Post).count()
        active_topics = len([t for t in topics if t.last_collected])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: #667eea; margin: 0;">📈 {total_posts}</h3>
                <p style="margin: 0;">Total Posts Collected</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: #51cf66; margin: 0;">🎯 {len(topics)}</h3>
                <p style="margin: 0;">Active Topics</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: #ff6b6b; margin: 0;">⚡ {active_topics}</h3>
                <p style="margin: 0;">Recently Updated</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Topic cards in grid layout
        cols = st.columns(3)
        for idx, topic in enumerate(topics):
            with cols[idx % 3]:
                posts = (
                    session.query(Post)
                    .filter_by(topic_id=topic.id)
                    .order_by(Post.posted_at.desc())
                    .all()
                )
                
                new_posts_count = 0
                if topic.last_viewed and posts:
                    new_posts_count = sum(1 for p in posts if p.posted_at > topic.last_viewed)
                
                # Enhanced topic card
                st.markdown(f"""
                <div class="topic-card" style="background: linear-gradient(135deg, {topic.color}15, {topic.color}25);">
                    <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                        <span style="font-size: 2rem; margin-right: 0.5rem;">{topic.icon}</span>
                        <div>
                            <h3 style="margin: 0; color: {topic.color};">{topic.name}</h3>
                            <p style="margin: 0; font-size: 0.9rem; color: #666;">
                                {len(posts)} posts • Last: {time_ago(topic.last_collected)}
                            </p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                if posts:
                    # Mini chart
                    df_mini = pd.DataFrame([{"posted_at": p.posted_at} for p in posts])
                    df_mini["date"] = df_mini["posted_at"].dt.date
                    daily_mini = df_mini.groupby("date").size()
                    st.line_chart(daily_mini, height=80)
                    
                    # Source breakdown
                    sources = df_mini = pd.DataFrame([{"source": p.source} for p in posts])
                    source_counts = sources.groupby("source").size()
                    
                    source_badges = ""
                    for source, count in source_counts.items():
                        icon = SOURCE_ICONS.get(source, "📄")
                        badge_class = f"{source}-badge" if source in ["reddit", "news", "instagram", "facebook", "youtube"] else ""
                        source_badges += f'<span class="source-badge {badge_class}">{icon} {count}</span> '
                    
                    st.markdown(source_badges, unsafe_allow_html=True)
                    
                    if new_posts_count > 0:
                        st.markdown(f"""
                        <div style="background: #51cf66; color: white; padding: 0.5rem; 
                                   border-radius: 15px; text-align: center; margin: 0.5rem 0;">
                            <strong>🔔 {new_posts_count} new posts!</strong>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No posts collected yet")
                
                if st.button("🔍 **Explore**", key=f"open_{topic.id}", use_container_width=True, type="primary"):
                    st.session_state.selected_topic = topic.id
                    st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
else:
    topic = session.query(Topic).get(st.session_state.selected_topic)
    if not topic:
        st.error("Topic not found!")
        st.session_state.selected_topic = None
        st.rerun()
        
    # Enhanced topic header
    col1, col2 = st.columns([1, 0.2])
    with col1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {topic.color}, {topic.color}aa); 
                   padding: 2rem; border-radius: 15px; margin-bottom: 2rem;">
            <h1 style="color: white; margin: 0; display: flex; align-items: center;">
                <span style="margin-right: 1rem; font-size: 3rem;">{topic.icon}</span>
                {topic.name}
            </h1>
            <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;">
                📅 Last collected: {time_ago(topic.last_collected)} | 
                🔍 Keywords: {topic.keywords or "None"} | 
                👥 Profiles: {len(topic.profiles.split(',')) if topic.profiles else 0}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        if st.button("🏠 **Home**", use_container_width=True, type="secondary"):
            st.session_state.selected_topic = None
            st.rerun()
    
    posts = (
        session.query(Post)
        .filter_by(topic_id=topic.id)
        .order_by(Post.posted_at.desc())
        .all()
    )
    
    if posts:
        df = pd.DataFrame([
            {
                "content": clean_content(p.content),
                "url": p.url,
                "posted_at": p.posted_at,
                "source": p.source,
                "likes": p.likes,
                "comments": p.comments,
                "image_url": getattr(p, 'image_url', None),
                "is_photo": getattr(p, 'is_photo', False),
                "subreddit": getattr(p, 'subreddit', None),  # Add subreddit info
            }
            for p in posts
        ])        # Enhanced metrics section
        col1, col2, col3, col4 = st.columns(4)
        
        # Separate regular posts from photos
        regular_posts_df = df[df["source"] != "photos"]
        photos_df = df[df["source"] == "photos"]
        
        with col1:
            st.metric("📊 Total Posts", len(regular_posts_df), help="Excludes photos (shown separately)")
        with col2:
            st.metric("❤️ Total Likes", f"{regular_posts_df['likes'].sum():,}")
        with col3:
            st.metric("💬 Total Comments", f"{regular_posts_df['comments'].sum():,}")
        with col4:
            recent_posts = len(regular_posts_df[regular_posts_df['posted_at'] > datetime.utcnow() - timedelta(days=1)])
            photos_count = len(photos_df)
            st.metric("� Photos Found", photos_count, help="Images found from web search")
        
        # Analytics section (excluding photos as they're for browsing, not trend analysis)
        st.markdown("## 📈 **Analytics**")
        
        # Use regular posts for analytics, not photos
        analytics_df = regular_posts_df.copy()
        analytics_df["date"] = analytics_df["posted_at"].dt.date
        daily = analytics_df.groupby("date").size().reset_index(name="mentions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Enhanced time series chart
            fig = px.line(
                daily, 
                x="date", 
                y="mentions", 
                title="📅 Mentions Over Time",
                color_discrete_sequence=[topic.color]
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=12)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Source distribution (excluding photos)
            source_dist = analytics_df.groupby("source").size().reset_index(name="count")
            source_dist["icon"] = source_dist["source"].map(SOURCE_ICONS)
            source_dist["display"] = source_dist["icon"] + " " + source_dist["source"].str.title()
            
            fig2 = px.pie(
                source_dist, 
                values="count", 
                names="display",
                title="📊 Posts by Source"
            )
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Word cloud (if content exists, excluding photos)
        text = " ".join(analytics_df["content"].astype(str))
        if text.strip():
            with st.expander("☁️ **Word Cloud**", expanded=False):
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

        now = datetime.utcnow()

        def render_post_gallery(row, key_prefix: str, topic=None, is_photo=False) -> None:
            """Render a post in a consistent-height gallery card.
            Cleans any HTML from the content so tags aren't shown while keeping
            the underline and styling intact.
            """
            import html as _html
            import re as _re

            content = clean_content(row["content"])


            # Title from first line of content (shorter for photos)
            max_title_length = 60 if is_photo else 80
            first_line = content.split("\n")[0]
            title_text = (first_line[:max_title_length] + ("..." if len(first_line) > max_title_length else "")).strip()

            # Escape early to prevent HTML from showing
            escaped_title = _html.escape(title_text)
            escaped_source = _html.escape(row["source"].title())
            escaped_age = _html.escape(time_ago(row["posted_at"]))
            subreddit_info = f"r/{row['subreddit']}" if row.get('subreddit') and row["source"] == "reddit" else ""
            escaped_subreddit = (" • " + _html.escape(subreddit_info)) if subreddit_info else ""

            # Underline subject name inside the escaped title (case-insensitive)
            if topic and topic.name:
                subj_escaped = _html.escape(topic.name)
                try:
                    escaped_title = _re.sub(
                        _re.compile(_re.escape(subj_escaped), _re.IGNORECASE),
                        f"<u>{subj_escaped}</u>",
                        escaped_title,
                    )
                except Exception:
                    # Fallback: no underline if anything goes wrong
                    pass

            # Engagement text
            likes = row.get('likes') or 0
            comments = row.get('comments') or 0
            engagement_text = f"❤️ {likes}   💬 {comments}" if (likes or comments) else ""
            escaped_engagement = _html.escape(engagement_text)

            # Content preview (2nd line onwards)
            preview = ""
            if not is_photo:
                remainder = content[len(first_line):].strip() if len(content) > len(first_line) else ""
                if remainder:
                    remainder = remainder[:140] + ("..." if len(remainder) > 140 else "")
                    preview = _html.escape(remainder)

            # Image handling
            has_image = bool(row.get('image_url') and str(row.get('image_url', '')).startswith('http'))
            img_url = _html.escape(str(row.get('image_url', ''))) if has_image else ""

            # Visual config
            source_icon = SOURCE_ICONS.get(row["source"], "📄")
            border_colors = {
                'reddit': '#ff4500',
                'instagram': '#e4405f',
                'facebook': '#1877f2',
                'news': '#0066cc',
                'photos': '#9b59b6',
                'youtube': '#ff0000',
            }
            border_color = border_colors.get(row["source"], '#6c757d')
            title_prefix = "📸 " if is_photo else ("" if row["source"] != "youtube" else "▶️ ")

            # Consistent card height to align squares
            # Slightly taller for photo cards
            min_h = 320 if is_photo else 260

            # Optional image section (kept within the card so the border wraps everything)
            img_block = (
                f'<div style="margin-bottom:10px; text-align:center;">'
                f'<img src="{img_url}" alt="image" style="width:100%; max-height:{160 if is_photo else 120}px; object-fit:cover; border-radius:8px;"/>'
                f"</div>"
            ) if has_image else ""

            # Optional engagement block
            engagement_block = (
                f'<div style="color:#666; font-size:0.9em;">{escaped_engagement}</div>'
            ) if escaped_engagement else ""

            # Content preview block
            preview_block = (
                f'<p style="margin: 8px 0 0 0; color:#555; line-height:1.4;">{preview}</p>'
            ) if preview else ""

            # Build the full card as a single HTML block, escaping all dynamic values
            card_html = f"""
            <div style="
                display:flex; flex-direction:column; justify-content:space-between;
                border:2px solid {border_color}; border-left:6px solid {border_color};
                border-radius:12px; padding:16px; margin:12px 0; min-height:{min_h}px;
                background:linear-gradient(135deg,#ffffff,#f8f9fa);
                box-shadow:0 4px 10px rgba(0,0,0,0.06); font-family:'Segoe UI', sans-serif;
            ">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <div style="font-weight:600; color:#333;">{source_icon} {escaped_source}{escaped_subreddit}</div>
                        <div style="color:#888; font-style:italic; font-size:0.9em;">{escaped_age}</div>
                    </div>
                    <div style="margin:8px 0 6px 0; font-weight:700; font-size:1.06em; color:#222;">
                        {title_prefix}{escaped_title}
                    </div>
                    {img_block}
                    {preview_block}
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; padding-top:10px; border-top:1px solid #eee;">
                    {engagement_block}
                    <a href="{_html.escape(str(row['url']))}" target="_blank" style="
                        color:#007bff; text-decoration:underline; font-weight:500; padding:6px 10px;
                        border:1px solid #007bff; border-radius:6px; transition:all .2s;"
                        onmouseover="this.style.backgroundColor='#007bff'; this.style.color='white'; this.style.textDecoration='none';"
                        onmouseout="this.style.backgroundColor='transparent'; this.style.color='#007bff'; this.style.textDecoration='underline';">
                        🔗 View
                    </a>
                </div>
            </div>
            """

            # Render the card
            st.markdown(card_html, unsafe_allow_html=True)

            # AI Summary button (outside the HTML for Python callback)
            if st.button("🤖 AI Summary", key=key_prefix, help="Generate AI Summary", type="secondary"):
                show_link_summary(str(row["content"]))

        def render_post(row, key_prefix: str, in_columns: bool = False) -> None:
            # Clean the content for display
            import html as _html

            content = clean_content(row["content"])[:200]

            
            age = time_ago(row["posted_at"])
            source_icon = SOURCE_ICONS.get(row["source"], "📄")
            
            # Enhanced post rendering
            is_recent = now - row["posted_at"] <= timedelta(hours=1)
            
            engagement = f"❤️ {row['likes']} 💬 {row['comments']}" if row['likes'] or row['comments'] else ""
            
            # Check if post has an image
            has_image = row.get('image_url') and str(row.get('image_url', '')).startswith('http')
            
            # Use native Streamlit components instead of complex HTML
            with st.container():
                # Create header row
                col_source, col_time = st.columns([4, 1])
                with col_source:
                    st.markdown(f"**{source_icon} {row['source'].title()}**")
                with col_time:
                    st.markdown(f"*{age}*")
                
                # Show image if available
                if has_image:
                    try:
                        st.image(row['image_url'], width=200 if not in_columns else 150)
                    except:
                        st.caption("📷 *Image preview unavailable*")
                
                # Content
                st.markdown(_html.escape(content) + "...")
                
                # Bottom row with engagement and actions
                col_engagement, col_link, col_ai = st.columns([2, 1, 1])
                with col_engagement:
                    if engagement:
                        st.caption(engagement)
                with col_link:
                    st.markdown(f"[🔗 View]({row['url']})")
                with col_ai:
                    if st.button(f"🤖 AI", key=key_prefix, type="secondary"):
                        show_link_summary(str(row["content"]))
                
                # Add separator
                st.markdown("---")

        # Posts sections with tabs
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "🕒 Recent", "📰 News", "🐦 Reddit", "📷 Instagram", "📘 Facebook", "📺 YouTube", "🖼️ Photos", "🤖 AI Summary"
        ])
        
        with tab1:
            st.markdown("### 🕒 **Recent Posts**")
            # Filter out photos and YouTube from recent posts - they should only appear in their dedicated tabs
            recent_df = df[(df["source"] != "photos") & (df["source"] != "youtube")]
            if not recent_df.empty:
                # Gallery view with two columns for better browsing
                recent_items = recent_df.sort_values("posted_at", ascending=False).head(10)
                
                # Create two-column layout
                col1, col2 = st.columns(2)
                
                for idx, (_, row) in enumerate(recent_items.iterrows()):
                    # Alternate between columns
                    current_col = col1 if idx % 2 == 0 else col2
                    
                    with current_col:
                        render_post_gallery(row, f"recent_gallery_{idx}", topic)
            else:
                st.info("No recent posts found. Try collecting data from sources other than photos.")
        
        with tab2:
            news_df = df[df["source"] == "news"]
            if not news_df.empty:
                st.markdown("### 📰 **Latest News Articles**")
                st.markdown(f"Found **{len(news_df)}** news articles")
                
                # Gallery view with two columns for easier browsing
                news_items = news_df.sort_values("posted_at", ascending=False).head(20)
                
                # Create two-column layout
                col1, col2 = st.columns(2)
                
                for idx, (_, row) in enumerate(news_items.iterrows()):
                    # Alternate between columns
                    current_col = col1 if idx % 2 == 0 else col2
                    
                    with current_col:
                        render_post_gallery(row, f"news_gallery_{idx}", topic)
                
                # Show source breakdown
                st.markdown("---")
                st.markdown("**📊 News Sources Summary:**")
                st.write(f"• Total articles: {len(news_df)}")
                st.write(f"• Latest article: {time_ago(news_df['posted_at'].max())}")
                if len(news_df) > 20:
                    st.info(f"Showing latest 20 articles out of {len(news_df)} total.")
            else:
                st.markdown("""
                <div style="text-align: center; padding: 2rem; background: #f8f9fa; border-radius: 15px;">
                    <h4>📰 No news articles found yet</h4>
                    <p>News articles will appear here when data collection finds relevant stories.</p>
                    <p>Make sure to:</p>
                    <ul style="text-align: left; display: inline-block;">
                        <li>Use relevant keywords in your topic</li>
                        <li>Set NEWSAPI_KEY in .env for more sources</li>
                        <li>Check that your topic names match current news topics</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        
        with tab3:
            reddit_df = df[df["source"] == "reddit"]
            if not reddit_df.empty:
                st.markdown("### 👽 **Reddit Posts**")
                
                # Gallery view with two columns
                reddit_items = reddit_df.sort_values("posted_at", ascending=False).head(10)
                
                # Create two-column layout
                col1, col2 = st.columns(2)
                
                for idx, (_, row) in enumerate(reddit_items.iterrows()):
                    # Alternate between columns
                    current_col = col1 if idx % 2 == 0 else col2
                    
                    with current_col:
                        render_post_gallery(row, f"reddit_gallery_{idx}", topic)
            else:
                st.info("No Reddit posts found for this topic.")
        
        with tab4:
            instagram_df = df[df["source"] == "instagram"]
            if not instagram_df.empty:
                st.markdown("### 📷 **Instagram Posts**")
                
                # Gallery view with two columns
                instagram_items = instagram_df.sort_values("posted_at", ascending=False).head(10)
                
                # Create two-column layout
                col1, col2 = st.columns(2)
                
                for idx, (_, row) in enumerate(instagram_items.iterrows()):
                    # Alternate between columns
                    current_col = col1 if idx % 2 == 0 else col2
                    
                    with current_col:
                        render_post_gallery(row, f"instagram_gallery_{idx}", topic)
            else:
                st.info("No Instagram posts found for this topic.")
        
        with tab5:
            facebook_df = df[df["source"] == "facebook"]
            if not facebook_df.empty:
                st.markdown("### 📘 **Facebook Posts**")
                
                # Gallery view with two columns
                facebook_items = facebook_df.sort_values("posted_at", ascending=False).head(10)
                
                # Create two-column layout
                col1, col2 = st.columns(2)
                
                for idx, (_, row) in enumerate(facebook_items.iterrows()):
                    # Alternate between columns
                    current_col = col1 if idx % 2 == 0 else col2
                    
                    with current_col:
                        render_post_gallery(row, f"facebook_gallery_{idx}", topic)
            else:
                st.info("No Facebook posts found for this topic.")
        
        with tab6:
            youtube_df = df[df["source"] == "youtube"]
            if not youtube_df.empty:
                st.markdown("### 📺 **YouTube Videos**")
                
                # Gallery view with two columns
                youtube_items = youtube_df.sort_values("posted_at", ascending=False).head(15)
                
                # Create two-column layout
                col1, col2 = st.columns(2)
                
                for idx, (_, row) in enumerate(youtube_items.iterrows()):
                    # Alternate between columns
                    current_col = col1 if idx % 2 == 0 else col2
                    
                    with current_col:
                        render_post_gallery(row, f"youtube_gallery_{idx}", topic)
            else:
                st.info("No YouTube videos found for this topic.")
        
        with tab7:
            # Photos tab - show all photo content and dedicated photo searches
            photos_df = df[df["source"] == "photos"]
            instagram_photos_df = df[(df["source"] == "instagram") & (df["is_photo"] == True)]
            
            if not photos_df.empty or not instagram_photos_df.empty:
                st.markdown("### 🖼️ **Recent Photos**")
                
                # Combine all photo content
                all_photos = pd.concat([photos_df, instagram_photos_df]) if not photos_df.empty and not instagram_photos_df.empty else (photos_df if not photos_df.empty else instagram_photos_df)
                
                if not all_photos.empty:
                    st.markdown(f"**Found {len(all_photos)} photos**")
                    
                    # Gallery view with two columns
                    col1, col2 = st.columns(2)
                    
                    for idx, (_, row) in enumerate(all_photos.sort_values("posted_at", ascending=False).head(12).iterrows()):
                        # Alternate between columns
                        current_col = col1 if idx % 2 == 0 else col2
                        
                        with current_col:
                            render_post_gallery(row, f"photo_gallery_{idx}", topic, is_photo=True)
                else:
                    st.info("No photos found yet. Try collecting data or add Instagram profiles to get photo content.")
            else:
                st.markdown("""
                <div style="text-align: center; padding: 2rem; background: #ffe6e6; border-radius: 15px; border: 2px solid #ff4444;">
                    <h4>� No Photos Found</h4>
                    <p><strong>To get actual photos of your subjects (Johnny Gosch, Amt Bradley), you need API keys:</strong></p>
                    
                    <div style="background: white; padding: 1rem; border-radius: 8px; margin: 1rem 0; text-align: left;">
                        <h5>🎯 Quick Setup (Free):</h5>
                        <ol>
                            <li><strong>Unsplash</strong>: Go to <a href="https://unsplash.com/developers" target="_blank">unsplash.com/developers</a></li>
                            <li>Create free account → Create new app → Copy "Access Key"</li>
                            <li>Add to .env file: <code>UNSPLASH_ACCESS_KEY=your_key_here</code></li>
                        </ol>
                        <p><em>Alternative:</em> <a href="https://pexels.com/api" target="_blank">Pexels API</a> with <code>PEXELS_API_KEY</code></p>
                    </div>
                    
                    <p>With API keys, you'll get actual photos of the people you're monitoring instead of random images.</p>
                </div>
                """, unsafe_allow_html=True)
        
        with tab8:
            st.markdown("### 🤖 **AI-Generated Summary**")
            with st.spinner("Generating AI summary..."):
                try:
                    # Use regular posts for AI summary, not photos
                    summary_content = analytics_df["content"].head(20).tolist()
                    summary = summarize(summary_content)
                    st.markdown(f"""
                    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 10px; 
                               border-left: 4px solid {topic.color};">
                        {strip_think(summary)}
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Failed to generate summary: {e}")
                    
    else:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; background: #f8f9fa; border-radius: 15px;">
            <h3>📭 No posts collected yet</h3>
            <p>Click "Collect All Topics Now" in the sidebar to start gathering data.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Update last viewed
    topic.last_viewed = datetime.utcnow()
    session.commit()

session.close()

