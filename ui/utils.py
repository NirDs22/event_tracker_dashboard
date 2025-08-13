"""Utility functions for text processing and data handling."""

import re
from datetime import datetime
from typing import Any, Optional

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


def _first(*vals):
    """Return the first non-empty value from the arguments."""
    for v in vals:
        if v not in (None, "", [], {}):
            return v
    return ""


def _to_text(x):
    """Convert any input to clean, usable text by removing HTML and normalizing whitespace."""
    if x is None: 
        return ""
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


def time_ago(dt: Optional[datetime]) -> str:
    """Return a human-readable time difference string."""
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


def clean_content(raw: str) -> str:
    """Return plain text with inline links, stripping any HTML tags."""
    import html as _html
    from monitoring.summarizer import strip_think
    
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
    clean_text = re.sub(r"<[^>]+>", "", raw_content)
    # Clean up extra whitespace
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    return clean_text


def contains_hebrew(text: str) -> bool:
    """Check if the text contains Hebrew characters."""
    hebrew_re = re.compile(r"[\u0590-\u05FF]")
    return bool(hebrew_re.search(text))
