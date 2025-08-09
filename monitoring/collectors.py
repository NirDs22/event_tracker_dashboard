"""Data collection utilities for social networks and news APIs."""
from datetime import datetime, timedelta
import os
from typing import Callable, List, Tuple

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
        reddit = praw.Reddit(
            client_id=client_id, client_secret=client_secret, user_agent=user_agent
        )
        query = topic.name
        if topic.keywords:
            query += ' ' + ' '.join(
                [k.strip() for k in topic.keywords.split(',') if k.strip()]
            )
        seen: set[str] = set()
        for sort in ("new", "hot"):
            for submission in reddit.subreddit('all').search(
                query, sort=sort, limit=25
            ):
                if submission.url in seen:
                    continue
                seen.add(submission.url)
                posts.append(
                    {
                        'source': 'reddit',
                        'content': submission.title,
                        'url': submission.url,
                        'posted_at': datetime.fromtimestamp(
                            submission.created_utc
                        ),
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


def collect_topic(
    topic: Topic,
    progress: Callable[[str], None] | None = None,
    force: bool = False,
) -> List[str]:
    """Collect posts for all sources for a given topic."""
    session = SessionLocal()
    db_topic = session.query(Topic).get(topic.id)
    now = datetime.utcnow()
    if db_topic and db_topic.last_collected and not force:
        if now - db_topic.last_collected < timedelta(hours=1):
            session.close()
            return ["Collected recently; skipping."]
    fetchers = [
        ("twitter", fetch_twitter),
        ("reddit", fetch_reddit),
        ("news", fetch_news),
        ("facebook", fetch_facebook),
    ]
    errors: List[str] = []
    for name, fetcher in fetchers:
        if progress:
            progress(f"checking {name}...")
        posts, errs = fetcher(db_topic)
        for item in posts:
            if not session.query(Post).filter_by(url=item['url']).first():
                post = Post(topic_id=db_topic.id, **item)
                session.add(post)
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            errors.append(f"Database error: {exc}")
        errors.extend(errs)
    if db_topic:
        db_topic.last_collected = datetime.utcnow()
        try:
            session.commit()
        except Exception:
            session.rollback()
    session.close()
    return errors
