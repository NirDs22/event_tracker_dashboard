"""Layout and styling components for the application."""

import streamlit as st
from streamlit.components.v1 import html as st_html
from textwrap import dedent


def apply_custom_css():
    """Apply custom CSS styling to the application."""
    # Directly inject font links and aggressive CSS fixes for cloud compatibility
    st.components.v1.html("""
    <iframe srcdoc='
    <link rel="preconnect" href="https://applesocial.s3.amazonaws.com" crossorigin>
    <link rel="preconnect" href="https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/" crossorigin>
    <!-- SF Pro fonts preloaded for better performance -->
    <link rel="preload" href="https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-regular-webfont.woff" as="font" type="font/woff" crossorigin>
    <link rel="preload" href="https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-medium-webfont.woff" as="font" type="font/woff" crossorigin>
    <link rel="preload" href="https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-semibold-webfont.woff" as="font" type="font/woff" crossorigin>
    <link rel="preload" href="https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscotext-regular-webfont.woff" as="font" type="font/woff" crossorigin>
    <link rel="preload" href="https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscotext-medium-webfont.woff" as="font" type="font/woff" crossorigin>
    ' style="width:0;height:0;border:0;"></iframe>

    <style>
    /* --- AGGRESSIVE CLOUD FIXES WITH FIXED WIDTH --- */

    /* Set global font fallback system */
    .stApp, .stApp * {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif !important;
    }

    /* Reset box model for more predictable layouts */
    *, *::before, *::after {
        box-sizing: border-box !important;
    }

    /* Fixed width main container for cloud environment */
    .fixed-container {
        max-width: 1200px !important;
        margin: 0 auto !important;
        width: 100% !important;
    }

    /* Force app container to use fixed width */
    [data-testid="stAppViewContainer"] > div:nth-child(2) {
        max-width: 1440px !important; 
        margin: 0 auto !important;
        width: 100% !important;
    }

    /* Fix sidebar width */
    [data-testid="stSidebar"] {
        width: 280px !important;
        max-width: 280px !important;
        min-width: 280px !important;
    }

    /* Aggressively fix column layouts */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 1.5rem !important;
        margin-bottom: 1.5rem !important;
        width: 100% !important;
    }

    /* Make sure columns take equal space and don't shrink */
    div[data-testid="column"] {
        flex: 1 1 0 !important; 
        width: 100% !important;
        min-width: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Fix element container width */
    .element-container {
        width: 100% !important;
        padding: 0 !important;
    }

    /* Fix HTML containers for cards */
    [data-testid="stHtml"] {
        width: 100% !important;
        overflow: visible !important;
        margin: 0 0 1rem 0 !important;
        padding: 0 !important;
    }

    /* Fix iframe containers */
    iframe:not([style*="width:0"]) {
        width: 100% !important;
        margin: 0 auto !important;
        display: block !important;
        border: none !important;
    }

    /* Force card containers to proper width */
    .stHtml > div {
        width: 100% !important;
    }

    /* Fix image containers */
    .stImage > img {
        max-width: 100% !important;
    }

    /* Cloud-specific fixes */
    @media screen {
        /* Adjust main container */
        [data-testid="block-container"] {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        
        /* Better spacing for mobile */
        @media (max-width: 768px) {
            [data-testid="block-container"] {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            
            div[data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
            }
            
            div[data-testid="column"] {
                margin-bottom: 1rem !important;
            }
        }
    }
    </style>
    """, height=0)

    # Apple-inspired Custom CSS with unified typography
    st.markdown(dedent("""
    <style>
    /* SF Pro Font Definitions */
    @font-face {
        font-family: 'SF Pro Display';
        src: local('SF Pro Display'), 
             url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-regular-webfont.woff') format('woff');
        font-weight: 400;
        font-display: swap;
    }
    @font-face {
        font-family: 'SF Pro Display';
        src: local('SF Pro Display Medium'), 
             url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-medium-webfont.woff') format('woff');
        font-weight: 500;
        font-display: swap;
    }
    @font-face {
        font-family: 'SF Pro Display';
        src: local('SF Pro Display Semibold'), 
             url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-semibold-webfont.woff') format('woff');
        font-weight: 600;
        font-display: swap;
    }
    @font-face {
        font-family: 'SF Pro Text';
        src: local('SF Pro Text'), 
             url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscotext-regular-webfont.woff') format('woff');
        font-weight: 400;
        font-display: swap;
    }
    @font-face {
        font-family: 'SF Pro Text';
        src: local('SF Pro Text Medium'), 
             url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscotext-medium-webfont.woff') format('woff');
        font-weight: 500;
        font-display: swap;
    }

    /* Global Apple-inspired styling */
    * {
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        font-feature-settings: "kern", "liga", "calt";
    }

    /* Root variables for consistent theming */
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

    /* Force consistent fonts across ALL elements */
    html, body, div, span, applet, object, iframe,
    h1, h2, h3, h4, h5, h6, p, blockquote, pre,
    a, abbr, acronym, address, big, cite, code,
    del, dfn, em, img, ins, kbd, q, s, samp,
    small, strike, strong, sub, sup, tt, var,
    b, u, i, center,
    dl, dt, dd, ol, ul, li,
    fieldset, form, label, legend,
    table, caption, tbody, tfoot, thead, tr, th, td,
    article, aside, canvas, details, embed, 
    figure, figcaption, footer, header, hgroup, 
    menu, nav, output, ruby, section, summary,
    time, mark, audio, video {
        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
    }

    /* Headings use SF Pro Display */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
        font-weight: 600 !important;
        color: var(--apple-text) !important;
        letter-spacing: -0.01em !important;
        line-height: 1.3 !important;
        margin-bottom: 0.5em !important;
        margin-top: 1em !important;
    }

    h1 { font-size: 32px !important; }
    h2 { font-size: 26px !important; }
    h3 { font-size: 22px !important; }
    h4 { font-size: 18px !important; }

    /* Override ALL Streamlit component fonts */
    .stApp, .stApp * {
        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
        letter-spacing: -0.01em;
    }

    /* Specifically target all text elements */
    .stMarkdown, .stMarkdown *, .stText, .stText *, .stCaption, .stCaption *, 
    .stWrite, .stWrite *, .stMetric, .stMetric *, p, p *, span, span *, 
    div, div *, label, label *, .stSelectbox, .stSelectbox *, .stButton, .stButton *,
    .stTabs, .stTabs *, .stInfo, .stInfo *, .stSuccess, .stSuccess *, 
    .stWarning, .stWarning *, .stError, .stError * {
        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
        color: var(--apple-text) !important;
    }

    /* Main app background */
    .main .block-container {
        background-color: #fff !important;
        padding: 1.5rem !important;
        max-width: 1200px !important;
        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
        line-height: 1.5 !important;
        box-shadow: 0 2px 16px rgba(0,0,0,0.04);
        border-radius: 18px;
    }

    /* Section headings */
    .section-heading {
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
        font-weight: 600 !important;
        color: var(--apple-text) !important;
        margin-bottom: 0.7rem !important;
        letter-spacing: -0.01em !important;
        font-size: 1.15rem !important;
    }

    h2.section-heading {
        font-size: 1.25rem !important;
        margin-top: 1.2rem !important;
    }

    h3.section-heading {
        font-size: 1.1rem !important;
        margin-top: 1rem !important;
    }

    /* Force button fonts */
    .stButton > button, button {
        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
        border: none !important;
        padding: 0.75rem 1.5rem !important;
        font-size: 0.9rem !important;
    }

    .stButton > button[kind="primary"], button[kind="primary"] {
        background: linear-gradient(135deg, var(--apple-blue), var(--apple-blue-hover)) !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(0, 122, 255, 0.3) !important;
    }

    .stButton > button:hover, button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4) !important;
    }

    /* Enhanced sidebar */
    .css-1d391kg, .css-1kyxreq, [data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid var(--sidebar-border) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
        box-shadow: 2px 0 8px rgba(0,0,0,0.03);
    }

    /* Hide Streamlit branding */
    .css-164nlkn, #MainMenu, footer, header {
        display: none !important;
    }

    /* Underlines for highlighted content */
    u {
        text-underline-offset: 3px;
        text-decoration-thickness: 2px;
        text-decoration-color: var(--primary-blue);
        text-decoration-style: solid;
    }

    /* Source badges */
    .source-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        border-radius: 16px;
        font-size: 0.8rem;
        font-weight: 600;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
        letter-spacing: 0.3px;
        text-transform: uppercase;
        margin: 2px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .reddit-badge { background: linear-gradient(135deg, #FF4500, #CC3400); color: white; }
    .news-badge { background: linear-gradient(135deg, #2563EB, #1D4ED8); color: white; }
    .instagram-badge { background: linear-gradient(135deg, #E4405F, #C13584); color: white; }
    .facebook-badge { background: linear-gradient(135deg, #1877F2, #1565C0); color: white; }
    .youtube-badge { background: linear-gradient(135deg, #FF0000, #CC0000); color: white; }
    .photos-badge { background: linear-gradient(135deg, #8B5CF6, #7C3AED); color: white; }

    /* Force font consistency on ALL possible Streamlit elements */
    [data-testid="stSidebar"] *, 
    [data-testid="column"] *,
    [data-testid="stVerticalBlock"] *,
    [data-testid="stHorizontalBlock"] *,
    [data-testid="stMetric"] *,
    [data-testid="stText"] *,
    [data-testid="stMarkdown"] *,
    [data-testid="baseButton-secondary"] *,
    [data-testid="baseButton-primary"] *,
    [data-baseweb="tab"] *,
    [data-baseweb="tab-list"] *,
    [data-baseweb="input"] *,
    [data-baseweb="select"] *,
    [data-baseweb="checkbox"] *,
    [data-baseweb="textarea"] *,
    .stApp header,
    .stApp footer,
    .element-container,
    .css-1kyxreq,
    .main .block-container,
    .streamlit-expanderHeader,
    .stAlert * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
    }

    /* Ensure plotly charts have consistent fonts */
    .js-plotly-plot *,
    .plotly-graph-div *,
    .svg-container * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
    }

    /* Apply the font to ALL components that might not be covered */
    body * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
    }
    </style>
    """), unsafe_allow_html=True)


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
            <h1 style="
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                font-weight: 700;
                font-size: 2.2rem;
                margin-bottom: 0.5rem;
                color: #222;
                letter-spacing: -0.01em;
            ">📰 Social & News Monitor</h1>
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
    ">
        <h1 style="font-size: 3rem; margin-bottom: 1rem; font-weight: 700;">🚀 Welcome!</h1>
        <p style="font-size: 1.25rem; margin-bottom: 2rem; opacity: 0.9; line-height: 1.6;">
            Ready to track what matters most to you?<br>
            Start by adding your first topic in the sidebar.
        </p>
        <div style="
            background: rgba(255, 255, 255, 0.15); 
            border-radius: 16px; 
            padding: 1.5rem; 
            margin-top: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
        ">
            <h3 style="margin-bottom: 1rem;">✨ What you can track:</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; text-align: left;">
                <div>📰 <strong>News Articles</strong><br><small>Stay updated with latest stories</small></div>
                <div>👽 <strong>Reddit Posts</strong><br><small>Monitor community discussions</small></div>
                <div>📷 <strong>Instagram</strong><br><small>Track visual content & posts</small></div>
                <div>📘 <strong>Facebook</strong><br><small>Follow public pages & posts</small></div>
                <div>📺 <strong>YouTube</strong><br><small>Find relevant videos & channels</small></div>
                <div>🖼️ <strong>Photos</strong><br><small>Discover images from web search</small></div>
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
        overflow: hidden;
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
                ">{topic.name}</h1>
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


