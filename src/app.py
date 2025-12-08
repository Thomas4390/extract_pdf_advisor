# -*- coding: utf-8 -*-
"""
Streamlit Application - Insurance Commission Data Pipeline
===========================================================

Application web avec systeme d'authentification pour gerer les acces
aux boards Monday.com et les donnees de commissions d'assurance.

Author: Thomas
Date: 2025-12-05
Version: 6.0.0 - Modular Architecture
"""

import sys
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from config import APP_NAME, APP_ICON, ROLE_ADMIN
from ui.styles import apply_global_styles
from ui.pages import render_login_page, render_admin_dashboard, render_employee_dashboard
from utils.session import init_session_state


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main application entry point."""
    # Initialize session state
    init_session_state()

    # Apply global styles
    apply_global_styles()

    # Route to appropriate page
    if not st.session_state.authenticated:
        render_login_page()
    else:
        user = st.session_state.current_user
        if user.role == ROLE_ADMIN:
            render_admin_dashboard()
        else:
            render_employee_dashboard()


if __name__ == "__main__":
    main()
