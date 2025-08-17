"""Main views for the application - overview and topic detail views."""

import streamlit as st
import pandas as pd
import html as py_html
from datetime import datetime
from textwrap import dedent
from streamlit.components.v1 import html as st_html

from .layout import render_welcome_screen, render_metrics_summary, render_topic_header
from .charts import create_time_series_chart, create_source_distribution_chart, create_mini_analytics_chart, create_word_cloud, create_source_badges, create_trending_keywords_chart, create_keyword_momentum_chart
from .cards import render_news_card, render_reddit_card, render_facebook_card, render_youtube_card, render_instagram_card, render_card
from .utils import time_ago, clean_content, _first
from monitoring.summarizer import summarize, strip_think


def render_overview_page(topics, session, Post, current_user_id: int):
    """Render the main overview page with topic cards."""
    # Filter topics by current user
    user_topics = [t for t in topics if t.user_id == current_user_id]
    
    # Only show welcome screen for new users without topics
    if not user_topics:
        render_welcome_screen()
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1rem;">
            <h2 style="color: #666;">🎯 Ready to start tracking?</h2>
            <p style="font-size: 1.1rem; color: #888; margin: 1rem 0 2rem 0;">
                Create your first topic to begin monitoring news and social media
            </p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Render topics grid
    render_metrics_summary(user_topics, session, Post)
    
    st.markdown("---")
    
    # Topic cards in responsive grid layout - always create 3 columns for proper sizing
    if user_topics:
        cols = st.columns(3)  # Always create 3 columns for consistent card sizing
        for idx, topic in enumerate(user_topics):
            # Use modulo to wrap to next row after 3 cards
            col_idx = idx % 3
            with cols[col_idx]:
                posts = (
                    session.query(Post)
                    .filter_by(topic_id=topic.id)
                    .order_by(Post.posted_at.desc())
                    .all()
                )
                
                new_posts_count = 0
                if topic.last_viewed and posts:
                    new_posts_count = sum(1 for p in posts if p.posted_at > topic.last_viewed)
                
                # Enhanced Apple-style topic card
                st_html(dedent(f"""
            <div style="
                background: #FFFFFF;
                border-radius: 20px;
                padding: 2rem 1.5rem;
                margin: 1rem 0;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
                transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                border: 1px solid #E5E5EA;
                position: relative;
                overflow: visible;
            ">
                <div style="
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: linear-gradient(90deg, {topic.color}, {topic.color}99);
                "></div>
                
                <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
                    <span style="font-size: 2.5rem; margin-right: 1rem;">{topic.icon}</span>
                    <div>
                        <h3 style="
                            margin: 0; 
                            color: {topic.color}; 
                            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                            font-weight: 600;
                            font-size: 1.25rem;
                            letter-spacing: -0.01em;
                        ">{topic.name.title()}</h3>
                        <p style="
                            margin: 0.25rem 0 0 0; 
                            font-size: 0.9rem; 
                            color: #8E8E93;
                            font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                            font-weight: 500;
                        ">
                            {len(posts)} posts • Last: {time_ago(topic.last_collected)}
                        </p>
                    </div>
                </div>
                
                <div style="
                    background: #F2F2F7;
                    border-radius: 12px;
                    padding: 1rem;
                    margin-bottom: 1rem;
                    border: 1px solid #E5E5EA;
                ">
                    <p style="
                        margin: 0;
                        font-size: 0.85rem;
                        color: #3A3A3C;
                        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                    ">
                        <strong>Keywords:</strong> {topic.keywords or "None specified"}<br>
                        <strong>Profiles:</strong> {len(topic.profiles.split(',')) if topic.profiles else 0} monitored
                    </p>
                </div>
            </div>
            """), height=200)
                
                if posts:
                    # Mini analytics chart with consistent styling
                    create_mini_analytics_chart(posts, topic.color)
                    
                    # Source breakdown with enhanced badges
                    source_badges = create_source_badges(posts)
                    st_html(source_badges, height=50)
                    
                    if new_posts_count > 0:
                        st_html(dedent(f"""
                        <div style="
                            background: linear-gradient(135deg, #34C759, #30B050); 
                            color: white; 
                            padding: 0.75rem; 
                            border-radius: 12px; 
                            text-align: center; 
                            margin: 0.5rem 0;
                            font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                            font-weight: 600;
                            box-shadow: 0 4px 15px rgba(52, 199, 89, 0.3);
                        ">
                            🔔 {new_posts_count} new posts!
                        </div>
                        """), height=60)
                    else:
                        st_html(dedent("""
                        <div style="
                            background: linear-gradient(135deg, #E5E5EA, #D1D1D6); 
                            color: #3A3A3C; 
                            padding: 0.75rem; 
                            border-radius: 12px; 
                            text-align: center; 
                            margin: 0.5rem 0;
                            font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                            font-weight: 600;
                            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                        ">
                            📭 No new posts
                        </div>
                        """), height=60)
                else:
                    st.info("No posts collected yet")
                
                # Apple-style explore button
                if st.button("🔍 **Explore**", key=f"open_{topic.id}", use_container_width=True, type="primary"):
                    st.session_state.selected_topic = topic.id
                    st.rerun()
            
            # Create new row of columns after every 3 cards
            if (idx + 1) % 3 == 0 and idx + 1 < len(user_topics):
                cols = st.columns(3)


