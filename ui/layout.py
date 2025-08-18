"""Layout and styling components for the application."""

import streamlit as st
from streamlit.components.v1 import html as st_html
from textwrap import dedent


def apply_custom_css():
    """Apply custom CSS styling to the application."""
    
    css_content = """
    :root {
        --apple-blue: #007AFF;
        --apple-blue-hover: #0056CC;
        --apple-gray: #8E8E93;
        --apple-gray-light: #F6F6F7;
        --apple-gray-medium: #AEAEB2;
        --apple-text: #1C1C1E;
        --apple-text-secondary: #3A3A3C;
        --apple-background: #FFFFFF;
        --apple-card: #FFFFFF;
        --apple-border: #E5E5EA;
        --apple-shadow: rgba(0, 0, 0, 0.08);
        --apple-shadow-hover: rgba(0, 0, 0, 0.16);
        --sidebar-bg: #F6F6F7;
        --sidebar-border: #E5E5EA;
    }

    /* ULTIMATE FONT OVERRIDE - FORCE SF PRO ON EVERYTHING */
    html, body, *, *:before, *:after,
    h1, h2, h3, h4, h5, h6, p, div, span, strong, small, br,
    .stApp, .stApp *, .stApp *:before, .stApp *:after {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif !important;
    }
    
    /* Clean font system - exclude icons and specific elements */
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;
        -webkit-font-smoothing: antialiased;
    }
    
    /* Fix Streamlit Material Icon elements specifically - MUST come after font override */
    [data-testid="stIconMaterial"], 
    span[data-testid="stIconMaterial"],
    [class*="st-emotion-cache-zkd0x0"] {
        font-family: "Material Symbols Rounded" !important;
        font-weight: 400 !important;
        font-style: normal !important;
        line-height: 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        direction: ltr !important;
        font-feature-settings: 'liga' !important;
        -webkit-font-smoothing: antialiased !important;
    }"""

    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    
    # JavaScript to force font changes at runtime
    js_content = """
    <script>
    function forceAppleFonts() {
        const appleFont = '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, system-ui, sans-serif';
        
        document.querySelectorAll('*').forEach(el => {
            if (!el.getAttribute('data-testid') || !el.getAttribute('data-testid').includes('Icon')) {
                el.style.setProperty('font-family', appleFont, 'important');
            }
        });
        
        document.querySelectorAll('[style*="font-size"], [style*="font-weight"], [style*="margin"]').forEach(el => {
            el.style.setProperty('font-family', appleFont, 'important');
        });
        
        document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, div, span, strong, small').forEach(el => {
            if (!el.getAttribute('data-testid') || !el.getAttribute('data-testid').includes('Icon')) {
                el.style.setProperty('font-family', appleFont, 'important');
            }
        });
    }
    
    forceAppleFonts();
    setTimeout(forceAppleFonts, 100);
    setTimeout(forceAppleFonts, 500);
    setTimeout(forceAppleFonts, 1000);
    
    if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver(forceAppleFonts);
        observer.observe(document.body, { childList: true, subtree: true });
    }
    </script>
    """
    
    st.markdown(js_content, unsafe_allow_html=True)


