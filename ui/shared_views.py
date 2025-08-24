"""Shared topic views - UI components for shared topic system."""

import streamlit as st
import pandas as pd
import time
from datetime import datetime
from typing import List, Dict, Any
from streamlit.components.v1 import html as st_html
from textwrap import dedent

from monitoring.shared_topics import (
    get_user_subscriptions,
    get_shared_topic_posts,
    unsubscribe_user_from_topic
)
from monitoring.database import SessionLocal
from ui.layout import render_welcome_screen, render_metrics_summary
from ui.cards import render_card
from ui.utils import time_ago


def render_shared_overview_page(current_user_id: int):
    """Render the main overview page with shared topic subscriptions."""
    
    session = SessionLocal()
    try:
        # Get user's topic subscriptions
        user_subscriptions = get_user_subscriptions(session, current_user_id)
        
        # Only show welcome screen for new users without topics
        if not user_subscriptions:
            render_welcome_screen()
            st.markdown("""
            <div style="text-align: center; padding: 3rem 1rem;">
                <h2 style="color: #666;">🎯 Ready to start tracking?</h2>
                <p style="font-size: 1.1rem; color: #888; margin: 1rem 0 2rem 0;">
                    Subscribe to topics or create new ones to begin monitoring news and social media
                </p>
            </div>
            """, unsafe_allow_html=True)
            return
        
        # Render shared topics metrics
        render_shared_metrics_summary(user_subscriptions, session)
        
        st.markdown("---")
        
        # Topic cards in responsive grid layout - always create 3 columns for proper sizing
        if user_subscriptions:
            cols = st.columns(3)  # Always create 3 columns for consistent card sizing
            for idx, subscription in enumerate(user_subscriptions):
                # Use modulo to wrap to next row after 3 cards
                col_idx = idx % 3
                with cols[col_idx]:
                    render_shared_topic_card(subscription, session)
                    
                # Create new row of columns after every 3 cards
                if (idx + 1) % 3 == 0 and idx + 1 < len(user_subscriptions):
                    cols = st.columns(3)
    
    finally:
        session.close()


