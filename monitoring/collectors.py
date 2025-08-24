
import requests
import re
from datetime import datetime, timedelta
from typing import List, Tuple
import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import time
import random
import json

from .database import Topic

# --- Helpers ---

def extract_youtube_id(url: str) -> str:
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_image_url_from_text(text: str) -> str:
    if not text:
        return None
    img_match = re.search(r'(https?://[\w./%-]+\.(?:jpg|jpeg|png|webp))', text)
    if img_match:
        return img_match.group(1)
    return None


# --- RSS Search ---

def perform_rss_search(query: str, site: str = None) -> Tuple[List[dict], List[str]]:
    posts, errors = [], []
    search_query = f"site:{site} {query}" if site else query

    try:
        rss_sources = [
            {
                'name': 'Google News',
                'url': f"https://news.google.com/rss/search?q={urllib.parse.quote(search_query)}&hl=en-US&gl=US&ceid=US:en",
                'source_type': site.replace('.com', '') if site else 'news'
            }
        ]
        if site and 'youtube.com' in site:
            rss_sources.append({
                'name': 'YouTube RSS',
                'url': f"https://www.youtube.com/feeds/videos.xml?search_query={urllib.parse.quote(query)}",
                'source_type': 'youtube'
            })

        for source in rss_sources:
            feed = feedparser.parse(source['url'])
            for entry in feed.entries[:10]:  # limit but not too strict
                url = entry.get('link', '')
                title = entry.get('title', '')
                content = entry.get('summary', entry.get('description', ''))

                posted_dt = datetime.utcnow()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    posted_dt = datetime(*entry.published_parsed[:6])

                if content:
                    soup = BeautifulSoup(content, 'html.parser')
                    content = soup.get_text(' ', strip=True)

                image_url = None
                if source['source_type'] == 'youtube':
                    vid = extract_youtube_id(url)
                    if vid:
                        image_url = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"

                posts.append({
                    'source': source['source_type'],
                    'title': title,
                    'content': content,
                    'url': url,
                    'posted_at': posted_dt,
                    'likes': 0,
                    'comments': 0,
                    'image_url': image_url,
                    'is_photo': False
                })

            time.sleep(0.2)  # shorter delay

    except Exception as exc:
        errors.append(f"RSS search failed: {exc}")

    return posts, errors


# --- YouTube ---

def fetch_youtube(topic: Topic) -> Tuple[List[dict], List[str]]:
    posts, errors = [], []
    query = topic.name.strip()
    try:
        rss_posts, rss_errors = perform_rss_search(query, 'youtube.com')
        posts.extend(rss_posts)
        errors.extend(rss_errors)

        for post in posts:
            post['source'] = 'youtube'
            if not post.get('image_url'):
                vid = extract_youtube_id(post.get('url', ''))
                if vid:
                    post['image_url'] = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
            post['title'] = f"📺 YouTube: {post['title']}"
    except Exception as exc:
        errors.append(f"YouTube fetch failed: {exc}")
    return posts[:8], errors


# --- Instagram ---

def fetch_instagram(topic: Topic) -> Tuple[List[dict], List[str]]:
    posts, errors = [], []
    query = topic.name.strip()
    try:
        from .collectors import perform_careful_duckduckgo_search
        ddg_posts, ddg_errors = perform_careful_duckduckgo_search(
            f"{query} instagram post OR photo", 'instagram.com'
        )
        posts.extend(ddg_posts)
        errors.extend(ddg_errors)

        for post in posts:
            post['source'] = 'instagram'
            post['title'] = f"📷 Instagram: {post.get('title', '')}"
            if 'instagram.com/p/' in post.get('url', ''):
                shortcode = post['url'].rstrip('/').split('/')[-1]
                try:
                    oembed_url = f"https://graph.facebook.com/v10.0/instagram_oembed?url={post['url']}&omitscript=true"
                    resp = requests.get(oembed_url, timeout=8)
                    if resp.ok:
                        data = resp.json()
                        post['image_url'] = data.get('thumbnail_url')
                    else:
                        post['image_url'] = f"https://www.instagram.com/p/{shortcode}/media/?size=l"
                except Exception:
                    post['image_url'] = f"https://www.instagram.com/p/{shortcode}/media/?size=l"
            else:
                if not post.get('image_url'):
                    post['image_url'] = extract_image_url_from_text(post.get('content', ''))
    except Exception as exc:
        errors.append(f"Instagram fetch failed: {exc}")
    return posts[:8], errors


