import app_config  # must be first

import os
from datetime import datetime, timedelta

# Determine if we're running in Streamlit Cloud for compatibility adjustments
IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit_sharing" or os.environ.get("STREAMLIT_SERVER_HEADLESS") == "true"

# Import streamlit after app_config has already configured the page
import streamlit as st

# Add any additional menu items
st._config.set_option("theme.base", "light")
st._config.set_option("client.toolbarMode", "minimal")
st._config.set_option("server.headless", True)
st._config.set_option("theme.primaryColor", "#4A90E2")

# Update menu items
if hasattr(st, 'update_page_config'):
    st.update_page_config(
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': "Social & News Monitor App"
        }
    )



from monitoring.database import SessionLocal, Topic, Post, User, init_db
from monitoring.scheduler import start_scheduler
from auth.service import ensure_user_authenticated, get_current_user, AuthResult
from auth.views import render_auth_panel, render_user_status_widget
from ui.layout import apply_custom_css, render_main_header
from ui.sidebar import (
    render_newsletter_frequency_settings,
    render_digest_email_section,
    render_add_topic_section,
    render_test_email_section,
    render_manage_topics_section,
    render_collect_all_section
)
from ui.views import render_overview_page, render_topic_detail_page
from ui.shared_views import render_shared_overview_page, render_shared_topic_detail_page

def main():
    """Main application function."""
    # Initialize database and scheduler
    init_db()
    try:
        scheduler = start_scheduler()
    except Exception:
        scheduler = None
    
    # Apply custom CSS
    apply_custom_css()
    
    # Initialize database session
    session = SessionLocal()
    
    # Check if we need to migrate to shared topics
    try:
        from monitoring.shared_topics import migrate_existing_topics_to_shared
        from monitoring.database import SharedTopic
        from sqlalchemy import text
        
        # Check if shared topics system is empty and we have legacy topics
        shared_count = session.query(SharedTopic).count()
        legacy_count = session.query(Topic).count()
        
        if shared_count == 0 and legacy_count > 0:
            st.info("🔄 Migrating to improved shared topic system... This will only happen once.")
            with st.spinner("Migrating data..."):
                migrate_existing_topics_to_shared()
            st.success("✅ Migration completed! You now have access to the shared topic system.")
            st.rerun()
            
    except Exception as e:
        # Migration is not critical, continue with app
        print(f"Migration check failed: {e}")
    
    # Handle authentication
    auth_result = ensure_user_authenticated()
    
    if auth_result.status == AuthResult.NEED_AUTH:
        # Show authentication panel
        render_auth_panel()
        session.close()
        return
    elif auth_result.status == AuthResult.PENDING_VERIFICATION:
        # Show verification pending message
        render_auth_panel()  # This will show the verification form
        session.close()
        return
    
    # User is authenticated, get current user
    current_user = get_current_user(session)
    if not current_user:
        st.error("Failed to load user session. Please refresh the page.")
        session.close()
        return
    
    # Render main header
    render_main_header()
    
    # Check scheduler status
    if scheduler is None:
        st.sidebar.info(
            "Background scheduler did not start. Scheduled collection won't run; check logs or collect manually."
        )
    
    # Initialize session state for shared topics
    if "selected_topic" not in st.session_state:
        st.session_state.selected_topic = None
    if "selected_shared_topic" not in st.session_state:
        st.session_state.selected_shared_topic = None
    if "use_shared_topics" not in st.session_state:
        st.session_state.use_shared_topics = True  # Default to new system
    
    # Enhanced sidebar styling
    st.sidebar.markdown("### 🎛️ Topic Management")
    st.sidebar.markdown("---")
    
    # System toggle (temporary for migration)
    with st.sidebar.expander("⚙️ System Settings", expanded=False):
        use_shared = st.checkbox("Use Shared Topic System", value=st.session_state.use_shared_topics, 
                                help="New efficient system where topics are shared across users")
        if use_shared != st.session_state.use_shared_topics:
            st.session_state.use_shared_topics = use_shared
            st.session_state.selected_topic = None
            st.session_state.selected_shared_topic = None
            st.rerun()
    
    # Show user status widget
    render_user_status_widget(current_user)
    
    # Render sidebar sections with current user
    render_newsletter_frequency_settings()
    render_digest_email_section()
    render_add_topic_section(current_user.id)
    render_test_email_section()
    render_manage_topics_section(current_user.id)
    render_collect_all_section(current_user.id)
    
    # Load user's topics for main view
    user_topics = session.query(Topic).filter_by(user_id=current_user.id).all()
    
    # Main navigation logic - use shared topic system by default
    if st.session_state.use_shared_topics:
        if st.session_state.selected_shared_topic is None:
            # Render shared overview page
            render_shared_overview_page(current_user.id)
        else:
            # Render shared topic detail page
            render_shared_topic_detail_page(st.session_state.selected_shared_topic, session)
    else:
        # Legacy system (for backward compatibility)
        if st.session_state.selected_topic is None:
            # Render overview page
            render_overview_page(user_topics, session, Post, current_user.id)
        else:
            # Get the selected topic object (ensure it belongs to current user)
            topic = session.query(Topic).filter_by(
                id=st.session_state.selected_topic,
                user_id=current_user.id
            ).first()
            if not topic:
                st.error("Topic not found!")
                st.session_state.selected_topic = None
                st.rerun()
            else:
                # Render topic detail page
                render_topic_detail_page(topic, session, Post)
    
    session.close()

# Run the main application
if __name__ == "__main__":
    main()
else:
    # This allows the app to be imported and run by Streamlit
    main()