def render_topic_detail_page(topic, session, Post):
    """Render the detailed view for a specific topic."""
    # Render topic header
    render_topic_header(topic)

    # Render home button
    col_left, col_right = st.columns([6, 1])
    with col_right:
        if st.button("🏠 Home", key="go_home", use_container_width=True):
            st.session_state.selected_topic = None
            st.rerun()

    posts = (
        session.query(Post)
        .filter_by(topic_id=topic.id)
        .order_by(Post.posted_at.desc())
        .all()
    )
    
    if not posts:
        st_html(dedent("""
        <div style="text-align: center; padding: 3rem; background: #f8f9fa; border-radius: 15px;">
            <h3>📭 No posts collected yet</h3>
            <p>Click "Collect My Topics Now" in the sidebar to start gathering data.</p>
        </div>
        """), height=200)
        return

    df = pd.DataFrame([
        {
            "title": p.title,
            "content": clean_content(p.content),
            "url": p.url,
            "posted_at": p.posted_at,
            "source": p.source,
            "likes": p.likes,
            "comments": p.comments,
            "image_url": getattr(p, 'image_url', None),
            "is_photo": getattr(p, 'is_photo', False),
            "subreddit": getattr(p, 'subreddit', None),
        }
        for p in posts
    ])

    # Enhanced metrics section
    col1, col2, col3, col4 = st.columns(4)
    
    # Separate regular posts from photos
    regular_posts_df = df[df["source"] != "photos"]
    photos_df = df[df["source"] == "photos"]
    
    with col1:
        st.metric(
            label="📊 Total Posts", 
            value=f"{len(regular_posts_df):,}", 
            help="Excludes photos (shown separately)"
        )
    with col2:
        total_likes = regular_posts_df['likes'].sum()
        st.metric(
            label="❤️ Total Likes", 
            value=f"{total_likes:,}"
        )
    with col3:
        total_comments = regular_posts_df['comments'].sum()
        st.metric(
            label="💬 Total Comments", 
            value=f"{total_comments:,}"
        )
    with col4:
        photos_count = len(photos_df)
        st.metric(
            label="🖼️ Photos Found", 
            value=f"{photos_count:,}", 
            help="Images found from web search"
        )
    
    # Analytics section (excluding photos)
    st.markdown('<h2 class="section-heading">📈 Analytics</h2>', unsafe_allow_html=True)
    
    analytics_df = regular_posts_df.copy()
    analytics_df["date"] = analytics_df["posted_at"].dt.date
    
    col1, col2 = st.columns(2)
    
    with col1:
        create_time_series_chart(analytics_df, topic.color)
    
    with col2:
        create_source_distribution_chart(analytics_df)
    
    # Word cloud
    text = " ".join(analytics_df["content"].astype(str))
    if text.strip():
        with st.expander("☁️ **Word Cloud**", expanded=False):
            create_word_cloud(text)

    # Posts sections with tabs
    render_posts_tabs(df, topic)
    
    # Update last viewed
    topic.last_viewed = datetime.utcnow()
    session.commit()


