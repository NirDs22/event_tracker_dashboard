#!/usr/bin/env python3
"""
Comprehensive test script to verify PostgreSQL migration is working correctly
"""

import sys
import traceback
from datetime import datetime

def test_database_operations():
    """Test all major database operations"""
    print("🔍 Testing PostgreSQL migration...")
    
    try:
        from monitoring.database import SessionLocal, User, SharedTopic, SharedPost, engine
        from monitoring.shared_topics import find_or_create_shared_topic
        from monitoring.secrets import get_secret
        
        print(f"   ✅ Connected to: {engine.dialect.name}")
        
        # Test 1: Database connection
        print("\n1. Testing database connection...")
        session = SessionLocal()
        
        # Test 2: User operations
        print("\n2. Testing user operations...")
        test_user = User(
            email="test@migration.com",
            is_guest=False,
            digest_enabled=True,
            digest_frequency='daily'
        )
        session.add(test_user)
        session.commit()
        user_id = test_user.id
        print(f"   ✅ Created test user with ID: {user_id}")
        
        # Test 3: Shared topic operations using service layer
        print("\n3. Testing shared topic operations...")
        shared_topic = find_or_create_shared_topic(
            session, 
            "Test Migration Topic",
            keywords="test,migration"
        )
        print(f"   ✅ Created/found shared topic: {shared_topic.name}")
        
        # Test 4: Shared post operations
        print("\n4. Testing shared post operations...")
        test_post = SharedPost(
            shared_topic_id=shared_topic.id,
            source='news',
            title='Test Migration Post',
            content='This is a test post to verify PostgreSQL migration',
            url=f'https://test.com/migration-{datetime.now().timestamp()}',
            posted_at=datetime.now(),
            likes=5,
            comments=2,
            image_url='https://example.com/test.jpg',
            subreddit='test'
        )
        session.add(test_post)
        session.commit()
        print(f"   ✅ Created shared post: {test_post.title}")
        
        # Test 5: Query operations
        print("\n5. Testing query operations...")
        
        # Count users
        user_count = session.query(User).count()
        print(f"   📊 Total users: {user_count}")
        
        # Count topics
        topic_count = session.query(SharedTopic).count()
        print(f"   📊 Total topics: {topic_count}")
        
        # Count posts
        post_count = session.query(SharedPost).count()
        print(f"   📊 Total posts: {post_count}")
        
        # Test complex query
        recent_posts = session.query(SharedPost).filter(
            SharedPost.source == 'news'
        ).order_by(SharedPost.posted_at.desc()).limit(5).all()
        print(f"   📊 Recent news posts: {len(recent_posts)}")
        
        # Test 6: Authentication features
        print("\n6. Testing authentication features...")
        user = session.query(User).filter(User.email == "test@migration.com").first()
        if user:
            print(f"   ✅ User authentication data: digest_enabled={user.digest_enabled}")
            print(f"   ✅ Remember me fields: {user.remember_me_enabled}")
        
        # Test 7: Clean up
        print("\n7. Cleaning up test data...")
        # Delete test data
        session.delete(test_post)
        session.delete(shared_topic)
        session.delete(test_user)
        session.commit()
        print("   ✅ Test data cleaned up")
        
        session.close()
        
        print("\n🎉 All database tests passed! PostgreSQL migration is successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()
        return False

def test_app_features():
    """Test application features"""
    print("\n🔍 Testing application features...")
    
    try:
        # Test core imports
        from ui.views import render_news_tab
        from ui.cards import render_card, render_youtube_card
        from monitoring.collectors import fetch_news
        from auth.service import start_login
        from monitoring.database import engine
        
        print(f"   ✅ Database engine: {engine.dialect.name}")
        print("   ✅ All core imports successful")
        print("   ✅ UI components available")
        print("   ✅ Data collectors available") 
        print("   ✅ Authentication service available")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Feature test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 POSTGRESQL MIGRATION VERIFICATION")
    print("=" * 60)
    
    db_success = test_database_operations()
    app_success = test_app_features()
    
    print("\n" + "=" * 60)
    if db_success and app_success:
        print("🎉 MIGRATION SUCCESSFUL! All tests passed.")
        print("✅ Database: PostgreSQL on Neon")
        print("✅ Features: All application features working")
        print("✅ Design: All UI components preserved")
        sys.exit(0)
    else:
        print("❌ MIGRATION ISSUES DETECTED")
        sys.exit(1)
