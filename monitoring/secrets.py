"""
Utility module for accessing secrets/environment variables across 
both local development (.env file) and Streamlit Cloud deployment (st.secrets).
"""
import os
import streamlit as st

def get_secret(key, default=None):
    """
    Get a secret from either Streamlit secrets or environment variable.
    
    Args:
        key: The name of the secret/environment variable
        default: Default value if the secret is not found
    
    Returns:
        The secret value or the default
    """
    # First try Streamlit secrets (for Streamlit Cloud)
    try:
        if hasattr(st, 'secrets'):
            try:
                if key in st.secrets:
                    return st.secrets[key]
            except Exception:
                # Streamlit secrets might throw an exception if not properly configured
                # This is common when running locally without a .streamlit/secrets.toml file
                pass
    except Exception:
        pass
    
    # Fall back to environment variables (for local development)
    return os.getenv(key, default)
