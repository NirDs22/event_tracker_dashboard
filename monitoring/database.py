import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from monitoring.secrets import get_secret

# Configure writable database path for Streamlit Cloud
DB_PATH = get_secret('TRACKER_DB')
if not DB_PATH:
    # Create data directory if it doesn't exist
    data_dir = 'data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    DB_PATH = os.path.join(data_dir, 'tracker.db')

engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=True, index=True)
    is_guest = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

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
    shared_topic_id = Column(Integer, ForeignKey('shared_topics.id'), nullable=False)
    source = Column(String, index=True)
    title = Column(Text, nullable=True)
    content = Column(Text)
    url = Column(String, unique=True)
    posted_at = Column(DateTime)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    image_url = Column(String, nullable=True)
    is_photo = Column(Boolean, default=False)
    subreddit = Column(String, nullable=True)
    
    shared_topic = relationship('SharedTopic', back_populates='posts')


class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id'))
    source = Column(String, index=True)
    # Optional human-readable title (for News/Reddit/etc.)
    title = Column(Text, nullable=True)
    content = Column(Text)
    url = Column(String, unique=True)
    posted_at = Column(DateTime)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    image_url = Column(String, nullable=True)  # URL to associated image
    is_photo = Column(Boolean, default=False)  # Whether this is primarily a photo post
    subreddit = Column(String, nullable=True)  # Subreddit name for Reddit posts

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
        
        # Check if users table exists, create if not
        try:
            session.execute(text("SELECT id FROM users LIMIT 1"))
        except Exception:
            # Users table doesn't exist, create it
            try:
                Base.metadata.create_all(engine)
                print("✅ Database migrated: Created users and login_codes tables")
            except Exception as e:
                print(f"⚠️ Migration warning for auth tables: {e}")
                session.rollback()
        
        # Create shared topics tables
        try:
            session.execute(text("SELECT id FROM shared_topics LIMIT 1"))
        except Exception:
            try:
                Base.metadata.create_all(engine)
                print("✅ Database migrated: Created shared topics system tables")
            except Exception as e:
                print(f"⚠️ Migration warning for shared topics: {e}")
                session.rollback()
        
        # Check if user_id column exists in topics table
        try:
            session.execute(text("SELECT user_id FROM topics LIMIT 1"))
        except Exception:
            # user_id column doesn't exist, add it
            try:
                session.execute(text("ALTER TABLE topics ADD COLUMN user_id INTEGER DEFAULT 0"))
                session.commit()
                print("✅ Database migrated: Added user_id column to topics table")
            except Exception as e:
                print(f"⚠️ Migration warning for user_id column: {e}")
                session.rollback()
        
        # Check if new columns exist in posts and add them if they don't
        try:
            session.execute(text("SELECT image_url, is_photo FROM posts LIMIT 1"))
        except Exception:
            # Columns don't exist, add them
            try:
                session.execute(text("ALTER TABLE posts ADD COLUMN image_url TEXT"))
                session.execute(text("ALTER TABLE posts ADD COLUMN is_photo BOOLEAN DEFAULT 0"))
                session.commit()
                print("✅ Database migrated: Added image_url and is_photo columns to posts table")
            except Exception as e:
                print(f"⚠️ Migration warning: {e}")
                session.rollback()

        # Ensure 'title' column exists for posts
        try:
            session.execute(text("SELECT title FROM posts LIMIT 1"))
        except Exception:
            try:
                session.execute(text("ALTER TABLE posts ADD COLUMN title TEXT"))
                session.commit()
                print("✅ Database migrated: Added title column to posts table")
            except Exception as e:
                print(f"⚠️ Migration warning for title column: {e}")
                session.rollback()
        
        # Check for subreddit column
        try:
            session.execute(text("SELECT subreddit FROM posts LIMIT 1"))
        except Exception:
            # Subreddit column doesn't exist, add it
            try:
                session.execute(text("ALTER TABLE posts ADD COLUMN subreddit TEXT"))
                session.commit()
                print("✅ Database migrated: Added subreddit column to posts table")
            except Exception as e:
                print(f"⚠️ Migration warning for subreddit column: {e}")
                session.rollback()
        
        # Create default admin user for existing topics if needed
        try:
            # Check if there are topics without a valid user_id
            result = session.execute(text("SELECT COUNT(*) FROM topics WHERE user_id = 0")).fetchone()
            if result and result[0] > 0:
                # Create default admin user
                admin_user_id = session.execute(text(
                    "INSERT INTO users (email, is_guest, created_at) VALUES (NULL, 1, datetime('now')) RETURNING id"
                )).fetchone()
                if admin_user_id:
                    admin_id = admin_user_id[0]
                    session.execute(text(f"UPDATE topics SET user_id = {admin_id} WHERE user_id = 0"))
                    session.commit()
                    print(f"✅ Database migrated: Created admin user (id={admin_id}) for existing topics")
        except Exception as e:
            print(f"⚠️ Migration warning for admin user creation: {e}")
            session.rollback()
        
        session.close()
    except Exception as e:
        print(f"❌ Migration error: {e}")


def get_db_session():
    """Get a new database session."""
    return SessionLocal()
