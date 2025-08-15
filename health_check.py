#!/usr/bin/env python3
"""
Streamlit Cloud deployment health check script.
Run this to verify all dependencies and core functionality work.
"""

import sys
import os

def test_imports():
    """Test that all required imports work."""
    print("Testing core imports...")
    
    try:
        import streamlit as st
        print("✓ Streamlit imported successfully")
    except ImportError as e:
        print(f"✗ Streamlit import failed: {e}")
        return False
    
    try:
        import pandas as pd
        print("✓ Pandas imported successfully")
    except ImportError as e:
        print(f"✗ Pandas import failed: {e}")
        return False
    
    try:
        import plotly.express as px
        print("✓ Plotly imported successfully")
    except ImportError as e:
        print(f"✗ Plotly import failed: {e}")
        return False
    
    try:
        import sqlalchemy
        print("✓ SQLAlchemy imported successfully")
    except ImportError as e:
        print(f"✗ SQLAlchemy import failed: {e}")
        return False
    
    try:
        import feedparser
        print("✓ Feedparser imported successfully")
    except ImportError as e:
        print(f"✗ Feedparser import failed: {e}")
        return False
    
    try:
        from bs4 import BeautifulSoup
        print("✓ BeautifulSoup imported successfully")
    except ImportError as e:
        print(f"✗ BeautifulSoup import failed: {e}")
        return False
    
    try:
        import requests
        print("✓ Requests imported successfully")
    except ImportError as e:
        print(f"✗ Requests import failed: {e}")
        return False
    
    return True

def test_database():
    """Test database initialization."""
    print("\nTesting database functionality...")
    
    try:
        from monitoring.database import init_db, SessionLocal
        init_db()
        session = SessionLocal()
        session.close()
        print("✓ Database initialization successful")
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_collectors():
    """Test data collectors."""
    print("\nTesting data collectors...")
    
    try:
        from monitoring.collectors import perform_rss_search
        posts, errors = perform_rss_search("test query")
        print(f"✓ RSS collector test completed (found {len(posts)} posts)")
        return True
    except Exception as e:
        print(f"✗ Collectors test failed: {e}")
        return False

def main():
    """Run all health checks."""
    print("=" * 50)
    print("STREAMLIT CLOUD DEPLOYMENT HEALTH CHECK")
    print("=" * 50)
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
    
    # Test database
    if not test_database():
        all_passed = False
    
    # Test collectors
    if not test_collectors():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Ready for Streamlit Cloud deployment!")
        print("=" * 50)
        return 0
    else:
        print("❌ SOME TESTS FAILED - Fix issues before deployment")
        print("=" * 50)
        return 1

if __name__ == "__main__":
    sys.exit(main())
