"""Authentication UI components."""

import streamlit as st
from textwrap import dedent
from streamlit.components.v1 import html as st_html
from .service import initiate_login, complete_login, get_current_user, logout
from .cookies import clear_auth_token


def render_auth_panel():
    """Render the authentication panel."""
    # Show welcome screen to encourage signup
    from ui.layout import render_welcome_screen
    render_welcome_screen()
    
    st.markdown("### 🔐 Sign In")
    
    # Check if we're in verification mode
    if 'pending_email' in st.session_state:
        render_verification_form()
        return
    
    # Email input form
    with st.form("email_form"):
        email = st.text_input(
            "Email address", 
            placeholder="your@email.com",
            help="We'll send you a secure sign-in code"
        )
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit_email = st.form_submit_button("Send Code", type="primary")
        with col2:
            guest_mode = st.form_submit_button("Continue as Guest")
    
    if submit_email and email:
        result = initiate_login(email, is_guest=False)
        if result.success:
            st.session_state.pending_email = email
            st.success("Check your email for the sign-in code!")
            st.rerun()
        else:
            st.error(result.message)
    
    if guest_mode:
        result = initiate_login("", is_guest=True)
        if result.success:
            st.success("Welcome! Signed in as guest.")
            st.rerun()
        else:
            st.error(result.message)


def render_verification_form():
    """Render the verification code input form."""
    email = st.session_state.get('pending_email', '')
    
    st.info(f"Enter the 6-digit code sent to {email}")
    
    with st.form("verification_form"):
        code = st.text_input("Verification Code", max_chars=6, placeholder="123456")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            verify_code = st.form_submit_button("Verify", type="primary")
        with col2:
            back_button = st.form_submit_button("← Back")
    
    if verify_code and code:
        result = complete_login(email, code)
        if result.success:
            del st.session_state.pending_email
            st.success("Successfully signed in!")
            st.rerun()
        else:
            st.error(result.message)
    
    if back_button:
        del st.session_state.pending_email
        st.rerun()


def render_user_status_widget(user):
    """Render a small user status widget in the sidebar."""
    if user.is_guest:
        user_type = "👤 Guest User"
        user_email = "Anonymous Session"
    else:
        user_type = "✅ Verified User"
        user_email = user.email
    
    # Create a compact user info widget
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👋 User Status")
    
    st.sidebar.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    ">
        <div style="font-weight: 600; margin-bottom: 0.5rem;">{user_type}</div>
        <div style="font-size: 0.8rem; opacity: 0.9;">{user_email}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sign out button
    if st.sidebar.button("🚪 Sign Out", type="secondary", use_container_width=True):
        logout()
        st.success("Signed out successfully!")
        st.rerun()
    
    # Upgrade guest account
    if user.is_guest:
        st.sidebar.markdown("---")
        if st.sidebar.button("⬆️ Upgrade to Verified Account", use_container_width=True):
            st.session_state.show_upgrade = True
            st.rerun()


def render_upgrade_flow():
    """Render the guest-to-verified upgrade flow."""
    st.markdown("### ⬆️ Upgrade Your Account")
    st.info("Convert your guest session to a verified account to keep your topics and receive email notifications.")
    
    with st.form("upgrade_form"):
        email = st.text_input(
            "Your email address",
            placeholder="your@email.com",
            help="Your current topics will be linked to this email"
        )
        
        col1, col2 = st.columns([1, 1])
        with col1:
            upgrade_button = st.form_submit_button("Send Verification Code", type="primary")
        with col2:
            cancel_button = st.form_submit_button("Cancel")
    
    if upgrade_button and email:
        # Initiate upgrade process
        result = initiate_login(email, is_guest=False, is_upgrade=True)
        if result.success:
            st.session_state.pending_email = email
            st.session_state.is_upgrade = True
            st.success("Check your email for the upgrade code!")
            st.rerun()
        else:
            st.error(result.message)
    
    if cancel_button:
        if 'show_upgrade' in st.session_state:
            del st.session_state.show_upgrade
        st.rerun()

