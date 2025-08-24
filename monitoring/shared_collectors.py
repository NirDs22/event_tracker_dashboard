"""Shared topic collectors - efficient centralized data collection."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from monitoring.database import SessionLocal
from monitoring.shared_topics import (
    get_all_shared_topics_for_collection,
    update_shared_topic_collection_time,
    create_shared_post
)
from monitoring.collectors import (
    # Import existing collector functions
    fetch_twitter,
    fetch_reddit,
    fetch_news,
    fetch_instagram,
    fetch_youtube,
    fetch_facebook,
    fetch_photos,
    collect_topic  # For backward compatibility
)


class SharedTopicCollector:
    """Centralized collector for shared topics."""
    
    def __init__(self):
        self.collection_sources = {
            'twitter': self._collect_twitter,
            'reddit': self._collect_reddit,
            'news': self._collect_news,
            'youtube': self._collect_youtube,
            'instagram': self._collect_instagram,
            'facebook': self._collect_facebook,
            'photos': self._collect_photos
        }
    
    def collect_all_shared_topics(self, progress_callback: Callable[[str], None] = None) -> Dict[str, Any]:
        """Collect data for all shared topics efficiently."""
        
        if progress_callback:
            progress_callback("🚀 Starting shared topic collection...")
        
        shared_topics = get_all_shared_topics_for_collection()
        
        if not shared_topics:
            if progress_callback:
                progress_callback("No shared topics found to collect")
            return {'total_topics': 0, 'total_posts': 0, 'errors': []}
        
        total_posts = 0
        all_errors = []
        
        if progress_callback:
            progress_callback(f"Found {len(shared_topics)} shared topics to collect")
        
        # Group topics by collection source for efficiency
        source_groups = self._group_topics_by_source(shared_topics)
        
        # Collect from each source with all relevant topics at once
        for source_name, topics_for_source in source_groups.items():
            if progress_callback:
                progress_callback(f"📊 Collecting from {source_name} for {len(topics_for_source)} topics")
            
            try:
                posts_collected, errors = self._collect_from_source(source_name, topics_for_source)
                total_posts += posts_collected
                all_errors.extend(errors)
                
                if progress_callback:
                    progress_callback(f"✅ {source_name}: {posts_collected} posts collected")
                    
            except Exception as e:
                error_msg = f"❌ Error collecting from {source_name}: {str(e)}"
                all_errors.append(error_msg)
                if progress_callback:
                    progress_callback(error_msg)
        
        # Update collection times
        for topic in shared_topics:
            update_shared_topic_collection_time(topic.id)
        
        result = {
            'total_topics': len(shared_topics),
            'total_posts': total_posts,
            'errors': all_errors,
            'sources_processed': list(source_groups.keys())
        }
        
        if progress_callback:
            progress_callback(f"🎉 Collection complete! {total_posts} total posts from {len(source_groups)} sources")
        
        return result
    
    def _group_topics_by_source(self, shared_topics) -> Dict[str, List]:
        """Group shared topics by their collection sources for efficiency."""
        source_groups = {}
        
        for topic in shared_topics:
            # Determine which sources this topic should use
            sources = self._determine_sources_for_topic(topic)
            
            for source in sources:
                if source not in source_groups:
                    source_groups[source] = []
                source_groups[source].append(topic)
        
        return source_groups
    
    def _determine_sources_for_topic(self, shared_topic) -> List[str]:
        """Determine which sources to use for a shared topic based on keywords/profiles."""
        # Default: collect from ALL major sources for comprehensive coverage
        sources = ['news', 'reddit', 'twitter', 'youtube']  
        
        keywords_lower = shared_topic.keywords.lower() if shared_topic.keywords else ''
        profiles_lower = shared_topic.profiles.lower() if shared_topic.profiles else ''
        
        # Add additional sources based on specific content
        if 'instagram' in profiles_lower or 'photo' in keywords_lower:
            sources.append('instagram')
        
        if 'facebook' in profiles_lower:
            sources.append('facebook')
            
        if 'photo' in keywords_lower or 'image' in keywords_lower:
            sources.append('photos')
        
        # Remove duplicates and return
        return list(set(sources))
        
        if 'instagram' in profiles_lower or 'photo' in keywords_lower:
            sources.append('instagram')
        
        if 'facebook' in profiles_lower:
            sources.append('facebook')
        
        return list(set(sources))  # Remove duplicates
    
    def _collect_from_source(self, source_name: str, topics: List) -> tuple[int, List[str]]:
        """Collect data from a specific source for multiple topics."""
        if source_name not in self.collection_sources:
            return 0, [f"Unknown source: {source_name}"]
        
        return self.collection_sources[source_name](topics)
    
    def _collect_twitter(self, topics: List) -> tuple[int, List[str]]:
        """Collect Twitter data for multiple topics efficiently."""
        total_posts = 0
        errors = []
        
        # Use existing twitter collector but optimize for multiple topics
        for topic in topics:
            try:
                # Convert shared topic to Topic-like object for compatibility
                temp_topic = type('Topic', (), {
                    'name': topic.name,
                    'keywords': topic.keywords,
                    'profiles': topic.profiles,
                    'id': topic.id
                })()
                
                posts, topic_errors = fetch_twitter_nitter(temp_topic)
                errors.extend(topic_errors)
                
                # Store posts in shared system
                for post_data in posts:
                    if self._create_shared_post_from_data(topic.id, post_data, 'twitter'):
                        total_posts += 1
                        
            except Exception as e:
                errors.append(f"Twitter error for {topic.name}: {str(e)}")
        
        return total_posts, errors
    
    def _collect_reddit(self, topics: List) -> tuple[int, List[str]]:
        """Collect Reddit data for multiple topics efficiently."""
        total_posts = 0
        errors = []
        
        for topic in topics:
            try:
                temp_topic = type('Topic', (), {
                    'name': topic.name,
                    'keywords': topic.keywords,
                    'profiles': topic.profiles,
                    'id': topic.id
                })()
                
                posts, topic_errors = fetch_reddit(temp_topic)
                errors.extend(topic_errors)
                
                for post_data in posts:
                    if self._create_shared_post_from_data(topic.id, post_data, 'reddit'):
                        total_posts += 1
                        
            except Exception as e:
                errors.append(f"Reddit error for {topic.name}: {str(e)}")
        
        return total_posts, errors
    
    def _collect_news(self, topics: List) -> tuple[int, List[str]]:
        """Collect news data for multiple topics efficiently."""
        total_posts = 0
        errors = []
        
        for topic in topics:
            try:
                temp_topic = type('Topic', (), {
                    'name': topic.name,
                    'keywords': topic.keywords,
                    'profiles': topic.profiles,
                    'id': topic.id
                })()
                
                posts, topic_errors = fetch_news(temp_topic)
                errors.extend(topic_errors)
                
                for post_data in posts:
                    if self._create_shared_post_from_data(topic.id, post_data, 'news'):
                        total_posts += 1
                        
            except Exception as e:
                errors.append(f"News error for {topic.name}: {str(e)}")
        
        return total_posts, errors
    
    def _collect_instagram(self, topics: List) -> tuple[int, List[str]]:
        """Collect Instagram data for multiple topics efficiently."""
        total_posts = 0
        errors = []
        
        for topic in topics:
            try:
                temp_topic = type('Topic', (), {
                    'name': topic.name,
                    'keywords': topic.keywords,
                    'profiles': topic.profiles,
                    'id': topic.id
                })()
                
                posts, topic_errors = fetch_instagram(temp_topic)
                errors.extend(topic_errors)
                
                for post_data in posts:
                    if self._create_shared_post_from_data(topic.id, post_data, 'instagram'):
                        total_posts += 1
                        
            except Exception as e:
                errors.append(f"Instagram error for {topic.name}: {str(e)}")
        
        return total_posts, errors
    
    def _collect_facebook(self, topics: List) -> tuple[int, List[str]]:
        """Collect Facebook data for multiple topics efficiently."""
        total_posts = 0
        errors = []
        
        for topic in topics:
            try:
                temp_topic = type('Topic', (), {
                    'name': topic.name,
                    'keywords': topic.keywords,
                    'profiles': topic.profiles,
                    'id': topic.id
                })()
                
                posts, topic_errors = fetch_facebook(temp_topic)
                errors.extend(topic_errors)
                
                for post_data in posts:
                    if self._create_shared_post_from_data(topic.id, post_data, 'facebook'):
                        total_posts += 1
                        
            except Exception as e:
                errors.append(f"Facebook error for {topic.name}: {str(e)}")
        
        return total_posts, errors
    
    def _collect_photos(self, topics: List) -> tuple[int, List[str]]:
        """Collect photo data for multiple topics efficiently."""
        total_posts = 0
        errors = []
        
        for topic in topics:
            try:
                temp_topic = type('Topic', (), {
                    'name': topic.name,
                    'keywords': topic.keywords,
                    'profiles': topic.profiles,
                    'id': topic.id
                })()
                
                posts, topic_errors = fetch_photos(temp_topic)
                errors.extend(topic_errors)
                
                for post_data in posts:
                    if self._create_shared_post_from_data(topic.id, post_data, 'photos'):
                        total_posts += 1
                        
            except Exception as e:
                errors.append(f"Photos error for {topic.name}: {str(e)}")
        
        return total_posts, errors
    
    def _collect_youtube(self, topics: List) -> tuple[int, List[str]]:
        """Collect YouTube data for multiple topics efficiently."""
        total_posts = 0
        errors = []
        
        for topic in topics:
            try:
                temp_topic = type('Topic', (), {
                    'name': topic.name,
                    'keywords': topic.keywords,
                    'profiles': topic.profiles,
                    'id': topic.id
                })()
                
                posts, topic_errors = fetch_youtube(temp_topic)
                errors.extend(topic_errors)
                
                for post_data in posts:
                    if self._create_shared_post_from_data(topic.id, post_data, 'youtube'):
                        total_posts += 1
                        
            except Exception as e:
                errors.append(f"YouTube error for {topic.name}: {str(e)}")
        
        return total_posts, errors
    
    def _post_matches_topic(self, post_content: str, topic) -> bool:
        """Check if a post matches a topic's keywords."""
        if not topic.keywords:
            return topic.name.lower() in post_content
        
        keywords = [k.strip().lower() for k in topic.keywords.split(',')]
        return any(keyword in post_content for keyword in keywords)
    
    def _create_shared_post_from_data(self, shared_topic_id: int, post_data: dict, source: str) -> bool:
        """Create a shared post from collected data."""
        try:
            return create_shared_post(
                shared_topic_id=shared_topic_id,
                source=source,
                content=post_data.get('content', ''),
                url=post_data.get('url', ''),
                posted_at=post_data.get('posted_at', datetime.utcnow()),
                title=post_data.get('title'),
                likes=post_data.get('likes', 0),
                comments=post_data.get('comments', 0),
                image_url=post_data.get('image_url'),
                is_photo=post_data.get('is_photo', False),
                subreddit=post_data.get('subreddit')
            )
        except Exception as e:
            print(f"Error creating shared post: {e}")
            return False


