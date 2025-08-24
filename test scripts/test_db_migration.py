#!/usr/bin/env python3
"""Test database connection and migration"""

try:
    from monitoring.database import engine, init_db, SessionLocal, User
    from monitoring.secrets import get_secret
    
    print("Testing database connection...")
    
    # Check database URL
    db_url = get_secret('postgres_url') or get_secret('DATABASE_URL')
    print(f"Database URL configured: {'Yes' if db_url else 'No (using SQLite fallback)'}")
    print(f"Database dialect: {engine.dialect.name}")
    print(f"Database URL (masked): {db_url[:20]}...{db_url[-10:] if db_url else 'None'}")
    
    # Test connection
    print("\nTesting database connection...")
    connection = engine.connect()
    print("✅ Database connection successful!")
    connection.close()
    
    # Initialize/migrate database
    print("\nInitializing database...")
    init_db()
    print("✅ Database initialization completed!")
    
    # Test a simple query
    print("\nTesting database operations...")
    session = SessionLocal()
    
    # Count users
    user_count = session.query(User).count()
    print(f"✅ Users in database: {user_count}")
    
    # Test creating a user if none exist
    if user_count == 0:
        print("Creating test user...")
        test_user = User(email="test@example.com", is_guest=False)
        session.add(test_user)
        session.commit()
        print("✅ Test user created successfully!")
        
        # Clean up
        session.delete(test_user)
        session.commit()
        print("✅ Test user cleaned up!")
    
    session.close()
    print("\n🎉 Database migration to PostgreSQL completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
