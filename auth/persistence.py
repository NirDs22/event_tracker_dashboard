"""Enhanced persistence utilities for authentication tokens."""

import streamlit as st
from typing import Optional


def init_persistent_auth():
    """
    Initialize persistent authentication by checking URL parameters.
    This is much more reliable than localStorage components.
    """
    try:
        if 'auth_persistence_checked' not in st.session_state:
            print("DEBUG: Checking URL parameters for existing token...")
            
            # Check if there's an auth parameter in URL
            try:
                if 'auth' in st.query_params:
                    url_token = st.query_params['auth']
                    if url_token and 'auth_token' not in st.session_state:
                        print(f"DEBUG: Found token in URL parameters: {url_token[:20]}...")
                        
                        # Verify the token before using it
                        from auth.cookies import verify_token
                        user_id = verify_token(url_token)
                        
                        if user_id:
                            print(f"DEBUG: URL token is valid for user_id: {user_id}")
                            st.session_state.auth_token = url_token
                            # Don't clear the URL parameter here - let the main auth flow handle it
                        else:
                            print("DEBUG: URL token is invalid")
                            # Clear invalid token from URL
                            del st.query_params['auth']
            except Exception as e:
                print(f"DEBUG: URL parameter check failed: {e}")
            
            st.session_state.auth_persistence_checked = True
            
    except Exception as e:
        print(f"DEBUG: init_persistent_auth failed: {e}")


# Keep these functions for compatibility but make them simple
def set_localstorage_token(token: str) -> None:
    """Placeholder for localStorage token setting."""
    print(f"DEBUG: localStorage not used - relying on cookies and URL params")


def clear_localstorage_token() -> None:
    """Placeholder for localStorage token clearing."""
    print(f"DEBUG: localStorage not used - relying on cookies and URL params")


def get_localstorage_token() -> Optional[str]:
    """Placeholder for localStorage token getting."""
    print(f"DEBUG: localStorage not used - relying on cookies and URL params")
    return None
