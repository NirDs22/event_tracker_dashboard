import os
from sqlalchemy import create_engine, text

DB_URL = os.environ.get("POSTGRES_URL")
engine = create_engine(DB_URL)

with engine.connect() as conn:
    # Remove guest users
    conn.execute(text("DELETE FROM users WHERE role='guest'"))
    # Remove topics with zero followers
    conn.execute(text("""
        DELETE FROM topics
        WHERE id NOT IN (
            SELECT DISTINCT topic_id FROM topic_followers
        )
    """))
    conn.commit()
print("Cleanup complete.")