def render_posts_tabs(df, topic):
    """Render the tabbed interface for different post types."""
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "🕒 Recent", "📰 News", "🐦 Reddit", "📷 Instagram", "📘 Facebook", "📺 YouTube", "🖼️ Photos", "🐦 Tweets", "📊 Analytics"
    ])
    
    with tab1:
        render_recent_posts_tab(df, topic)
    
    with tab2:
        render_news_tab(df)
    
    with tab3:
        render_reddit_tab(df)
    
    with tab4:
        render_instagram_tab(df)
    
    with tab5:
        render_facebook_tab(df)
    
    with tab6:
        render_youtube_tab(df)
    
    with tab7:
        render_photos_tab(df)
    
    with tab8:
        render_tweets_tab(df)
    
    with tab9:
        render_analytics_tab(df, topic)


def render_recent_posts_tab(df, topic):
    """Render the recent posts tab."""
    st.markdown('<h3 class="section-heading">🕒 Recent Posts</h3>', unsafe_allow_html=True)
    recent_df = df[(df["source"] != "photos") & (df["source"] != "youtube")]
    
    def _source_rank(s):
        if s in ("news", "reddit"): return 0
        elif s == "instagram": return 1
        elif s == "facebook": return 2
        elif s == "twitter": return 3
        return 4
    
    recent_df["_source_order"] = recent_df["source"].apply(_source_rank)
    recent_df = recent_df.sort_values(["_source_order", "posted_at"], ascending=[True, False])
    
    if not recent_df.empty:
        recent_items = recent_df.head(10)
        col1, col2 = st.columns(2)
        for idx, (_, row) in enumerate(recent_items.iterrows()):
            current_col = col1 if idx % 2 == 0 else col2
            with current_col:
                if row["source"] == "news":
                    render_news_card(row)
                elif row["source"] == "reddit":
                    render_reddit_card(row)
                elif row["source"] == "facebook":
                    render_facebook_card(row)
                elif row["source"] == "instagram":
                    render_instagram_card(row)
                elif row["source"] == "twitter":
                    render_twitter_card(row)
                else:
                    render_generic_card(row, topic)
    else:
        st.info("No recent posts found. Try collecting data from sources other than photos.")


def render_news_tab(df):
    """Render the news tab."""
    news_df = df[df["source"] == "news"]
    if not news_df.empty:
        st.markdown('<h3 class="section-heading">📰 Latest News Articles</h3>', unsafe_allow_html=True)
        st.markdown(f"Found **{len(news_df)}** news articles")
        
        news_items = news_df.sort_values("posted_at", ascending=False).head(20)
        col1, col2 = st.columns(2)
        
        for idx, (_, row) in enumerate(news_items.iterrows()):
            current_col = col1 if idx % 2 == 0 else col2
            with current_col:
                render_news_card(row)
        
        st.markdown("---")
        st.markdown("**📊 News Sources Summary:**")
        st.write(f"• Total articles: {len(news_df)}")
        st.write(f"• Latest article: {time_ago(news_df['posted_at'].max())}")
        if len(news_df) > 20:
            st.info(f"Showing latest 20 articles out of {len(news_df)} total.")
    else:
        render_no_content_message("news")


