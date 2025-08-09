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
from monitoring.collectors import collect_topic
from monitoring.scheduler import start_scheduler
from monitoring.summarizer import summarize, strip_think


def time_ago(dt: datetime | None) -> str:
    if not dt:
        return "never"
    diff = datetime.utcnow() - dt
    if diff.days:
        return f"{diff.days}d ago"
    hours = diff.seconds // 3600
    if hours:
        return f"{hours}h ago"
    minutes = diff.seconds // 60
    if minutes:
        return f"{minutes}m ago"
    return f"{diff.seconds}s ago"


SOURCE_ICONS = {
    "twitter": "🐦",
    "reddit": "👽",
    "news": "📰",
    "facebook": "📘",
}


HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
DEFAULT_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def contains_hebrew(text: str) -> bool:
    return bool(HEBREW_RE.search(text))


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

st.set_page_config(page_title="Social & News Monitor", layout="wide")
st.title("\U0001F4F0 Social & News Monitoring Dashboard")

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

if not os.getenv("NEWSAPI_KEY"):
    st.sidebar.warning(
        "NEWSAPI_KEY not set: using Google News RSS. "
        "Get a free key at newsapi.org and add NEWSAPI_KEY to .env to unlock more sources."
    )

try:
    import facebook_scraper  # type: ignore  # noqa: F401
except Exception:
    st.sidebar.info(
        "Facebook scraping requires the `facebook-scraper` package. Install with `pip install \"facebook-scraper[lxml]\" lxml_html_clean` to enable."
    )

if not os.getenv("SMTP_HOST") or not os.getenv("SMTP_USER"):
    st.sidebar.info(
        "Email digests disabled. Set SMTP_HOST, SMTP_PORT, SMTP_USER and SMTP_PASSWORD in .env to enable."
    )

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


# Sidebar for adding topics
st.sidebar.header("Add / Manage Topics")
name = st.sidebar.text_input("Topic or Person")
keywords = st.sidebar.text_input("Keywords (comma separated)")
profiles = st.sidebar.text_input("Profiles or Emails (comma separated)")
color = st.sidebar.color_picker("Color", "#1f77b4")
icon = st.sidebar.text_input("Icon", "📌")

session = SessionLocal()
topic_names = [t.name for t in session.query(Topic).all()]

if st.sidebar.button("Add Topic") and name:
    if name not in topic_names:
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
            st.sidebar.write(f"{icon} {msg}")

        collect_topic(topic, progress=progress, force=True)

remove_choice = st.sidebar.selectbox("Remove Topic", ["None"] + topic_names)
if st.sidebar.button("Delete") and remove_choice != "None":
    to_del = session.query(Topic).filter_by(name=remove_choice).first()
    if to_del:
        session.delete(to_del)
        session.commit()

if st.sidebar.button("Collect Now"):
    errors: list[str] = []
    for t in session.query(Topic).all():
        def progress(msg: str, ic=t.icon):
            st.sidebar.write(f"{ic} {msg}")
        errors.extend(collect_topic(t, progress=progress))
    if errors:
        for err in errors:
            st.sidebar.error(err)
    else:
        st.sidebar.success("Collection finished")

session.close()


# Load topics for main view
session = SessionLocal()
topics = session.query(Topic).all()

