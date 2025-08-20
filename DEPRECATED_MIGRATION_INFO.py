#!/usr/bin/env python3
"""
DEPRECATED: Database migration scripts are no longer needed.

The application has been migrated to PostgreSQL on Neon cloud database.
All table creation and migrations are now handled automatically by 
the init_db() function in monitoring/database.py

The PostgreSQL database automatically creates all required tables and 
handles schema migrations through SQLAlchemy's create_all() method.

If you need to reset the database, simply:
1. Drop tables in your Neon console
2. Restart the application - it will recreate all tables automatically
"""

print("This migration script is deprecated.")
print("The app now uses PostgreSQL with automatic schema creation.")
print("No manual migration is needed.")
