"""Cookie-based authentication utilities."""

import time
from typing import Optional
import streamlit as st
from extra_streamlit_components import CookieManager
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from monitoring.secrets import get_secret


def get_cookie_mgr() -> CookieManager:
    """Get the cookie manager instance with proper initialization."""
    # Use a unique key to avoid conflicts and ensure proper initialization
    try:
        if 'cookie_manager' not in st.session_state:
            # print("DEBUG: Initializing new cookie manager")
            st.session_state.cookie_manager = CookieManager(key='auth_cookie_mgr_v2')
        
        # Give the cookie manager time to initialize on first run
        if not hasattr(st.session_state.cookie_manager, '_cookies_ready'):
            import time
            time.sleep(0.1)  # Small delay for initialization
            st.session_state.cookie_manager._cookies_ready = True
            
        return st.session_state.cookie_manager
    except Exception as e:
        # print(f"DEBUG: Cookie manager initialization error: {e}")
        # Fallback - create new instance
        return CookieManager(key='auth_cookie_mgr_fallback')


def make_token(user_id: int, days: int = 90) -> str:
    """Create a signed token for the user (default 90 days)."""
    auth_secret = get_secret('AUTH_SECRET')
    if not auth_secret:
        raise ValueError("AUTH_SECRET not configured")
    
    serializer = URLSafeTimedSerializer(auth_secret, salt='user-auth')
    payload = {
        "uid": user_id,
        "iat": int(time.time())
    }
    return serializer.dumps(payload)


def verify_token(token: str, max_age_days: int = 120) -> Optional[int]:
    """Verify a token and return the user ID if valid (default 120 days max age)."""
    try:
        auth_secret = get_secret('AUTH_SECRET')
        if not auth_secret:
            print("DEBUG: AUTH_SECRET not configured")
            return None
        
        serializer = URLSafeTimedSerializer(auth_secret, salt='user-auth')
        payload = serializer.loads(token, max_age=max_age_days * 24 * 3600)  # Convert days to seconds
        
        user_id = payload.get("uid")
        # print(f"DEBUG: Token verified successfully, user_id: {user_id}")
        return user_id
    except SignatureExpired:
        # print("DEBUG: Token has expired")
        return None
    except BadSignature:
        # print("DEBUG: Token signature is invalid")
        return None
    except (KeyError, TypeError) as e:
        # print(f"DEBUG: Token payload error: {e}")
        return None


def set_auth_cookie(cookie_mgr: CookieManager, user_id: int, days: int = 90):
    """Set the authentication cookie with improved reliability (default 90 days)."""
    token = make_token(user_id, days)
    try:
        # Try different cookie settings for better compatibility
        cookie_mgr.set(
            'event_tracker_auth', 
            token, 
            expires_at=None,  # Let it be session cookie with long max_age
            max_age=days * 24 * 3600,  # 90 days in seconds
            path='/',
            secure=False,  # Allow on both HTTP and HTTPS
            httpOnly=False,  # Allow JavaScript access if needed
            samesite='Lax'  # Better compatibility
        )
        # print(f"DEBUG: Cookie set with max_age={days * 24 * 3600} seconds")
    except Exception as e:
        # print(f"DEBUG: Cookie setting failed: {e}")
        # Fallback: try simpler setting
        try:
            cookie_mgr.set('event_tracker_auth', token)
            # print(f"DEBUG: Cookie set with fallback method")
        except Exception as e2:
            # print(f"DEBUG: Fallback cookie setting also failed: {e2}")
            pass


def get_auth_cookie(cookie_mgr: CookieManager) -> Optional[int]:
    """Get and verify the authentication cookie, return user ID if valid."""
    try:
        # Try new cookie name first
        token = cookie_mgr.get('event_tracker_auth')
        if not token:
            # Fallback to old cookie name
            token = cookie_mgr.get('auth')
        
        if not token:
            return None
        
        user_id = verify_token(token)
        if user_id is None:
            # Invalid token, delete both possible cookies
            cookie_mgr.delete('event_tracker_auth')
            cookie_mgr.delete('auth')
        
        return user_id
    except Exception as e:
        print(f"DEBUG: Cookie reading failed: {e}")
        return None


def delete_auth_cookie(cookie_mgr: CookieManager):
    """Delete the authentication cookie."""
    try:
        cookie_mgr.delete('event_tracker_auth')
        cookie_mgr.delete('auth')  # Also delete old cookie name
        print("DEBUG: Cookies deleted successfully")
    except Exception as e:
        print(f"DEBUG: Cookie deletion failed: {e}")


