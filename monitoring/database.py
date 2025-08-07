import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
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

    topic = relationship('Topic', back_populates='posts')


def init_db():
    """Initialise database tables."""
    Base.metadata.create_all(engine)