if st.session_state.selected_topic is None:
    if not topics:
        st.info("Use the sidebar to add topics to monitor.")
    else:
        cols = st.columns(3)
        for idx, topic in enumerate(topics):
            with cols[idx % 3]:
                st.markdown(
                    f"<div style='background-color:{topic.color}; padding:10px; border-radius:5px'>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"### {topic.icon} {topic.name}")
                posts = (
                    session.query(Post)
                    .filter_by(topic_id=topic.id)
                    .order_by(Post.posted_at.desc())
                    .all()
                )
                if posts:
                    df = pd.DataFrame([{"posted_at": p.posted_at} for p in posts])
                    df["date"] = df["posted_at"].dt.date
                    st.line_chart(df.groupby("date").size(), height=100)
                    new_posts = 0
                    if topic.last_viewed:
                        new_posts = sum(
                            1 for p in posts if p.posted_at > topic.last_viewed
                        )
                    if new_posts:
                        st.markdown(f"**{new_posts} new posts**")
                if st.button("Open", key=f"open_{topic.id}"):
                    st.session_state.selected_topic = topic.id
                st.markdown("</div>", unsafe_allow_html=True)
else:
    topic = session.query(Topic).get(st.session_state.selected_topic)
    if st.button("Return Home"):
        st.session_state.selected_topic = None
    if topic:
        st.markdown(f"## {topic.icon} {topic.name}")
        st.caption(f"Last collected {time_ago(topic.last_collected)}")
        posts = (
            session.query(Post)
            .filter_by(topic_id=topic.id)
            .order_by(Post.posted_at.desc())
            .all()
        )
        if posts:
            df = pd.DataFrame([
                {
                    "content": p.content,
                    "url": p.url,
                    "posted_at": p.posted_at,
                    "source": p.source,
                    "likes": p.likes,
                    "comments": p.comments,
                }
                for p in posts
            ])
            df["date"] = df["posted_at"].dt.date
            daily = df.groupby("date").size().reset_index(name="mentions")
            fig = px.line(daily, x="date", y="mentions", title="Mentions Over Time")
            text = " ".join(df["content"].astype(str))
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig, use_container_width=True)
            if text.strip():
                font = str(DEFAULT_FONT) if DEFAULT_FONT.exists() else None
                wc = WordCloud(
                    width=800,
                    height=400,
                    background_color="white",
                    max_words=20,
                    font_path=font,
                ).generate(text)
                with col2:
                    st.image(wc.to_array(), use_column_width=True)

            now = datetime.utcnow()

            def render_post(row, key_prefix: str) -> None:
                content = strip_think(str(row["content"]))
                age = time_ago(row["posted_at"])
                ic = SOURCE_ICONS.get(row["source"], "")
                cols = st.columns([0.9, 0.1])
                with cols[0]:
                    if contains_hebrew(content):
                        link_html = f"<a href='{row['url']}'>{content[:100]}...</a>"
                        if now - row["posted_at"] <= timedelta(hours=1):
                            link_html = f"<strong>{link_html}</strong>"
                        line = (
                            f"&bull; {ic} {link_html} <em>({row['source']}, {age})</em>"
                        )
                        st.markdown(
                            f"<div dir='rtl'>{line}</div>", unsafe_allow_html=True
                        )
                    else:
                        link = f"[{content[:100]}...]({row['url']})"
                        if now - row["posted_at"] <= timedelta(hours=1):
                            link = f"**{link}**"
                        st.markdown(f"- {ic} {link} _({row['source']}, {age})_")
                with cols[1]:
                    if st.button("AI", key=key_prefix):
                        show_link_summary(str(row["content"]))

            st.subheader("Recent Posts")
            for idx, row in (
                df.sort_values("posted_at", ascending=False).head(5).iterrows()
            ):
                render_post(row, f"recent_{idx}")

            reddit_df = df[df["source"] == "reddit"]
            if not reddit_df.empty:
                st.subheader("Newest Reddit Post")
                for idx, row in (
                    reddit_df.sort_values("posted_at", ascending=False)
                    .head(1)
                    .iterrows()
                ):
                    render_post(row, f"reddit_new_{idx}")
                st.subheader("Hot Reddit Posts")
                for idx, row in (
                    reddit_df.sort_values("likes", ascending=False)
                    .head(5)
                    .iterrows()
                ):
                    render_post(row, f"reddit_hot_{idx}")

            st.subheader("AI Summary")
            st.write(strip_think(summarize(df["content"].head(20).tolist())))
        else:
            st.write("No posts collected yet.")
        topic.last_viewed = datetime.utcnow()
        session.commit()

session.close()

