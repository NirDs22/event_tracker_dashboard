"""Data collection utilities for social networks and news APIs."""
from datetime import datetime
import os
from typing import Iterable

from .database import SessionLocal, Topic, Post


def fetch_twitter(topic: Topic) -> Iterable[dict]:
    """Collect tweets using snscrape."""
    try:
        from snscrape.modules.twitter import TwitterSearchScraper
    except Exception as exc:
        print("snscrape not installed or failed", exc)
        return []

    query = topic.name
    if topic.keywords:
        kw = " OR ".join([k.strip() for k in topic.keywords.split(',') if k.strip()])
        query = f"{query} ({kw})"

    scraper = TwitterSearchScraper(query)
    for tweet in scraper.get_items():
        yield {
            'source': 'twitter',
            'content': tweet.content,
            'url': tweet.url,
            'posted_at': tweet.date,
            'likes': getattr(tweet, 'likeCount', 0),
            'comments': getattr(tweet, 'replyCount', 0)
        }


def fetch_reddit(topic: Topic) -> Iterable[dict]:
    """Collect posts from Reddit using PRAW."""
    try:
        import praw
    except Exception as exc:
        print("praw not installed", exc)
        return []

    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    user_agent = os.getenv('REDDIT_USER_AGENT', 'tracker')
    if not (client_id and client_secret):
        print('Missing Reddit credentials')
        return []
    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
    query = topic.name
    if topic.keywords:
        query += ' ' + ' '.join([k.strip() for k in topic.keywords.split(',') if k.strip()])
    for submission in reddit.subreddit('all').search(query, limit=50):
        yield {
            'source': 'reddit',
            'content': submission.title,
            'url': submission.url,
            'posted_at': datetime.fromtimestamp(submission.created_utc),
            'likes': submission.score,
            'comments': submission.num_comments,
        }


def fetch_news(topic: Topic) -> Iterable[dict]:
    """Fetch news articles via API or public RSS."""
    api_key = os.getenv('NEWSAPI_KEY')
    query = topic.name
    if topic.keywords:
        query += ' ' + ' OR '.join([k.strip() for k in topic.keywords.split(',') if k.strip()])

    if api_key:
        try:
            from newsapi import NewsApiClient

            newsapi = NewsApiClient(api_key=api_key)
            articles = newsapi.get_everything(q=query, language='en', sort_by='publishedAt', page_size=20)
            for art in articles.get('articles', []):
                yield {
                    'source': 'news',
                    'content': art['title'],
                    'url': art['url'],
                    'posted_at': datetime.fromisoformat(art['publishedAt'].replace('Z', '+00:00')),
                    'likes': 0,
                    'comments': 0,
                }
            return
        except Exception as exc:
            print('NewsAPI fetch failed', exc)

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
            yield {
                'source': 'news',
                'content': entry.get('title', ''),
                'url': entry.get('link', ''),
                'posted_at': posted_dt,
                'likes': 0,
                'comments': 0,
            }
    except Exception as exc:
        print('Google News RSS fetch failed', exc)
        return []


def collect_topic(topic: Topic):
    """Collect posts for all sources for a given topic."""
    session = SessionLocal()
    fetchers = [fetch_twitter, fetch_reddit, fetch_news]
    for fetcher in fetchers:
        try:
            for item in fetcher(topic):
                if not session.query(Post).filter_by(url=item['url']).first():
                    post = Post(topic_id=topic.id, **item)
                    session.add(post)
            session.commit()
        except Exception as exc:
            session.rollback()
            print('Error in fetcher', fetcher.__name__, exc)
    session.close()
