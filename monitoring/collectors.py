"""Data collection utilities for social networks and news APIs."""
from datetime import datetime
import os
from typing import List, Tuple

from .database import SessionLocal, Topic, Post


def fetch_twitter(topic: Topic) -> Tuple[List[dict], List[str]]:
    """Collect tweets using snscrape."""
    posts: List[dict] = []
    errors: List[str] = []
    try:
        from snscrape.modules.twitter import TwitterSearchScraper
    except Exception:
        errors.append(
            "snscrape not installed. Install with `pip install snscrape` to enable Twitter scraping."
        )
        return posts, errors

    query = topic.name
    if topic.keywords:
        kw = " OR ".join([k.strip() for k in topic.keywords.split(',') if k.strip()])
        query = f"{query} ({kw})"

    scraper = TwitterSearchScraper(query)
    try:
        for tweet in scraper.get_items():
            posts.append(
                {
                    'source': 'twitter',
                    'content': tweet.content,
                    'url': tweet.url,
                    'posted_at': tweet.date,
                    'likes': getattr(tweet, 'likeCount', 0),
                    'comments': getattr(tweet, 'replyCount', 0),
                }
            )
    except Exception as exc:
        errors.append(
            "Twitter fetch failed: {exc}. Twitter may be blocking requests; try again later or update snscrape.".format(
                exc=exc
            )
        )
    return posts, errors


def fetch_reddit(topic: Topic) -> Tuple[List[dict], List[str]]:
    """Collect posts from Reddit using PRAW."""
    posts: List[dict] = []
    errors: List[str] = []
    try:
        import praw
    except Exception:
        errors.append(
            "praw not installed. Install with `pip install praw` to enable Reddit scraping."
        )
        return posts, errors

    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    user_agent = os.getenv('REDDIT_USER_AGENT', 'tracker')
    if not (client_id and client_secret):
        errors.append(
            "Missing Reddit credentials. Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in your .env file."
        )
        return posts, errors
    try:
        reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
        query = topic.name
        if topic.keywords:
            query += ' ' + ' '.join([k.strip() for k in topic.keywords.split(',') if k.strip()])
        for submission in reddit.subreddit('all').search(query, limit=50):
            posts.append(
                {
                    'source': 'reddit',
                    'content': submission.title,
                    'url': submission.url,
                    'posted_at': datetime.fromtimestamp(submission.created_utc),
                    'likes': submission.score,
                    'comments': submission.num_comments,
                }
            )
    except Exception as exc:
        errors.append(
            f"Reddit fetch failed: {exc}. Verify your Reddit credentials in .env."
        )
    return posts, errors


def fetch_news(topic: Topic) -> Tuple[List[dict], List[str]]:
    """Fetch news articles via API or public RSS."""
    posts: List[dict] = []
    errors: List[str] = []
    api_key = os.getenv('NEWSAPI_KEY')
    query = topic.name
    if topic.keywords:
        query += ' ' + ' OR '.join([k.strip() for k in topic.keywords.split(',') if k.strip()])

    if api_key:
        try:
            from newsapi import NewsApiClient

            newsapi = NewsApiClient(api_key=api_key)
            articles = newsapi.get_everything(
                q=query, language='en', sort_by='publishedAt', page_size=20
            )
            for art in articles.get('articles', []):
                posts.append(
                    {
                        'source': 'news',
                        'content': art['title'],
                        'url': art['url'],
                        'posted_at': datetime.fromisoformat(
                            art['publishedAt'].replace('Z', '+00:00')
                        ),
                        'likes': 0,
                        'comments': 0,
                    }
                )
            return posts, errors
        except Exception as exc:
            errors.append(
                f"NewsAPI request failed: {exc}. Check your NEWSAPI_KEY in .env or remove it to use free RSS."
            )

    # Fallback to Google News RSS (no key required)
    try:
        import feedparser
        import urllib.parse

        feed_url = (
            "https://news.google.com/rss/search?q="
            + urllib.parse.quote(query)
            + "&hl=en-US&gl=US&ceid=US:en"
        )
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:20]:
            posted = entry.get('published_parsed')
            posted_dt = datetime(*posted[:6]) if posted else datetime.utcnow()
            posts.append(
                {
                    'source': 'news',
                    'content': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'posted_at': posted_dt,
                    'likes': 0,
                    'comments': 0,
                }
            )
    except Exception as exc:
        errors.append(
            f"Google News RSS fetch failed: {exc}. Check your internet connection."
        )
    return posts, errors


def fetch_facebook(topic: Topic) -> Tuple[List[dict], List[str]]:
    """Scrape public Facebook pages listed in the topic profiles."""
    posts: List[dict] = []
    errors: List[str] = []
    try:
        from facebook_scraper import get_posts
    except Exception:
        errors.append(
            "facebook-scraper not installed. Install with `pip install \"facebook-scraper[lxml]\" lxml_html_clean` to enable Facebook scraping."
        )
        return posts, errors

    profiles = [
        p.strip() for p in (topic.profiles or "").split(",") if "facebook.com" in p
    ]
    if not profiles:
        return posts, errors

    keywords = [k.strip().lower() for k in (topic.keywords or "").split(",") if k.strip()]

    for url in profiles:
        page = url.rstrip("/").split("/")[-1]
        try:
            for post in get_posts(account=page, pages=1):
                text = post.get("text", "")
                if keywords and not any(k in text.lower() for k in keywords):
                    continue
                posts.append(
                    {
                        "source": "facebook",
                        "content": text,
                        "url": post.get("post_url", ""),
                        "posted_at": post.get("time", datetime.utcnow()),
                        "likes": post.get("likes", 0),
                        "comments": post.get("comments", 0),
                    }
                )
        except Exception as exc:
            errors.append(f"Facebook fetch failed for {page}: {exc}")
    return posts, errors


