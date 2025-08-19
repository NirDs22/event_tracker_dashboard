#!/usr/bin/env python3
"""Test the  #!/usr/bin/env python3
"""Test the improved digest summary functionality."""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from monitoring.summarizer import summarize_posts_for_digest

def test_improved_summary():
    """Test the improved digest summary with sample data."""
    
    # Sample post data similar to what would come from monitoring
    test_posts = [
        "Topic: Piper Rockelle - New music video released with 2M views in first day, collaboration with famous producer announced",
        "Topic: Amy Bradley - Controversy over recent social media statements, fans divided on new direction", 
        "Topic: Johnny Gosch - Missing person case update: New evidence discovered after 40 years, family hopeful for breakthrough",
        "Topic: Tech News - Major tech company announces AI breakthrough, stock prices surge 15% after announcement",
        "Topic: Weather - Severe storm warning issued for coastal areas, evacuation recommended for low-lying regions"
    ]
    
    print("Testing improved digest summary...")
    print("=" * 50)
    
    # Test the summary function
    summary = summarize_posts_for_digest(test_posts)
    
    print("Generated Summary:")
    print("-" * 30)
    print(summary)
    print("-" * 30)
    
    print(f"Summary length: {len(summary)} characters")
    newline_count = summary.count('
') + 1
    print(f"Number of lines: {newline_count}")
    
    # Test with empty content
    print("")
    print("=" * 50)
    print("Testing with empty content...")
    empty_summary = summarize_posts_for_digest([])
    print(f"Empty summary: {empty_summary}")

if __name__ == "__main__":
    test_improved_summary()print(f"Summary length: {len(summary)} characters")
    newline_count = summary.count('\n') + 1
    print(f"Number of lines: {newline_count}")mproved digest summary functionality."""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from monitoring.summarizer import summarize_posts_for_digest

def test_improved_summary():
    """Test the improved digest summary with sample data."""
    
    # Sample post data similar to what would come from monitoring
    test_posts = [
        "Topic: Piper Rockelle - New music video released with 2M views in first day, collaboration with famous producer announced",
        "Topic: Amy Bradley - Controversy over recent social media statements, fans divided on new direction", 
        "Topic: Johnny Gosch - Missing person case update: New evidence discovered after 40 years, family hopeful for breakthrough",
        "Topic: Tech News - Major tech company announces AI breakthrough, stock prices surge 15% after announcement",
        "Topic: Weather - Severe storm warning issued for coastal areas, evacuation recommended for low-lying regions"
    ]
    
    print("Testing improved digest summary...")
    print("=" * 50)
    
    # Test the summary function
    summary = summarize_posts_for_digest(test_posts)
    
    print("Generated Summary:")
    print("-" * 30)
    print(summary)
    print("-" * 30)
    
    print(f"\nSummary length: {len(summary)} characters")
    print(f"Number of lines: {summary.count('\n') + 1}")
    
    # Test with empty content
    print("\n" + "=" * 50)
    print("Testing with empty content...")
    empty_summary = summarize_posts_for_digest([])
    print(f"Empty summary: {empty_summary}")

if __name__ == "__main__":
    test_improved_summary()
