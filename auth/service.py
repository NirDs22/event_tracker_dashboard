"""Authentication service for handling login flows."""

import random
import string
from datetime import datetime, timedelta
from typing import Optional, NamedTuple
import hashlib
import hmac
import secrets
# import bcrypt  # Removed for cloud compatibility  # Removed for cloud compatibility
from monitoring.database import SessionLocal, User, LoginCode
from monitoring.notifier import send_otp_email
from .cookies import get_auth_token, set_auth_token, clear_auth_token


class AuthResult(NamedTuple):
    """Result of authentication check."""
    AUTHENTICATED = "authenticated"
    NEED_AUTH = "need_auth"
    PENDING_VERIFICATION = "pending_verification"
    
    status: str
    user_id: Optional[int] = None
    message: str = ""


class LoginResult(NamedTuple):
    """Result of login operation."""
    success: bool
    message: str = ""
    user_id: Optional[int] = None


def ensure_user_authenticated():
    """Ensure user is authenticated. Returns AuthResult."""
    import streamlit as st
    from monitoring.database import get_db_session, User
    
    # Get auth token from various sources (session state, cookies, URL params)
    auth_token = get_auth_token()
    
    if not auth_token:
        return AuthResult(status=AuthResult.NEED_AUTH)
    
    # Parse user ID from token format "user_X"
    if not auth_token.startswith("user_"):
        return AuthResult(status=AuthResult.NEED_AUTH)
    
    try:
        user_id = int(auth_token.split("_")[1])
    except (IndexError, ValueError):
        return AuthResult(status=AuthResult.NEED_AUTH)
    
    # Verify user exists in database
    try:
        session = get_db_session()
        user = session.query(User).filter(User.id == user_id).first()
        user_exists = user is not None
        session.close()
        
        if not user_exists:
            # Clear invalid session state
            if 'auth_token' in st.session_state:
                del st.session_state.auth_token
            return AuthResult(status=AuthResult.NEED_AUTH)
            
    except Exception as e:
        return AuthResult(status=AuthResult.NEED_AUTH)
    
    return AuthResult(status=AuthResult.AUTHENTICATED, user_id=user_id)


def logout() -> None:
    """Log out the current user by clearing all authentication tokens."""
    print("DEBUG: logout() called")
    clear_auth_token()
    print("DEBUG: Authentication tokens cleared")


def get_current_user(session=None) -> Optional[User]:
    """Get the currently authenticated user."""
    token = get_auth_token()
    if not token:
        return None
    
    user_id = int(token.split('_')[1]) if '_' in token else None
    if not user_id:
        return None
    
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True
    
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if user and close_session:
            # Detach from session to avoid lazy loading issues
            session.expunge(user)
        return user
    finally:
        if close_session:
            session.close()


def can_skip_verification(email: str) -> bool:
    """Check if a user can skip verification due to remember me feature."""
    session = SessionLocal()
    
    try:
        email = email.lower().strip()
        user = session.query(User).filter_by(email=email).first()
        
        if not user or not user.remember_me_enabled:
            return False
        
        # Check if the email was verified recently (within 30 days)
        if not user.last_verification_date:
            return False
        
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        return (user.last_verified_email == email and 
                user.last_verification_date > thirty_days_ago)
        
    except Exception as e:
        print(f"Error checking remember me status: {e}")
        return False
    finally:
        session.close()


def initiate_login(email: str, is_guest: bool = False, is_upgrade: bool = False, remember_me: bool = False) -> LoginResult:
    """Initiate login process - either guest or email-based."""
    if is_guest:
        return _create_guest_login()
    else:
        return _start_email_login(email, is_upgrade, remember_me)


def _create_guest_login() -> LoginResult:
    """Create a guest user and set auth token."""
    try:
        guest_user_id = create_guest_user()
        set_auth_token(str(guest_user_id))  # Pass user ID as string
        return LoginResult(success=True, user_id=guest_user_id, message="Guest account created")
    except Exception as e:
        return LoginResult(success=False, message=f"Failed to create guest account: {str(e)}")


