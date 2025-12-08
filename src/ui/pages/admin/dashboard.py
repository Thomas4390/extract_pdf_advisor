# -*- coding: utf-8 -*-
"""
Admin dashboard page.
"""

import streamlit as st

from config import ROLE_ADMIN, ROLE_EMPLOYEE
from utils.session import logout, get_success_message
from ui.components import (
    render_stat_card,
    render_success_banner,
    render_gradient_header,
    render_divider,
    render_user_header
)
from ui.pages.admin.users import render_user_management
from ui.pages.admin.boards import render_board_assignment
from ui.pages.admin.settings import render_admin_settings


def render_admin_dashboard() -> None:
    """Render admin dashboard with modern design."""
    user = st.session_state.current_user

    _render_sidebar(user)
    _render_main_content(user)


def _render_sidebar(user) -> None:
    """Render admin sidebar."""
    with st.sidebar:
        render_user_header(user.name, user.role, icon="👑")

        if st.button("🚪 Deconnexion", use_container_width=True):
            logout()


def _render_main_content(user) -> None:
    """Render main dashboard content."""
    # Success message
    success_message = get_success_message()
    if success_message:
        render_success_banner(success_message)

    # Header
    render_gradient_header(
        "Tableau de bord",
        "Gerez les utilisateurs et les acces aux boards"
    )

    # Stats cards
    _render_stats()

    render_divider()

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "👥 Utilisateurs",
        "📋 Assignation Boards",
        "⚙️ Parametres"
    ])

    with tab1:
        render_user_management()

    with tab2:
        render_board_assignment()

    with tab3:
        render_admin_settings()


def _render_stats() -> None:
    """Render statistics cards."""
    auth_manager = st.session_state.auth_manager
    users = auth_manager.get_all_users()
    admins = sum(1 for u in users if u['role'] == ROLE_ADMIN)
    employees = sum(1 for u in users if u['role'] == ROLE_EMPLOYEE)
    boards_count = len(st.session_state.monday_boards or [])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_stat_card(str(len(users)), "Utilisateurs")

    with col2:
        render_stat_card(str(admins), "Admins")

    with col3:
        render_stat_card(str(employees), "Employes")

    with col4:
        render_stat_card(str(boards_count), "Boards")
