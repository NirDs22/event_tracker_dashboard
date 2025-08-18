"""Card rendering components for different content types."""

import html as py_html
import re
from textwrap import dedent
from streamlit.components.v1 import html as st_html
from typing import Optional
import streamlit as st

from .utils import _first, _to_text, time_ago


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
    
    # Escape the topic name for regex and create case-insensitive pattern
    escaped_topic = py_html.escape(topic_name)
    try:
        pattern = re.compile(re.escape(escaped_topic), re.IGNORECASE)
        result = pattern.sub(f'<u>{escaped_topic}</u>', py_html.escape(text))
        return result
    except Exception:
        return py_html.escape(text)


def render_card(title, summary, image_url, age_text, link, badge="News", topic_name=None, height=None):
    """Render a content card with proper title and summary display.
    Contract:
    - Inputs: raw title/summary may be None/HTML; image/link optional; badge text.
    - Behavior: derive a sensible title when missing, show preview only if it adds info beyond title, and avoid duplicates.
    - Output: Renders a Streamlit HTML component with consistent typography.
    """
    import os
    
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
                margin: 0;
                width: 100%;
                box-sizing: border-box;
            }}
            
            .card {{
                background: var(--apple-card);
                border-radius: 16px;
                box-shadow: 0 4px 20px var(--apple-shadow);
                border: 1px solid var(--apple-border);
                overflow: visible;
                transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                height: auto;
                min-height: 200px;
                width: 100%;
                display: flex;
                flex-direction: column;
                position: relative;
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
                box-sizing: border-box;
                margin: 0 auto;
                max-width: 550px; /* Fixed width for cards */
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
                overflow: visible;
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
        
        # Adjust height for cloud environment - more aggressive adjustment
        if IN_CLOUD:
            # Add significant padding in cloud environment
            height += 100  # More padding to prevent content cutoff
            
            # Additional height for specific card types
            if image_url:
                height += 50  # More space for image cards
            if summary_html and len(summary_html) > 100:
                height += 40  # More space for long text
        
    st_html(html, height=height, scrolling=True)


def render_news_card(item, tab_context=""):
    """Render a news article card"""
    import os
    IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit_sharing" or os.environ.get("STREAMLIT_SERVER_HEADLESS") == "true"
    
    # Create a container div for better layout in cloud with fixed width
    if IS_CLOUD:
        st.markdown('<div class="card-container card-fixed-width" style="width:100%; max-width:900px; margin:0 auto 20px auto;">', unsafe_allow_html=True)
    
    # Extract data from item
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
    
    # Render the card
    render_card(title, summary, image, age, link, badge="News")

    # TL;DR button with AI summary - pass tab context for unique keys
    render_tldr_button(title, summary, content_type="news article", tab_context=tab_context)

    # Close the container div
    if IS_CLOUD:
        st.markdown('</div>', unsafe_allow_html=True)


def render_reddit_card(post):
    """Render a Reddit post card"""
    import os
    IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit_sharing" or os.environ.get("STREAMLIT_SERVER_HEADLESS") == "true"
    
    # Create a container div for better layout in cloud with fixed width
    if IS_CLOUD:
        st.markdown('<div class="card-container card-fixed-width" style="width:100%; max-width:900px; margin:0 auto 20px auto;">', unsafe_allow_html=True)
    
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
    
    render_card(title, summary, thumb, age, link, badge="Reddit")

    # TL;DR button with AI summary
    render_tldr_button(title, summary, content_type="Reddit post")

    # Close the container div
    if IS_CLOUD:
        st.markdown('</div>', unsafe_allow_html=True)


def render_facebook_card(post):
    """Render a Facebook post card"""
    import os
    IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit_sharing" or os.environ.get("STREAMLIT_SERVER_HEADLESS") == "true"
    
    # Create a container div for better layout in cloud with fixed width
    if IS_CLOUD:
        st.markdown('<div class="card-container card-fixed-width" style="width:100%; max-width:900px; margin:0 auto 20px auto;">', unsafe_allow_html=True)
        
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
                 
    render_card(title, summary, image, age, link, badge="Facebook")
    
    # TL;DR button with AI summary
    render_tldr_button(title, summary, content_type="Facebook post")
    
    # Close the container div
    if IS_CLOUD:
        st.markdown('</div>', unsafe_allow_html=True)


def render_youtube_card(video):
    """Render a YouTube video card"""
    import os
    IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit_sharing" or os.environ.get("STREAMLIT_SERVER_HEADLESS") == "true"
    
    # Create a container div for better layout in cloud with fixed width
    if IS_CLOUD:
        st.markdown('<div class="card-container card-fixed-width" style="width:100%; max-width:900px; margin:0 auto 20px auto;">', unsafe_allow_html=True)
        
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
                 
    render_card(title, summary, thumb, age, link, badge="YouTube")
    
    # TL;DR button with AI summary
    render_tldr_button(title, summary, content_type="YouTube video")
    
    # Close the container div
    if IS_CLOUD:
        st.markdown('</div>', unsafe_allow_html=True)


def render_instagram_card(post):
    """Render an Instagram post card"""
    import os
    IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit_sharing" or os.environ.get("STREAMLIT_SERVER_HEADLESS") == "true"
    
    # Create a container div for better layout in cloud with fixed width
    if IS_CLOUD:
        st.markdown('<div class="card-container card-fixed-width" style="width:100%; max-width:900px; margin:0 auto 20px auto;">', unsafe_allow_html=True)
        
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
                 
    render_card(title, summary, image, age, link, badge="Instagram")
    
    # TL;DR button with AI summary
    render_tldr_button(title, summary, content_type="Instagram post")
    
    # Close the container div
    if IS_CLOUD:
        st.markdown('</div>', unsafe_allow_html=True)

TLDR_COUNTER = 0
def render_tldr_button(title, summary, content_type="post", tab_context=""):
    """Render TL;DR button with AI summary functionality - SIMPLIFIED WORKING VERSION"""
    import hashlib
    import time
    import random

    global TLDR_COUNTER

    # Create simple unique key
    content_hash = hashlib.md5(f"{title}:{summary}".encode()).hexdigest()
    unique_key = f"tldr_{content_type.replace(' ', '_')}_{content_hash}"
    
    # Initialize session state keys
    summary_key = f"summary_{unique_key}"
    clicked_key = f"clicked_{unique_key}"
    
    if summary_key not in st.session_state:
        st.session_state[summary_key] = None
    if clicked_key not in st.session_state:
        st.session_state[clicked_key] = False
    
    # Show states based on current status
    if st.session_state[summary_key]:
        # Display the AI summary
        if "AI not answering" in str(st.session_state[summary_key]):
            st.error(f"**❌ AI Summary:** {st.session_state[summary_key]}")
        else:
            st.success(f"**🤖 AI Summary:** {st.session_state[summary_key]}")
        
        # Reset button
        if st.button("✅ Got it!", key=f"reset_{unique_key}_{int(time.time())}_{random.randint(1000, 9999)}", use_container_width=True):
            st.session_state[summary_key] = None
            st.session_state[clicked_key] = False
            st.rerun()
            
    elif st.session_state[clicked_key]:
        # Processing state - show immediately and process
        st.info("🤖 **AI is analyzing content...** Please wait.")
        
        try:
            import g4f
            
            # Create prompt using your specified format
            subject = title if title and len(title.strip()) > 3 else content_type
            prompt = f"Give a professional summary of this post or article about {subject}, No questions. - title {title}; content {summary}"

            print(f"DEBUG: Processing AI request for {unique_key}")
            print(f"DEBUG: Prompt: {prompt}")
            
            # Try different AI models
            models = ["gpt-4",  "mixtral-8x7b", "gpt-3.5-turbo"]
            ai_response = None
            
            for model in models:
                try:
                    response = g4f.ChatCompletion.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "Create concise 2-3 sentence summaries of posts and articles. No questions."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    
                    if response and len(response.strip()) > 15:
                        ai_response = response.strip()
                        print(f"DEBUG: Got response from {model}: {ai_response[:50]}...")
                        break
                        
                except Exception as e:
                    print(f"DEBUG: {model} failed: {e}")
                    continue
            
            # Store the result
            if ai_response:
                st.session_state[summary_key] = ai_response
            else:
                st.session_state[summary_key] = "AI not answering 😢"
                
            st.session_state[clicked_key] = False
            st.rerun()
            
        except Exception as e:
            print(f"DEBUG: Error processing AI: {e}")
            st.session_state[summary_key] = "AI not answering 😢"
            st.session_state[clicked_key] = False
            st.rerun()
    
    else:
        # Initial state - show TL;DR button
        try:
            if st.button("📄 TL;DR", key=f"tldr_{unique_key}", use_container_width=True):
                print(f"DEBUG: TL;DR clicked for {unique_key}")
                st.session_state[clicked_key] = True
                st.rerun()
        except st.errors.StreamlitDuplicateElementKey as e:
            print(f"DEBUG: Error showing TL;DR button: {e}")
            TLDR_COUNTER += 1
            unique_key = f"tldr_{content_type.replace(' ', '_')}_{content_hash}_{TLDR_COUNTER}"
            if st.button("📄 TL;DR", key=f"tldr_{unique_key}", use_container_width=True):
                print(f"DEBUG: TL;DR clicked for {unique_key}")
                st.session_state[clicked_key] = True
                st.rerun()