# Global collector instance
shared_collector = SharedTopicCollector()


def collect_all_shared_topics_efficiently(progress_callback: Callable[[str], None] = None) -> Dict[str, Any]:
    """Main function to collect all shared topics efficiently."""
    return shared_collector.collect_all_shared_topics(progress_callback)


# Backward compatibility function for migration
def migrate_to_shared_topics():
    """Migrate existing topics to shared topic system."""
    from monitoring.shared_topics import migrate_existing_topics_to_shared
    migrate_existing_topics_to_shared()


def collect_shared_topic_data(shared_topic_id: int, topic_name: str, keywords: str, profiles: str) -> Dict[str, Any]:
    """
    Collect data for a specific shared topic.
    Used by GitHub Actions workflow for individual topic collection.
    
    Returns:
        Dict with success status, posts_collected count, and any errors
    """
    try:
        print(f"🔄 Collecting data for shared topic: {topic_name}")
        
        # Create a temporary topic object for the collector
        temp_topic = type('SharedTopic', (), {
            'id': shared_topic_id,
            'name': topic_name,
            'keywords': keywords or '',
            'profiles': profiles or ''
        })()
        
        # Use the shared collector to collect data for this single topic
        total_posts = 0
        all_errors = []
        
        # Determine sources for this topic
        sources = shared_collector._determine_sources_for_topic(temp_topic)
        
        # Collect from each source
        for source_name in sources:
            try:
                posts_collected, errors = shared_collector._collect_from_source(source_name, [temp_topic])
                total_posts += posts_collected
                all_errors.extend(errors)
                
                if posts_collected > 0:
                    print(f"  ✅ {source_name}: {posts_collected} posts")
                    
            except Exception as e:
                error_msg = f"Error collecting from {source_name}: {str(e)}"
                all_errors.append(error_msg)
                print(f"  ❌ {source_name}: {error_msg}")
        
        # Return success result
        result = {
            'success': True,
            'posts_collected': total_posts,
            'sources_processed': sources,
            'errors': all_errors
        }
        
        if total_posts > 0:
            print(f"✅ Successfully collected {total_posts} posts for {topic_name}")
        else:
            print(f"ℹ️ No new posts found for {topic_name}")
            
        return result
        
    except Exception as e:
        error_msg = f"Failed to collect data for {topic_name}: {str(e)}"
        print(f"❌ {error_msg}")
        
        return {
            'success': False,
            'posts_collected': 0,
            'error': error_msg,
            'sources_processed': []
        }
