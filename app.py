import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from textwrap import dedent

# Determine if we're running in Streamlit Cloud for compatibility adjustments
IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit_sharing" or os.environ.get("STREAMLIT_SERVER_HEADLESS") == "true"

# Configure Streamlit page FIRST, before any other st commands
import streamlit as st
st.set_page_config(
    page_title="Social & News Monitor", 
    layout="wide",
    page_icon="📰",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Social & News Monitor App"
    }
)

from streamlit.components.v1 import html as st_html
import html as py_html
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

# Load environment variables from .env file if available (for local development)
try:
    from dotenv import load_dotenv
    ENV_LOADED = load_dotenv(dotenv_path='.env')
    if not ENV_LOADED:
        # Try loading from absolute path as fallback
        ENV_LOADED = load_dotenv(dotenv_path='/Users/nird/Documents/ENV/.env')
except Exception:
    ENV_LOADED = False

# Import the secret management utility
from monitoring.secrets import get_secret

from monitoring.database import init_db, SessionLocal, Topic, Post
from monitoring.collectors import collect_topic, collect_all_topics_efficiently, fetch_twitter_nitter
from monitoring.scheduler import start_scheduler, send_test_digest
from monitoring.summarizer import summarize, strip_think


# Utility functions
def _first(*vals):
    for v in vals:
        if v not in (None, "", [], {}):
            return v
    return ""

def _to_text(x):
    """Convert any input to clean, usable text by removing HTML and normalizing whitespace."""
    if x is None: return ""
    s = str(x).strip()
    
    # Nothing to process for empty strings
    if not s: 
        return ""
        
    # Strip HTML to plain text if it looks like markup
    if ("<" in s and ">" in s):
        if BeautifulSoup is not None:
            try:
                s = BeautifulSoup(s, "html.parser").get_text(" ", strip=True)
            except Exception:
                # Fallback to regex if BeautifulSoup fails
                s = re.sub(r'<[^>]*>', ' ', s)
        else:
            # No BeautifulSoup available, use regex
            s = re.sub(r'<[^>]*>', ' ', s)
    
    # Normalize whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    return s


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


# Card rendering functions
def _is_meaningfully_different(text1, text2):
    """Determine if two text strings are meaningfully different for display purposes"""
    if not text1 or not text2:
        return True
        
    # Normalize both texts for comparison
    def normalize(text):
        # Convert to lowercase and normalize whitespace
        text = re.sub(r'\s+', ' ', text.lower().strip())
        # Remove punctuation and special characters
        text = re.sub(r'[^\w\s]', '', text)
        return text
        
    # Get clean versions for comparison
    norm1 = normalize(text1)
    norm2 = normalize(text2)
    
    # Empty strings aren't meaningful
    if not norm1 or not norm2:
        return False
    
    # If they're exactly the same after normalization, they're not different
    if norm1 == norm2:
        return False
    
    # Length comparison - if one is much longer than the other, they're different
    len1 = len(norm1)
    len2 = len(norm2)
    
    # If one text is significantly longer, they're meaningfully different
    if max(len1, len2) > min(len1, len2) * 1.7:  # One is 70% longer than the other
        return True
        
    # If one is completely contained within the other, they're not meaningfully different
    if norm1 in norm2 or norm2 in norm1:
        return False
    
    # For short strings, be more strict with similarity comparison
    if len(norm1) < 40 or len(norm2) < 40:
        # Calculate text similarity ratio
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        if similarity > 0.5:  # More than 50% similar for short strings
            return False
    
    # Calculate word overlap as a percentage
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    
    if not words1 or not words2:
        return False
        
    # Calculate overlap metrics
    overlap = len(words1.intersection(words2))
    smaller_set_size = min(len(words1), len(words2))
    
    # If high word overlap and similar lengths, not meaningfully different
    if smaller_set_size > 0 and overlap / smaller_set_size > 0.7:
        # Also check if the longer text contains substantially more words
        larger_set_size = max(len(words1), len(words2))
        # If the larger set has at least 40% more unique words, they're different
        if larger_set_size > smaller_set_size * 1.4:
            return True
        return False
        
    return True

def _add_topic_underlines(text, topic_name):
    """Add underlines to topic mentions in text"""
    if not topic_name or not text:
        return text
    
    import re
    # Escape the topic name for regex and create case-insensitive pattern
    escaped_topic = py_html.escape(topic_name)
    try:
        pattern = re.compile(re.escape(escaped_topic), re.IGNORECASE)
        result = pattern.sub(f'<u>{escaped_topic}</u>', py_html.escape(text))
        return result
    except Exception:
        return py_html.escape(text)