def render_main_header():
    """Render the main application header."""
    st_html(dedent("""
        <div style="
            background: #fff;
            border-radius: 20px;
            margin: 2rem 0 2.5rem 0;
            box-shadow: 0 8px 32px rgba(0,0,0,0.07);
            padding: 2.5rem 1.5rem 2rem 1.5rem;
            text-align: center;
            max-width: 700px;
            margin-left: auto;
            margin-right: auto;
            border: 1px solid #ececec;
        ">
            <div style="display: flex; align-items: center; justify-content: center; gap: 1rem; margin-bottom: 0.5rem;">
                <div style="
                    width: 48px; 
                    height: 48px; 
                    background: #f0f0f0; 
                    border-radius: 8px; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center;
                    font-size: 24px;
                ">📰</div>
                <h1 style="
                    font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                    font-weight: 700;
                    font-size: 2.2rem;
                    margin: 0;
                    color: #222;
                    letter-spacing: -0.01em;
                ">Social & News Monitor</h1>
            </div>
            <p style="
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                font-size: 1.1rem;
                color: #444;
                margin-bottom: 1.5rem;
                opacity: 0.85;
            ">
                Effortlessly track topics across news and social media, with AI-powered insights.
            </p>
            <div style="
                display: flex;
                justify-content: center;
                gap: 1.5rem;
                flex-wrap: wrap;
                margin-bottom: 0.5rem;
            ">
                <div style="display: flex; align-items: center; gap: 0.4rem; font-size: 1.05rem; color: #007AFF;">
                    📰 <span style="font-size: 0.98rem; color: #444;">News</span>
                </div>
                <div style="display: flex; align-items: center; gap: 0.4rem; font-size: 1.05rem; color: #FF4500;">
                    👽 <span style="font-size: 0.98rem; color: #444;">Reddit</span>
                </div>
                <div style="display: flex; align-items: center; gap: 0.4rem; font-size: 1.05rem; color: #E4405F;">
                    📷 <span style="font-size: 0.98rem; color: #444;">Instagram</span>
                </div>
                <div style="display: flex; align-items: center; gap: 0.4rem; font-size: 1.05rem; color: #1877F2;">
                    📘 <span style="font-size: 0.98rem; color: #444;">Facebook</span>
                </div>
                <div style="display: flex; align-items: center; gap: 0.4rem; font-size: 1.05rem; color: #FF0000;">
                    📺 <span style="font-size: 0.98rem; color: #444;">YouTube</span>
                </div>
            </div>
        </div>
        """),
        height=180
    )


def render_welcome_screen():
    """Render the welcome screen for new users."""
    st_html(dedent("""
    <div style="
        text-align: center; 
        padding: 4rem 2rem; 
        background: linear-gradient(135deg, #007AFF, #5856D6); 
        border-radius: 24px; 
        margin: 2rem 0;
        color: white;
        box-shadow: 0 12px 40px rgba(0, 122, 255, 0.25);
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;
    ">
        <h1 style="font-size: 3rem; margin-bottom: 1rem; font-weight: 700; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">🚀 Welcome!</h1>
        <p style="font-size: 1.25rem; margin-bottom: 2rem; opacity: 0.9; line-height: 1.6; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">
            Ready to track what matters most to you?<br>
            Start by adding your first topic in the sidebar.
        </p>
        <div style="
            background: rgba(255, 255, 255, 0.15); 
            border-radius: 16px; 
            padding: 1.5rem; 
            margin-top: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;
        ">
            <h3 style="margin-bottom: 1rem; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">✨ What you can track:</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; text-align: left; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">📰 <strong style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">News Articles</strong><br><small style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">Stay updated with latest stories</small></div>
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">👽 <strong style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">Reddit Posts</strong><br><small style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">Monitor community discussions</small></div>
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">📷 <strong style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">Instagram</strong><br><small style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">Track visual content &amp; posts</small></div>
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">📘 <strong style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">Facebook</strong><br><small style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">Follow public pages &amp; posts</small></div>
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">📺 <strong style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">YouTube</strong><br><small style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">Find relevant videos &amp; channels</small></div>
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">🖼️ <strong style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">Photos</strong><br><small style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, system-ui, sans-serif;">Discover images from web search</small></div>
            </div>
        </div>
    </div>
    """), height=500)


