#!/usr/bin/env python3
"""
Quick performance test for the database optimizations
"""

import time
from monitoring.database import SessionLocal, SharedTopic, SharedPost, Post, Topic

def test_query_performance():
    """Test database query performance"""
    session = SessionLocal()
    
    try:
        print("🔍 Testing database query performance...")
        
        # Test 1: Count shared topics
        start_time = time.time()
        topic_count = session.query(SharedTopic).count()
        elapsed = time.time() - start_time
        print(f"   📊 Shared topics count ({topic_count}): {elapsed:.3f}s")
        
        # Test 2: Count shared posts
        start_time = time.time()
        post_count = session.query(SharedPost).count()
        elapsed = time.time() - start_time
        print(f"   📊 Shared posts count ({post_count}): {elapsed:.3f}s")
        
        # Test 3: Recent posts with join (optimized query)
        start_time = time.time()
        recent_posts = (
            session.query(SharedPost, SharedTopic)
            .join(SharedTopic)
            .order_by(SharedPost.posted_at.desc())
            .limit(20)
            .all()
        )
        elapsed = time.time() - start_time
        print(f"   📊 Recent posts with join ({len(recent_posts)}): {elapsed:.3f}s")
        
        # Test 4: Topics with post counts
        start_time = time.time()
        topics_with_counts = session.query(SharedTopic).limit(10).all()
        elapsed = time.time() - start_time
        print(f"   📊 Topics query ({len(topics_with_counts)}): {elapsed:.3f}s")
        
        print("✅ Performance tests completed!")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    test_query_performance()
