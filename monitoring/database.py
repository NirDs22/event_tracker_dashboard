import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DB_PATH = os.getenv('TRACKER_DB', 'tracker.db')
engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


class Topic(Base):
    __tablename__ = 'topics'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)
    keywords = Column(String, default='')  # comma separated
    profiles = Column(String, default='')  # comma separated profiles
    color = Column(String, default="#1f77b4")
    icon = Column(String, default="📌")
    last_collected = Column(DateTime)
    last_viewed = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    posts = relationship('Post', back_populates='topic', cascade='all, delete-orphan')


class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id'))
    source = Column(String, index=True)
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
    """Apply database migrations for new columns."""
    try:
        from sqlalchemy import text
        # Check if new columns exist and add them if they don't
        session = SessionLocal()
        
        # Try to query the new columns - if this fails, they don't exist
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
        
        session.close()
    except Exception as e:
        print(f"❌ Migration error: {e}")