def render_shared_metrics_summary(subscriptions: List[Dict], session):
    """Render enhanced metrics summary for shared subscriptions with custom cards."""
    from streamlit.components.v1 import html as st_html
    from textwrap import dedent
    from datetime import datetime
    
    total_posts = sum(sub['posts_count'] for sub in subscriptions)
    total_topics = len(subscriptions)
    
    # Calculate recent activity (last 24 hours)
    recent_posts = 0
    
    # Calculate additional metrics
    most_active_topic = None
    avg_posts_per_topic = round(total_posts / total_topics if total_topics > 0 else 0, 1)
    topics_with_posts = len([sub for sub in subscriptions if sub['posts_count'] > 0])
    topics_updated_today = len([sub for sub in subscriptions if sub.get('last_collected') and 
                               (datetime.now() - sub['last_collected']).days < 1]) if subscriptions else 0
    
    if subscriptions:
        most_active = max(subscriptions, key=lambda x: x['posts_count'])
        most_active_topic = most_active['name']
        most_active_count = most_active['posts_count']
    else:
        most_active_count = 0
    
    # Use custom card design with 6 metrics in wider layout
    st_html(dedent(f"""
    <div style="
        display: flex;
        justify-content: center;
        gap: 0.8rem;
        margin: 2rem 0;
        flex-wrap: wrap;
        padding: 0 0.5rem;
        max-width: 1200px;
        margin-left: auto;
        margin-right: auto;
    ">
        <!-- Total Topics Card -->
        <div style="
            background: #fff;
            border-radius: 14px;
            padding: 1.2rem;
            box-shadow: 0 3px 15px rgba(0, 0, 0, 0.06);
            border: 1px solid #E5E5EA;
            text-align: center;
            min-width: 120px;
            flex: 1;
            max-width: 160px;
            position: relative;
        ">
            <div style="
                width: 36px;
                height: 36px;
                background: linear-gradient(135deg, #007AFF, #5856D6);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 0.8rem auto;
                color: white;
                font-size: 1.1rem;
                font-weight: 600;
            ">📊</div>
            <div style="
                font-size: 1.8rem;
                font-weight: 700;
                color: #1C1C1E;
                margin-bottom: 0.2rem;
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">{total_topics}</div>
            <div style="
                font-size: 0.8rem;
                color: #8E8E93;
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">Total Topics</div>
        </div>
        
        <!-- Total Posts Card -->
        <div style="
            background: #fff;
            border-radius: 14px;
            padding: 1.2rem;
            box-shadow: 0 3px 15px rgba(0, 0, 0, 0.06);
            border: 1px solid #E5E5EA;
            text-align: center;
            min-width: 120px;
            flex: 1;
            max-width: 160px;
            position: relative;
        ">
            <div style="
                width: 36px;
                height: 36px;
                background: linear-gradient(135deg, #34C759, #30B050);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 0.8rem auto;
                color: white;
                font-size: 1.1rem;
                font-weight: 600;
            ">📰</div>
            <div style="
                font-size: 1.8rem;
                font-weight: 700;
                color: #1C1C1E;
                margin-bottom: 0.2rem;
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">{total_posts:,}</div>
            <div style="
                font-size: 0.8rem;
                color: #8E8E93;
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">Total Posts</div>
        </div>
        
        <!-- Average Posts Per Topic Card -->
        <div style="
            background: #fff;
            border-radius: 14px;
            padding: 1.2rem;
            box-shadow: 0 3px 15px rgba(0, 0, 0, 0.06);
            border: 1px solid #E5E5EA;
            text-align: center;
            min-width: 120px;
            flex: 1;
            max-width: 160px;
            position: relative;
        ">
            <div style="
                width: 36px;
                height: 36px;
                background: linear-gradient(135deg, #FF9500, #FF7A00);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 0.8rem auto;
                color: white;
                font-size: 1.1rem;
                font-weight: 600;
            ">�</div>
            <div style="
                font-size: 1.8rem;
                font-weight: 700;
                color: #1C1C1E;
                margin-bottom: 0.2rem;
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">{avg_posts_per_topic}</div>
            <div style="
                font-size: 0.8rem;
                color: #8E8E93;
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">Avg Posts/Topic</div>
        </div>
        
        <!-- Active Topics Card -->
        <div style="
            background: #fff;
            border-radius: 14px;
            padding: 1.2rem;
            box-shadow: 0 3px 15px rgba(0, 0, 0, 0.06);
            border: 1px solid #E5E5EA;
            text-align: center;
            min-width: 120px;
            flex: 1;
            max-width: 160px;
            position: relative;
        ">
            <div style="
                width: 36px;
                height: 36px;
                background: linear-gradient(135deg, #2563EB, #1D4ED8);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 0.8rem auto;
                color: white;
                font-size: 1.1rem;
                font-weight: 600;
            ">🎯</div>
            <div style="
                font-size: 1.8rem;
                font-weight: 700;
                color: #1C1C1E;
                margin-bottom: 0.2rem;
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">{topics_with_posts}</div>
            <div style="
                font-size: 0.8rem;
                color: #8E8E93;
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">Active Topics</div>
        </div>
        
        <!-- Topics Updated Today Card -->
        <div style="
            background: #fff;
            border-radius: 14px;
            padding: 1.2rem;
            box-shadow: 0 3px 15px rgba(0, 0, 0, 0.06);
            border: 1px solid #E5E5EA;
            text-align: center;
            min-width: 120px;
            flex: 1;
            max-width: 160px;
            position: relative;
        ">
            <div style="
                width: 36px;
                height: 36px;
                background: linear-gradient(135deg, #00B8D9, #0056CC);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 0.8rem auto;
                color: white;
                font-size: 1.1rem;
                font-weight: 600;
            ">⚡</div>
            <div style="
                font-size: 1.8rem;
                font-weight: 700;
                color: #1C1C1E;
                margin-bottom: 0.2rem;
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">{topics_updated_today}</div>
            <div style="
                font-size: 0.8rem;
                color: #8E8E93;
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">Updated Today</div>
        </div>
        
        <!-- Most Active Topic Card -->
        <div style="
            background: #fff;
            border-radius: 14px;
            padding: 1.2rem;
            box-shadow: 0 3px 15px rgba(0, 0, 0, 0.06);
            border: 1px solid #E5E5EA;
            text-align: center;
            min-width: 120px;
            flex: 1;
            max-width: 160px;
            position: relative;
        ">
            <div style="
                width: 36px;
                height: 36px;
                background: linear-gradient(135deg, #8B5CF6, #7C3AED);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 0.8rem auto;
                color: white;
                font-size: 1.1rem;
                font-weight: 600;
            ">🔥</div>
            <div style="
                font-size: 1.2rem;
                font-weight: 700;
                color: #1C1C1E;
                margin-bottom: 0.2rem;
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                line-height: 1.1;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            ">{most_active_topic.title()[:12] + ("..." if len(most_active_topic) > 12 else "") if most_active_topic else "-"}</div>
            <div style="
                font-size: 0.8rem;
                color: #8E8E93;
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">Most Active</div>
        </div>
    </div>
    """), height=180)