def render_reddit_tab(df):
    """Render the Reddit tab."""
    reddit_df = df[df["source"] == "reddit"]
    if not reddit_df.empty:
        st.markdown('<h3 class="section-heading">👽 Reddit Posts</h3>', unsafe_allow_html=True)
        
        reddit_items = reddit_df.sort_values("posted_at", ascending=False).head(10)
        col1, col2 = st.columns(2)
        
        for idx, (_, row) in enumerate(reddit_items.iterrows()):
            current_col = col1 if idx % 2 == 0 else col2
            with current_col:
                render_reddit_card(row)
    else:
        st.info("No Reddit posts found for this topic.")


def render_instagram_tab(df):
    """Render the Instagram tab."""
    instagram_df = df[df["source"] == "instagram"]
    if not instagram_df.empty:
        st.markdown('<h3 class="section-heading">📷 Instagram Posts</h3>', unsafe_allow_html=True)
        
        instagram_items = instagram_df.sort_values("posted_at", ascending=False).head(10)
        col1, col2 = st.columns(2)
        
        for idx, (_, row) in enumerate(instagram_items.iterrows()):
            current_col = col1 if idx % 2 == 0 else col2
            with current_col:
                render_instagram_card(row)
    else:
        st.info("No Instagram posts found for this topic.")


def render_facebook_tab(df):
    """Render the Facebook tab."""
    facebook_df = df[df["source"] == "facebook"]
    if not facebook_df.empty:
        st.markdown('<h3 class="section-heading">📘 Facebook Posts</h3>', unsafe_allow_html=True)
        
        facebook_items = facebook_df.sort_values("posted_at", ascending=False).head(10)
        col1, col2 = st.columns(2)
        
        for idx, (_, row) in enumerate(facebook_items.iterrows()):
            current_col = col1 if idx % 2 == 0 else col2
            with current_col:
                render_facebook_card(row)
    else:
        st.info("No Facebook posts found for this topic.")


def render_youtube_tab(df):
    """Render the YouTube tab."""
    youtube_df = df[df["source"] == "youtube"]
    if not youtube_df.empty:
        st.markdown('<h3 class="section-heading">📺 YouTube Videos</h3>', unsafe_allow_html=True)
        
        youtube_items = youtube_df.sort_values("posted_at", ascending=False).head(15)
        col1, col2 = st.columns(2)
        
        for idx, (_, row) in enumerate(youtube_items.iterrows()):
            current_col = col1 if idx % 2 == 0 else col2
            with current_col:
                render_youtube_card(row)
    else:
        st.info("No YouTube videos found for this topic.")


def render_photos_tab(df):
    """Render the Photos tab."""
    photos_df = df[df["source"] == "photos"]
    instagram_photos_df = df[(df["source"] == "instagram") & (df["is_photo"] == True)]
    
    if not photos_df.empty or not instagram_photos_df.empty:
        st.markdown('<h3 class="section-heading">🖼️ Recent Photos</h3>', unsafe_allow_html=True)
        all_photos = pd.concat([photos_df, instagram_photos_df]) if not photos_df.empty and not instagram_photos_df.empty else (photos_df if not photos_df.empty else instagram_photos_df)
        
        if not all_photos.empty:
            st.markdown(f"**Found {len(all_photos)} photos**")
            col1, col2 = st.columns(2)
            for idx, (_, row) in enumerate(all_photos.sort_values("posted_at", ascending=False).head(12).iterrows()):
                current_col = col1 if idx % 2 == 0 else col2
                with current_col:
                    render_instagram_card(row)
        else:
            st.info("No photos found yet. Try collecting data or add Instagram profiles to get photo content.")
    else:
        render_photo_setup_message()


def render_tweets_tab(df):
    """Render the Tweets tab."""
    st.markdown('<h3 class="section-heading">🐦 Tweets (via Nitter)</h3>', unsafe_allow_html=True)
    tweets_df = df[df["source"] == "twitter"]
    
    if not tweets_df.empty:
        for _, tweet in tweets_df.iterrows():
            render_twitter_card(tweet)
    else:
        st.info("No tweets found for this topic.")


