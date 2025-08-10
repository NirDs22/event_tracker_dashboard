#!/usr/bin/env python3
"""
Script to clean existing HTML content in the database.
Run this once to fix any existing posts that contain HTML code.
"""
import re
from monitoring.database import SessionLocal, Post

def clean_html_content(raw_content: str) -> str:
    """Clean HTML content using BeautifulSoup or regex fallback."""
    if not raw_content:
        return raw_content
        
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw_content, 'html.parser')
        # Convert links to text with URLs
        for a in soup.find_all("a"):
            href = a.get("href")
            if href:
                a.replace_with(f"{a.get_text(' ', strip=True)} ({href})")
        return soup.get_text(" ", strip=True)
    except ImportError:
        # Fallback: use regex
        # First handle common HTML entities
        content = raw_content.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        # Remove all HTML tags
        content = re.sub(r"<[^>]+>", "", content)
        # Clean up extra whitespace
        content = re.sub(r"\s+", " ", content).strip()
        return content

def main():
    """Clean HTML content from existing posts in the database."""
    session = SessionLocal()
    
    try:
        # Get all posts that might contain HTML
        posts_with_html = session.query(Post).filter(
            Post.content.like('%<%') | Post.content.like('%>%')
        ).all()
        
        print(f"Found {len(posts_with_html)} posts that might contain HTML")
        
        cleaned_count = 0
        for post in posts_with_html:
            original_content = post.content
            cleaned_content = clean_html_content(original_content)
            
            # Only update if the content actually changed
            if cleaned_content != original_content:
                post.content = cleaned_content
                cleaned_count += 1
                print(f"Cleaned post {post.id}: {post.source}")
        
        if cleaned_count > 0:
            session.commit()
            print(f"Successfully cleaned {cleaned_count} posts")
        else:
            print("No posts needed cleaning")
            
    except Exception as e:
        print(f"Error cleaning database: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