def _render_card(title, summary, image_url, age_text, link, badge="News", topic_name=None, height=None):
    """Render a content card with proper title and summary display.
    Contract:
    - Inputs: raw title/summary may be None/HTML; image/link optional; badge text.
    - Behavior: derive a sensible title when missing, show preview only if it adds info beyond title, and avoid duplicates.
    - Output: Renders a Streamlit HTML component with consistent typography.
    """
    # Determine if we're in Streamlit Cloud environment - use more conservative height
    IN_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit_sharing" or os.environ.get("STREAMLIT_SERVER_HEADLESS") == "true"
    # Process and clean inputs - ensure we have fallbacks for missing data
    raw_title = str(title or "").strip()
    raw_summary = str(summary or "").strip()
    
    # Clean inputs with proper HTML sanitization
    title = _to_text(raw_title)
    summary = _to_text(raw_summary) or ""
    image_url = _to_text(image_url) or ""
    age_text = _to_text(age_text) or "Recently"
    link = _to_text(link) or ""
    
    # If title is missing/placeholder, derive it from summary or link
    def _derive_title():
        # Use first sentence or first ~90 chars of summary
        if summary:
            first = summary.split('. ')[0].strip()
            candidate = first if len(first) >= 12 else summary[:90]
            candidate = candidate.strip().rstrip('.,;:')
            if candidate:
                return candidate
        # Fallback to domain from link
        if link:
            try:
                import urllib.parse as _url
                netloc = _url.urlparse(link).netloc
                if netloc:
                    return netloc.replace('www.', '')
            except Exception:
                pass
        return "Untitled"
    
    if not title or title.strip().lower() in {"untitled", "(untitled)", "unknown", ""}:
        title = _derive_title()
    
    # Prepare title for display
    if len(title) > 120:
        title = title[:117] + "..."
    
    # Create HTML-safe title with topic highlighting if needed
    title_html = _add_topic_underlines(title, topic_name) if topic_name else py_html.escape(title)
    
    # Process summary - ensure it adds value beyond the title and isn't self-duplicated
    # 1) Remove title fragments from summary when they appear inside it
    def _strip_title_from_summary(s, t):
        if not s:
            return s
        cleaned = s
        if t and len(t) >= 12:
            try:
                pattern = re.compile(re.escape(t), re.IGNORECASE)
                cleaned = pattern.sub(" ", cleaned)
            except Exception:
                pass
        # Deduplicate repeated segments split by common separators
        parts = re.split(r"\s*[\-|\u2013\u2014\|]\s+", cleaned)
        seen = set()
        uniq_parts = []
        for p in parts:
            key = p.strip().lower()
            if key and key not in seen:
                uniq_parts.append(p.strip())
                seen.add(key)
        cleaned = " - ".join(uniq_parts) if uniq_parts else cleaned
        # If the text is an exact double (e.g., X X), collapse to first half
        half = len(cleaned) // 2
        if len(cleaned) > 40 and cleaned[:half].strip().lower() == cleaned[half:].strip().lower():
            cleaned = cleaned[:half].strip()
        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
    
    # Keep a copy of the original summary for fallback
    _orig_summary = summary
    summary = _strip_title_from_summary(summary, title)

    # Helper to choose the best preview text
    def _choose_preview(orig_s: str, cleaned_s: str, t: str, badge_txt: str) -> str:
        # Prefer cleaned summary if it's reasonably informative
        candidate = cleaned_s or ""
        # If too short, try to pick the next informative sentence from the original
        if len(candidate) < 30 and orig_s:
            sentences = re.split(r"(?<=[\.!?])\s+", orig_s)
            for snt in sentences[:4]:
                if len(snt) >= 20 and _is_meaningfully_different(t, snt):
                    candidate = snt.strip()
                    break
        # If still short and it's News/Reddit, allow a lighter check
        if len(candidate) < 30 and badge_txt in {"News", "Reddit"} and orig_s:
            # Use the original but remove exact title tokens, then trim
            fallback = _strip_title_from_summary(orig_s, t)
            candidate = fallback if len(fallback) >= 20 else orig_s
        candidate = (candidate or "").strip()
        return candidate
    
    # First verify we actually have a summary and it's not just the title repeated
    has_meaningful_summary = False
    summary_html = ""
    preview = _choose_preview(_orig_summary, summary, title, badge)
    # Relax: show if preview has at least 20 chars or passes meaningful-different test
    if preview and (len(preview) >= 20 or _is_meaningfully_different(title, preview)):
        has_meaningful_summary = True
        # Clamp length with soft sentence boundary
        if len(preview) > 320:
            cut = max(preview.rfind('. ', 220, 320), preview.rfind(' ', 260, 320))
            cut = cut if cut != -1 else 300
            preview = preview[:cut].rstrip() + "..."
        summary_html = _add_topic_underlines(preview, topic_name) if topic_name else py_html.escape(preview)
    
    # Log for debugging if needed
    # print(f"Title: {title}\nSummary: {summary}\nMeaningful: {has_meaningful_summary}")

    # Apple-inspired card design with professional typography
    html = dedent(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <!-- Preload SF Pro fonts for better performance -->
        <link rel="preload" href="https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-regular-webfont.woff" as="font" type="font/woff" crossorigin>
        <link rel="preload" href="https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-medium-webfont.woff" as="font" type="font/woff" crossorigin>
        <link rel="preload" href="https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-semibold-webfont.woff" as="font" type="font/woff" crossorigin>
        <link rel="preload" href="https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscotext-regular-webfont.woff" as="font" type="font/woff" crossorigin>
        <link rel="preload" href="https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscotext-medium-webfont.woff" as="font" type="font/woff" crossorigin>
        
        <!-- Load SF Pro fonts -->
        <style>
            /* SF Pro Font declarations */
            @font-face {{
                font-family: 'SF Pro Display';
                src: local('SF Pro Display'), 
                     url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-regular-webfont.woff') format('woff');
                font-weight: 400;
                font-display: swap;
            }}
            @font-face {{
                font-family: 'SF Pro Display';
                src: local('SF Pro Display Medium'), 
                     url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-medium-webfont.woff') format('woff');
                font-weight: 500;
                font-display: swap;
            }}
            @font-face {{
                font-family: 'SF Pro Display';
                src: local('SF Pro Display Semibold'), 
                     url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-semibold-webfont.woff') format('woff');
                font-weight: 600;
                font-display: swap;
            }}
            @font-face {{
                font-family: 'SF Pro Text';
                src: local('SF Pro Text'), 
                     url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscotext-regular-webfont.woff') format('woff');
                font-weight: 400;
                font-display: swap;
            }}
            @font-face {{
                font-family: 'SF Pro Text';
                src: local('SF Pro Text Medium'), 
                     url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscotext-medium-webfont.woff') format('woff');
                font-weight: 500;
                font-display: swap;
            }}
        </style>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
                text-rendering: optimizeLegibility;
            }}
            
            /* Add specific rule to enforce font family */
            .title, .preview, .badge, .age, .view-btn {{
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
            }}
            
            :root {{
                --apple-blue: #007AFF;
                --apple-blue-hover: #0056CC;
                --apple-gray: #8E8E93;
                --apple-gray-light: #F2F2F7;
                --apple-text: #1C1C1E;
                --apple-text-secondary: #3A3A3C;
                --apple-text-tertiary: #8E8E93;
                --apple-card: #FFFFFF;
                --apple-border: #E5E5EA;
                --apple-shadow: rgba(0, 0, 0, 0.08);
                --apple-shadow-hover: rgba(0, 0, 0, 0.16);
            }}
            
            body {{
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
                background: var(--apple-gray-light);
                padding: 8px;
                line-height: 1.5;
                color: var(--apple-text);
                font-size: 14px;
            }}
            
            .card {{
                background: var(--apple-card);
                border-radius: 16px;
                box-shadow: 0 4px 20px var(--apple-shadow);
                border: 1px solid var(--apple-border);
                overflow: hidden;
                transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                height: auto;
                min-height: 200px;
                display: flex;
                flex-direction: column;
                position: relative;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            }}
            
            .card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, var(--apple-blue), #5856D6, #FF9500);
            }}
            
            .card:hover {{
                transform: translateY(-6px);
                box-shadow: 0 12px 40px var(--apple-shadow-hover);
            }}
            
            .card-header {{
                padding: 16px 20px 12px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid var(--apple-border);
                background: rgba(248, 250, 252, 0.5);
            }}
            
            .badge {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                font-size: 12px;
                font-weight: 600;
                color: var(--apple-text);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            }}
            
            .age {{
                font-size: 11px;
                color: var(--apple-text-tertiary);
                font-weight: 500;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            }}
            
            .card-body {{
                padding: 0 24px;
                flex-grow: 1;
                display: flex;
                flex-direction: column;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
            }}
            
            .title {{
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
                font-size: 17px;
                font-weight: 600;
                color: var(--apple-text);
                line-height: 1.3;
                margin: 16px 0 12px 0;
                letter-spacing: -0.01em;
                display: -webkit-box;
                -webkit-line-clamp: 3;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }}
            
            .image-container {{
                margin: 14px 0 18px 0;
                border-radius: 16px;
                overflow: hidden;
                background: var(--apple-gray-light);
                box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
            }}
            
            .image {{
                width: 100%;
                height: 180px;
                object-fit: cover;
                display: block;
                transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            }}
            
            .image:hover {{
                transform: scale(1.05);
            }}
            
            .preview {{
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
                font-size: 14px;
                color: var(--apple-text-secondary);
                line-height: 1.5;
                margin: 4px 0 20px 0;
                padding: 0 1px;
                display: -webkit-box;
                -webkit-line-clamp: 4;
                -webkit-box-orient: vertical;
                overflow: hidden;
                flex-grow: 1;
                letter-spacing: 0;
            }}
            
            .card-footer {{
                padding: 16px 24px 24px 24px;
                border-top: 1px solid var(--apple-border);
                margin-top: auto;
                background: rgba(248, 249, 250, 0.3);
            }}
            
            .view-btn {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                padding: 14px 20px;
                background: linear-gradient(135deg, var(--apple-blue), var(--apple-blue-hover));
                color: white;
                text-decoration: none;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 600;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                border: none;
                cursor: pointer;
                box-shadow: 0 4px 15px rgba(0, 122, 255, 0.3);
                width: 100%;
                min-height: 48px;
            }}
            
            .view-btn:hover {{
                background: linear-gradient(135deg, var(--apple-blue-hover), #003d99);
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0, 122, 255, 0.4);
                text-decoration: none;
                color: white;
            }}
            
            .view-btn:active {{
                transform: translateY(0);
            }}
            
            .icon {{
                font-size: 16px;
            }}
            
            u {{
                text-decoration: underline;
                text-decoration-color: var(--apple-blue);
                text-decoration-thickness: 2px;
                text-underline-offset: 3px;
                text-decoration-style: solid;
            }}
            
            /* Ensure no text cutoff */
            .card-body {{
                min-height: 120px;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
            }}
        </style>
    </head>
    <body>
        <!-- Ensure fonts are loaded -->
        <script>
            document.fonts.ready.then(function() {{
                document.body.classList.add('fonts-loaded');
            }});
        </script>
        
        <div class="card">
            <div class="card-header">
                <div class="badge">
                    <span class="icon">{('📰' if badge == 'News' else '👽' if badge == 'Reddit' else '📘' if badge == 'Facebook' else '📺' if badge == 'YouTube' else '📷' if badge == 'Instagram' else '📄')}</span>
                    {py_html.escape(badge)}
                </div>
                <div class="age">{py_html.escape(age_text)}</div>
            </div>
            
            <div class="card-body">
                <!-- Force consistent font styling -->
                <style>
                    .title, .preview {{
                        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
                    }}
                </style>
                
                <!-- Title always visible -->
                <div class="title">{title_html}</div>
                
                <!-- Image if available -->
                {f'''<div class="image-container">
                    <img class="image" src="{py_html.escape(image_url)}" alt="Content image" loading="lazy" referrerpolicy="no-referrer">
                </div>''' if image_url else ''}
                
                <!-- Preview content only if it adds value beyond the title -->
                {f'<div class="preview">{summary_html}</div>' if summary_html else ''}
            </div>
            
            {f'''<div class="card-footer">
                <a href="{py_html.escape(link)}" target="_blank" rel="noopener" class="view-btn">
                    <span class="icon">🔗</span> Read More
                </a>
            </div>''' if link else ''}
        </div>
    </body>
    </html>
    """)
    
    # Calculate appropriate height based on content
    if height is None:
        # Base height for card with just title and header/footer
        base = 280
        
        # Add space for image if present
        if image_url: 
            base += 220  # Space for image and margins
            
        # Add space for content preview based on its length
        if summary_html:
            # Roughly estimate 24px per line of text (assuming 60 chars per line)
            text_length = len(summary_html)
            estimated_lines = min(4, max(1, text_length // 60))
            base += estimated_lines * 24 + 30  # Add lines plus margins
            
        # Add space for longer titles (assuming line breaks)
        title_length = len(title)
        if title_length > 30:
            estimated_title_lines = min(3, max(1, title_length // 30))
            base += (estimated_title_lines - 1) * 24  # Add space for extra lines
            
        # Ensure reasonable bounds for the card height
        height = min(max(base, 250), 750)  # Minimum 250px, maximum 750px
        
        # Adjust height for cloud environment
        if IN_CLOUD:
            height += 50  # Add extra padding in cloud environment
        
    st_html(html, height=height, scrolling=False)

def render_news_card(item):
    title = _first(getattr(item, "title", None), item.get("title") if hasattr(item, 'get') else getattr(item, 'title', None))
    summary = _first(getattr(item, "summary", None), getattr(item, "description", None), getattr(item, "content", None),
                     item.get("summary") if hasattr(item, 'get') else None,
                     item.get("description") if hasattr(item, 'get') else None,
                     item.get("content") if hasattr(item, 'get') else None)
    image = _first(getattr(item, "image_url", None), getattr(item, "image", None),
                   item.get("image_url") if hasattr(item, 'get') else None,
                   item.get("image") if hasattr(item, 'get') else None)
    link = _first(getattr(item, "url", None), getattr(item, "link", None),
                  item.get("url") if hasattr(item, 'get') else None,
                  item.get("link") if hasattr(item, 'get') else None)
    age = _first(getattr(item, "age_text", None), 
                 time_ago(getattr(item, "posted_at", None)),
                 item.get("age_text") if hasattr(item, 'get') else None)
    _render_card(title, summary, image, age, link, badge="News")

def render_reddit_card(post):
    title = _first(getattr(post, "title", None), post.get("title") if hasattr(post, 'get') else None)
    summary = _first(getattr(post, "selftext", None), getattr(post, "content", None),
                     post.get("selftext") if hasattr(post, 'get') else None,
                     post.get("content") if hasattr(post, 'get') else None)
    thumb = _first(getattr(post, "thumbnail", None), getattr(post, "image_url", None),
                   post.get("thumbnail") if hasattr(post, 'get') else None,
                   post.get("image_url") if hasattr(post, 'get') else None)
    # Build a proper link if we only have permalink
    link = _first(getattr(post, "url", None), getattr(post, "permalink", None),
                  post.get("url") if hasattr(post, 'get') else None,
                  ("https://reddit.com" + post.get("permalink")) if hasattr(post, 'get') and post.get("permalink") else None)
    age = _first(getattr(post, "age_text", None), 
                 time_ago(getattr(post, "posted_at", None)),
                 post.get("age_text") if hasattr(post, 'get') else None)
    _render_card(title, summary, thumb, age, link, badge="Reddit")

def render_facebook_card(post):
    title = _first(getattr(post, "title", None), getattr(post, "page_name", None),
                   post.get("title") if hasattr(post, 'get') else None,
                   post.get("page_name") if hasattr(post, 'get') else None)
    summary = _first(getattr(post, "text", None), getattr(post, "content", None),
                     post.get("text") if hasattr(post, 'get') else None,
                     post.get("content") if hasattr(post, 'get') else None)
    image = _first(getattr(post, "image", None), getattr(post, "image_url", None),
                   post.get("image") if hasattr(post, 'get') else None,
                   post.get("image_url") if hasattr(post, 'get') else None)
    link = _first(getattr(post, "post_url", None), getattr(post, "url", None),
                  post.get("post_url") if hasattr(post, 'get') else None,
                  post.get("url") if hasattr(post, 'get') else None)
    age = _first(getattr(post, "age_text", None), 
                 time_ago(getattr(post, "posted_at", None)),
                 post.get("age_text") if hasattr(post, 'get') else None)
    _render_card(title, summary, image, age, link, badge="Facebook")

def render_youtube_card(video):
    title = _first(getattr(video, "title", None), video.get("title") if hasattr(video, 'get') else None)
    title = title[:min(124, len(title))].rjust(124)
    summary = _first(getattr(video, "description", None), getattr(video, "content", None),
                     video.get("description") if hasattr(video, 'get') else None,
                     video.get("content") if hasattr(video, 'get') else None)
    thumb = _first(getattr(video, "thumbnail", None), getattr(video, "image_url", None),
                   video.get("thumbnail") if hasattr(video, 'get') else None,
                   video.get("image_url") if hasattr(video, 'get') else None)
    link = _first(getattr(video, "url", None), getattr(video, "watch_url", None),
                  video.get("url") if hasattr(video, 'get') else None,
                  video.get("watch_url") if hasattr(video, 'get') else None)
    age = _first(getattr(video, "age_text", None), 
                 time_ago(getattr(video, "posted_at", None)),
                 video.get("age_text") if hasattr(video, 'get') else None)
    _render_card(title, summary, thumb, age, link, badge="YouTube")

def render_instagram_card(post):
    title = _first(getattr(post, "username", None), post.get("username") if hasattr(post, 'get') else None)
    summary = _first(getattr(post, "caption", None), getattr(post, "content", None),
                     post.get("caption") if hasattr(post, 'get') else None,
                     post.get("content") if hasattr(post, 'get') else None)
    image = _first(getattr(post, "display_url", None), getattr(post, "image_url", None),
                   post.get("display_url") if hasattr(post, 'get') else None,
                   post.get("image_url") if hasattr(post, 'get') else None)
    link = _first(getattr(post, "url", None), post.get("url") if hasattr(post, 'get') else None)
    age = _first(getattr(post, "age_text", None), 
                 time_ago(getattr(post, "posted_at", None)),
                 post.get("age_text") if hasattr(post, 'get') else None)
    _render_card(title, summary, image, age, link, badge="Instagram")


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
        # Only use BeautifulSoup if content actually looks like HTML
        if "<" in raw_content and ">" in raw_content and ("</" in raw_content or "<!DOCTYPE" in raw_content or "<html" in raw_content):
            try:
                soup = BeautifulSoup(raw_content, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href")
                    if href:
                        a.replace_with(f"{a.get_text(' ', strip=True)} ({href})")
                return soup.get_text(" ", strip=True)
            except Exception:
                pass  # Fall back to regex if BeautifulSoup fails

    # Fallback: use regex to strip all HTML tags
    # First handle common HTML entities
    raw_content = raw_content.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    # Remove all HTML tags
    clean_text = _re.sub(r"<[^>]+>", "", raw_content)
    # Clean up extra whitespace
    clean_text = _re.sub(r"\s+", " ", clean_text).strip()
    return clean_text


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

# st.set_page_config moved to the top of the file

# Directly inject font links in the head section to ensure proper loading - using iframe to avoid CSP issues
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
/* Set global font fallback system */
.stApp, .stApp * {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif !important;
}

/* Fix card container widths */
.element-container {
    width: 100%;
}

/* Ensure columns have consistent widths */
[data-testid="column"] {
    width: 100% !important;
    flex: 1 1 auto !important;
    min-width: 0 !important;
}

/* Better mobile responsiveness */
@media (max-width: 640px) {
    .stApp [data-testid="column"] {
        width: 100% !important;
        margin-bottom: 1rem !important;
    }
}
</style>
""", height=0)