def render_analytics_tab(df, topic=None):
    """Render the Analytics tab with trending keywords and AI summary."""
    st.markdown('<h3 class="section-heading">📊 Analytics & Insights</h3>', unsafe_allow_html=True)
    
    # Use regular posts for analysis, not photos
    analytics_df = df[df["source"] != "photos"]
    
    if len(analytics_df) == 0:
        st.info("📭 No data available for analytics")
        return
    
    # Convert DataFrame to list of dictionaries for trending analysis
    posts_data = []
    for _, row in analytics_df.iterrows():
        posts_data.append({
            'content': row.get('content', ''),
            'posted_at': pd.to_datetime(row['posted_at']) if row.get('posted_at') else datetime.now(),
            'source': row.get('source', ''),
            'url': row.get('url', ''),
            'likes': row.get('likes', 0)
        })
    
    # Time window selector
    col1, col2 = st.columns([2, 2])
    with col1:
        time_window = st.selectbox(
            "📅 Analysis Period",
            [7, 14, 30],
            format_func=lambda x: f"Last {x} days",
            index=0
        )
    with col2:
        max_terms = st.selectbox(
            "📝 Terms to Show",
            [3, 5, 8],
            format_func=lambda x: f"Top {x}",
            index=1  # Default to 5
        )
    
    st.markdown("### 🔥 Trending Keywords & Hashtags (Last 3 Months)")
    
    # Create trending keywords chart
    try:
        # Get color safely - SharedTopic objects don't have color attribute
        chart_color = getattr(topic, 'color', "#007AFF") if topic else "#007AFF"
        create_trending_keywords_chart(posts_data, chart_color, time_window, max_terms)
    except Exception as e:
        st.warning(f"⚠️ Could not analyze keywords: {e}")
        st.info("💡 This might be due to missing text analysis libraries. Install nltk for better keyword extraction.")
    
    # Keyword momentum chart
    st.markdown("---")
    st.markdown("### 🚀 Keyword Momentum")
    try:
        # Get color safely - SharedTopic objects don't have color attribute
        chart_color = getattr(topic, 'color', "#007AFF") if topic else "#007AFF"
        create_keyword_momentum_chart(posts_data, chart_color)
    except Exception as e:
        st.warning(f"⚠️ Could not create momentum chart: {e}")
    
    # AI Summary section
    st.markdown("---")
    st.markdown("### 🤖 AI-Generated Summary")
    
    with st.spinner("Generating AI summary..."):
        try:
            summary_content = analytics_df["content"].head(20).tolist()
            summary_text = strip_think(summarize(summary_content)).strip()

            summary_html_body, line_count = _to_bulleted_html(summary_text)
            computed_height = 180 + line_count * 30
            
            # Get color safely - SharedTopic objects don't have color attribute
            border_color = getattr(topic, 'color', "#007AFF") if topic else "#007AFF"

            st_html(dedent(f"""
            <div style="
                background: #f8f9fa; 
                padding: 1.5rem; 
                border-radius: 10px; 
                border-left: 4px solid {border_color};
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                color: #1C1C1E;
                line-height: 1.8;
                font-size: 18px;
                min-height: 220px;
                max-height: 700px;
                overflow-y: auto;
            ">
                <div style="font-family: inherit; color: inherit;">
                    {summary_html_body}
                </div>
            </div>
            """), height=max(computed_height, 220))
        except Exception as e:
            st.error(f"Failed to generate summary: {e}")


