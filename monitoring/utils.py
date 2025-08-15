"""Utility functions for the monitoring system."""

from datetime import datetime, timedelta
from monitoring.database import Topic


def should_skip_collection(topic: Topic) -> bool:
    """Check if we should skip collection based on last collected time."""
    if not topic.last_collected:
        return False
    
    # Skip if collected within last 30 minutes
    time_threshold = datetime.utcnow() - timedelta(minutes=30)
    return topic.last_collected > time_threshold
