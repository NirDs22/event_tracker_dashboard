import os
from sqlalchemy import create_engine, text

DB_URL = os.environ.get("POSTGRES_URL")
engine = create_engine(DB_URL)

# Backfill image_url for YouTube, Instagram, and photo posts
with engine.connect() as conn:
    # YouTube
    conn.execute(text("""
        UPDATE posts SET image_url =
        'https://img.youtube.com/vi/' || SUBSTRING(url FROM 'v=([a-zA-Z0-9_-]{11})') || '/hqdefault.jpg'
        WHERE source = 'youtube' AND (image_url IS NULL OR image_url = '');
    """))
    # Instagram
    conn.execute(text("""
        UPDATE posts SET image_url =
        'https://www.instagram.com/p/' || SPLIT_PART(url, '/', 5) || '/media/?size=l'
        WHERE source = 'instagram' AND (image_url IS NULL OR image_url = '');
    """))
    # Photos (try to extract from content)
    conn.execute(text("""
        UPDATE posts SET image_url = SUBSTRING(content FROM '(https?://[^\s]+\.(jpg|jpeg|png|webp))')
        WHERE (source = 'photo' OR title ILIKE '%photo%') AND (image_url IS NULL OR image_url = '');
    """))
    conn.commit()
print("Thumbnails backfilled.")