# --- Photos ---

def search_real_photos_enhanced(query: str) -> Tuple[List[dict], List[str]]:
    posts, errors = [], []
    try:
        rss_posts, rss_errors = perform_rss_search(f"{query} photos")
        for post in rss_posts:
            if not post.get('image_url'):
                post['image_url'] = extract_image_url_from_text(post.get('content', ''))
            post['source'] = 'photos'
            post['title'] = f"📸 Photo: {post['title']}"
            post['is_photo'] = True
            posts.append(post)
        errors.extend(rss_errors)
    except Exception as exc:
        errors.append(f"Photo search failed: {exc}")
    return posts[:8], errors


# --- Twitter ---

def fetch_twitter(topic: Topic) -> Tuple[List[dict], List[str]]:
    posts, errors = [], []
    query = topic.name.strip()
    try:
        from .collectors import perform_rss_search, perform_careful_duckduckgo_search
        rss_posts, rss_errors = perform_rss_search(query, 'twitter.com')
        posts.extend(rss_posts)
        errors.extend(rss_errors)

        if len(posts) < 3:
            ddg_posts, ddg_errors = perform_careful_duckduckgo_search(f"{query} twitter", 'twitter.com')
            posts.extend(ddg_posts)
            errors.extend(ddg_errors)

        for post in posts:
            post['source'] = 'twitter'
            post['title'] = f"🐦 Twitter/X: {post['title']}"
            if not post.get('image_url'):
                post['image_url'] = extract_image_url_from_text(post.get('content', ''))
    except Exception as exc:
        errors.append(f"Twitter fetch failed: {exc}")
    return posts[:8], errors


# --- Facebook ---

def fetch_facebook(topic: Topic) -> Tuple[List[dict], List[str]]:
    posts, errors = [], []
    query = topic.name.strip()
    try:
        from .collectors import perform_careful_duckduckgo_search
        ddg_posts, ddg_errors = perform_careful_duckduckgo_search(f"{query} facebook", 'facebook.com')
        posts.extend(ddg_posts)
        errors.extend(ddg_errors)

        for post in posts:
            post['source'] = 'facebook'
            post['title'] = f"📘 Facebook: {post['title']}"
            if not post.get('image_url'):
                post['image_url'] = extract_image_url_from_text(post.get('content', ''))
    except Exception as exc:
        errors.append(f"Facebook fetch failed: {exc}")
    return posts[:8], errors


# --- Reddit ---

def fetch_reddit(topic: Topic) -> Tuple[List[dict], List[str]]:
    posts, errors = [], []
    query = topic.name.strip()
    try:
        from .collectors import perform_rss_search
        rss_posts, rss_errors = perform_rss_search(query, 'reddit.com')
        posts.extend(rss_posts)
        errors.extend(rss_errors)

        for post in posts:
            post['source'] = 'reddit'
            post['title'] = f"🔴 Reddit: {post['title']}"
            if not post.get('image_url'):
                post['image_url'] = extract_image_url_from_text(post.get('content', ''))
    except Exception as exc:
        errors.append(f"Reddit fetch failed: {exc}")
    return posts[:8], errors


# --- News ---

def fetch_news(topic: Topic) -> Tuple[List[dict], List[str]]:
    posts, errors = [], []
    query = topic.name.strip()
    try:
        news_sources = [
            f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en",
            f"https://www.bing.com/news/search?q={urllib.parse.quote(query)}&format=RSS"
        ]
        for source_url in news_sources:
            feed = feedparser.parse(source_url)
            for entry in feed.entries[:12]:
                posted = entry.get('published_parsed')
                posted_dt = datetime(*posted[:6]) if posted else datetime.utcnow()
                content = entry.get('title', '')
                summary = entry.get('summary', '')
                if summary and summary != content:
                    soup = BeautifulSoup(summary, 'html.parser')
                    summary_clean = soup.get_text(' ', strip=True)
                    content += '\n\n' + summary_clean
                posts.append({
                    'source': 'news',
                    'title': f"📰 {entry.get('title', 'No title')}",
                    'content': content,
                    'url': entry.get('link', ''),
                    'posted_at': posted_dt,
                    'likes': 0,
                    'comments': 0,
                    'image_url': None,
                    'is_photo': False,
                })
            time.sleep(0.2)
    except Exception as exc:
        errors.append(f"News fetch failed: {exc}")

    # remove duplicates
    seen = set()
    unique_posts = []
    for post in posts:
        if post['url'] not in seen:
            seen.add(post['url'])
            unique_posts.append(post)

    return unique_posts[:20], errors