def render_metrics_summary(topics, session, posts_model):
    """Render the glassmorphic metrics summary for the overview page."""
    from datetime import datetime, timedelta
    
    total_posts = session.query(posts_model).count()
    active_topics = len([t for t in topics if t.last_collected])
    recently_updated = len([t for t in topics if t.last_collected and (datetime.utcnow() - t.last_collected).days < 1])
    posts_today = session.query(posts_model).filter(posts_model.posted_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)).count()
    posts_last_7d = session.query(posts_model).filter(posts_model.posted_at >= datetime.utcnow() - timedelta(days=7)).count()
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
        align-items: flex-end;
        margin-bottom: 1.5rem;
    ">
        <div style="
            background: rgba(255,255,255,0.55);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.12);
            backdrop-filter: blur(18px) saturate(1.5);
            -webkit-backdrop-filter: blur(18px) saturate(1.5);
            border-radius: 2.2rem;
            border: 1.5px solid rgba(255,255,255,0.25);
            padding: 0.7rem 1.2rem 0.7rem 1.2rem;
            display: grid;
            grid-template-columns: repeat(6, minmax(80px, 1fr));
            gap: 0.3rem 1.2rem;
            min-width: 0;
            max-width: 900px;
            width: 100%;
            margin: 0 auto;
            position: relative;
            overflow: visible;
        ">
            <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 1.15rem; margin-bottom: 0.05rem; background: linear-gradient(135deg, #007AFF, #5856D6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700;">📰</span>
                <span style="font-size: 1.02rem; font-weight: 700; color: #222; font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;">{total_posts}</span>
                <span style="font-size: 0.72rem; color: #3A3A3C; font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif; font-weight: 500; margin-top: 0.04rem;">Total Posts</span>
            </div>
            <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 1.15rem; margin-bottom: 0.05rem; background: linear-gradient(135deg, #34C759, #30B050); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700;">🎯</span>
                <span style="font-size: 1.02rem; font-weight: 700; color: #222; font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;">{active_topics}</span>
                <span style="font-size: 0.72rem; color: #3A3A3C; font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif; font-weight: 500; margin-top: 0.04rem;">Active Topics</span>
            </div>
            <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 1.15rem; margin-bottom: 0.05rem; background: linear-gradient(135deg, #FF9500, #FF7A00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700;">⚡</span>
                <span style="font-size: 1.02rem; font-weight: 700; color: #222; font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;">{recently_updated}</span>
                <span style="font-size: 0.72rem; color: #3A3A3C; font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif; font-weight: 500; margin-top: 0.04rem;">Topics Updated 24h</span>
            </div>
            <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 1.15rem; margin-bottom: 0.05rem; background: linear-gradient(135deg, #2563EB, #1D4ED8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700;">📅</span>
                <span style="font-size: 1.02rem; font-weight: 700; color: #222; font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;">{posts_today}</span>
                <span style="font-size: 0.72rem; color: #3A3A3C; font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif; font-weight: 500; margin-top: 0.04rem;">Posts Today</span>
            </div>
            <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 1.15rem; margin-bottom: 0.05rem; background: linear-gradient(135deg, #00B8D9, #0056CC); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700;">📈</span>
                <span style="font-size: 1.02rem; font-weight: 700; color: #222; font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;">{posts_last_7d}</span>
                <span style="font-size: 0.72rem; color: #3A3A3C; font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif; font-weight: 500; margin-top: 0.04rem;">Posts Last 7d</span>
            </div>
            <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 1.15rem; margin-bottom: 0.05rem; background: linear-gradient(135deg, #8B5CF6, #7C3AED); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700;">🏆</span>
                <span style="font-size: 0.88rem; font-weight: 700; color: #222; font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;">{most_active_topic if most_active_topic else "-"}</span>
                <span style="font-size: 0.72rem; color: #3A3A3C; font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif; font-weight: 500; margin-top: 0.04rem;">Most Active Topic</span>
            </div>
        </div>
    </div>
    """), height=100)
