import streamlit as st
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud

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

# Sidebar for adding topics
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
    for t in topics:
        collect_topic(t)
    session.close()
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