def _start_email_login(email: str, is_upgrade: bool = False, remember_me: bool = False) -> LoginResult:
    """Start email-based login process."""
    try:
        print(f"DEBUG: _start_email_login called with email='{email}', remember_me={remember_me}")
        success = start_login(email, remember_me=remember_me)
        print(f"DEBUG: start_login returned: {success}")
        if success:
            return LoginResult(success=True, message="Verification code sent")
        else:
            return LoginResult(success=False, message="Failed to send verification code")
    except Exception as e:
        print(f"DEBUG: Email login exception: {str(e)}")
        return LoginResult(success=False, message=f"Login failed: {str(e)}")


def complete_login(email: str, code: str, remember_me: bool = False, skip_verification: bool = False) -> LoginResult:
    """Complete the login process with verification code."""
    try:
        # Get current guest user if exists for potential upgrade
        current_token = get_auth_token()
        current_guest_id = None
        if current_token:
            current_guest_id = int(current_token.split('_')[1]) if '_' in current_token else None
        
        print(f"DEBUG: complete_login called with email='{email}', code='{code}', remember_me={remember_me}, skip_verification={skip_verification}")
        
        if skip_verification:
            # Skip verification for remember me users
            user_id = _handle_remember_me_login(email, current_guest_id)
        else:
            # Normal verification flow
            user_id = _complete_login_internal(email, code, current_guest_id, remember_me)
        
        print(f"DEBUG: Login process returned user_id={user_id}")
        
        if user_id:
            set_auth_token(str(user_id))  # Just pass the user ID, set_auth_token will handle token creation
            print(f"DEBUG: Auth token set for user {user_id}")
            return LoginResult(success=True, user_id=user_id, message="Successfully logged in")
        else:
            print("DEBUG: Login failed - invalid verification code or remember me check failed")
            return LoginResult(success=False, message="Invalid verification code" if not skip_verification else "Login failed")
    except Exception as e:
        print(f"DEBUG: Login exception: {str(e)}")
        return LoginResult(success=False, message=f"Login failed: {str(e)}")


def _handle_remember_me_login(email: str, current_guest_user_id: Optional[int] = None) -> Optional[int]:
    """Handle login for remember me users without verification code."""
    session = SessionLocal()
    
    try:
        email = email.lower().strip()
        print(f"DEBUG: _handle_remember_me_login called with email='{email}'")
        
        user = session.query(User).filter_by(email=email).first()
        
        if not user:
            print("DEBUG: No user found for remember me login")
            return None
        
        if not user.remember_me_enabled:
            print("DEBUG: Remember me not enabled for this user")
            return None
        
        # Verify remember me is still valid (within 30 days)
        if not user.last_verification_date:
            print("DEBUG: No last verification date found")
            return None
        
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        if user.last_verification_date <= thirty_days_ago:
            print("DEBUG: Remember me period has expired")
            return None
        
        if user.last_verified_email != email:
            print("DEBUG: Email doesn't match last verified email")
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        session.commit()
        
        print(f"DEBUG: Remember me login successful for user {user.id}")
        return user.id
        
    except Exception as e:
        session.rollback()
        print(f"Error in _handle_remember_me_login: {e}")
        return None
    finally:
        session.close()


def start_login(email: str, remember_me: bool = False) -> bool:
    """Start the login process by generating and sending a 6-digit code."""
    session = SessionLocal()
    
    try:
        print(f"DEBUG: start_login called with email='{email}'")
        # Generate 6-digit code
        code = f"{random.randint(0, 999999):06d}"
        print(f"DEBUG: Generated code: {code}")
        
        # Hash the code
        salt = secrets.token_hex(16)
        code_hash = hashlib.pbkdf2_hmac('sha256', code.encode('utf-8'), salt.encode('utf-8'), 100000)
        code_hash_str = salt + ':' + code_hash.hex()
        
        # Create login code record with 10 minute expiry
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        login_code = LoginCode(
            email=email.lower().strip(),
            code_hash=code_hash_str,
            expires_at=expires_at,
            attempts=0
        )
        
        session.add(login_code)
        session.commit()
        print(f"DEBUG: Login code saved to database")
        
        # Send OTP email
        print(f"DEBUG: Calling send_otp_email with email='{email}', code='{code}'")
        success = send_otp_email(email, code)
        print(f"DEBUG: send_otp_email returned: {success}")
        
        if not success:
            # Clean up if email sending failed
            session.delete(login_code)
            session.commit()
            print(f"DEBUG: Cleaned up login code due to email failure")
            
        return success
        
    except Exception as e:
        session.rollback()
        print(f"Error in start_login: {e}")
        return False
    finally:
        session.close()


