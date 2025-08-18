#!/usr/bin/env python3
"""
Database migration script to add collection status columns to shared_topics table
"""

import sqlite3
import os

# Database path
db_path = "/Users/nird/Library/CloudStorage/OneDrive-Personal/Code/event_tacker/tracker.db"

def run_migration():
    """Run the database migration"""
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(shared_topics)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"Current columns in shared_topics: {columns}")
        
        # Add missing columns
        migrations = [
            ("collection_status", "ALTER TABLE shared_topics ADD COLUMN collection_status TEXT DEFAULT 'idle'"),
            ("collection_start_time", "ALTER TABLE shared_topics ADD COLUMN collection_start_time DATETIME"),
            ("collection_end_time", "ALTER TABLE shared_topics ADD COLUMN collection_end_time DATETIME"),
            ("collection_errors", "ALTER TABLE shared_topics ADD COLUMN collection_errors TEXT")
        ]
        
        for column_name, sql in migrations:
            if column_name not in columns:
                print(f"Adding column: {column_name}")
                cursor.execute(sql)
            else:
                print(f"Column {column_name} already exists, skipping")
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(shared_topics)")
        new_columns = [column[1] for column in cursor.fetchall()]
        print(f"New columns in shared_topics: {new_columns}")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
