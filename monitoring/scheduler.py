"""Background scheduler for periodic data collection and notifications."""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging

from .database import SessionLocal, Topic, Post
from .collectors import collect_topic
from .summarizer import summarize
from .notifier import send_email, create_digest_html

logger = logging.getLogger(__name__)


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
        # Run every hour, on the hour
        scheduler.add_job(
            run_cycle,
            'cron',
            minute=0,
            id='hourly_collection',
            replace_existing=True
        )
        scheduler.start()
        logger.info("Scheduler started successfully - collectors will run every hour on the hour.")
        return scheduler
    except Exception as exc:
        logger.error(f"Failed to start scheduler: {exc}")
        return None
