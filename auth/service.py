"""Authentication service for handling login flows."""

import random
import string
from datetime import datetime, timedelta
from typing import Optional, NamedTuple
import bcrypt
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


def ensure_user_authenticated() -> AuthResult:
    """Check if user is authenticated and return appropriate status."""
    # Check for existing auth token (this now checks session state, localStorage, and cookies)
    token = get_auth_token()
    print(f"DEBUG: ensure_user_authenticated - token found: {bool(token)}")
    
    if token:
        print(f"DEBUG: Token value: '{token}'")
        user_id = int(token.split('_')[1]) if '_' in token else None
        print(f"DEBUG: Extracted user_id: {user_id}")
        
        if user_id:
            # Verify user exists in database
            session = SessionLocal()
            try:
                user = session.query(User).filter_by(id=user_id).first()
                print(f"DEBUG: User found in database: {bool(user)}")
                if user:
                    # Update last login time to track activity
                    user.last_login = datetime.utcnow()
                    session.commit()
                    print(f"DEBUG: User authenticated successfully - user_id={user_id}, email={user.email or 'guest'}")
                    return AuthResult(AuthResult.AUTHENTICATED, user_id=user_id)
                else:
                    print(f"DEBUG: User not found in database for user_id={user_id}, clearing invalid token")
                    # Clear invalid token
                    clear_auth_token()
            except Exception as e:
                print(f"DEBUG: Database error during authentication: {e}")
                session.rollback()
            finally:
                session.close()
    
    print("DEBUG: No valid authentication found")
    # No valid authentication found
    return AuthResult(AuthResult.NEED_AUTH)


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


def initiate_login(email: str, is_guest: bool = False, is_upgrade: bool = False) -> LoginResult:
    """Initiate login process - either guest or email-based."""
    if is_guest:
        return _create_guest_login()
    else:
        return _start_email_login(email, is_upgrade)


def _create_guest_login() -> LoginResult:
    """Create a guest user and set auth token."""
    try:
        guest_user_id = create_guest_user()
        set_auth_token(str(guest_user_id))  # Pass user ID as string
        return LoginResult(success=True, user_id=guest_user_id, message="Guest account created")
    except Exception as e:
        return LoginResult(success=False, message=f"Failed to create guest account: {str(e)}")


def _start_email_login(email: str, is_upgrade: bool = False) -> LoginResult:
    """Start email-based login process."""
    try:
        print(f"DEBUG: _start_email_login called with email='{email}'")
        success = start_login(email)
        print(f"DEBUG: start_login returned: {success}")
        if success:
            return LoginResult(success=True, message="Verification code sent")
        else:
            return LoginResult(success=False, message="Failed to send verification code")
    except Exception as e:
        print(f"DEBUG: Email login exception: {str(e)}")
        return LoginResult(success=False, message=f"Login failed: {str(e)}")


def complete_login(email: str, code: str) -> LoginResult:
    """Complete the login process with verification code."""
    try:
        # Get current guest user if exists for potential upgrade
        current_token = get_auth_token()
        current_guest_id = None
        if current_token:
            current_guest_id = int(current_token.split('_')[1]) if '_' in current_token else None
        
        print(f"DEBUG: complete_login called with email='{email}', code='{code}'")
        user_id = _complete_login_internal(email, code, current_guest_id)
        print(f"DEBUG: _complete_login_internal returned user_id={user_id}")
        
        if user_id:
            set_auth_token(str(user_id))  # Just pass the user ID, set_auth_token will handle token creation
            print(f"DEBUG: Auth token set for user {user_id}")
            return LoginResult(success=True, user_id=user_id, message="Successfully logged in")
        else:
            print("DEBUG: Login failed - invalid verification code")
            return LoginResult(success=False, message="Invalid verification code")
    except Exception as e:
        print(f"DEBUG: Login exception: {str(e)}")
        return LoginResult(success=False, message=f"Login failed: {str(e)}")


def start_login(email: str) -> bool:
    """Start the login process by generating and sending a 6-digit code."""
    session = SessionLocal()
    
    try:
        print(f"DEBUG: start_login called with email='{email}'")
        # Generate 6-digit code
        code = f"{random.randint(0, 999999):06d}"
        print(f"DEBUG: Generated code: {code}")
        
        # Hash the code
        code_hash = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create login code record with 10 minute expiry
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        login_code = LoginCode(
            email=email.lower().strip(),
            code_hash=code_hash,
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


def _complete_login_internal(email: str, code: str, current_guest_user_id: Optional[int] = None) -> Optional[int]:
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
        if not bcrypt.checkpw(code.encode('utf-8'), login_code.code_hash.encode('utf-8')):
            print("DEBUG: Code verification failed")
            return None
        
        print("DEBUG: Code verification successful")
        # Code is valid, find or create user
        user = session.query(User).filter_by(email=email).first()
        
        if user:
            # Update existing user
            user.is_guest = False
            user.last_login = datetime.utcnow()
        else:
            # Check if we should upgrade a guest user
            if current_guest_user_id:
                guest_user = session.query(User).filter_by(id=current_guest_user_id, is_guest=True, email=None).first()
                if guest_user:
                    # Upgrade the guest user
                    guest_user.email = email
                    guest_user.is_guest = False
                    guest_user.last_login = datetime.utcnow()
                    user = guest_user
            
            if not user:
                # Create new user
                user = User(
                    email=email,
                    is_guest=False,
                    last_login=datetime.utcnow()
                )
                session.add(user)
        
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