# --- Wrapper for photos ---

def fetch_photos(topic: Topic) -> Tuple[List[dict], List[str]]:
    return search_real_photos_enhanced(topic.name.strip())


# --- Gather posts ---

def gather_posts_for_topic(topic: Topic) -> Tuple[List[dict], List[str]]:
    all_posts, all_errors = [], []
    sources = [
        ('news', fetch_news),
        ('reddit', fetch_reddit),
        ('youtube', fetch_youtube),
        ('photos', fetch_photos),
        ('twitter', fetch_twitter),
        ('facebook', fetch_facebook),
        ('instagram', fetch_instagram),
    ]
    for source_name, fetch_func in sources:
        try:
            posts, errors = fetch_func(topic)
            all_posts.extend(posts)
            all_errors.extend(errors)
            time.sleep(1)  # shorter but respectful
        except Exception as e:
            all_errors.append(f"{source_name} collector failed: {e}")
    return all_posts, all_errors


# --- Collect single topic ---

def collect_topic(topic: Topic, force: bool = False, progress=None, shared_topic_id=None) -> List[str]:
    errors = []
    try:
        from .utils import should_skip_collection
        if not force and should_skip_collection(topic):
            errors.append("Collected recently; skipping.")
            return errors

        posts_data, collection_errors = gather_posts_for_topic(topic)
        errors.extend(collection_errors)

        if posts_data:
            from .database import get_db_session, Post, SharedPost, SharedTopic
            session = get_db_session()
            try:
                posts_saved, duplicate_posts = 0, 0
                for post_data in posts_data:
                    if shared_topic_id:
                        existing = session.query(SharedPost).filter(
                            SharedPost.shared_topic_id == shared_topic_id,
                            SharedPost.url == post_data.get('url', '')
                        ).first()
                        if not existing:
                            post = SharedPost(
                                shared_topic_id=shared_topic_id,
                                source=post_data.get('source', 'unknown'),
                                title=post_data.get('title', ''),
                                content=post_data.get('content', ''),
                                url=post_data.get('url', ''),
                                posted_at=post_data.get('posted_at', datetime.utcnow()),
                                likes=post_data.get('likes', 0),
                                comments=post_data.get('comments', 0),
                                image_url=post_data.get('image_url'),
                                is_photo=post_data.get('is_photo', False)
                            )
                            session.add(post)
                            posts_saved += 1
                        else:
                            duplicate_posts += 1
                    else:
                        existing = session.query(Post).filter(
                            Post.topic_id == topic.id,
                            Post.url == post_data.get('url', '')
                        ).first()
                        if not existing:
                            post = Post(
                                topic_id=topic.id,
                                source=post_data.get('source', 'unknown'),
                                title=post_data.get('title', ''),
                                content=post_data.get('content', ''),
                                url=post_data.get('url', ''),
                                posted_at=post_data.get('posted_at', datetime.utcnow()),
                                likes=post_data.get('likes', 0),
                                comments=post_data.get('comments', 0),
                                image_url=post_data.get('image_url'),
                                is_photo=post_data.get('is_photo', False)
                            )
                            session.add(post)
                            posts_saved += 1
                        else:
                            duplicate_posts += 1

                session.commit()
                if shared_topic_id:
                    shared_topic = session.query(SharedTopic).get(shared_topic_id)
                    if shared_topic:
                        shared_topic.last_collected = datetime.utcnow()
                else:
                    topic.last_collected = datetime.utcnow()
                session.commit()

                if progress and hasattr(progress, 'text'):
                    progress.text(f"Saved {posts_saved} new posts for {topic.name} ({duplicate_posts} duplicates skipped)")
            except Exception as db_error:
                session.rollback()
                errors.append(f"Database error: {db_error}")
            finally:
                session.close()
        else:
            errors.append("No posts collected from web search")
    except Exception as e:
        errors.append(f"Collection failed: {e}")
    return errors


# --- Collect all topics ---

def collect_all_topics_efficiently():
    from .database import get_all_topics
    topics = get_all_topics()
    total_errors = []
    for i, topic in enumerate(topics):
        try:
            topic_errors = collect_topic(topic, force=False)
            total_errors.extend(topic_errors)
            if i < len(topics) - 1:
                time.sleep(random.uniform(3, 5))
        except Exception as e:
            total_errors.append(f"Failed to process topic {topic.name}: {e}")
    return total_errors
