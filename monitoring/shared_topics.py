"""Service layer for shared topic management."""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from monitoring.database import (
    SessionLocal, 
    SharedTopic, 
    SharedPost, 
    UserTopicSubscription, 
    User,
    Topic,  # Keep for backward compatibility during migration
    Post    # Keep for backward compatibility during migration
)


def normalize_topic_name(name: str) -> str:
    """Normalize topic name for consistent matching."""
    # Convert to lowercase and remove special characters
    normalized = re.sub(r'[^\w\s]', '', name.lower().strip())
    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def get_shared_topic_stats(session: Session, shared_topic_id: int) -> Dict[str, int]:
    """Get statistics for a shared topic."""
    posts_count = session.query(func.count(SharedPost.id)).filter(
        SharedPost.shared_topic_id == shared_topic_id
    ).scalar() or 0
    
    subscribers_count = session.query(func.count(UserTopicSubscription.id)).filter(
        UserTopicSubscription.shared_topic_id == shared_topic_id
    ).scalar() or 0
    
    return {
        'posts_count': posts_count,
        'subscribers_count': subscribers_count
    }


def find_exact_shared_topic(session: Session, topic_name: str) -> Optional[SharedTopic]:
    """Find exact shared topic match by normalized name."""
    normalized_name = normalize_topic_name(topic_name)
    
    return session.query(SharedTopic).filter(
        SharedTopic.name == normalized_name
    ).first()


def find_or_create_shared_topic(
    session: Session, 
    topic_name: str, 
    keywords: str = '', 
    profiles: str = ''
) -> SharedTopic:
    """Find existing shared topic or create new one."""
    normalized_name = normalize_topic_name(topic_name)
    
    # Try to find existing shared topic
    existing = session.query(SharedTopic).filter(
        SharedTopic.name == normalized_name
    ).first()
    
    if existing:
        # Update keywords and profiles if new ones provided
        if keywords and keywords not in existing.keywords:
            if existing.keywords:
                existing.keywords = f"{existing.keywords}, {keywords}"
            else:
                existing.keywords = keywords
        
        if profiles and profiles not in existing.profiles:
            if existing.profiles:
                existing.profiles = f"{existing.profiles}, {profiles}"
            else:
                existing.profiles = profiles
                
        session.commit()
        return existing
    
    # Create new shared topic
    shared_topic = SharedTopic(
        name=normalized_name,
        keywords=keywords,
        profiles=profiles,
        created_at=datetime.utcnow()
    )
    session.add(shared_topic)
    session.commit()
    session.refresh(shared_topic)
    
    return shared_topic


def subscribe_user_to_topic(
    session: Session,
    user_id: int,
    shared_topic_id: int,
    display_name: str = None,
    color: str = "#1f77b4",
    icon: str = "📌"
) -> UserTopicSubscription:
    """Subscribe user to a shared topic."""
    
    # Check if already subscribed
    existing = session.query(UserTopicSubscription).filter(
        and_(
            UserTopicSubscription.user_id == user_id,
            UserTopicSubscription.shared_topic_id == shared_topic_id
        )
    ).first()
    
    if existing:
        return existing
    
    # Create subscription
    subscription = UserTopicSubscription(
        user_id=user_id,
        shared_topic_id=shared_topic_id,
        display_name=display_name,
        color=color,
        icon=icon,
        subscribed_at=datetime.utcnow()
    )
    
    session.add(subscription)
    session.commit()
    session.refresh(subscription)
    
    return subscription


def get_user_subscriptions(session: Session, user_id: int) -> List[Dict[str, Any]]:
    """Get all topics a user is subscribed to with their customizations."""
    
    subscriptions = (
        session.query(UserTopicSubscription, SharedTopic)
        .join(SharedTopic)
        .filter(UserTopicSubscription.user_id == user_id)
        .order_by(UserTopicSubscription.subscribed_at.desc())
        .all()
    )
    
    result = []
    for subscription, shared_topic in subscriptions:
        # Get recent posts count
        posts_count = session.query(func.count(SharedPost.id)).filter(
            SharedPost.shared_topic_id == shared_topic.id
        ).scalar() or 0
        
        result.append({
            'subscription_id': subscription.id,
            'shared_topic_id': shared_topic.id,
            'name': subscription.display_name or shared_topic.name,
            'original_name': shared_topic.name,
            'color': subscription.color,
            'icon': subscription.icon,
            'keywords': shared_topic.keywords,
            'profiles': shared_topic.profiles,
            'last_viewed': subscription.last_viewed,
            'subscribed_at': subscription.subscribed_at,
            'last_collected': shared_topic.last_collected,
            'posts_count': posts_count
        })
    
    return result


