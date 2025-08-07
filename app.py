import os

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
from monitoring.summarizer import summarize

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

try:
    import instaloader  # type: ignore  # noqa: F401
except Exception:
    st.sidebar.info(
        "Instagram scraping requires the `instaloader` package. Install with `pip install instaloader` to enable."
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

# Sidebar for data source toggles and adding topics
st.sidebar.header("Data Sources")
enable_twitter = st.sidebar.checkbox(
    "Twitter", value=os.getenv("ENABLE_TWITTER", "1") == "1"
)
enable_reddit = st.sidebar.checkbox(
    "Reddit", value=os.getenv("ENABLE_REDDIT", "1") == "1"
)
enable_news = st.sidebar.checkbox(
    "News", value=os.getenv("ENABLE_NEWS", "1") == "1"
)
enable_facebook = st.sidebar.checkbox(
    "Facebook", value=os.getenv("ENABLE_FACEBOOK", "1") == "1"
)
enable_instagram = st.sidebar.checkbox(
    "Instagram", value=os.getenv("ENABLE_INSTAGRAM", "1") == "1"
)

os.environ["ENABLE_TWITTER"] = "1" if enable_twitter else "0"
os.environ["ENABLE_REDDIT"] = "1" if enable_reddit else "0"
os.environ["ENABLE_NEWS"] = "1" if enable_news else "0"
os.environ["ENABLE_FACEBOOK"] = "1" if enable_facebook else "0"
os.environ["ENABLE_INSTAGRAM"] = "1" if enable_instagram else "0"

st.sidebar.header("Add / Manage Topics")
name = st.sidebar.text_input("Topic or Person")
keywords = st.sidebar.text_input("Keywords (comma separated)")
profiles = st.sidebar.text_input("Profiles or Emails (comma separated)")
if st.sidebar.button("Add Topic") and name:
    session = SessionLocal()
    if not session.query(Topic).filter_by(name=name).first():
        session.add(Topic(name=name, keywords=keywords, profiles=profiles))
        session.commit()
    session.close()

if st.sidebar.button("Collect Now"):
    session = SessionLocal()
    topics = session.query(Topic).all()
    errors = []
    for t in topics:
        errors.extend(collect_topic(t))
    session.close()
    if errors:
        for err in errors:
            st.sidebar.error(err)
    else:
        st.sidebar.success("Collection finished")

session = SessionLocal()
topics = session.query(Topic).all()
if not topics:
    st.info("Use the sidebar to add topics to monitor.")

for topic in topics:
    st.markdown(f"## {topic.name}")
    posts = session.query(Post).filter_by(topic_id=topic.id).order_by(Post.posted_at.desc()).all()
    if posts:
        df = pd.DataFrame([
            {
                'content': p.content,
                'url': p.url,
                'posted_at': p.posted_at,
                'source': p.source,
                'likes': p.likes,
                'comments': p.comments,
            } for p in posts
        ])
        df['date'] = df['posted_at'].dt.date
        daily = df.groupby('date').size().reset_index(name='mentions')
        fig = px.line(daily, x='date', y='mentions', title='Mentions Over Time')
        st.plotly_chart(fig, use_container_width=True)

        text = " ".join(df['content'].astype(str))
        if text.strip():
            wc = WordCloud(width=800, height=400, background_color='white').generate(text)
            st.image(wc.to_array(), use_column_width=True)

        st.subheader("Recent Posts")
        for _, row in df.sort_values('posted_at', ascending=False).head(5).iterrows():
            st.markdown(f"- [{row['content'][:100]}...]({row['url']})")

        st.subheader("AI Summary")
        st.write(summarize(df['content'].head(20).tolist()))
    else:
        st.write("No posts collected yet.")

session.close()
