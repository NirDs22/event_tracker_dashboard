"""Background scheduler for periodic data collection and notifications."""
from apscheduler.schedulers.background import BackgroundScheduler

from .database import SessionLocal, Topic
from .collectors import collect_topic
from .summarizer import summarize
from .notifier import send_email


def run_cycle():
    session = SessionLocal()
    topics = session.query(Topic).all()
    for topic in topics:
        collect_topic(topic)
        posts = [p.content for p in topic.posts[-20:]]
        summary = summarize(posts)
        # Example: send summary if user email stored in profiles field as mail
        for profile in topic.profiles.split(','):
            if '@' in profile:
                send_email(profile.strip(), f"Daily digest for {topic.name}", summary)
    session.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_cycle, 'interval', hours=24, id='daily_collection')
    scheduler.start()
    return scheduler
