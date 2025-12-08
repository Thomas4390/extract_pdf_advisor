# -*- coding: utf-8 -*-
"""
Session state management utilities.
"""

import os
from typing import Optional

import streamlit as st

from models.user import User
from services.auth_manager import AuthManager


def init_session_state() -> None:
    """Initialize all session state variables with defaults."""
    defaults = {
        'authenticated': False,
        'current_user': None,
        'auth_manager': None,
        'monday_api_key': os.getenv("MONDAY_API_KEY", ""),
        'monday_boards': None,
        'edit_user_id': None,
        'show_create_user': False,
        'success_message': None,
        'selected_board_id': None,
        'employee_view': 'dashboard',
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

    # Initialize auth_manager separately to avoid issues with caching
    if st.session_state.auth_manager is None:
        st.session_state.auth_manager = AuthManager()


def logout() -> None:
    """Log out current user and reset session state."""
    keys_to_reset = {
        'authenticated': False,
        'current_user': None,
        'edit_user_id': None,
        'show_create_user': False,
        'success_message': None,
        'selected_board_id': None,
        'employee_view': 'dashboard',
    }

    for key, default_value in keys_to_reset.items():
        if key in st.session_state:
            st.session_state[key] = default_value

    st.rerun()


def get_current_user() -> Optional[User]:
    """Get the currently authenticated user."""
    return st.session_state.get('current_user')


def is_authenticated() -> bool:
    """Check if a user is currently authenticated."""
    return st.session_state.get('authenticated', False)


def set_success_message(message: str) -> None:
    """Set a success message to display on next render."""
    st.session_state.success_message = message


def clear_success_message() -> None:
    """Clear the current success message."""
    st.session_state.success_message = None


def get_success_message() -> Optional[str]:
    """Get and clear the current success message."""
    message = st.session_state.get('success_message')
    if message:
        st.session_state.success_message = None
    return message


def get_auth_manager() -> AuthManager:
    """Get the authentication manager instance."""
    if st.session_state.auth_manager is None:
        st.session_state.auth_manager = AuthManager()
    return st.session_state.auth_manager


def get_monday_api_key() -> str:
    """Get the Monday.com API key."""
    return st.session_state.get('monday_api_key', '')


def set_monday_api_key(api_key: str) -> None:
    """Set the Monday.com API key and clear cached boards."""
    st.session_state.monday_api_key = api_key
    st.session_state.monday_boards = None


def get_monday_boards() -> Optional[list]:
    """Get cached Monday.com boards."""
    return st.session_state.get('monday_boards')


def set_monday_boards(boards: list) -> None:
    """Cache Monday.com boards."""
    st.session_state.monday_boards = boards


def clear_monday_boards() -> None:
    """Clear cached Monday.com boards."""
    st.session_state.monday_boards = None