# Apple-inspired Custom CSS with unified typography
st.markdown(dedent("""
<style>
/* SF Pro Font Definitions */
@font-face {{
    font-family: 'SF Pro Display';
    src: local('SF Pro Display'), 
         url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-regular-webfont.woff') format('woff');
    font-weight: 400;
    font-display: swap;
}}
@font-face {{
    font-family: 'SF Pro Display';
    src: local('SF Pro Display Medium'), 
         url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-medium-webfont.woff') format('woff');
    font-weight: 500;
    font-display: swap;
}}
@font-face {{
    font-family: 'SF Pro Display';
    src: local('SF Pro Display Semibold'), 
         url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-semibold-webfont.woff') format('woff');
    font-weight: 600;
    font-display: swap;
}}
@font-face {{
    font-family: 'SF Pro Text';
    src: local('SF Pro Text'), 
         url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscotext-regular-webfont.woff') format('woff');
    font-weight: 400;
    font-display: swap;
}}
@font-face {{
    font-family: 'SF Pro Text';
    src: local('SF Pro Text Medium'), 
         url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscotext-medium-webfont.woff') format('woff');
    font-weight: 500;
    font-display: swap;
}}

/* Preload fonts for better performance */

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
/* Main app background: white */
.main .block-container {
    background-color: #fff !important;
    padding: 1.5rem !important;
    max-width: 1200px !important;
    font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
    line-height: 1.5 !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.04);
    border-radius: 18px;
}

/* Beautiful main header */
.main-header {
    background: linear-gradient(135deg, var(--apple-blue), #5856D6);
    padding: 2rem 1.2rem;
    border-radius: 20px;
    margin-bottom: 1.2rem;
    text-align: center;
    color: white;
    box-shadow: 0 8px 24px rgba(0, 122, 255, 0.18);
    border: 1px solid rgba(255, 255, 255, 0.08);
}

.main-header h1 {
    color: white !important;
    font-weight: 700 !important;
    font-size: 2rem !important;
    margin-bottom: 0.5rem !important;
    letter-spacing: -0.01em !important;
    font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
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

.main-header p {
    color: rgba(255, 255, 255, 0.9) !important;
    font-size: 1.125rem !important;
    font-weight: 400 !important;
    line-height: 1.5 !important;
    font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
}

/* Enhanced metric cards */
.metric-card {
    background: var(--apple-card);
    padding: 1.1rem 0.8rem;
    border-radius: 14px;
    box-shadow: 0 2px 10px var(--apple-shadow);
    text-align: center;
    border: 1px solid var(--apple-border);
    transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    position: relative;
    overflow: hidden;
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, var(--apple-blue), #5856D6, #FF9500);
}

.metric-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 30px var(--apple-shadow-hover);
}

.metric-card h3 {
    font-size: 2.5rem !important;
    font-weight: 700 !important;
    margin: 0.5rem 0 !important;
    background: linear-gradient(135deg, var(--apple-blue), #5856D6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
}

.metric-card p {
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    color: var(--apple-text-secondary) !important;
    margin: 0 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif !important;
}

/* Enhanced topic cards */
.topic-card {
    background: var(--apple-card);
    border-radius: 20px;
    padding: 2rem;
    margin: 1.5rem 0;
    box-shadow: 0 4px 20px var(--apple-shadow);
    transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    border: 1px solid var(--apple-border);
    position: relative;
    overflow: hidden;
}

.topic-card:hover {
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 12px 40px var(--apple-shadow-hover);
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
/* Enhanced sidebar with light grey background */
.css-1d391kg, .css-1kyxreq, [data-testid="stSidebar"] {
    background-color: var(--sidebar-bg) !important;
    border-right: 1px solid var(--sidebar-border) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
    box-shadow: 2px 0 8px rgba(0,0,0,0.03);
}

/* Better tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background-color: var(--light-gray);
    border-radius: 10px;
    padding: 4px;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
    font-weight: 500 !important;
    padding: 12px 20px !important;
    border-radius: 8px !important;
    background-color: transparent !important;
    color: var(--text-secondary) !important;
    border: none !important;
    transition: all 0.2s ease !important;
}

.stTabs [data-baseweb="tab"]:hover {
    background-color: var(--card-bg) !important;
    color: var(--text-primary) !important;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background-color: var(--card-bg) !important;
    color: var(--text-primary) !important;
    box-shadow: 0 2px 8px var(--card-shadow) !important;
}

/* Metric display improvements */
.stMetric {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
}

.stMetric > div {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
}

.stMetric [data-testid="metric-value"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
    font-weight: 700 !important;
    font-size: 2rem !important;
}

.stMetric [data-testid="metric-label"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
    font-weight: 500 !important;
    color: var(--text-secondary) !important;
}

/* Info boxes */
.stInfo, .stSuccess, .stWarning, .stError {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
    border-radius: 10px !important;
    border: none !important;
}

/* Input fields */
.stTextInput input, .stSelectbox select, .stTextArea textarea {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
    border-radius: 8px !important;
    border: 1px solid var(--card-border) !important;
    background-color: var(--card-bg) !important;
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

if not ENV_LOADED:
    st.sidebar.info(
        "No .env file found. Using defaults; some features may be limited. "
        "Copy .env.example to .env to add your own keys."
    )

if not get_secret("REDDIT_CLIENT_ID") or not get_secret("REDDIT_CLIENT_SECRET"):
    st.sidebar.warning(
        "Reddit credentials missing. Reddit posts won't be collected. "
        "Create a Reddit app and set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env."
    )


if not get_secret("NEWSAPI_KEY"):
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
    import re
    import bs4  # type: ignore  # noqa: F401
except Exception:
    st.sidebar.info(
        "Photo searching requires `requests` and `beautifulsoup4`. Install with `pip install requests beautifulsoup4` to enable."
    )

if not get_secret("UNSPLASH_ACCESS_KEY") and not get_secret("PEXELS_API_KEY"):
    st.sidebar.error(
        "🚨 **No Photo Search Configured**\n\n"
        "To get actual photos of your subjects:\n\n"
        "1. **Unsplash** (recommended): Get free key at unsplash.com/developers\n"
        "2. **Pexels**: Get free key at pexels.com/api\n\n"
        "Add to .env file or Streamlit Cloud secrets:\n"
        "```\n"
        "UNSPLASH_ACCESS_KEY=your_key\n"
        "PEXELS_API_KEY=your_key\n"
        "```\n\n"
        "Without API keys, no photos will be collected."
    )

# Facebook scraping now works via web search - no packages needed


if not get_secret("OLLAMA_MODEL"):
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
# ...existing sidebar content...

# --- Newsletter Frequency Option (now truly at the bottom) ---
def render_newsletter_freq():
    import json
    import pathlib
    
    # Add better heading at the top
    st.sidebar.markdown("### 📧 Newsletter Settings")
    
    FREQ_FILE = pathlib.Path(".newsletter_freq.json")
    FREQ_OPTIONS = [
        ("Daily", {"type": "cron", "minute": 0, "hour": 8}),
        ("Weekly", {"type": "cron", "minute": 0, "hour": 8, "day_of_week": "mon"}),
        ("Monthly", {"type": "cron", "minute": 0, "hour": 8, "day": 1}),
        # Removed "Every 1 day" as it's redundant with "Daily"
        ("Every 2 days", {"type": "interval", "days": 2}),
        ("Every 3 days", {"type": "interval", "days": 3}),
        ("Every 4 days", {"type": "interval", "days": 4}),
        ("Every 5 days", {"type": "interval", "days": 5}),
        ("Every 6 days", {"type": "interval", "days": 6}),
    ]
    default_freq = "Daily"
    saved_freq = default_freq
    if FREQ_FILE.exists():
        try:
            saved_freq = json.loads(FREQ_FILE.read_text()).get("freq", default_freq)
        except Exception:
            saved_freq = default_freq
    freq_labels = [x[0] for x in FREQ_OPTIONS]
    selected_freq = st.sidebar.selectbox(
        "How often to send the newsletter?",
        freq_labels,
        index=freq_labels.index(saved_freq) if saved_freq in freq_labels else 0,
        key="newsletter_freq_selectbox"
    )
    if selected_freq != saved_freq:
        FREQ_FILE.write_text(json.dumps({"freq": selected_freq}))
        st.sidebar.success(f"✅ Frequency set to: {selected_freq}. Please restart the app to apply.")

# ...existing code for main app and sidebar...

# --- Send Digest Mail Now (send full digest for all topics) ---
with st.sidebar.expander("📧 Send Digest Mail Now (All Topics)", expanded=False):
    digest_email = st.text_input("Target Email Address", key="digest_all_email")
    
    # Track email sending status in session state
    if "email_sending" not in st.session_state:
        st.session_state.email_sending = False
    if "email_status" not in st.session_state:
        st.session_state.email_status = None
    
    # Show status if email is currently being sent
    if st.session_state.email_sending:
        st.info("📤 Sending email in background... You can continue using the app.")
    
    # Show results of previous send operation
    if st.session_state.email_status == "success":
        st.success(f"✅ Full digest sent to {st.session_state.get('last_email', '')}!")
        st.session_state.email_status = None  # Reset after showing
    elif st.session_state.email_status == "failure":
        st.error(f"❌ Failed to send digest to {st.session_state.get('last_email', '')}.")
        st.session_state.email_status = None  # Reset after showing
        
    if st.button("Send Full Digest Now", key="digest_all_btn", disabled=st.session_state.email_sending):
        if not digest_email:
            st.warning("Please enter an email address.")
        else:
            import threading
            import traceback
            from monitoring.notifier import create_digest_html, send_email
            
            # Store the email for status messages
            st.session_state.last_email = digest_email
            st.session_state.email_sending = True
            
            # Function to run in background thread
            def send_digest_in_background():
                try:
                    topics = session.query(Topic).all()
                    all_posts = []
                    for topic in topics:
                        posts = (
                            session.query(Post)
                            .filter_by(topic_id=topic.id)
                            .order_by(Post.posted_at.desc())
                            .limit(10)
                            .all()
                        )
                        for post in posts:
                            all_posts.append({
                                'content': post.content,
                                'url': post.url,
                                'source': post.source,
                                'posted_at': post.posted_at,
                                'likes': post.likes,
                                'comments': post.comments,
                                'topic': topic.name
                            })
                    if not all_posts:
                        print("[DEBUG] No posts found for any topic.")
                        st.session_state.email_status = "failure"
                    else:
                        summary = f"Digest includes {len(all_posts)} posts from {len(topics)} topics."
                        html_body = create_digest_html("All Topics", all_posts, summary)
                        print(f"[DEBUG] Sending digest to {digest_email} with {len(all_posts)} posts.")
                        success = send_email(digest_email, "📰 Full Digest: All Topics", html_body, 'html')
                        if success:
                            print(f"[DEBUG] Digest sent to {digest_email} successfully.")
                            st.session_state.email_status = "success"
                        else:
                            print(f"[DEBUG] Failed to send digest to {digest_email}.")
                            st.session_state.email_status = "failure"
                except Exception as e:
                    print(f"[DEBUG] Exception: {e}\n{traceback.format_exc()}")
                    st.session_state.email_status = "failure"
                finally:
                    # Always reset the sending flag when done
                    st.session_state.email_sending = False
            
            # Start the background thread and notify user
            thread = threading.Thread(target=send_digest_in_background)
            thread.daemon = True  # Allow the thread to be killed when the app exits
            thread.start()
            st.info("📤 Sending email in background... You can continue using the app.")
            st.experimental_rerun()  # Rerun to show the status immediately

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

# Add email testing section if email is configured
if get_secret("SMTP_HOST") or get_secret("SMTP_SERVER") or get_secret("BREVO_API"):
    with st.sidebar.expander("📧 **Test Email Digest**"):
        # Track test email sending status in session state
        if "test_email_sending" not in st.session_state:
            st.session_state.test_email_sending = False
        if "test_email_status" not in st.session_state:
            st.session_state.test_email_status = None
            
        test_email = st.text_input("📧 Test Email", placeholder="your@email.com")
        
        # Show status if email is currently being sent
        if st.session_state.test_email_sending:
            st.info("📤 Sending test email in background... You can continue using the app.")
        
        # Show results of previous send operation
        if st.session_state.test_email_status == "success":
            st.success(f"✅ Test digest sent to {st.session_state.get('last_test_email', '')}!")
            st.session_state.test_email_status = None  # Reset after showing
        elif st.session_state.test_email_status == "failure":
            st.error(f"❌ Failed to send test digest to {st.session_state.get('last_test_email', '')}.")
            st.session_state.test_email_status = None  # Reset after showing
            
        if topic_names:
            test_topic = st.selectbox("Select Topic", topic_names)
            if st.button("📨 **Send Test Digest**", use_container_width=True, disabled=st.session_state.test_email_sending) and test_email and test_topic:
                import threading
                
                # Store the email for status messages
                st.session_state.last_test_email = test_email
                st.session_state.test_email_sending = True
                
                # Function to run in background thread
                def send_test_digest_in_background():
                    try:
                        topic_obj = session.query(Topic).filter_by(name=test_topic).first()
                        if topic_obj:
                            success = send_test_digest(topic_obj.id, test_email)
                            if success:
                                st.session_state.test_email_status = "success"
                                print(f"[DEBUG] Test digest sent to {test_email} successfully.")
                            else:
                                st.session_state.test_email_status = "failure"
                                print(f"[DEBUG] Failed to send test digest to {test_email}.")
                    except Exception as e:
                        import traceback
                        print(f"[DEBUG] Exception sending test digest: {e}\n{traceback.format_exc()}")
                        st.session_state.test_email_status = "failure"
                    finally:
                        # Always reset the sending flag when done
                        st.session_state.test_email_sending = False
                
                # Start the background thread and notify user
                thread = threading.Thread(target=send_test_digest_in_background)
                thread.daemon = True  # Allow the thread to be killed when the app exits
                thread.start()
                st.info("📤 Sending test email in background... You can continue using the app.")
                st.experimental_rerun()  # Rerun to show the status immediately
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

# Place the newsletter frequency control at the very end of the sidebar
st.sidebar.markdown("---")
render_newsletter_freq()

session.close()


# Load topics for main view
topics = session.query(Topic).all()

if st.session_state.selected_topic is None:
    if not topics:
        # Beautiful welcome screen
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
    else:
        # Topic overview with enhanced Apple-style cards



        # Apple glassmorphic metrics summary (ultra-modern, Apple-style)
        total_posts = session.query(Post).count()
        active_topics = len([t for t in topics if t.last_collected])
        recently_updated = len([t for t in topics if t.last_collected and (datetime.utcnow() - t.last_collected).days < 1])
        posts_today = session.query(Post).filter(Post.posted_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)).count()
        posts_last_7d = session.query(Post).filter(Post.posted_at >= datetime.utcnow() - timedelta(days=7)).count()
        most_active_topic = None
        most_active_count = 0
        if topics:
            topic_post_counts = [(t.name, session.query(Post).filter_by(topic_id=t.id).count()) for t in topics]
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

        st.markdown("---")
        
        # Topic cards in responsive grid layout
        cols = st.columns(min(len(topics), 3))
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
                    overflow: hidden;
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
                            ">{topic.name}</h3>
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
                    df_mini = pd.DataFrame([{"posted_at": p.posted_at} for p in posts])
                    df_mini["date"] = df_mini["posted_at"].dt.date
                    daily_mini = df_mini.groupby("date").size()
                    
                    # Create a simple line chart with better styling
                    fig_mini = px.line(
                        x=daily_mini.index, 
                        y=daily_mini.values,
                        title=None,
                        color_discrete_sequence=[topic.color]
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
                    
                    # Source breakdown with enhanced badges
                    sources = pd.DataFrame([{"source": p.source} for p in posts])
                    source_counts = sources.groupby("source").size()
                    
                    source_badges = ""
                    for source, count in source_counts.items():
                        icon = SOURCE_ICONS.get(source, "📄")
                        badge_class = f"{source}-badge"
                        source_badges += f'<span class="source-badge {badge_class}">{icon} {count}</span> '
                    
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
                    st.info("No posts collected yet")
                
                # Apple-style explore button
                if st.button("🔍 **Explore**", key=f"open_{topic.id}", use_container_width=True, type="primary"):
                    st.session_state.selected_topic = topic.id
                    st.rerun()
                
else:
    topic = session.get(Topic, st.session_state.selected_topic)
    if not topic:
        st.error("Topic not found!")
        st.session_state.selected_topic = None
        st.rerun()
        
    # Create a container for our combined header and home button
    header_container = st.container()

    # Redesigned Apple-style topic header with the visible title
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

    # Render a Streamlit button for "Home" aligned to the right side of the UI
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
    
    if posts:
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
                "subreddit": getattr(p, 'subreddit', None),  # Add subreddit info
            }
            for p in posts
        ])        # Enhanced metrics section with proper Streamlit components
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
        
        # Analytics section (excluding photos as they're for browsing, not trend analysis)
        st.markdown('<h2 class="section-heading">📈 Analytics</h2>', unsafe_allow_html=True)
        
        # Use regular posts for analytics, not photos
        analytics_df = regular_posts_df.copy()
        analytics_df["date"] = analytics_df["posted_at"].dt.date
        daily = analytics_df.groupby("date").size().reset_index(name="mentions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Enhanced time series chart with consistent Inter font
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
        
        with col2:
            # Source distribution with consistent fonts
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

        # Posts sections with tabs
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
            "🕒 Recent", "📰 News", "🐦 Reddit", "📷 Instagram", "📘 Facebook", "📺 YouTube", "🖼️ Photos", "🐦 Tweets", "🤖 AI Summary"
        ])
        
        with tab1:
            st.markdown('<h3 class="section-heading">🕒 Recent Posts</h3>', unsafe_allow_html=True)
            # Filter out photos and YouTube from recent posts - they should only appear in their dedicated tabs
            recent_df = df[(df["source"] != "photos") & (df["source"] != "youtube")]
            # Define tab order for sources: news and reddit equally first, then instagram, facebook, twitter
            def _source_rank(s):
                if s in ("news", "reddit"): return 0
                elif s == "instagram": return 1
                elif s == "facebook": return 2
                elif s == "twitter": return 3
                return 4
            recent_df["_source_order"] = recent_df["source"].apply(_source_rank)
            # Sort by source order, then by posted_at descending
            recent_df = recent_df.sort_values(["_source_order", "posted_at"], ascending=[True, False])
            if not recent_df.empty:
                # Gallery view with two columns for better browsing
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
                            # Render tweets in a simple card
                            st.markdown(f"""
                                <div style='background:rgba(255,255,255,0.7);border-radius:12px;padding:1rem;margin-bottom:1rem;box-shadow:0 2px 8px #0001;'>
                                    <div style='font-size:1.1rem;line-height:1.5;'>{py_html.escape(row.get('text', row.get('content', '')))}</div>
                                    <div style='margin-top:0.5rem;font-size:0.9rem;color:#888;'>
                                        <a href='{row.get('url','')}' target='_blank'>View on Nitter</a> · {row.get('author','')} · {time_ago(row['posted_at'] if 'posted_at' in row else row.get('created_at'))}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            title = _first(row.get("title", ""), row.get("content", "")[:80])
                            summary = _first(row.get("summary", ""), row.get("content", ""))
                            image = row.get("image_url", "")
                            link = row.get("url", "")
                            age = time_ago(row["posted_at"] if "posted_at" in row else row.get("created_at"))
                            source_name = row["source"].title()
                            _render_card(title, summary, image, age, link, badge=source_name, topic_name=topic.name)
            else:
                st.info("No recent posts found. Try collecting data from sources other than photos.")
        
        with tab2:
            news_df = df[df["source"] == "news"]
            if not news_df.empty:
                st.markdown('<h3 class="section-heading">📰 Latest News Articles</h3>', unsafe_allow_html=True)
                st.markdown(f"Found **{len(news_df)}** news articles")
                
                # Gallery view with two columns for easier browsing
                news_items = news_df.sort_values("posted_at", ascending=False).head(20)
                
                # Create two-column layout
                col1, col2 = st.columns(2)
                
                for idx, (_, row) in enumerate(news_items.iterrows()):
                    # Alternate between columns
                    current_col = col1 if idx % 2 == 0 else col2
                    
                    with current_col:
                        render_news_card(row)
                
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
                st.markdown('<h3 class="section-heading">👽 Reddit Posts</h3>', unsafe_allow_html=True)
                
                # Gallery view with two columns
                reddit_items = reddit_df.sort_values("posted_at", ascending=False).head(10)
                
                # Create two-column layout
                col1, col2 = st.columns(2)
                
                for idx, (_, row) in enumerate(reddit_items.iterrows()):
                    # Alternate between columns
                    current_col = col1 if idx % 2 == 0 else col2
                    
                    with current_col:
                        render_reddit_card(row)
            else:
                st.info("No Reddit posts found for this topic.")
        
        with tab4:
            instagram_df = df[df["source"] == "instagram"]
            if not instagram_df.empty:
                st.markdown('<h3 class="section-heading">📷 Instagram Posts</h3>', unsafe_allow_html=True)
                
                # Gallery view with two columns
                instagram_items = instagram_df.sort_values("posted_at", ascending=False).head(10)
                
                # Create two-column layout
                col1, col2 = st.columns(2)
                
                for idx, (_, row) in enumerate(instagram_items.iterrows()):
                    # Alternate between columns
                    current_col = col1 if idx % 2 == 0 else col2
                    
                    with current_col:
                        render_instagram_card(row)
            else:
                st.info("No Instagram posts found for this topic.")
        
        with tab5:
            facebook_df = df[df["source"] == "facebook"]
            if not facebook_df.empty:
                st.markdown('<h3 class="section-heading">📘 Facebook Posts</h3>', unsafe_allow_html=True)
                
                # Gallery view with two columns
                facebook_items = facebook_df.sort_values("posted_at", ascending=False).head(10)
                
                # Create two-column layout
                col1, col2 = st.columns(2)
                
                for idx, (_, row) in enumerate(facebook_items.iterrows()):
                    # Alternate between columns
                    current_col = col1 if idx % 2 == 0 else col2
                    
                    with current_col:
                        render_facebook_card(row)
            else:
                st.info("No Facebook posts found for this topic.")
        
        with tab6:
            youtube_df = df[df["source"] == "youtube"]
            if not youtube_df.empty:
                st.markdown('<h3 class="section-heading">📺 YouTube Videos</h3>', unsafe_allow_html=True)
                
                # Gallery view with two columns
                youtube_items = youtube_df.sort_values("posted_at", ascending=False).head(15)
                
                # Create two-column layout
                col1, col2 = st.columns(2)
                
                for idx, (_, row) in enumerate(youtube_items.iterrows()):
                    # Alternate between columns
                    current_col = col1 if idx % 2 == 0 else col2
                    
                    with current_col:
                        render_youtube_card(row)
            else:
                st.info("No YouTube videos found for this topic.")
        
        with tab7:
            # Photos tab - show all photo content and dedicated photo searches
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
                st_html(dedent("""
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
                """), height=350)

        # Tweets tab
        with tab8:
            st.markdown('<h3 class="section-heading">🐦 Tweets (via Nitter)</h3>', unsafe_allow_html=True)
            tweets_df = df[df["source"] == "twitter"]
            if not tweets_df.empty:
                for _, tweet in tweets_df.iterrows():
                    st.markdown(f"""
                        <div style='background:rgba(255,255,255,0.7);border-radius:12px;padding:1rem;margin-bottom:1rem;box-shadow:0 2px 8px #0001;'>
                            <div style='font-size:1.1rem;line-height:1.5;'>{py_html.escape(tweet['content'])}</div>
                            <div style='margin-top:0.5rem;font-size:0.9rem;color:#888;'>
                                <a href='{tweet['url']}' target='_blank'>View on Nitter</a> · {tweet['likes']} Likes · {tweet['comments']} Replies
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No tweets found for this topic.")
        
        with tab9:
            st.markdown('<h3 class="section-heading">🤖 AI-Generated Summary</h3>', unsafe_allow_html=True)
            with st.spinner("Generating AI summary..."):
                try:
                    # Use regular posts for AI summary, not photos
                    summary_content = analytics_df["content"].head(20).tolist()
                    summary_text = strip_think(summarize(summary_content)).strip()

                    # Convert lines and inline " - " (and similar) bullets to HTML list items, preserving spacing
                    def _to_bulleted_html(text: str) -> tuple[str, int]:
                        # First, split text at " - " to handle inline bullets, but preserve real line breaks
                        split_text = []
                        for line in (text or "").splitlines():
                            # Split the line at " - " but keep empty strings to preserve positioning
                            parts = [p for p in line.split(" - ")]
                            # Add the first part
                            if parts[0].strip():
                                split_text.append(parts[0].strip())
                            # Add remaining parts with bullet points
                            for part in parts[1:]:
                                if part.strip():
                                    split_text.append("- " + part.strip())

                        lines = split_text
                        parts: list[str] = []
                        in_list = False
                        non_empty_line_count = 0

                        # Matches bullets at line start: -, *, •
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

                            # Case 1: bullet at the beginning of the line
                            if start_bullet_re.match(line):
                                if not in_list:
                                    parts.append('<ul style="margin: 0.75rem 0; padding-left: 1.5rem; list-style-position: outside;">')
                                    in_list = True
                                item = start_bullet_re.sub('', line).strip()
                                if item:
                                    parts.append(f'<li style="margin-bottom: 0.5rem;">{py_html.escape(item)}</li>')
                                    non_empty_line_count += 1
                                continue

                            # All non-bullet text becomes a paragraph
                            if not start_bullet_re.match(line):
                                close_list()
                                parts.append(f'<p style="margin: 0 0 0.5rem 0;">{py_html.escape(line)}</p>')
                                non_empty_line_count += 1
                                continue

                            # Default: regular paragraph
                            close_list()
                            parts.append(f'<p style="margin: 0 0 0.5rem 0;">{py_html.escape(line)}</p>')
                            non_empty_line_count += 1

                        close_list()
                        html = "".join(parts) if parts else f"<p>{py_html.escape(text)}</p>"
                        return html, non_empty_line_count

                    summary_html_body, line_count = _to_bulleted_html(summary_text)

                    # Adjust height to avoid clipping when there are many lines/items
                    # Increased base height and per-line height to prevent truncation
                    computed_height =  180 + line_count * 30

                    st_html(dedent(f"""
                    <div style="
                        background: #f8f9fa; 
                        padding: 1.5rem; 
                        border-radius: 10px; 
                        border-left: 4px solid {topic.color};
                        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                        color: #1C1C1E;
                        line-height: 1.8;
                        font-size: 18px;
                    ">
                        <div style="font-family: inherit; color: inherit;">
                            {summary_html_body}
                        </div>
                    </div>
                    """), height=computed_height)
                except Exception as e:
                    st.error(f"Failed to generate summary: {e}")
                    
    else:
        st_html(dedent("""
        <div style="text-align: center; padding: 3rem; background: #f8f9fa; border-radius: 15px;">
            <h3>📭 No posts collected yet</h3>
            <p>Click "Collect All Topics Now" in the sidebar to start gathering data.</p>
        </div>
        """), height=200)
    
    # Update last viewed
    topic.last_viewed = datetime.utcnow()
    session.commit()

session.close()

