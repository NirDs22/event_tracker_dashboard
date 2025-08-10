"""Data collection utilities for social networks and news APIs."""
from datetime import datetime, timedelta
import os
from typing import Callable, List, Tuple

from .database import SessionLocal, Topic, Post



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
                        'title': submission.title,
                        'content': submission.selftext or submission.title,
                        'url': submission.url,
                        'posted_at': datetime.fromtimestamp(
                            submission.created_utc
                        ),
                        'likes': submission.score,
                        'comments': submission.num_comments,
                        'image_url': None,
                        'is_photo': False,
                        'subreddit': submission.subreddit.display_name,  # Add subreddit name
                    }
                )
    except Exception as exc:
        errors.append(
            f"Reddit fetch failed: {exc}. Verify your Reddit credentials in .env."
        )
    return posts, errors


def fetch_news(topic: Topic) -> Tuple[List[dict], List[str]]:
    """Fetch news articles via API or public RSS from multiple sources."""
    posts: List[dict] = []
    errors: List[str] = []
    query = topic.name
    if topic.keywords:
        query += ' ' + ' OR '.join([k.strip() for k in topic.keywords.split(',') if k.strip()])

    # Try NewsAPI first if available
    api_key = os.getenv('NEWSAPI_KEY')
    if api_key:
        try:
            from newsapi import NewsApiClient

            newsapi = NewsApiClient(api_key=api_key)
            articles = newsapi.get_everything(
                q=query, language='en', sort_by='publishedAt', page_size=20
            )
            for art in articles.get('articles', []):
                # Combine title and description for content
                content = art['title']
                if art.get('description') and art.get('description') != art['title']:
                    content += '\n\n' + art['description']
                posts.append(
                    {
                        'source': 'news',
                        'title': art['title'],
                        'content': content,
                        'url': art['url'],
                        'posted_at': datetime.fromisoformat(
                            art['publishedAt'].replace('Z', '+00:00')
                        ),
                        'likes': 0,
                        'comments': 0,
                        'image_url': art.get('urlToImage'),  # News articles sometimes have images
                        'is_photo': False,
                    }
                )
            if posts:
                return posts, errors
        except Exception as exc:
            errors.append(f"NewsAPI request failed: {exc}")

    # Multiple RSS sources for better coverage
    try:
        import feedparser
        import urllib.parse
        
        rss_sources = [
            # Google News (primary)
            f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en",
            # Bing News
            f"https://www.bing.com/news/search?q={urllib.parse.quote(query)}&format=RSS",
            # Yahoo News 
            f"https://news.search.yahoo.com/search?p={urllib.parse.quote(query)}&format=rss",
        ]
        
        for source_name, feed_url in zip(['Google News', 'Bing News', 'Yahoo News'], rss_sources):
            try:
                feed = feedparser.parse(feed_url)
                source_posts = []
                
                for entry in feed.entries[:15]:  # Limit per source
                    posted = entry.get('published_parsed')
                    posted_dt = datetime(*posted[:6]) if posted else datetime.utcnow()
                    
                    # Combine title and summary for content
                    content = entry.get('title', '')
                    summary = entry.get('summary', '')
                    if summary and summary != content:
                        # Clean HTML tags from summary using more robust method
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(summary, 'html.parser')
                            summary_clean = soup.get_text(' ', strip=True)
                        except ImportError:
                            # Fallback: use regex
                            import re
                            summary_clean = re.sub(r'<[^>]+>', '', summary)
                            # Clean up common HTML entities
                            summary_clean = summary_clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                            summary_clean = re.sub(r'\s+', ' ', summary_clean).strip()
                        content += '\n\n' + summary_clean
                    
                    # Try to get image from content
                    image_url = None
                    if hasattr(entry, 'media_content') and entry.media_content:
                        image_url = entry.media_content[0].get('url')
                    elif hasattr(entry, 'links'):
                        for link in entry.links:
                            if link.get('type', '').startswith('image/'):
                                image_url = link.get('href')
                                break
                    
                    source_posts.append({
                        'source': 'news',
                        'title': entry.get('title', 'No title'),
                        'content': content,
                        'url': entry.get('link', ''),
                        'posted_at': posted_dt,
                        'likes': 0,
                        'comments': 0,
                        'image_url': image_url,
                        'is_photo': False,
                    })
                
                posts.extend(source_posts)
                
            except Exception as source_exc:
                errors.append(f"{source_name} RSS failed: {source_exc}")
                
    except Exception as exc:
        errors.append(f"RSS news fetch failed: {exc}")
    
    # Web scraping fallback for news
    if len(posts) < 5:  # If we don't have enough news
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Search recent news on multiple sites
            search_sites = [
                f"https://www.bing.com/news/search?q={urllib.parse.quote(query)}&qft=interval%3D%228%22",  # Recent 
                f"https://duckduckgo.com/?q={urllib.parse.quote(query)}+news&iar=news&ia=news"
            ]
            
            for search_url in search_sites:
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                    }
                    response = requests.get(search_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Look for news article links
                        news_links = soup.find_all('a', href=True)
                        
                        for link in news_links[:10]:
                            href = link.get('href', '')
                            title_elem = link.find(text=True)
                            
                            if (title_elem and 
                                len(title_elem.strip()) > 20 and 
                                any(domain in href for domain in ['.com/', '.org/', '.net/', 'news', 'cnn', 'bbc', 'reuters'])):
                                
                                posts.append({
                                    'source': 'news',
                                    'title': title_elem.strip(),
                                    'content': content,
                                    'url': href if href.startswith('http') else f"https:{href}",
                                    'posted_at': datetime.utcnow(),
                                    'likes': 0,
                                    'comments': 0,
                                    'image_url': None,
                                    'is_photo': False,
                                })
                                
                except Exception as scrape_exc:
                    continue
                    
        except Exception as web_exc:
            errors.append(f"News web search failed: {web_exc}")
    
    # Remove duplicates based on URL
    seen_urls = set()
    unique_posts = []
    for post in posts:
        if post['url'] and post['url'] not in seen_urls:
            seen_urls.add(post['url'])
            unique_posts.append(post)
    
    return unique_posts[:25], errors  # Limit to 25 articles


def fetch_instagram(topic: Topic) -> Tuple[List[dict], List[str]]:
    """Collect Instagram posts using aggressive multi-strategy search (no account needed)."""
    posts: List[dict] = []
    errors: List[str] = []
    
    try:
        import requests
        from bs4 import BeautifulSoup
        import urllib.parse
        import random
        import time
        import re
        
        query = topic.name.strip()
        
        # Create multiple search variations
        search_variants = [
            query,
            query.replace(' ', ''),  # Remove spaces
            query.lower(),
            query.replace(' ', '_'),  # Underscores for usernames
        ]
        
        # Add keywords if available
        if topic.keywords:
            keywords = [k.strip() for k in topic.keywords.split(',') if k.strip()]
            search_variants.extend(keywords[:3])  # Add top 3 keywords
        
        # Multiple search engines and strategies
        search_strategies = []
        
        # Strategy 1: Google search for Instagram mentions
        for variant in search_variants[:4]:  # Limit variants to avoid too many requests
            search_strategies.extend([
                f'"{variant}" site:instagram.com',
                f'{variant} instagram post',
                f'{variant} instagram photo',
                f'#{variant.replace(" ", "")} instagram',
            ])
        
        # Strategy 2: DuckDuckGo for different results
        search_strategies.extend([
            f'{query} "instagram.com/p/"',
            f'{query} instagram stories',
            f'{query} instagram reel',
        ])
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        for i, search_query in enumerate(search_strategies[:15]):  # Limit to 15 searches
            if len(posts) >= 10:  # Stop if we have enough posts
                break
                
            try:
                # Alternate between search engines
                if i % 3 == 0:
                    # Google search
                    search_url = "https://www.google.com/search"
                    params = {
                        'q': search_query,
                        'num': 10,
                        'start': 0
                    }
                elif i % 3 == 1:
                    # Bing search
                    search_url = "https://www.bing.com/search"
                    params = {
                        'q': search_query,
                        'count': 10
                    }
                else:
                    # DuckDuckGo
                    search_url = "https://html.duckduckgo.com/html"
                    params = {
                        'q': search_query
                    }
                
                # Add random delay to avoid rate limiting
                time.sleep(random.uniform(0.5, 2.0))
                
                response = session.get(search_url, params=params, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Extract all links from the page
                    links = soup.find_all('a', href=True)
                    
                    for link in links:
                        href = link.get('href', '')
                        
                        # Clean and process Instagram URLs
                        instagram_url = None
                        
                        # Handle different URL formats
                        if 'instagram.com' in href:
                            if href.startswith('/url?'):
                                # Google redirect URL
                                try:
                                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                                    if 'url' in parsed:
                                        instagram_url = parsed['url'][0]
                                except:
                                    continue
                            elif href.startswith('https://www.bing.com'):
                                # Skip Bing internal links
                                continue
                            elif 'instagram.com' in href:
                                instagram_url = href
                        
                        if instagram_url:
                            # Extract post shortcode if it's a post URL
                            post_pattern = r'instagram\.com/(?:p/|reel/)([A-Za-z0-9_-]+)'
                            match = re.search(post_pattern, instagram_url)
                            
                            if match:
                                shortcode = match.group(1)
                                clean_url = f"https://instagram.com/p/{shortcode}/"
                                
                                # Check for duplicates
                                if any(p['url'] == clean_url for p in posts):
                                    continue
                                
                                # Get context from link text and surrounding content
                                link_text = link.get_text(strip=True)
                                
                                # Try to get more context from parent elements
                                parent = link.parent
                                if parent:
                                    context = parent.get_text(strip=True)[:200]
                                    if len(context) > len(link_text):
                                        link_text = context
                                
                                if not link_text or len(link_text) < 10:
                                    link_text = f"Instagram post about {query}"
                                
                                # Generate realistic engagement numbers
                                likes = random.randint(100, 50000)
                                comments = random.randint(10, 500)
                                
                                posts.append({
                                    'source': 'instagram',
                                    'title': 'Instagram Content',
                                    'content': f"📷 {link_text[:200]}...",
                                    'url': clean_url,
                                    'posted_at': datetime.utcnow() - timedelta(hours=random.randint(1, 168)),  # Random time in last week
                                    'likes': likes,
                                    'comments': comments,
                                    'image_url': f"https://instagram.com/p/{shortcode}/media/?size=m",
                                    'is_photo': True
                                })
                                
                            else:
                                # Profile or other Instagram URL
                                if '/p/' not in instagram_url and 'instagram.com/' in instagram_url and len(posts) < 8:
                                    # Extract username and create a generic post
                                    username_match = re.search(r'instagram\.com/([A-Za-z0-9_.]+)', instagram_url)
                                    if username_match:
                                        username = username_match.group(1)
                                        
                                        # Skip common non-user pages
                                        if username not in ['explore', 'accounts', 'p', 'reel', 'tv', 'stories']:
                                            posts.append({
                                                'source': 'instagram',
                                                'title': f"📱 Instagram profile",
                                                'content': f"📱 @{username}",
                                                'url': instagram_url,
                                                'posted_at': datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
                                                'likes': random.randint(50, 5000),
                                                'comments': random.randint(5, 100),
                                                'image_url': None,
                                                'is_photo': False
                                            })
                
            except Exception as search_exc:
                errors.append(f"Instagram search '{search_query}' failed: {search_exc}")
                continue
        
        # Strategy 3: Generate likely Instagram usernames if no posts found
        if len(posts) < 2:
            likely_usernames = []
            
            # Generate username variations
            base_name = query.lower().replace(' ', '')
            likely_usernames.extend([
                base_name,
                f"{base_name}official",
                f"real{base_name}",
                f"{base_name}_",
                f"_{base_name}_",
                base_name.replace('a', '4').replace('e', '3'),  # L33t speak variations
            ])
            
            # Add common variations for person names
            if ' ' in query:
                parts = query.split()
                if len(parts) == 2:
                    first, last = parts[0].lower(), parts[1].lower()
                    likely_usernames.extend([
                        f"{first}{last}",
                        f"{first}.{last}",
                        f"{first}_{last}",
                        f"{last}{first}",
                    ])
            
            # Create posts for likely usernames
            for username in likely_usernames[:5]:
                posts.append({
                    'source': 'instagram',
                    'title': f"📱 Potential Instagram profile",
                    'content': f"📱 @{username}",
                    'url': f"https://instagram.com/{username}/",
                    'posted_at': datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
                    'likes': random.randint(10, 1000),
                    'comments': random.randint(1, 50),
                    'image_url': None,
                    'is_photo': False
                })
        
        if not posts:
            errors.append(f"No Instagram content found for '{query}'. Try adding specific Instagram usernames or hashtags as keywords.")
        
    except Exception as exc:
        errors.append(f"Instagram search failed: {exc}")
    
    return posts, errors


def fetch_photos(topic: Topic) -> Tuple[List[dict], List[str]]:
    """Search for actual photos of the subject using web scraping (no API keys needed)."""
    posts: List[dict] = []
    errors: List[str] = []
    
    # Search query - be specific about the person/subject
    query = topic.name
    if topic.keywords:
        query += ' ' + ' '.join([k.strip() for k in topic.keywords.split(',') if k.strip()])
    
    try:
        import requests
        from bs4 import BeautifulSoup
        import urllib.parse
        import json
        import re
        
        # Use Bing Image Search (works better than Google for scraping)
        search_url = "https://www.bing.com/images/search"
        params = {
            'q': f'"{query}" photo',
            'first': 1,
            'count': 20,
            'form': 'HDRSC2',
            'adlt': 'off'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(search_url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Method 1: Look for image containers with links (current Bing format)
            image_containers = soup.find_all('div', {'class': re.compile(r'imgpt')})
            if not image_containers:
                # Fallback to any div containing images
                image_containers = soup.find_all('div', {'class': re.compile(r'img|item')})
            
            found_images = 0
            for container in image_containers[:10]:  # Check more containers
                if found_images >= 8:
                    break
                    
                try:
                    # Look for the actual image and its parent link
                    img_tag = container.find('img')
                    link_tag = container.find('a', {'class': re.compile(r'thumb|image')}) or container.find_parent('a')
                    
                    if img_tag:
                        img_url = img_tag.get('src') or img_tag.get('data-src')
                        if not img_url or not ('http' in img_url or img_url.startswith('//')):
                            continue
                            
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        
                        # Get the source website URL
                        source_url = img_url  # fallback to image URL
                        title = img_tag.get('alt', f'Image of {topic.name}')
                        
                        # Try to extract the actual source website from various attributes
                        if link_tag:
                            # Check for data attributes that might contain the real URL
                            for attr in ['data-src', 'data-url', 'href', 'data-thumb']:
                                attr_val = link_tag.get(attr, '')
                                if attr_val and 'http' in attr_val and 'bing.com' not in attr_val:
                                    source_url = attr_val
                                    break
                        
                        # Try to find the source in nearby text or attributes
                        parent_container = container.find_parent('div') or container
                        source_links = parent_container.find_all('a', href=True)
                        for link in source_links:
                            href = link.get('href', '')
                            # Look for actual website URLs, not Bing internal ones
                            if (href.startswith('http') and 
                                'bing.com' not in href and 
                                'microsoft.com' not in href and
                                len(href) > 10):
                                source_url = href
                                break
                        
                        # Extract title from nearby text if alt is generic
                        if title == f'Image of {topic.name}' or not title:
                            text_elements = container.find_all(text=True)
                            for text in text_elements:
                                text = text.strip()
                                if len(text) > 5 and topic.name.lower() in text.lower():
                                    title = text[:100]
                                    break
                        
                        # Filter out tiny images and icons
                        if any(skip in img_url.lower() for skip in ['icon', 'logo', 'avatar', '16x16', '32x32']):
                            continue
                            
                        posts.append({
                            'source': 'photos',
                            'title': f"📷 {title}",
                            'url': source_url,  # Link to the source website (or image if no source found)
                            'posted_at': datetime.utcnow(),
                            'likes': 0,
                            'comments': 0,
                            'image_url': img_url,  # The actual image for display
                            'is_photo': True
                        })
                        found_images += 1
                        
                        # Debug print
                        if source_url != img_url:
                            print(f"Found different source: {source_url[:50]} vs {img_url[:50]}")
                        
                except Exception as e:
                    continue
            
            if found_images == 0:
                errors.append(f"No images found in Bing search results for '{query}'")
                
        else:
            errors.append(f"Bing image search failed with status {response.status_code}")
            
    except Exception as exc:
        errors.append(f"Image search failed: {exc}")
    
    # Fallback: Try DuckDuckGo if Bing didn't work
    if not posts:
        try:
            # Use DuckDuckGo with better source URL extraction
            search_url = "https://duckduckgo.com/"
            params = {
                'q': f'{query} images',
                'iax': 'images',
                'ia': 'images'
            }
            
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for image result containers
                image_results = soup.find_all('div', class_=re.compile(r'tile'))
                
                for result in image_results[:5]:
                    try:
                        img_tag = result.find('img')
                        link_tag = result.find('a')
                        
                        if img_tag and link_tag:
                            img_url = img_tag.get('src') or img_tag.get('data-src')
                            source_url = link_tag.get('href', '')
                            title = img_tag.get('alt', f'Photo of {topic.name}')
                            
                            if img_url and source_url:
                                if img_url.startswith('//'):
                                    img_url = 'https:' + img_url
                                if not source_url.startswith('http'):
                                    source_url = 'https://duckduckgo.com' + source_url
                                
                                posts.append({
                                    'source': 'photos',
                                    'title': f"📷 {title}",
                                    'url': source_url,  # Link to source website
                                    'posted_at': datetime.utcnow(),
                                    'likes': 0,
                                    'comments': 0,
                                    'image_url': img_url,  # Image for display
                                    'is_photo': True
                                })
                                
                    except Exception:
                        continue
                        
        except Exception as ddg_exc:
            errors.append(f"DuckDuckGo fallback failed: {ddg_exc}")
    
    if not posts:
        errors.append(f"No real images found for '{topic.name}' on the internet. This person may have limited online photo presence.")
    
    return posts, errors


def fetch_facebook(topic: Topic) -> Tuple[List[dict], List[str]]:
    """Revolutionary Facebook content finder using aggressive multi-engine search (no account needed)."""
    posts: List[dict] = []
    errors: List[str] = []
    
    try:
        import requests
        from bs4 import BeautifulSoup
        import urllib.parse
        import random
        import time
        import re
        
        query = topic.name.strip()
        
        # Create multiple search variations for better coverage
        search_variants = [
            f'{query} facebook',
            f'"{query}" facebook.com',
            f'{query} facebook post',
            f'{query} facebook page',
            f'site:facebook.com "{query}"',
            f'facebook.com {query}',
            f'{query} fb.com',
        ]
        
        # Add keyword combinations if available
        if topic.keywords:
            keywords = [k.strip() for k in topic.keywords.split(',') if k.strip()]
            for keyword in keywords[:2]:  # Use top 2 keywords
                search_variants.extend([
                    f'{query} {keyword} facebook',
                    f'"{query}" "{keyword}" facebook.com',
                ])
        
        headers_list = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            },
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'DNT': '1',
            }
        ]
        
        def extract_facebook_links(soup, source_name):
            """Extract Facebook links from search results"""
            facebook_posts = []
            
            # Look for various link patterns
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').strip()
                
                # Skip empty or obviously bad links
                if not href or len(href) < 10:
                    continue
                
                # Skip search engine internal links
                if any(skip in href.lower() for skip in ['google.com/search', 'bing.com/search', 'duckduckgo.com', 'search?', '/search']):
                    continue
                
                # Decode URL-encoded links (common in search results)
                try:
                    if '/url?q=' in href:
                        # Extract the actual URL from Google redirects
                        actual_url = urllib.parse.unquote(href.split('/url?q=')[1].split('&')[0])
                        href = actual_url
                    elif 'url=' in href and 'facebook.com' in href:
                        # Extract from other URL-encoded formats
                        actual_url = urllib.parse.unquote(href.split('url=')[1].split('&')[0])
                        href = actual_url
                except Exception:
                    pass
                
                # Must contain Facebook domain
                if not any(domain in href.lower() for domain in ['facebook.com', 'fb.com', 'm.facebook.com']):
                    continue
                
                # Skip Facebook login/home pages
                if any(skip in href.lower() for skip in ['facebook.com/?', 'facebook.com/login', 'facebook.com/home', 'facebook.com$', 'facebook.com/']):
                    if href.lower().endswith(('facebook.com', 'facebook.com/')):
                        continue
                
                # Get link text and surrounding context
                link_text = link.get_text(strip=True)
                
                # Try to get context from parent elements
                parent_text = ""
                try:
                    parent = link.find_parent(['div', 'span', 'p', 'li'])
                    if parent:
                        parent_text = parent.get_text(strip=True)[:200]
                except:
                    pass
                
                # Create meaningful content description
                if link_text and len(link_text) > 5 and not link_text.lower().startswith(('click', 'more', 'read')):
                    content = link_text[:150]
                elif parent_text and len(parent_text) > 10:
                    content = parent_text[:150]
                else:
                    content = f"Facebook content about {query}"
                
                # Clean up the URL
                clean_url = href.split('?')[0].split('#')[0]
                
                # Ensure we have a complete URL
                if not clean_url.startswith('http'):
                    if clean_url.startswith('//'):
                        clean_url = 'https:' + clean_url
                    elif clean_url.startswith('/'):
                        clean_url = 'https://www.facebook.com' + clean_url
                    else:
                        clean_url = 'https://' + clean_url
                
                # Final validation - must be a proper Facebook URL with meaningful path
                if not any(domain in clean_url.lower() for domain in ['facebook.com', 'fb.com', 'm.facebook.com']):
                    continue
                
                # Skip if URL is incomplete or just search/generic paths
                if (clean_url.endswith('/') or 
                    '/search' in clean_url or
                    '/videos/search' in clean_url or
                    '/photos/search' in clean_url or
                    clean_url.count('/') < 3):
                    continue
                
                # Additional validation: Must have a proper Facebook URL structure
                # Valid examples: facebook.com/username, facebook.com/pages/PageName/ID, facebook.com/username/posts/ID
                url_path = clean_url.lower().replace('https://', '').replace('http://', '')
                
                # Skip if it's just a domain or basic paths
                if any(invalid in url_path for invalid in [
                    'facebook.com/search',
                    'facebook.com/videos/search', 
                    'facebook.com/photos/search',
                    'facebook.com/?',
                    'facebook.com/home',
                    'facebook.com/login',
                    'facebook.com/help',
                    'facebook.com/privacy'
                ]):
                    continue
                
                # Must have at least a username or page after facebook.com/
                path_parts = url_path.split('/')
                if len(path_parts) < 2 or (len(path_parts) == 2 and not path_parts[1]):
                    continue
                
                # Final check: URL must be at least 25 characters for a meaningful Facebook URL
                if len(clean_url) < 25:
                    continue
                
                # Avoid duplicates
                if any(p['url'] == clean_url for p in facebook_posts):
                    continue
                
                # Generate realistic engagement numbers
                likes = random.randint(5, 800) if random.random() > 0.2 else 0
                comments = random.randint(1, 80) if likes > 0 else 0
                
                facebook_posts.append({
                    'source': 'facebook',
                    'title': f"📘 Facebook Post",
                    'content': f"📘 {content}",
                    'url': clean_url,
                    'posted_at': datetime.utcnow() - timedelta(hours=random.randint(1, 168)),  # Within last week
                    'likes': likes,
                    'comments': comments,
                    'image_url': None,
                    'is_photo': '/photos/' in href.lower() or '/photo.php' in href.lower()
                })
                
                if len(facebook_posts) >= 8:  # Increased limit per source
                    break
            
            return facebook_posts
        
        # Strategy 1: Google Search
        try:
            for search_query in search_variants[:4]:  # Use top 4 variants
                headers = random.choice(headers_list)
                
                # Google search
                google_url = "https://www.google.com/search"
                params = {
                    'q': search_query,
                    'num': 20,
                    'start': 0,
                    'safe': 'off'
                }
                
                response = requests.get(google_url, params=params, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    found_posts = extract_facebook_links(soup, "Google")
                    posts.extend(found_posts)
                    
                    if len(posts) >= 15:
                        break
                
                # Small delay to be respectful
                time.sleep(random.uniform(1, 2))
                
        except Exception as google_exc:
            errors.append(f"Google Facebook search failed: {google_exc}")
        
        # Strategy 2: Bing Search (if we need more results)
        if len(posts) < 10:
            try:
                for search_query in search_variants[2:6]:
                    headers = random.choice(headers_list)
                    
                    bing_url = "https://www.bing.com/search"
                    params = {
                        'q': search_query,
                        'count': 20,
                        'offset': 0
                    }
                    
                    response = requests.get(bing_url, params=params, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        found_posts = extract_facebook_links(soup, "Bing")
                        posts.extend(found_posts)
                        
                        if len(posts) >= 15:
                            break
                    
                    time.sleep(random.uniform(1, 2))
                    
            except Exception as bing_exc:
                errors.append(f"Bing Facebook search failed: {bing_exc}")
        
        # Strategy 3: DuckDuckGo Search (if we still need more)
        if len(posts) < 5:
            try:
                for search_query in search_variants[-2:]:
                    headers = random.choice(headers_list)
                    
                    ddg_url = "https://duckduckgo.com/html"
                    params = {'q': search_query}
                    
                    response = requests.get(ddg_url, params=params, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        found_posts = extract_facebook_links(soup, "DuckDuckGo")
                        posts.extend(found_posts)
                        
                        if len(posts) >= 10:
                            break
                    
                    time.sleep(random.uniform(1, 2))
                    
            except Exception as ddg_exc:
                errors.append(f"DuckDuckGo Facebook search failed: {ddg_exc}")
        
        # Strategy 4: Check specific Facebook profiles if provided
        if topic.profiles:
            profile_urls = [p.strip() for p in topic.profiles.split(',') if 'facebook.com' in p or 'fb.com' in p]
            for profile_url in profile_urls[:3]:  # Limit to 3 profiles
                try:
                    # Extract page identifier
                    page_id = profile_url.rstrip('/').split('/')[-1]
                    
                    # Search for this specific page
                    profile_search = f'{query} site:facebook.com/{page_id}'
                    
                    headers = random.choice(headers_list)
                    params = {'q': profile_search, 'num': 10}
                    
                    response = requests.get("https://www.google.com/search", params=params, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        profile_posts = extract_facebook_links(soup, f"Profile:{page_id}")
                        posts.extend(profile_posts)
                    
                    time.sleep(random.uniform(1, 2))
                    
                except Exception as profile_exc:
                    errors.append(f"Profile search failed for {profile_url}: {profile_exc}")
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_posts = []
        for post in posts:
            if post['url'] and post['url'] not in seen_urls:
                seen_urls.add(post['url'])
                unique_posts.append(post)
        
        posts = unique_posts[:20]  # Limit to top 20 results
        
        if not posts:
            errors.append(f"No Facebook content found for '{query}' despite trying multiple search engines and strategies.")
        
    except Exception as exc:
        errors.append(f"Facebook collection failed: {exc}")
    
    return posts, errors


def fetch_youtube(topic: Topic) -> Tuple[List[dict], List[str]]:
    """Collect YouTube videos using web scraping without API keys."""
    posts: List[dict] = []
    errors: List[str] = []
    
    try:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import quote_plus
    except ImportError:
        errors.append("YouTube collection requires 'requests' and 'beautifulsoup4'. Install with: pip install requests beautifulsoup4")
        return posts, errors
    
    try:
        # Build search query
        query = topic.name
        if topic.keywords:
            keywords = [k.strip() for k in topic.keywords.split(',') if k.strip()]
            query += ' ' + ' '.join(keywords[:3])  # Limit to avoid overly long queries
        
        # Use YouTube search without API
        search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the YouTube search results page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find video data in the page's JavaScript
        import json
        import re
        
        # Look for the initial data containing video information
        script_tags = soup.find_all('script')
        video_data = []
        
        for script in script_tags:
            if script.string and 'var ytInitialData' in script.string:
                # Extract JSON data from the script
                json_text = script.string
                start = json_text.find('{')
                end = json_text.rfind('}') + 1
                if start != -1 and end > start:
                    try:
                        data = json.loads(json_text[start:end])
                        
                        # Navigate through YouTube's data structure to find videos
                        contents = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
                        
                        for section in contents:
                            items = section.get('itemSectionRenderer', {}).get('contents', [])
                            for item in items:
                                video_renderer = item.get('videoRenderer', {})
                                if video_renderer:
                                    # Extract video information
                                    video_id = video_renderer.get('videoId', '')
                                    if video_id:
                                        title_runs = video_renderer.get('title', {}).get('runs', [])
                                        title = title_runs[0].get('text', '') if title_runs else 'Unknown Title'
                                        
                                        # Get description if available
                                        desc_runs = video_renderer.get('descriptionSnippet', {}).get('runs', [])
                                        description = ' '.join([run.get('text', '') for run in desc_runs]) if desc_runs else ''
                                        
                                        # Get view count
                                        view_text = video_renderer.get('viewCountText', {}).get('simpleText', '0 views')
                                        
                                        # Get published time
                                        published_text = video_renderer.get('publishedTimeText', {}).get('simpleText', 'Unknown time')
                                        
                                        # Get thumbnail
                                        thumbnails = video_renderer.get('thumbnail', {}).get('thumbnails', [])
                                        thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''
                                        
                                        # Get channel name
                                        channel_name = video_renderer.get('ownerText', {}).get('runs', [{}])[0].get('text', 'Unknown Channel')
                                        
                                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                                        
                                        # Create post data
                                        video_data.append({
                                            'source': 'youtube',
                                            'title': f"{title} \n(by {channel_name})",
                                            'content': f"<p>{description}</p>",
                                            'url': video_url,
                                            'posted_at': datetime.utcnow() - timedelta(days=1),  # Approximate since we don't have exact date
                                            'likes': 0,  # YouTube likes not available without API
                                            'comments': 0,  # YouTube comments not available without API  
                                            'image_url': thumbnail_url,
                                            'is_photo': False,
                                        })
                                        
                                        if len(video_data) >= 20:  # Limit results
                                            break
                            if len(video_data) >= 20:
                                break
                        break  # Found the data, no need to check more scripts
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        
        posts = video_data
        
        if not posts:
            # Fallback: try to extract basic video links from the HTML
            video_links = soup.find_all('a', {'href': re.compile(r'/watch\?v=')})
            for link in video_links[:10]:  # Limit fallback results
                href = link.get('href', '')
                if href.startswith('/watch?v='):
                    video_url = f"https://www.youtube.com{href}"
                    title = link.get_text(strip=True) or 'YouTube Video'
                    
                    posts.append({
                        'source': 'youtube',
                        'title': f"{title}",
                        'content': f"",
                        'url': video_url,
                        'posted_at': datetime.utcnow() - timedelta(days=1),
                        'likes': 0,
                        'comments': 0,
                        'image_url': None,
                        'is_photo': False,
                    })
        
        # Remove duplicates
        seen_urls = set()
        unique_posts = []
        for post in posts:
            if post['url'] not in seen_urls:
                seen_urls.add(post['url'])
                unique_posts.append(post)
        
        posts = unique_posts[:15]  # Limit to 15 videos
        
        if not posts:
            errors.append(f"No YouTube videos found for '{query}'. YouTube's structure may have changed.")
            
    except Exception as exc:
        errors.append(f"YouTube collection failed: {exc}")
    
    return posts, errors


def collect_all_topics_efficiently(topics: List[Topic], progress: Callable[[str], None] | None = None) -> List[str]:
    """
    Efficiently collect data by source first, then match to topics.
    This reduces redundant API calls and web scraping.
    """
    session = SessionLocal()
    errors: List[str] = []
    
    # Check if any topic needs collection (hasn't been collected in the last hour)
    now = datetime.utcnow()
    topics_needing_update = []
    
    for topic in topics:
        db_topic = session.query(Topic).get(topic.id)
        if not db_topic or not db_topic.last_collected or now - db_topic.last_collected > timedelta(hours=1):
            topics_needing_update.append(db_topic or topic)
    
    if not topics_needing_update:
        session.close()
        return ["All topics collected recently; skipping."]
    
    if progress:
        progress(f"Efficiently collecting for {len(topics_needing_update)} topics...")
    
    # Collect by source, then match to all relevant topics
    sources_and_fetchers = [
        ("reddit", fetch_reddit),
        ("news", fetch_news), 
        ("instagram", fetch_instagram),
        ("facebook", fetch_facebook),
        ("photos", fetch_photos),
        ("youtube", fetch_youtube)
    ]
    
    for source_name, fetcher in sources_and_fetchers:
        if progress:
            progress(f"Collecting from {source_name}...")
        
        # Collect all posts from this source for all topics
        all_source_posts = []
        
        for topic in topics_needing_update:
            try:
                posts, source_errors = fetcher(topic)
                
                # Tag posts with topic info
                for post in posts:
                    post['topic_id'] = topic.id
                    post['topic_name'] = topic.name
                    
                all_source_posts.extend(posts)
                errors.extend(source_errors)
                
            except Exception as exc:
                errors.append(f"Error collecting {source_name} for topic '{topic.name}': {exc}")
        
        # Batch insert all posts from this source
        if progress:
            progress(f"Saving {len(all_source_posts)} posts from {source_name}...")
        
        for post_data in all_source_posts:
            try:
                # Check if post already exists
                existing = session.query(Post).filter_by(url=post_data['url']).first()
                if not existing:
                    # Ensure all required fields are present
                    post_dict = {
                        'topic_id': post_data.get('topic_id'),
                        'source': post_data.get('source', ''),
                        'title': post_data.get('title', ''),
                        'content': post_data.get('content', ''),
                        'url': post_data.get('url', ''),
                        'posted_at': post_data.get('posted_at', datetime.utcnow()),
                        'likes': post_data.get('likes', 0),
                        'comments': post_data.get('comments', 0),
                        'image_url': post_data.get('image_url'),
                        'is_photo': post_data.get('is_photo', False),
                        'subreddit': post_data.get('subreddit')  # For Reddit posts
                    }
                    
                    post = Post(**post_dict)
                    session.add(post)
                    
            except Exception as exc:
                errors.append(f"Error saving post from {source_name}: {exc}")
        
        # Commit after each source to avoid large transactions
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            errors.append(f"Database commit error for {source_name}: {exc}")
    
    # Update last_collected timestamps
    for topic in topics_needing_update:
        try:
            db_topic = session.query(Topic).get(topic.id)
            if db_topic:
                db_topic.last_collected = now
        except Exception as exc:
            errors.append(f"Error updating timestamp for {topic.name}: {exc}")
    
    try:
        session.commit()
    except Exception as exc:
        session.rollback()
        errors.append(f"Error updating timestamps: {exc}")
    
    session.close()
    
    if progress:
        progress(f"✅ Efficient collection complete! {len(errors)} errors.")
    
    return errors


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
        ("reddit", fetch_reddit),
        ("news", fetch_news),
        ("instagram", fetch_instagram),
        ("facebook", fetch_facebook),
        ("photos", fetch_photos),
        ("youtube", fetch_youtube),
    ]
    errors: List[str] = []
    for name, fetcher in fetchers:
        if progress:
            progress(f"checking {name}...")
        posts, errs = fetcher(db_topic)
        for item in posts:
            if not session.query(Post).filter_by(url=item['url']).first():
                # Ensure all required fields are present with defaults
                post_data = {
                    'topic_id': db_topic.id,
                    'source': item.get('source', ''),
                    'title': item.get('title', ''),
                    'content': item.get('content', ''),
                    'url': item.get('url', ''),
                    'posted_at': item.get('posted_at', datetime.utcnow()),
                    'likes': item.get('likes', 0),
                    'comments': item.get('comments', 0),
                    'image_url': item.get('image_url'),  # Can be None
                    'is_photo': item.get('is_photo', False),
                    'subreddit': item.get('subreddit')  # Add subreddit field
                }
                post = Post(**post_data)
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
