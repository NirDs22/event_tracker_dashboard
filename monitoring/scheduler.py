"""Background scheduler for periodic data collection and notifications."""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging

from .database import SessionLocal, Topic, Post, User, UserTopicSubscription
from .collectors import collect_topic
from .summarizer import summarize
from .notifier import send_email, create_digest_html

logger = logging.getLogger(__name__)


def cleanup_old_guest_users():
    """Clean up guest users older than 24 hours and their associated data."""
    session = SessionLocal()
    try:
        # Calculate cutoff time (24 hours ago)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Find old guest users
        old_guests = session.query(User).filter(
            User.is_guest == True,
            User.created_at <= cutoff_time
        ).all()
        
        if not old_guests:
            logger.info("No old guest users to clean up")
            return
        
        logger.info(f"Found {len(old_guests)} guest users older than 24 hours")
        
        deleted_count = 0
        for user in old_guests:
            try:
                # Delete associated subscriptions
                subscriptions_deleted = session.query(UserTopicSubscription).filter(
                    UserTopicSubscription.user_id == user.id
                ).delete()
                
                # Delete associated legacy topics and their posts
                legacy_topics = session.query(Topic).filter(Topic.user_id == user.id).all()
                for topic in legacy_topics:
                    posts_deleted = session.query(Post).filter(Post.topic_id == topic.id).delete()
                    if posts_deleted > 0:
                        logger.info(f"Deleted {posts_deleted} posts for legacy topic '{topic.name}' of old guest user {user.id}")
                
                topics_deleted = session.query(Topic).filter(Topic.user_id == user.id).delete()
                
                # Delete the user
                session.delete(user)
                deleted_count += 1
                
                logger.info(f"Deleted old guest user ID {user.id} with {subscriptions_deleted} subscriptions and {topics_deleted} legacy topics")
                
            except Exception as e:
                logger.error(f"Error deleting guest user {user.id}: {e}")
                continue
        
        session.commit()
        logger.info(f"Successfully cleaned up {deleted_count} old guest users")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error during guest user cleanup: {e}")
    finally:
        session.close()


def cleanup_abandoned_topics():
    """Clean up shared topics with no subscribers and legacy topics with deleted users."""
    session = SessionLocal()
    try:
        from .database import SharedTopic, SharedPost
        
        # Find shared topics with no subscribers
        abandoned_shared_topics = []
        shared_topics = session.query(SharedTopic).all()
        
        for topic in shared_topics:
            subscriber_count = session.query(UserTopicSubscription).filter(
                UserTopicSubscription.shared_topic_id == topic.id
            ).count()
            
            if subscriber_count == 0:
                abandoned_shared_topics.append(topic)
        
        if abandoned_shared_topics:
            logger.info(f"Found {len(abandoned_shared_topics)} abandoned shared topics")
            
            for topic in abandoned_shared_topics:
                try:
                    # Delete associated posts first
                    posts_deleted = session.query(SharedPost).filter(
                        SharedPost.shared_topic_id == topic.id
                    ).delete()
                    
                    # Delete the topic
                    session.delete(topic)
                    
                    logger.info(f"Deleted abandoned shared topic '{topic.name}' (ID: {topic.id}) with {posts_deleted} posts")
                    
                except Exception as e:
                    logger.error(f"Error deleting shared topic {topic.id}: {e}")
                    continue
        
        # Find legacy topics with no valid users
        abandoned_legacy_topics = []
        legacy_topics = session.query(Topic).all()
        
        for topic in legacy_topics:
            user_exists = session.query(User).filter(User.id == topic.user_id).first()
            if not user_exists:
                abandoned_legacy_topics.append(topic)
        
        if abandoned_legacy_topics:
            logger.info(f"Found {len(abandoned_legacy_topics)} legacy topics with deleted users")
            
            for topic in abandoned_legacy_topics:
                try:
                    # Delete associated posts first
                    posts_deleted = session.query(Post).filter(
                        Post.topic_id == topic.id
                    ).delete()
                    
                    # Delete the topic
                    session.delete(topic)
                    
                    logger.info(f"Deleted orphaned legacy topic '{topic.name}' (ID: {topic.id}) with {posts_deleted} posts")
                    
                except Exception as e:
                    logger.error(f"Error deleting legacy topic {topic.id}: {e}")
                    continue
        
        if abandoned_shared_topics or abandoned_legacy_topics:
            session.commit()
            total_deleted = len(abandoned_shared_topics) + len(abandoned_legacy_topics)
            logger.info(f"Successfully cleaned up {total_deleted} abandoned topics")
        else:
            logger.info("No abandoned topics found")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error during abandoned topic cleanup: {e}")
    finally:
        session.close()


