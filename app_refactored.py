import app_config  # must be first

import os
import re
from pathlib import Path
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

# --- diagnostics (toggleable) ---
import os, sys, json
import pandas as pd
import plotly
import numpy as np

if "show_diagnostics" not in st.session_state:
    st.session_state["show_diagnostics"] = False

if st.sidebar.checkbox("Show diagnostics", value=st.session_state["show_diagnostics"], key="diag_cb"):
    st.session_state["show_diagnostics"] = True
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Runtime Info:**")
    
    st.sidebar.info(f"Python: {sys.version}")
    st.sidebar.info(f"Streamlit: {st.__version__}")
    st.sidebar.info(f"pandas: {pd.__version__}")
    st.sidebar.info(f"plotly: {plotly.__version__}")
    st.sidebar.info(f"numpy: {np.__version__}")
    
    # environment variables
    if st.sidebar.checkbox("Show ENV"):
        env_vars = dict(os.environ)
        st.sidebar.json(env_vars)

    # Show more detailed environment information if requested
    if IS_CLOUD:
        with st.sidebar.expander("Environment & Package Info", expanded=True):
            st.write("**Running in Streamlit Cloud**")
            
            # Show key environment variables relevant to deployment
            cloud_env_vars = {}
            for key in ['STREAMLIT_SHARING_MODE', 'STREAMLIT_SERVER_HEADLESS', 'PATH', 'PWD']:
                if key in os.environ:
                    cloud_env_vars[key] = os.environ[key]
            
            st.json(cloud_env_vars)
            
            # Show current working directory and files
            st.write("**Current Directory:**", os.getcwd())
            
            try:
                files = list(Path(".").iterdir())
                st.write("**Files in current directory:**")
                for f in files[:10]:  # Limit to first 10 files
                    st.write(f"- {f.name}")
                if len(files) > 10:
                    st.write(f"... and {len(files) - 10} more files")
            except Exception as e:
                st.write(f"Error listing files: {e}")
else:
    st.session_state["show_diagnostics"] = False

from monitoring.database import SessionLocal, Topic, Post, init_db
from monitoring.scheduler import start_scheduler
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
    
    # Render main header
    render_main_header()
    
    # Check scheduler status
    if scheduler is None:
        st.sidebar.info(
            "Background scheduler did not start. Scheduled collection won't run; check logs or collect manually."
        )
    
    # Initialize session state
    if "selected_topic" not in st.session_state:
        st.session_state.selected_topic = None
    
    # Initialize database session
    session = SessionLocal()
    
    # Enhanced sidebar styling
    st.sidebar.markdown("### 🎛️ **Topic Management**")
    st.sidebar.markdown("---")
    
    # Render sidebar sections
    render_newsletter_frequency_settings()
    render_digest_email_section()
    render_add_topic_section()
    render_test_email_section()
    render_manage_topics_section()
    render_collect_all_section()
    
    # Load topics for main view
    topics = session.query(Topic).all()
    
    # Main navigation logic
    if st.session_state.selected_topic is None:
        # Render overview page
        render_overview_page(topics, session, Post)
    else:
        # Render topic detail page
        render_topic_detail_page(session, st.session_state.selected_topic)
    
    session.close()

# Run the main application
if __name__ == "__main__":
    main()
else:
    # This allows the app to be imported and run by Streamlit
    main()
