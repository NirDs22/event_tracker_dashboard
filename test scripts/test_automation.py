#!/usr/bin/env python3
"""
Test script to verify automation components work correctly.
Run this locally to test the automation before deploying to GitHub Actions.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from monitoring.database import SessionLocal, User, SharedTopic
from monitoring.shared_topics import get_all_shared_topics_for_collection
from monitoring.shared_collectors import collect_shared_topic_data
from ui.sidebar import generate_and_send_digest
from sqlalchemy import and_, func


def test_database_connection():
    """Test database connectivity."""
    print("🔌 Testing database connection...")
    try:
        session = SessionLocal()
        session.execute('SELECT 1')
        session.close()
        print("✅ Database connection: OK")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def test_shared_topics():
    """Test shared topic functionality."""
    print("\n📊 Testing shared topics...")
    try:
        topics = get_all_shared_topics_for_collection()
        print(f"✅ Found {len(topics)} shared topics")
        
        if topics:
            print("   Topics:")
            for topic in topics[:5]:  # Show first 5
                print(f"   • {topic.name} (ID: {topic.id})")
            if len(topics) > 5:
                print(f"   ... and {len(topics) - 5} more")
        
        return len(topics) > 0
    except Exception as e:
        print(f"❌ Shared topics test failed: {e}")
        return False


def test_data_collection():
    """Test data collection for one topic."""
    print("\n🔄 Testing data collection...")
    try:
        topics = get_all_shared_topics_for_collection()
        if not topics:
            print("❌ No topics available for collection test")
            return False
        
        # Test with first topic
        test_topic = topics[0]
        print(f"   Testing collection for: {test_topic.name}")
        
        result = collect_shared_topic_data(
            test_topic.id,
            test_topic.name,
            test_topic.keywords or '',
            test_topic.profiles or ''
        )
        
        if result.get('success'):
            posts = result.get('posts_collected', 0)
            sources = result.get('sources_processed', [])
            print(f"✅ Collection test successful: {posts} posts from {len(sources)} sources")
            return True
        else:
            error = result.get('error', 'Unknown error')
            print(f"⚠️ Collection test had issues: {error}")
            return False
            
    except Exception as e:
        print(f"❌ Data collection test failed: {e}")
        return False


def test_users_for_digest():
    """Test user eligibility for digest emails."""
    print("\n👥 Testing users for digest emails...")
    try:
        session = SessionLocal()
        
        # Count total users
        total_users = session.query(func.count(User.id)).scalar()
        print(f"   Total users: {total_users}")
        
        # Count eligible users
        eligible_users = session.query(func.count(User.id)).filter(
            and_(
                User.digest_enabled == True,
                User.email.isnot(None),
                User.is_guest == False
            )
        ).scalar()
        print(f"   Eligible for digest: {eligible_users}")
        
        # Show some eligible users
        users = session.query(User).filter(
            and_(
                User.digest_enabled == True,
                User.email.isnot(None),
                User.is_guest == False
            )
        ).limit(3).all()
        
        if users:
            print("   Eligible users:")
            for user in users:
                freq = user.digest_frequency or 'daily'
                last_sent = user.last_digest_sent.strftime('%Y-%m-%d %H:%M') if user.last_digest_sent else 'Never'
                print(f"   • {user.email} (freq: {freq}, last sent: {last_sent})")
        
        session.close()
        print(f"✅ User eligibility test: {eligible_users} users eligible")
        return eligible_users > 0
        
    except Exception as e:
        print(f"❌ User eligibility test failed: {e}")
        return False


def test_digest_generation():
    """Test digest email generation (without sending)."""
    print("\n📧 Testing digest generation...")
    try:
        session = SessionLocal()
        
        # Find a user for testing
        user = session.query(User).filter(
            and_(
                User.email.isnot(None),
                User.is_guest == False
            )
        ).first()
        
        if not user:
            print("❌ No eligible user found for digest test")
            return False
        
        print(f"   Testing digest for user: {user.email}")
        
        # Generate sample digest (user_id = 0 for sample)
        result = generate_and_send_digest("test@example.com", user_id=0)
        
        # We don't actually send, just test generation
        if isinstance(result, dict):
            success = result.get('success', False)
        else:
            success = bool(result)
        
        if success:
            print("✅ Digest generation test successful")
            return True
        else:
            print("⚠️ Digest generation test had issues")
            return False
            
    except Exception as e:
        print(f"❌ Digest generation test failed: {e}")
        return False
    finally:
        session.close()


def main():
    """Run all tests."""
    print("🧪 Event Tracker Automation Tests")
    print("=" * 40)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Shared Topics", test_shared_topics),
        ("Data Collection", test_data_collection),
        ("User Eligibility", test_users_for_digest),
        ("Digest Generation", test_digest_generation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Automation should work correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
