#!/usr/bin/env python3
"""
Database migration script to add remember me functionality to users table.
"""

import sqlite3
from monitoring.secrets import get_secret
import os

def migrate_database():
    """Add remember me columns to users table."""
    # Get database path
    DB_PATH = get_secret('TRACKER_DB')
    if not DB_PATH:
        data_dir = 'data'
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        DB_PATH = os.path.join(data_dir, 'tracker.db')
    
    print(f"Migrating database at: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Existing columns: {columns}")
        
        # Add new columns if they don't exist
        new_columns = [
            ('last_verified_email', 'TEXT'),
            ('last_verification_date', 'DATETIME'),
            ('remember_me_enabled', 'BOOLEAN DEFAULT 0')
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in columns:
                print(f"Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
            else:
                print(f"Column {column_name} already exists")
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify the migration
        cursor.execute("PRAGMA table_info(users)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        print(f"Updated columns: {updated_columns}")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