def get_shared_topic_posts(
    session: Session, 
    shared_topic_id: int, 
    limit: int = 50,
    offset: int = 0
) -> List[SharedPost]:
    """Get posts for a shared topic."""
    
    posts = (
        session.query(SharedPost)
        .filter(SharedPost.shared_topic_id == shared_topic_id)
        .order_by(SharedPost.posted_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return posts


def unsubscribe_user_from_topic(session: Session, user_id: int, shared_topic_id: int) -> bool:
    """Unsubscribe user from a shared topic."""
    
    subscription = session.query(UserTopicSubscription).filter(
        and_(
            UserTopicSubscription.user_id == user_id,
            UserTopicSubscription.shared_topic_id == shared_topic_id
        )
    ).first()
    
    if subscription:
        session.delete(subscription)
        session.commit()
        return True
    
    return False


def migrate_existing_topics_to_shared():
    """Migrate existing user topics to shared topic system."""
    session = SessionLocal()
    try:
        print("🔄 Starting migration to shared topics...")
        
        # Get all existing topics
        existing_topics = session.query(Topic).all()
        migrated_count = 0
        
        for old_topic in existing_topics:
            try:
                # Find or create shared topic
                shared_topic = find_or_create_shared_topic(
                    session, 
                    old_topic.name,
                    old_topic.keywords,
                    old_topic.profiles
                )
                
                # Subscribe user to shared topic
                subscribe_user_to_topic(
                    session,
                    old_topic.user_id,
                    shared_topic.id,
                    display_name=old_topic.name,  # Keep original display name
                    color=old_topic.color,
                    icon=old_topic.icon
                )
                
                # Migrate posts
                old_posts = session.query(Post).filter(Post.topic_id == old_topic.id).all()
                for old_post in old_posts:
                    # Check if post already exists in shared topic
                    existing_shared_post = session.query(SharedPost).filter(
                        SharedPost.url == old_post.url
                    ).first()
                    
                    if not existing_shared_post:
                        shared_post = SharedPost(
                            shared_topic_id=shared_topic.id,
                            source=old_post.source,
                            title=old_post.title,
                            content=old_post.content,
                            url=old_post.url,
                            posted_at=old_post.posted_at,
                            likes=old_post.likes,
                            comments=old_post.comments,
                            image_url=old_post.image_url,
                            is_photo=old_post.is_photo,
                            subreddit=old_post.subreddit
                        )
                        session.add(shared_post)
                
                # Update shared topic posts count
                shared_topic.posts_count = session.query(func.count(SharedPost.id)).filter(
                    SharedPost.shared_topic_id == shared_topic.id
                ).scalar() or 0
                
                session.commit()
                migrated_count += 1
                print(f"✅ Migrated topic: {old_topic.name} (User: {old_topic.user_id})")
                
            except Exception as e:
                print(f"❌ Error migrating topic {old_topic.name}: {e}")
                session.rollback()
                continue
        
        print(f"✅ Migration completed! Migrated {migrated_count} topics to shared system.")
        
        # Note: We keep old tables for now for safety. They can be dropped later.
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        session.rollback()
    finally:
        session.close()


def get_all_shared_topics_for_collection() -> List[SharedTopic]:
    """Get all shared topics that need data collection."""
    session = SessionLocal()
    try:
        topics = session.query(SharedTopic).all()
        return topics
    finally:
        session.close()


def update_shared_topic_collection_time(shared_topic_id: int):
    """Update the last collected time for a shared topic."""
    session = SessionLocal()
    try:
        shared_topic = session.query(SharedTopic).filter(
            SharedTopic.id == shared_topic_id
        ).first()
        
        if shared_topic:
            shared_topic.last_collected = datetime.utcnow()
            shared_topic.posts_count = session.query(func.count(SharedPost.id)).filter(
                SharedPost.shared_topic_id == shared_topic_id
            ).scalar() or 0
            session.commit()
            
    except Exception as e:
        print(f"❌ Error updating collection time: {e}")
        session.rollback()
    finally:
        session.close()


def create_shared_post(
    shared_topic_id: int,
    source: str,
    content: str,
    url: str,
    posted_at: datetime,
    title: str = None,
    likes: int = 0,
    comments: int = 0,
    image_url: str = None,
    is_photo: bool = False,
    subreddit: str = None
) -> bool:
    """Create a new shared post, avoiding duplicates."""
    session = SessionLocal()
    try:
        # Check if post already exists
        existing = session.query(SharedPost).filter(SharedPost.url == url).first()
        if existing:
            return False  # Post already exists
        
        shared_post = SharedPost(
            shared_topic_id=shared_topic_id,
            source=source,
            title=title,
            content=content,
            url=url,
            posted_at=posted_at,
            likes=likes,
            comments=comments,
            image_url=image_url,
            is_photo=is_photo,
            subreddit=subreddit
        )
        
        session.add(shared_post)
        session.commit()
        return True
        
    except Exception as e:
        print(f"❌ Error creating shared post: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def search_shared_topics(query: str) -> List[Dict[str, Any]]:
    """Search for shared topics by name or keywords."""
    session = SessionLocal()
    try:
        normalized_query = normalize_topic_name(query)
        
        topics = session.query(SharedTopic).filter(
            or_(
                SharedTopic.name.contains(normalized_query),
                SharedTopic.keywords.contains(query)
            )
        ).limit(10).all()
        
        result = []
        for topic in topics:
            posts_count = session.query(func.count(SharedPost.id)).filter(
                SharedPost.shared_topic_id == topic.id
            ).scalar() or 0
            
            subscribers_count = session.query(func.count(UserTopicSubscription.id)).filter(
                UserTopicSubscription.shared_topic_id == topic.id
            ).scalar() or 0
            
            result.append({
                'id': topic.id,
                'name': topic.name,
                'keywords': topic.keywords,
                'profiles': topic.profiles,
                'posts_count': posts_count,
                'subscribers_count': subscribers_count,
                'last_collected': topic.last_collected,
                'created_at': topic.created_at
            })
        
        return result
        
    finally:
        session.close()