def render_topic_header(topic):
    """Render the header for a specific topic view."""
    from .utils import time_ago
    
    st_html(dedent(f'''
    <div style="
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        background: #fff;
        border-radius: 24px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.10);
        border: 1px solid #e5e5ea;
        margin-bottom: 2.2rem;
        padding: 3.2rem 2.8rem 2.7rem 2.8rem;
        position: relative;
        overflow: visible;
        min-height: 210px;
    ">
        <div style="display: flex; align-items: center; gap: 2.5rem; flex: 1;">
            <span style="font-size: 3.7rem; filter: drop-shadow(0 4px 12px rgba(0,0,0,0.13));">{topic.icon}</span>
            <div>
                <h1 style="
                    font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                    font-weight: 700;
                    font-size: 2.6rem;
                    color: #1C1C1E;
                    margin: 0 0 0.3rem 0;
                    letter-spacing: -0.01em;
                    text-shadow: 0 2px 8px rgba(0,0,0,0.04);
                ">{topic.name.title()}</h1>
                <div style="display: flex; gap: 1.7rem; flex-wrap: wrap;">
                    <div style="color: #555; font-size: 1.08rem; font-weight: 500; display: flex; align-items: center; gap: 0.4rem;">
                        📅 <span style="opacity:0.85;">{time_ago(topic.last_collected)}</span>
                    </div>
                    <div style="color: #555; font-size: 1.08rem; font-weight: 500; display: flex; align-items: center; gap: 0.4rem;">
                        🔍 <span style="opacity:0.85;">{topic.keywords or "None specified"}</span>
                    </div>
                    <div style="color: #555; font-size: 1.08rem; font-weight: 500; display: flex; align-items: center; gap: 0.4rem;">
                        👥 <span style="opacity:0.85;">{len(topic.profiles.split(',') ) if topic.profiles else 0}</span>
                    </div>
                </div>
            </div>
        </div>
        <!-- The Home button will be rendered by Streamlit below -->
    </div>
    '''), height=250)


