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


def collect_topic(topic: Topic) -> List[str]:
    """Collect posts for all sources for a given topic."""
    session = SessionLocal()
    fetchers = [fetch_twitter, fetch_reddit, fetch_news]
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
