import streamlit as st
import os

# This module must be imported before any other Streamlit call.
# Configure page settings for optimal cloud deployment
st.set_page_config(
    page_title="Social & News Monitor",
    layout="wide",
    page_icon="📰",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Event Tracker Dashboard - Monitor topics across social media and news sources"
    }
)

# Cloud deployment optimizations
if os.getenv('STREAMLIT_RUNNING', 'false').lower() == 'true':
    # Running on Streamlit Cloud
    st.cache_data.clear()
    st.cache_resource.clear()
