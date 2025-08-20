import os
import functools
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from monitoring.secrets import get_secret

# Simple in-memory cache for frequently accessed data
_query_cache = {}
_cache_timeout = 300  # 5 minutes


def cached_query(timeout_seconds=300):
    """Decorator for caching database queries."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            now = datetime.now()
            
            # Check if cached result exists and is still valid
            if cache_key in _query_cache:
                result, timestamp = _query_cache[cache_key]
                if (now - timestamp).total_seconds() < timeout_seconds:
                    return result
            
            # Execute query and cache result
            result = func(*args, **kwargs)
            _query_cache[cache_key] = (result, now)
            
            return result
        return wrapper
    return decorator

# Get database URL from secrets - prefer PostgreSQL, fallback to SQLite for local dev
DATABASE_URL = get_secret('postgres_url') or get_secret('DATABASE_URL')

if DATABASE_URL:
    # Using PostgreSQL from Neon - optimized for performance
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,          # Increase pool size for better concurrency
        max_overflow=20,       # Allow overflow connections
        pool_recycle=3600,     # Recycle connections every hour
        pool_timeout=30,       # Wait up to 30 seconds for a connection
        echo=False,            # Disable SQL logging for performance
        connect_args={
            "sslmode": "require",
            "connect_timeout": 10,
            "application_name": "event_tracker"
        }
    )
else:
    # Fallback to SQLite for local development
    print("Using SQLite fallback for local development")
    DB_PATH = get_secret('TRACKER_DB')
    if not DB_PATH:
        # Create data directory if it doesn't exist
        data_dir = 'data'
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        DB_PATH = os.path.join(data_dir, 'tracker.db')
    
    engine = create_engine(
        f'sqlite:///{DB_PATH}',
        connect_args={'check_same_thread': False},
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,       # Don't auto-flush to improve performance
    expire_on_commit=False # Don't expire objects on commit for better caching
)

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=True, index=True)
    is_guest = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Remember me functionality
    last_verified_email = Column(String, nullable=True)  # Last email that was verified with code
    last_verification_date = Column(DateTime, nullable=True)  # When it was last verified
    remember_me_enabled = Column(Boolean, default=False, nullable=False)  # Whether user enabled remember me
    
    # Daily Digest preferences
    digest_enabled = Column(Boolean, default=True, nullable=False)  # Whether to send digest emails
    digest_frequency = Column(String, default='daily', nullable=False)  # daily, every2days, every3days, etc.
    last_digest_sent = Column(DateTime, nullable=True)  # When digest was last sent to this user

    topics = relationship('Topic', back_populates='user', cascade='all, delete-orphan')
    topic_subscriptions = relationship('UserTopicSubscription', back_populates='user', cascade='all, delete-orphan')


class LoginCode(Base):
    __tablename__ = 'login_codes'

    id = Column(Integer, primary_key=True)
    email = Column(String, index=True, nullable=False)
    code_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Topic(Base):
    __tablename__ = 'topics'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), default=0, nullable=False)
    name = Column(String, nullable=False, index=True)
    keywords = Column(String, default='')  # comma separated
    profiles = Column(String, default='')  # comma separated profiles
    color = Column(String, default="#1f77b4")
    icon = Column(String, default="📌")
    last_collected = Column(DateTime)
    last_viewed = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Unique constraint for (user_id, name) combination
    __table_args__ = (UniqueConstraint('user_id', 'name', name='uq_user_topic_name'),)

    user = relationship('User', back_populates='topics')
    posts = relationship('Post', back_populates='topic', cascade='all, delete-orphan')


class SharedTopic(Base):
    """Centralized topic pool shared across all users."""
    __tablename__ = 'shared_topics'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)  # Topic name (normalized)
    keywords = Column(String, default='')  # comma separated keywords
    profiles = Column(String, default='')  # comma separated social profiles  
    last_collected = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    posts_count = Column(Integer, default=0)  # Cache for performance
    
    # Collection status tracking
    collection_status = Column(String, default=None)  # 'collecting', 'completed', 'failed', None
    collection_start_time = Column(DateTime)
    collection_end_time = Column(DateTime)
    collection_errors = Column(Text)
    
    # Relationships
    posts = relationship('SharedPost', back_populates='shared_topic', cascade='all, delete-orphan')
    subscriptions = relationship('UserTopicSubscription', back_populates='shared_topic', cascade='all, delete-orphan')


class UserTopicSubscription(Base):
    """User subscription to shared topics."""
    __tablename__ = 'user_topic_subscriptions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    shared_topic_id = Column(Integer, ForeignKey('shared_topics.id'), nullable=False)
    
    # User customization
    display_name = Column(String, nullable=True)  # Custom display name (defaults to shared topic name)
    color = Column(String, default="#1f77b4")
    icon = Column(String, default="📌")
    last_viewed = Column(DateTime, default=datetime.utcnow)
    subscribed_at = Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint - user can only subscribe once to each shared topic
    __table_args__ = (UniqueConstraint('user_id', 'shared_topic_id', name='uq_user_shared_topic'),)

    # Relationships
    user = relationship('User', back_populates='topic_subscriptions')
    shared_topic = relationship('SharedTopic', back_populates='subscriptions')


class SharedPost(Base):
    """Posts belonging to shared topics."""
    __tablename__ = 'shared_posts'

    id = Column(Integer, primary_key=True)
    shared_topic_id = Column(Integer, ForeignKey('shared_topics.id'), nullable=False, index=True)
    source = Column(String, index=True)
    title = Column(Text, nullable=True)
    content = Column(Text)
    url = Column(String, unique=True, index=True)  # Index for faster duplicate checking
    posted_at = Column(DateTime, index=True)  # Index for date-based queries
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    image_url = Column(String, nullable=True)
    is_photo = Column(Boolean, default=False, index=True)  # Index for filtering photos
    subreddit = Column(String, nullable=True, index=True)  # Index for subreddit filtering
    
    shared_topic = relationship('SharedTopic', back_populates='posts')


class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id'), index=True)
    source = Column(String, index=True)
    # Optional human-readable title (for News/Reddit/etc.)
    title = Column(Text, nullable=True)
    content = Column(Text)
    url = Column(String, unique=True, index=True)  # Index for faster duplicate checking
    posted_at = Column(DateTime, index=True)  # Index for date-based queries
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    image_url = Column(String, nullable=True)  # URL to associated image
    is_photo = Column(Boolean, default=False, index=True)  # Index for filtering photos
    subreddit = Column(String, nullable=True, index=True)  # Index for subreddit filtering

    topic = relationship('Topic', back_populates='posts')


def init_db():
    """Initialise database tables."""
    Base.metadata.create_all(engine)
    
    # Run migrations for existing databases
    migrate_database()


def migrate_database():
    """Apply database migrations for new columns and user authentication."""
    try:
        from sqlalchemy import text
        session = SessionLocal()
        
        # First, create all tables if they don't exist
        Base.metadata.create_all(engine)
        
        # Detect database type
        db_dialect = engine.dialect.name
        is_sqlite = db_dialect == 'sqlite'
        is_postgresql = db_dialect == 'postgresql'
        
        # Check if users table exists and has data
        try:
            result = session.execute(text("SELECT COUNT(*) FROM users")).fetchone()
            users_exist = result[0] > 0 if result else False
        except Exception:
            users_exist = False
            
        if not users_exist:
            print("✅ Database initialized: Created all tables on new database")
        
        # For SQLite, we might need to handle specific column additions
        # For PostgreSQL, the create_all should handle everything
        if is_sqlite:
            # Handle SQLite-specific migrations if needed
            try:
                # Check if user_id column exists in topics table
                session.execute(text("SELECT user_id FROM topics LIMIT 1"))
            except Exception:
                try:
                    session.execute(text("ALTER TABLE topics ADD COLUMN user_id INTEGER DEFAULT 0"))
                    session.commit()
                    print("✅ Database migrated: Added user_id column to topics table")
                except Exception as e:
                    print(f"⚠️ Migration warning for user_id column: {e}")
                    session.rollback()
            
            # Check for image_url and is_photo columns
            try:
                session.execute(text("SELECT image_url, is_photo FROM posts LIMIT 1"))
            except Exception:
                try:
                    session.execute(text("ALTER TABLE posts ADD COLUMN image_url TEXT"))
                    session.execute(text("ALTER TABLE posts ADD COLUMN is_photo BOOLEAN DEFAULT 0"))
                    session.commit()
                    print("✅ Database migrated: Added image_url and is_photo columns to posts table")
                except Exception as e:
                    print(f"⚠️ Migration warning: {e}")
                    session.rollback()
            
            # Check for subreddit column
            try:
                session.execute(text("SELECT subreddit FROM posts LIMIT 1"))
            except Exception:
                try:
                    session.execute(text("ALTER TABLE posts ADD COLUMN subreddit TEXT"))
                    session.commit()
                    print("✅ Database migrated: Added subreddit column to posts table")
                except Exception as e:
                    print(f"⚠️ Migration warning for subreddit column: {e}")
                    session.rollback()
        
        # Create default admin user for existing topics if needed (database-agnostic)
        try:
            result = session.execute(text("SELECT COUNT(*) FROM topics WHERE user_id = 0")).fetchone()
            if result and result[0] > 0:
                # Create default admin user
                if is_sqlite:
                    admin_user_result = session.execute(text(
                        "INSERT INTO users (email, is_guest, created_at) VALUES (NULL, 1, datetime('now')) RETURNING id"
                    )).fetchone()
                elif is_postgresql:
                    admin_user_result = session.execute(text(
                        "INSERT INTO users (email, is_guest, created_at) VALUES (NULL, true, NOW()) RETURNING id"
                    )).fetchone()
                else:
                    # Generic approach
                    session.execute(text(
                        "INSERT INTO users (email, is_guest, created_at) VALUES (NULL, true, NOW())"
                    ))
                    admin_user_result = session.execute(text("SELECT lastval()")).fetchone()
                
                if admin_user_result:
                    admin_id = admin_user_result[0]
                    session.execute(text(f"UPDATE topics SET user_id = {admin_id} WHERE user_id = 0"))
                    session.commit()
                    print(f"✅ Database migrated: Created admin user (id={admin_id}) for existing topics")
        except Exception as e:
            print(f"⚠️ Migration warning for admin user creation: {e}")
            session.rollback()
                
        session.close()
        print(f"✅ Database migration completed successfully on {db_dialect}")
        
    except Exception as e:
        print(f"❌ Migration error: {e}")


def get_db_session():
    """Get a new database session."""
    return SessionLocal()


def get_db_context():
    """Context manager for database sessions - ensures proper cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