def run_cycle():
    """Run the daily collection and notification cycle."""
    session = SessionLocal()
    try:
        topics = session.query(Topic).all()
        logger.info(f"Running daily cycle for {len(topics)} topics")
        
        for topic in topics:
            try:
                # Collect new posts for this topic
                logger.info(f"Collecting posts for topic: {topic.name}")
                errors = collect_topic(topic, force=False)  # Don't force if recently collected
                
                if errors:
                    logger.warning(f"Collection errors for {topic.name}: {errors}")
                
                # Get recent posts (last 24 hours or last 20 posts, whichever is more)
                recent_posts = (
                    session.query(Post)
                    .filter_by(topic_id=topic.id)
                    .filter(Post.posted_at > datetime.utcnow() - timedelta(days=1))
                    .order_by(Post.posted_at.desc())
                    .limit(20)
                    .all()
                )
                
                if not recent_posts:
                    logger.info(f"No recent posts for {topic.name}, skipping digest")
                    continue
                
                # Create summary
                post_contents = [p.content for p in recent_posts if p.content]
                summary = summarize(post_contents) if post_contents else "No recent content to summarize."
                
                # Send email to anyone with @ in the profiles field
                if topic.profiles:
                    emails = [
                        profile.strip() 
                        for profile in topic.profiles.split(',') 
                        if '@' in profile.strip()
                    ]
                    
                    for email in emails:
                        try:
                            # Prepare post data for HTML digest
                            posts_data = []
                            for post in recent_posts:
                                posts_data.append({
                                    'content': post.content,
                                    'url': post.url,
                                    'source': post.source,
                                    'posted_at': post.posted_at,
                                    'likes': post.likes,
                                    'comments': post.comments
                                })
                            
                            # Create HTML digest
                            html_body = create_digest_html(topic.name, posts_data, summary)
                            
                            # Send email
                            subject = f"📰 Daily Digest: {topic.name} ({len(recent_posts)} new posts)"
                            success = send_email(email, subject, html_body, 'html')
                            
                            if success:
                                logger.info(f"Digest sent successfully to {email} for topic {topic.name}")
                            else:
                                logger.error(f"Failed to send digest to {email} for topic {topic.name}")
                                
                        except Exception as email_exc:
                            logger.error(f"Error sending email to {email}: {email_exc}")
                
            except Exception as topic_exc:
                logger.error(f"Error processing topic {topic.name}: {topic_exc}")
                
    except Exception as cycle_exc:
        logger.error(f"Error in daily cycle: {cycle_exc}")
    finally:
        session.close()


def send_test_digest(topic_id: int, test_email: str) -> bool:
    """Send a test digest for a specific topic to verify email configuration."""
    session = SessionLocal()
    try:
        topic = session.query(Topic).get(topic_id)
        if not topic:
            logger.error(f"Topic with ID {topic_id} not found")
            return False
        
        # Get recent posts
        recent_posts = (
            session.query(Post)
            .filter_by(topic_id=topic.id)
            .order_by(Post.posted_at.desc())
            .limit(10)
            .all()
        )
        
        if not recent_posts:
            logger.warning(f"No posts found for topic {topic.name}")
            return False
        
        # Create summary
        post_contents = [p.content for p in recent_posts if p.content]
        summary = summarize(post_contents) if post_contents else "No content to summarize."
        
        # Prepare post data
        posts_data = []
        for post in recent_posts:
            posts_data.append({
                'content': post.content,
                'url': post.url,
                'source': post.source,
                'posted_at': post.posted_at,
                'likes': post.likes,
                'comments': post.comments
            })
        
        # Create and send test digest
        html_body = create_digest_html(topic.name, posts_data, summary)
        subject = f"🧪 Test Digest: {topic.name} ({len(recent_posts)} posts)"
        
        return send_email(test_email, subject, html_body, 'html')
        
    except Exception as exc:
        logger.error(f"Error sending test digest: {exc}")
        return False
    finally:
        session.close()


def start_scheduler():
    """Start the background scheduler for daily data collection and notifications."""
    try:
        scheduler = BackgroundScheduler()
        
        # Run collection every hour, on the hour
        scheduler.add_job(
            run_cycle,
            'cron',
            minute=0,
            id='hourly_collection',
            replace_existing=True
        )
        
        # Run guest user cleanup every 6 hours at minute 30
        scheduler.add_job(
            cleanup_old_guest_users,
            'cron',
            minute=30,
            hour='*/6',
            id='guest_user_cleanup',
            replace_existing=True
        )
        
        # Run abandoned topic cleanup every 24 hours at 2:00 AM
        scheduler.add_job(
            cleanup_abandoned_topics,
            'cron',
            hour=2,
            minute=0,
            id='abandoned_topic_cleanup',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Scheduler started successfully - collectors every hour, guest cleanup every 6 hours, topic cleanup daily at 2 AM.")
        return scheduler
    except Exception as exc:
        logger.error(f"Failed to start scheduler: {exc}")
        return None