def render_collection_progress_cards(current_user_id: int):
    """Render progress cards for topics currently being collected with mock loading phases."""
    from monitoring.database import SessionLocal, SharedTopic, UserTopicSubscription
    from datetime import datetime
    import streamlit as st
    import time
    import random
    
    session = SessionLocal()
    try:
        # Get topics currently being collected for this user
        collecting_topics = session.query(SharedTopic).join(
            UserTopicSubscription,
            SharedTopic.id == UserTopicSubscription.shared_topic_id
        ).filter(
            UserTopicSubscription.user_id == current_user_id,
            SharedTopic.collection_status == 'collecting'
        ).all()
        
        if not collecting_topics:
            return
        
        st.markdown("### 🔄 Collection in Progress")
        
        # Define collection phases
        collection_phases = [
            {"emoji": "�", "text": "Collecting news articles...", "progress": 15},
            {"emoji": "🐦", "text": "Collecting social media posts...", "progress": 35},
            {"emoji": "💬", "text": "Collecting Reddit discussions...", "progress": 55},
            {"emoji": "📱", "text": "Collecting Facebook posts...", "progress": 70},
            {"emoji": "📸", "text": "Collecting Instagram content...", "progress": 85},
            {"emoji": "🔍", "text": "Processing and filtering content...", "progress": 95},
            {"emoji": "✅", "text": "Finalizing collection...", "progress": 100}
        ]
        
        # Create columns for progress cards
        cols = st.columns(min(3, len(collecting_topics)))
        
        for idx, shared_topic in enumerate(collecting_topics):
            col_idx = idx % 3
            with cols[col_idx]:
                # Get user's display name for this topic
                subscription = session.query(UserTopicSubscription).filter(
                    UserTopicSubscription.user_id == current_user_id,
                    UserTopicSubscription.shared_topic_id == shared_topic.id
                ).first()
                
                topic_name = subscription.display_name if subscription and subscription.display_name else shared_topic.name
                
                # Calculate elapsed time to determine phase
                start_time = shared_topic.collection_start_time
                if start_time:
                    elapsed = int((datetime.utcnow() - start_time).total_seconds())
                    # Each phase lasts about 15-20 seconds, with some randomness
                    phase_index = min(len(collection_phases) - 1, elapsed // 15)
                    # Add some randomness to make it feel more realistic
                    if elapsed > 10:
                        phase_index = min(len(collection_phases) - 1, (elapsed + random.randint(-5, 10)) // 15)
                else:
                    phase_index = 0
                    elapsed = 0
                
                current_phase = collection_phases[phase_index]
                
                # Create a smooth progress bar
                progress_width = min(100, max(5, current_phase["progress"] + random.randint(-5, 5)))
                
                # Progress card with realistic loading phases
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 15px;
                    padding: 1.5rem;
                    margin-bottom: 1rem;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
                    color: white;
                ">
                    <div style="display: flex; align-items: center; gap: 0.8rem; margin-bottom: 1rem;">
                        <span style="font-size: 1.5rem;">📊</span>
                        <h4 style="margin: 0; font-weight: 600; font-size: 1.1rem;">{topic_name}</h4>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                            <span style="font-size: 1rem;">{current_phase["emoji"]}</span>
                            <div style="font-size: 0.9rem; opacity: 0.95; font-weight: 500;">{current_phase["text"]}</div>
                        </div>
                        <div style="font-size: 0.75rem; opacity: 0.7;">Running for {elapsed}s</div>
                    </div>
                    
                    <!-- Progress Bar -->
                    <div style="
                        background: rgba(255, 255, 255, 0.2);
                        height: 6px;
                        border-radius: 3px;
                        overflow: hidden;
                        margin-bottom: 0.5rem;
                    ">
                        <div style="
                            background: linear-gradient(90deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.7));
                            height: 100%;
                            width: {progress_width}%;
                            border-radius: 3px;
                            transition: width 0.5s ease;
                            animation: shimmer 2s infinite;
                        "></div>
                    </div>
                    
                    <div style="font-size: 0.7rem; opacity: 0.6; text-align: right;">
                        {progress_width}% complete
                    </div>
                </div>
                
                <style>
                @keyframes shimmer {{
                    0% {{ opacity: 0.7; }}
                    50% {{ opacity: 1; }}
                    100% {{ opacity: 0.7; }}
                }}
                </style>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        
        st.markdown("---")
        
    finally:
        session.close()


def render_metrics_summary(topics, session, posts_model):
    """Render the enhanced metrics summary with individual cards for the overview page."""
    from datetime import datetime, timedelta
    
    total_posts = session.query(posts_model).count()
    active_topics = len([t for t in topics if t.last_collected])
    recently_updated = len([t for t in topics if t.last_collected and (datetime.utcnow() - t.last_collected).days < 1])
    posts_today = session.query(posts_model).filter(posts_model.posted_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)).count()
    posts_last_7d = session.query(posts_model).filter(posts_model.posted_at >= datetime.utcnow() - timedelta(days=7)).count()
    
    # Calculate additional metrics
    avg_posts_per_topic = round(total_posts / len(topics) if topics else 0, 1)
    topics_with_posts = len([t for t in topics if session.query(posts_model).filter_by(topic_id=t.id).count() > 0])
    
    most_active_topic = None
    most_active_count = 0
    if topics:
        topic_post_counts = [(t.name, session.query(posts_model).filter_by(topic_id=t.id).count()) for t in topics]
        topic_post_counts.sort(key=lambda x: x[1], reverse=True)
        if topic_post_counts and topic_post_counts[0][1] > 0:
            most_active_topic, most_active_count = topic_post_counts[0]

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
        <!-- Total Posts Card -->
        <div style="
            background: #fff;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid #E5E5EA;
            text-align: center;
            min-width: 140px;
            flex: 1;
            max-width: 180px;
            position: relative;
        ">
            <div style="
                width: 40px;
                height: 40px;
                background: linear-gradient(135deg, #007AFF, #5856D6);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 1rem auto;
                color: white;
                font-size: 1.2rem;
                font-weight: 600;
            ">📰</div>
            <div style="
                font-size: 2rem;
                font-weight: 700;
                color: #1C1C1E;
                margin-bottom: 0.25rem;
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">{total_posts}</div>
            <div style="
                font-size: 0.85rem;
                color: #8E8E93;
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">Total Posts</div>
        </div>
        
        <!-- Active Topics Card -->
        <div style="
            background: #fff;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid #E5E5EA;
            text-align: center;
            min-width: 140px;
            flex: 1;
            max-width: 180px;
            position: relative;
        ">
            <div style="
                width: 40px;
                height: 40px;
                background: linear-gradient(135deg, #34C759, #30B050);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 1rem auto;
                color: white;
                font-size: 1.2rem;
                font-weight: 600;
            ">🎯</div>
            <div style="
                font-size: 2rem;
                font-weight: 700;
                color: #1C1C1E;
                margin-bottom: 0.25rem;
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">{active_topics}</div>
            <div style="
                font-size: 0.85rem;
                color: #8E8E93;
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">Active Topics</div>
        </div>
        
        <!-- Topics Updated 24h Card -->
        <div style="
            background: #fff;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid #E5E5EA;
            text-align: center;
            min-width: 140px;
            flex: 1;
            max-width: 180px;
            position: relative;
        ">
            <div style="
                width: 40px;
                height: 40px;
                background: linear-gradient(135deg, #FF9500, #FF7A00);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 1rem auto;
                color: white;
                font-size: 1.2rem;
                font-weight: 600;
            ">⚡</div>
            <div style="
                font-size: 2rem;
                font-weight: 700;
                color: #1C1C1E;
                margin-bottom: 0.25rem;
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">{recently_updated}</div>
            <div style="
                font-size: 0.85rem;
                color: #8E8E93;
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">Topics Updated 24h</div>
        </div>
        
        <!-- Posts Today Card -->
        <div style="
            background: #fff;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid #E5E5EA;
            text-align: center;
            min-width: 140px;
            flex: 1;
            max-width: 180px;
            position: relative;
        ">
            <div style="
                width: 40px;
                height: 40px;
                background: linear-gradient(135deg, #2563EB, #1D4ED8);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 1rem auto;
                color: white;
                font-size: 1.2rem;
                font-weight: 600;
            ">📅</div>
            <div style="
                font-size: 2rem;
                font-weight: 700;
                color: #1C1C1E;
                margin-bottom: 0.25rem;
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">{posts_today}</div>
            <div style="
                font-size: 0.85rem;
                color: #8E8E93;
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">Posts Today</div>
        </div>
        
        <!-- Posts Last 7d Card -->
        <div style="
            background: #fff;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid #E5E5EA;
            text-align: center;
            min-width: 140px;
            flex: 1;
            max-width: 180px;
            position: relative;
        ">
            <div style="
                width: 40px;
                height: 40px;
                background: linear-gradient(135deg, #00B8D9, #0056CC);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 1rem auto;
                color: white;
                font-size: 1.2rem;
                font-weight: 600;
            ">📈</div>
            <div style="
                font-size: 2rem;
                font-weight: 700;
                color: #1C1C1E;
                margin-bottom: 0.25rem;
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">{posts_last_7d}</div>
            <div style="
                font-size: 0.85rem;
                color: #8E8E93;
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">Posts Last 7d</div>
        </div>
        
        <!-- Most Active Topic Card -->
        <div style="
            background: #fff;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid #E5E5EA;
            text-align: center;
            min-width: 140px;
            flex: 1;
            max-width: 180px;
            position: relative;
        ">
            <div style="
                width: 40px;
                height: 40px;
                background: linear-gradient(135deg, #8B5CF6, #7C3AED);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 1rem auto;
                color: white;
                font-size: 1.2rem;
                font-weight: 600;
            ">🏆</div>
            <div style="
                font-size: 1.4rem;
                font-weight: 700;
                color: #1C1C1E;
                margin-bottom: 0.25rem;
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                line-height: 1.2;
            ">{most_active_topic.title() if most_active_topic else "-"}</div>
            <div style="
                font-size: 0.85rem;
                color: #8E8E93;
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            ">Most Active Topic</div>
        </div>
    </div>
    """), height=200)


def render_welcome_screen_for_new_users(has_topics: bool = False):
    """Conditionally render the welcome screen only for new users without topics."""
    if not has_topics:
        render_welcome_screen()