def fetch_instagram(topic: Topic) -> Tuple[List[dict], List[str]]:
    """Collect public Instagram posts for profiles listed in the topic."""
    posts: List[dict] = []
    errors: List[str] = []
    try:
        import instaloader
    except Exception:
        instaloader = None
        errors.append(
            "instaloader not installed. Install with `pip install instaloader` to enable Instagram scraping."
        )

    profiles = [
        p.strip() for p in (topic.profiles or "").split(",") if "instagram.com" in p
    ]
    if not profiles:
        return posts, errors

    keywords = [k.strip().lower() for k in (topic.keywords or "").split(",") if k.strip()]

    for url in profiles:
        username = url.rstrip("/").split("/")[-1]
        profile_url = f"https://www.instagram.com/{username}/"
        fetched = False

        if instaloader:
            try:
                L = instaloader.Instaloader(
                    download_pictures=False,
                    download_videos=False,
                    download_comments=False,
                    save_metadata=False,
                    compress_json=False,
                )
                profile = instaloader.Profile.from_username(L.context, username)
                if profile.is_private:
                    errors.append(f"Instagram profile {username} is private")
                    posts.append(
                        {
                            "source": "instagram",
                            "content": "Profile is private",
                            "url": profile_url,
                            "posted_at": datetime.utcnow(),
                            "likes": 0,
                            "comments": 0,
                        }
                    )
                    fetched = True
                else:
                    count = 0
                    for post in profile.get_posts():
                        text = post.caption or ""
                        if keywords and not any(k in text.lower() for k in keywords):
                            continue
                        posts.append(
                            {
                                "source": "instagram",
                                "content": text,
                                "url": f"https://www.instagram.com/p/{post.shortcode}/",
                                "posted_at": post.date_utc,
                                "likes": post.likes,
                                "comments": post.comments,
                            }
                        )
                        count += 1
                        if count >= 10:
                            break
                    fetched = True
            except Exception as exc:
                errors.append(
                    f"Instagram fetch via Instaloader failed for {username}: {exc}"
                )

        if not fetched:
            try:
                import requests

                resp = requests.get(
                    f"https://r.jina.ai/http://www.instagram.com/{username}/?__a=1&__d=dis",
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json().get("graphql", {}).get("user", {})
                    if data.get("is_private"):
                        errors.append(f"Instagram profile {username} is private")
                        posts.append(
                            {
                                "source": "instagram",
                                "content": "Profile is private",
                                "url": profile_url,
                                "posted_at": datetime.utcnow(),
                                "likes": 0,
                                "comments": 0,
                            }
                        )
                        continue
                    edges = (
                        data.get("edge_owner_to_timeline_media", {}).get("edges", [])
                    )
                    for edge in edges[:10]:
                        node = edge.get("node", {})
                        text = ""
                        cap_edges = (
                            node.get("edge_media_to_caption", {}).get("edges", [])
                        )
                        if cap_edges:
                            text = cap_edges[0].get("node", {}).get("text", "")
                        if keywords and not any(k in text.lower() for k in keywords):
                            continue
                        posts.append(
                            {
                                "source": "instagram",
                                "content": text,
                                "url": f"https://www.instagram.com/p/{node.get('shortcode', '')}/",
                                "posted_at": datetime.fromtimestamp(
                                    node.get("taken_at_timestamp", 0)
                                ),
                                "likes": node.get("edge_liked_by", {}).get("count", 0),
                                "comments": node.get("edge_media_to_comment", {}).get(
                                    "count", 0
                                ),
                            }
                        )
                else:
                    errors.append(
                        f"Instagram fetch failed for {username}: HTTP {resp.status_code}"
                    )
            except Exception as exc:
                errors.append(f"Instagram fetch failed for {username}: {exc}")

    return posts, errors


def collect_topic(topic: Topic) -> List[str]:
    """Collect posts for all sources for a given topic."""
    session = SessionLocal()
    fetchers = []
    if os.getenv("ENABLE_TWITTER", "1") == "1":
        fetchers.append(fetch_twitter)
    if os.getenv("ENABLE_REDDIT", "1") == "1":
        fetchers.append(fetch_reddit)
    if os.getenv("ENABLE_NEWS", "1") == "1":
        fetchers.append(fetch_news)
    if os.getenv("ENABLE_FACEBOOK", "1") == "1":
        fetchers.append(fetch_facebook)
    if os.getenv("ENABLE_INSTAGRAM", "1") == "1":
        fetchers.append(fetch_instagram)
    errors: List[str] = []
    for fetcher in fetchers:
        posts, errs = fetcher(topic)
        for item in posts:
            if not session.query(Post).filter_by(url=item['url']).first():
                post = Post(topic_id=topic.id, **item)
                session.add(post)
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            errors.append(f"Database error: {exc}")
        errors.extend(errs)
    session.close()
    return errors