def render_twitter_card(tweet):
    """Render a Twitter card."""
    st.markdown(f"""
        <div style='background:rgba(255,255,255,0.7);border-radius:12px;padding:1rem;margin-bottom:1rem;box-shadow:0 2px 8px #0001;'>
            <div style='font-size:1.1rem;line-height:1.5;'>{py_html.escape(tweet.get('text', tweet.get('content', '')))}</div>
            <div style='margin-top:0.5rem;font-size:0.9rem;color:#888;'>
                <a href='{tweet.get('url','')}' target='_blank'>View on Nitter</a> · {tweet.get('author','')} · {time_ago(tweet['posted_at'] if 'posted_at' in tweet else tweet.get('created_at'))}
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_generic_card(row, topic):
    """Render a generic card for unknown source types."""
    title = _first(row.get("title", ""), row.get("content", "")[:80])
    summary = _first(row.get("summary", ""), row.get("content", ""))
    image = row.get("image_url", "")
    link = row.get("url", "")
    age = time_ago(row["posted_at"] if "posted_at" in row else row.get("created_at"))
    source_name = row["source"].title()
    render_card(title, summary, image, age, link, badge=source_name, topic_name=topic.name.title())


def render_no_content_message(content_type):
    """Render a message when no content is found."""
    messages = {
        "news": {
            "title": "📰 No news articles found yet",
            "content": "News articles will appear here when data collection finds relevant stories.",
            "tips": [
                "Use relevant keywords in your topic",
                "Set NEWSAPI_KEY in .env for more sources", 
                "Check that your topic names match current news topics"
            ]
        }
    }
    
    message = messages.get(content_type, {
        "title": f"No {content_type} content found yet",
        "content": f"{content_type.title()} content will appear here when available.",
        "tips": ["Try collecting data or adjusting your topic keywords"]
    })
    
    tips_html = "\n".join([f"<li>{tip}</li>" for tip in message["tips"]])
    
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem; background: #f8f9fa; border-radius: 15px;">
        <h4>{message['title']}</h4>
        <p>{message['content']}</p>
        <p>Make sure to:</p>
        <ul style="text-align: left; display: inline-block;">
            {tips_html}
        </ul>
    </div>
    """, unsafe_allow_html=True)


def render_photo_setup_message():
    """Render the photo setup message when no photos are found."""
    st_html(dedent("""
    <div style="text-align: center; padding: 2rem; background: #ffe6e6; border-radius: 15px; border: 2px solid #ff4444;">
        <h4>🖼️ No Photos Found</h4>
        <p><strong>To get actual photos of your subjects, you need API keys:</strong></p>
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
    """), height=350)


def _to_bulleted_html(text: str) -> tuple[str, int]:
    """Convert text with bullets to HTML format and return line count."""
    import re
    
    split_text = []
    for line in (text or "").splitlines():
        parts = [p for p in line.split(" - ")]
        if parts[0].strip():
            split_text.append(parts[0].strip())
        for part in parts[1:]:
            if part.strip():
                split_text.append("- " + part.strip())

    lines = split_text
    parts: list[str] = []
    in_list = False
    non_empty_line_count = 0

    start_bullet_re = re.compile(r'^\s*[-\*\u2022]\s+')

    def close_list():
        nonlocal in_list
        if in_list:
            parts.append("</ul>")
            in_list = False

    for raw in lines:
        line = raw.rstrip("\r").strip()
        if not line:
            close_list()
            parts.append('<div style="height: 0.5rem;"></div>')
            continue

        if start_bullet_re.match(line):
            if not in_list:
                parts.append('<ul style="margin: 0.75rem 0; padding-left: 1.5rem; list-style-position: outside;">')
                in_list = True
            item = start_bullet_re.sub('', line).strip()
            if item:
                parts.append(f'<li style="margin-bottom: 0.5rem;">{py_html.escape(item)}</li>')
                non_empty_line_count += 1
            continue

        if not start_bullet_re.match(line):
            close_list()
            parts.append(f'<p style="margin: 0 0 0.5rem 0;">{py_html.escape(line)}</p>')
            non_empty_line_count += 1
            continue

        close_list()
        parts.append(f'<p style="margin: 0 0 0.5rem 0;">{py_html.escape(line)}</p>')
        non_empty_line_count += 1

    close_list()
    html = "".join(parts) if parts else f"<p>{py_html.escape(text)}</p>"
    return html, non_empty_line_count