def _complete_login_internal(email: str, code: str, current_guest_user_id: Optional[int] = None, remember_me: bool = False) -> Optional[int]:
    """Complete the login process by verifying the code and returning user ID."""
    session = SessionLocal()
    
    try:
        email = email.lower().strip()
        print(f"DEBUG: _complete_login_internal called with email='{email}', code='{code}'")
        
        # Get the most recent login code for this email
        login_code = (session.query(LoginCode)
                     .filter_by(email=email)
                     .order_by(LoginCode.created_at.desc())
                     .first())
        
        if not login_code:
            print("DEBUG: No login code found for this email")
            return None
        
        print(f"DEBUG: Found login code, expires at {login_code.expires_at}, attempts: {login_code.attempts}")
        
        # Check if code has expired
        if datetime.utcnow() > login_code.expires_at:
            print("DEBUG: Login code has expired")
            return None
        
        # Check if too many attempts
        if login_code.attempts >= 5:
            print("DEBUG: Too many attempts")
            return None
        
        # Increment attempts regardless of success
        login_code.attempts += 1
        session.commit()
        
        # Verify the code
        print(f"DEBUG: Verifying code '{code}' against hash")
        try:
            salt, stored_hash = login_code.code_hash.split(':')
            code_hash = hashlib.pbkdf2_hmac('sha256', code.encode('utf-8'), salt.encode('utf-8'), 100000)
            if not hmac.compare_digest(code_hash.hex(), stored_hash):
                print("DEBUG: Code verification failed")
                return None
        except ValueError:
            print("DEBUG: Invalid hash format")
            return None
        
        print("DEBUG: Code verification successful")
        # Code is valid, find or create user
        user = session.query(User).filter_by(email=email).first()
        
        if user:
            # Update existing user
            user.is_guest = False
            user.last_login = datetime.utcnow()
            
            # Handle remember me functionality
            if remember_me:
                user.remember_me_enabled = True
                user.last_verified_email = email
                user.last_verification_date = datetime.utcnow()
                print(f"DEBUG: Remember me enabled for user {user.id}")
        else:
            # Check if we should upgrade a guest user
            if current_guest_user_id:
                guest_user = session.query(User).filter_by(id=current_guest_user_id, is_guest=True, email=None).first()
                if guest_user:
                    # Upgrade the guest user
                    guest_user.email = email
                    guest_user.is_guest = False
                    guest_user.last_login = datetime.utcnow()
                    
                    # Handle remember me functionality
                    if remember_me:
                        guest_user.remember_me_enabled = True
                        guest_user.last_verified_email = email
                        guest_user.last_verification_date = datetime.utcnow()
                        print(f"DEBUG: Remember me enabled for upgraded guest user {guest_user.id}")
                    
                    user = guest_user
            
            if not user:
                # Create new user
                user = User(
                    email=email,
                    is_guest=False,
                    last_login=datetime.utcnow(),
                    remember_me_enabled=remember_me,
                    last_verified_email=email if remember_me else None,
                    last_verification_date=datetime.utcnow() if remember_me else None
                )
                session.add(user)
                if remember_me:
                    print(f"DEBUG: Remember me enabled for new user")
        
        session.commit()
        
        # Clean up the used login code
        session.delete(login_code)
        session.commit()
        
        return user.id
        
    except Exception as e:
        session.rollback()
        print(f"Error in complete_login: {e}")
        return None
    finally:
        session.close()


def create_guest_user() -> int:
    """Create a new guest user and return their ID."""
    session = SessionLocal()
    
    try:
        guest_user = User(is_guest=True)
        session.add(guest_user)
        session.commit()
        return guest_user.id
    except Exception as e:
        session.rollback()
        print(f"Error creating guest user: {e}")
        raise
    finally:
        session.close()


def get_user_by_id(user_id: int) -> Optional[User]:
    """Get user by ID."""
    session = SessionLocal()
    
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            # Detach from session to avoid lazy loading issues
            session.expunge(user)
        return user
    finally:
        session.close()
