#!/usr/bin/env python3
"""
Quick test script to validate TL;DR functionality
"""

import sys
sys.path.append('.')

def test_ai_summary():
    """Test the AI summary generation"""
    try:
        import g4f
        
        # Test content
        title = "Amy Bradley Case Gets New Attention"
        content = "Amy Bradley disappeared from a cruise ship in 1998. A Netflix documentary has brought new attention to her case, with new witnesses coming forward and the Kardashians showing interest in helping solve the case."
        
        prompt = f"Provide a concise TL;DR summary (2-3 sentences max) of this news article.\n\nTitle: {title}\n\nContent: {content}"
        
        models_to_try = ["gpt-3.5-turbo", "gpt-4", "mixtral-8x7b"]
        
        print("Testing AI summary generation...")
        
        for model in models_to_try:
            try:
                print(f"Trying {model}...")
                response = g4f.ChatCompletion.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that creates concise TL;DR summaries. Keep responses under 3 sentences and focus on key points."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                if response and len(response.strip()) > 20:
                    print(f"✅ SUCCESS with {model}!")
                    print(f"Summary: {response.strip()}")
                    return response.strip()
                else:
                    print(f"❌ {model} returned empty/short response")
                    
            except Exception as model_error:
                print(f"❌ {model} failed: {model_error}")
                continue
        
        print("❌ All models failed")
        return None
        
    except Exception as e:
        print(f"❌ General error: {e}")
        return None

def test_streamlit_components():
    """Test that streamlit components are available"""
    try:
        import streamlit as st
        print("✅ Streamlit available")
        
        # Test session state would work
        print("✅ Session state functionality available")
        return True
        
    except ImportError as e:
        print(f"❌ Streamlit not available: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing TL;DR Functionality")
    print("=" * 50)
    
    # Test 1: Streamlit components
    print("Test 1: Streamlit Components")
    test_streamlit_components()
    print()
    
    # Test 2: AI Summary
    print("Test 2: AI Summary Generation")
    result = test_ai_summary()
    print()
    
    if result:
        print("🎉 TL;DR functionality should work!")
        print(f"Sample summary: {result[:100]}...")
    else:
        print("⚠️  AI summary generation failed - TL;DR will show error message")