def render_shared_topic_card(subscription: Dict, session):
    """Render a card for a shared topic subscription with Apple-style design."""
    
    topic_name = subscription['name']
    posts_count = subscription['posts_count']
    last_collected = subscription['last_collected']
    topic_color = subscription.get('color', '#007AFF')
    topic_icon = subscription.get('icon', '📋')
    keywords = subscription.get('keywords', '')
    profiles = subscription.get('profiles', '')
    
    # Get recent posts for analytics
    recent_posts = get_shared_topic_posts(
        session, 
        subscription['shared_topic_id'], 
        limit=50
    )
    
    # ✅ Calculate new posts since last viewed
    last_viewed = subscription.get("last_viewed")
    if last_viewed:
        new_posts_count = sum(1 for p in recent_posts if p.posted_at > last_viewed)
    else:
        new_posts_count = len(recent_posts)

    # Card design
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
            background: linear-gradient(90deg, {topic_color}, {topic_color}99);
        "></div>
        
        <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
            <span style="font-size: 2.5rem; margin-right: 1rem;">{topic_icon}</span>
            <div>
                <h3 style="
                    margin: 0; 
                    color: {topic_color}; 
                    font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                    font-weight: 600;
                    font-size: 1.25rem;
                    letter-spacing: -0.01em;
                ">{topic_name.title()}</h3>
                <p style="
                    margin: 0.25rem 0 0 0; 
                    font-size: 0.9rem; 
                    color: #8E8E93;
                    font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                    font-weight: 500;
                ">
                    {posts_count} posts • Last: {time_ago(last_collected) if last_collected else "Never"}
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
                <strong>Keywords:</strong> {keywords or "None specified"}<br>
                <strong>Profiles:</strong> {len(profiles.split(',')) if profiles else 0} monitored
            </p>
        </div>
    </div>
    """), height=200)
    
    if recent_posts:
        from ui.charts import create_mini_analytics_chart, create_source_badges
        create_mini_analytics_chart(recent_posts, topic_color)
        source_badges = create_source_badges(recent_posts)
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
                {new_posts_count} new posts! 🔔
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
    
    # ✅ Unique key for button
    button_key = f"explore_{subscription['subscription_id']}"
    
    # ✅ Apply green style only to THIS button
    if new_posts_count > 0:
        st.markdown(f"""
        <style>
        div[data-testid="stButton"][key="{button_key}"] button {{
            background: linear-gradient(135deg, #34C759, #30B050) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(52, 199, 89, 0.3) !important;
        }}
        </style>
        """, unsafe_allow_html=True)
    
    # Explore button
    if st.button("🔍 **Explore**", key=button_key, use_container_width=True, type="primary"):
        st.session_state.selected_shared_topic = subscription['shared_topic_id']
        st.rerun()



def render_shared_post_preview(post):
    """Render a preview of a shared post."""
    
    # Post header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{post.source.title()}** • {time_ago(post.posted_at)}")
    with col2:
        if post.url:
            st.markdown(f"[🔗 Open]({post.url})")
    
    # Post content
    if post.title:
        st.markdown(f"**{post.title}**")
    
    if post.content:
        # Truncate content for preview
        content = post.content[:200] + "..." if len(post.content) > 200 else post.content
        st.markdown(content)
    
    # Post metrics
    if post.likes > 0 or post.comments > 0:
        col1, col2 = st.columns(2)
        with col1:
            if post.likes > 0:
                st.caption(f"👍 {post.likes}")
        with col2:
            if post.comments > 0:
                st.caption(f"💬 {post.comments}")


def render_shared_topic_detail_page(shared_topic_id: int, session):
    """Render the detailed view for a specific shared topic with ORIGINAL design."""
    from monitoring.database import SharedTopic, SharedPost
    from ui.utils import clean_content
    
    # Get the shared topic and its posts
    shared_topic = session.query(SharedTopic).filter_by(id=shared_topic_id).first()
    if not shared_topic:
        st.error("Topic not found!")
        st.session_state.selected_shared_topic = None
        st.rerun()
        return
    
    # Render header EXACTLY like original but for shared topics
    from ui.layout import render_topic_header
    # Create a temporary topic object with shared topic data for header rendering
    class TempTopic:
        def __init__(self, shared_topic):
            self.name = shared_topic.name
            self.last_collected = shared_topic.last_collected
            self.keywords = shared_topic.keywords
            self.profiles = shared_topic.profiles
            self.icon = "📊"  # Default icon for shared topics
    
    temp_topic = TempTopic(shared_topic)
    render_topic_header(temp_topic)
    
    # Back button (matching original Home button placement)
    col_left, col_right = st.columns([6, 1])
    with col_right:
        if st.button("← Back", key="go_back", use_container_width=True):
            st.session_state.selected_shared_topic = None
            st.rerun()
    
    # Get posts
    posts = shared_topic.posts
    
    if not posts:
        col1, col2 = st.columns([2, 1])
        with col1:
            st_html(dedent("""
            <div style="text-align: center; padding: 2rem; background: #f8f9fa; border-radius: 15px;">
                <h3>📭 No posts collected yet</h3>
                <p>Posts will appear here as data is collected for this topic.</p>
            </div>
            """), height=150)
        
        with col2:
            # Add a collect now button for topics with no posts
            if st.button("🚀 Collect Now", type="primary", use_container_width=True, key=f"collect_now_{shared_topic_id}"):
                # Create a progress display
                progress_placeholder = st.empty()
                
                try:
                    from monitoring.collectors import collect_topic
                    from monitoring.database import Topic
                    import time
                    import random
                    
                    # Define collection phases for visual feedback
                    collection_phases = [
                        {"emoji": "📰", "text": "Collecting news articles..."},
                        {"emoji": "🐦", "text": "Gathering social media posts..."},
                        {"emoji": "💬", "text": "Scanning Reddit discussions..."},
                        {"emoji": "📱", "text": "Searching Facebook posts..."},
                        {"emoji": "📸", "text": "Finding Instagram content..."},
                        {"emoji": "🔍", "text": "Processing and filtering..."},
                        {"emoji": "✅", "text": "Finalizing collection..."}
                    ]
                    
                    # Show progress phases
                    for i, phase in enumerate(collection_phases):
                        progress_value = (i + 1) / len(collection_phases)
                        progress_placeholder.markdown(f"""
                        <div style="padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; color: white; text-align: center;">
                            <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">{phase["emoji"]}</div>
                            <div style="font-weight: 500;">{phase["text"]}</div>
                            <div style="margin-top: 0.8rem; background: rgba(255,255,255,0.3); height: 6px; border-radius: 3px; overflow: hidden;">
                                <div style="background: white; height: 100%; width: {progress_value*100:.0f}%; border-radius: 3px; transition: width 0.3s;"></div>
                            </div>
                            <div style="margin-top: 0.3rem; font-size: 0.8rem; opacity: 0.9;">{progress_value*100:.0f}% complete</div>
                        </div>
                        """, unsafe_allow_html=True)
                        time.sleep(0.3 + random.uniform(0, 0.4))  # Realistic timing
                    
                    # Create a temporary Topic object for the collector
                    temp_topic = Topic()
                    temp_topic.id = shared_topic.id
                    temp_topic.name = shared_topic.name
                    temp_topic.keywords = shared_topic.keywords
                    
                    # Force collection for this topic
                    errors = collect_topic(temp_topic, force=True, shared_topic_id=shared_topic.id)
                    
                    # Clear progress display and show results
                    progress_placeholder.empty()
                    
                    if errors:
                        st.error(f"Collection completed with some issues: {'; '.join(errors[:2])}")
                    else:
                        st.success("Collection completed successfully!")
                    
                    # Refresh the page to show new posts
                    time.sleep(1)
                    st.rerun()
                        
                except Exception as e:
                    progress_placeholder.empty()
                    st.error(f"Collection failed: {str(e)}")
        
        return
    
    # Convert to dataframe for easier processing (EXACTLY like original)
    df = pd.DataFrame([
        {
            "title": p.title,
            "content": clean_content(p.content),
            "url": p.url,
            "posted_at": p.posted_at,  # SharedPost uses posted_at, not created_at
            "source": p.source,
            "likes": getattr(p, 'likes', 0),
            "comments": getattr(p, 'comments', 0),
            "image_url": getattr(p, 'image_url', None),
            "is_photo": getattr(p, 'is_photo', False),
            "subreddit": getattr(p, 'subreddit', None),
        }
        for p in posts
    ])
    
    # Enhanced metrics section (EXACTLY like original)
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
    
    # Analytics section (excluding photos) - EXACTLY like original
    st.markdown('<h2 class="section-heading">📈 Analytics</h2>', unsafe_allow_html=True)
    
    analytics_df = regular_posts_df.copy()
    analytics_df["date"] = analytics_df["posted_at"].dt.date
    
    col1, col2 = st.columns(2)
    
    with col1:
        from ui.charts import create_time_series_chart
        create_time_series_chart(analytics_df, "#1f77b4")  # Use default color
    
    with col2:
        from ui.charts import create_source_distribution_chart
        create_source_distribution_chart(analytics_df)
    
    # Word cloud (EXACTLY like original)
    text = " ".join(analytics_df["content"].astype(str))
    if text.strip():
        with st.expander("☁️ **Word Cloud**", expanded=False):
            from ui.charts import create_word_cloud
            create_word_cloud(text)

    # Posts sections with tabs - THE ORIGINAL TABBED INTERFACE!
    from ui.views import render_posts_tabs
    render_posts_tabs(df, shared_topic)
    
    # Update last viewed for user's subscription
    from monitoring.database import UserTopicSubscription
    current_user_id = st.session_state.get('user_id', 1)  # Get current user ID
    subscription = session.query(UserTopicSubscription).filter_by(
        user_id=current_user_id, 
        shared_topic_id=shared_topic_id
    ).first()
    if subscription:
        subscription.last_viewed = datetime.utcnow()
        session.commit()


def render_shared_post_card(post):
    """Render a full post card for shared posts."""
    
    with st.container():
        # Post header
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.markdown(f"**{post.source.title()}**")
        with col2:
            st.markdown(f"*{time_ago(post.posted_at)}*")
        with col3:
            if post.url:
                st.markdown(f"[🔗 Open]({post.url})")
        
        # Post content
        if post.title:
            st.markdown(f"### {post.title}")
        
        if post.content:
            with st.expander("📄 Read More", expanded=True):
                st.markdown(post.content)
        
        # Post image
        if post.image_url:
            st.image(post.image_url, width=300)
        
        # Post metrics and actions
        col1, col2, col3 = st.columns(3)
        with col1:
            if post.likes > 0:
                st.caption(f"👍 {post.likes} likes")
        with col2:
            if post.comments > 0:
                st.caption(f"💬 {post.comments} comments")
        with col3:
            if post.subreddit:
                st.caption(f"📍 r/{post.subreddit}")
        
        st.markdown("---")


def unsubscribe_from_topic(user_id: int, shared_topic_id: int):
    """Unsubscribe user from a shared topic."""
    session = SessionLocal()
    try:
        success = unsubscribe_user_from_topic(session, user_id, shared_topic_id)
        if success:
            st.success("✅ Unsubscribed successfully!")
            st.rerun()
        else:
            st.error("❌ Failed to unsubscribe")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
    finally:
        session.close()


def render_shared_topic_search_page():
    """Render a page to search and discover shared topics."""
    st.markdown("## 🔍 Discover Topics")
    
    search_query = st.text_input("Search topics", placeholder="e.g., AI, Python, Tesla")
    
    if search_query:
        from monitoring.shared_topics import search_shared_topics
        matching_topics = search_shared_topics(search_query)
        
        if matching_topics:
            st.markdown(f"Found {len(matching_topics)} matching topics:")
            
            for topic in matching_topics:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{topic['name']}**")
                        if topic['keywords']:
                            st.caption(f"Keywords: {topic['keywords']}")
                    
                    with col2:
                        st.metric("Posts", topic['posts_count'])
                        st.metric("Subscribers", topic['subscribers_count'])
                    
                    with col3:
                        if st.button("Subscribe", key=f"search_sub_{topic['id']}"):
                            # This would need current user ID
                            st.info("Please use the sidebar to subscribe to topics")
                    
                    st.markdown("---")
        else:
            st.info("No matching topics found. Try creating a new one!")