# Simplified API for use in service layer
def get_auth_token() -> Optional[str]:
    """Get authentication token from multiple sources with better reliability."""
    try:
        import streamlit as st
        # print("DEBUG: get_auth_token called")
        
        # 1. First check session state (fastest)
        if hasattr(st, 'session_state') and 'auth_token' in st.session_state:
            token = st.session_state.auth_token
            # print(f"DEBUG: Found token in session state")
            if token:
                user_id = verify_token(token)
                if user_id:
                    # print(f"DEBUG: Session token verified successfully, user_id: {user_id}")
                    return f"user_{user_id}"
                else:
                    # print(f"DEBUG: Session token verification failed, clearing")
                    del st.session_state.auth_token
        
        # 2. Check cookies with proper initialization
        try:
            cookie_mgr = get_cookie_mgr()
            # Try both cookie names
            for cookie_name in ['event_tracker_auth', 'auth']:
                raw_token = cookie_mgr.get(cookie_name)
                if raw_token:
                    # print(f"DEBUG: Found token in cookie '{cookie_name}'")
                    user_id = verify_token(raw_token)
                    if user_id:
                        # print(f"DEBUG: Cookie token verified successfully, user_id: {user_id}")
                        # Store in session state for faster future access
                        st.session_state.auth_token = raw_token
                        return f"user_{user_id}"
                    else:
                        # print(f"DEBUG: Cookie token verification failed")
                        pass
        except Exception as cookie_e:
            # print(f"DEBUG: Cookie check failed: {cookie_e}")
            pass

        # 3. Check URL parameters (for shared links or bookmarks)
        try:
            if hasattr(st, 'query_params') and 'auth' in st.query_params:
                url_token = st.query_params['auth']
                # print(f"DEBUG: Found token in URL parameters")
                user_id = verify_token(url_token)
                if user_id:
                    # print(f"DEBUG: URL token verified successfully, user_id: {user_id}")
                    # Store in session state for future use
                    st.session_state.auth_token = url_token
                    # Also store in cookie for persistence
                    try:
                        cookie_mgr = get_cookie_mgr()
                        set_auth_cookie(cookie_mgr, user_id, 90)
                    except:
                        pass  # Don't fail if cookie setting fails
                    return f"user_{user_id}"
                else:
                    print(f"DEBUG: URL token verification failed")
        except Exception as url_e:
            print(f"DEBUG: URL parameter check failed: {url_e}")
        
        print("DEBUG: No valid token found in any location")
        return None
        
    except Exception as e:
        print(f"DEBUG: get_auth_token exception: {e}")
        return None


def set_auth_token(user_id_or_token: str, days: int = 90):
    """Set authentication token with improved persistence."""
    try:
        print(f"DEBUG: set_auth_token called with user_id_or_token='{user_id_or_token}', days={days}")
        
        # Create or use token
        if user_id_or_token.isdigit():
            user_id = int(user_id_or_token)
            token = make_token(user_id, days)
            print(f"DEBUG: Created signed token for user_id {user_id}")
        else:
            token = user_id_or_token
            user_id = verify_token(token)
            print(f"DEBUG: Using provided token for user_id {user_id}")
        
        # 1. Store in session state (primary method - always works)
        st.session_state.auth_token = token
        print(f"DEBUG: Token stored in session state")
        
        # 2. Try to set cookie (secondary method - may fail but that's ok)
        try:
            cookie_mgr = get_cookie_mgr()
            set_auth_cookie(cookie_mgr, user_id, days)
            print(f"DEBUG: Cookie set successfully")
        except Exception as cookie_e:
            print(f"DEBUG: Cookie setting failed (this is ok): {cookie_e}")
        
        # 3. Set URL parameter as backup (for bookmarking)
        try:
            st.query_params.auth = token
            print("DEBUG: Auth parameter added to URL for bookmarking")
        except Exception as url_e:
            print(f"DEBUG: URL parameter setting failed: {url_e}")
            
    except Exception as e:
        print(f"DEBUG: set_auth_token exception: {e}")


def clear_auth_token():
    """Clear authentication token from all locations."""
    try:
        print("DEBUG: clear_auth_token called")
        
        # 1. Clear session state
        keys_to_clear = ['auth_token', 'auth_url_set']
        for key in keys_to_clear:
            if hasattr(st, 'session_state') and key in st.session_state:
                del st.session_state[key]
                print(f"DEBUG: Cleared {key} from session state")
        
        # 2. Clear URL parameters
        try:
            if 'auth' in st.query_params:
                del st.query_params['auth']
            print("DEBUG: Cleared URL parameters")
        except Exception as url_e:
            print(f"DEBUG: URL parameter clearing failed: {url_e}")
        
        # 3. Clear cookies
        try:
            cookie_mgr = get_cookie_mgr()
            delete_auth_cookie(cookie_mgr)
        except Exception as cookie_e:
            print(f"DEBUG: Cookie clearing failed: {cookie_e}")
            
    except Exception as e:
        print(f"DEBUG: clear_auth_token exception: {e}")

