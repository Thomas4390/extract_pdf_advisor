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
    render_user_header,
    render_api_key_input
)
from ui.pages.admin.users import render_user_management
from ui.pages.admin.boards import render_board_assignment
from ui.pages.admin.settings import render_admin_settings
from ui.pages.admin.board_creator import render_board_creator


def render_admin_dashboard() -> None:
    """Render admin dashboard with modern design."""
    user = st.session_state.current_user

    _render_sidebar(user)
    _render_main_content(user)


def _render_sidebar(user) -> None:
    """Render admin sidebar."""
    with st.sidebar:
        render_user_header(user.name, user.role, icon="👑")

        render_api_key_input()

        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)

        if st.button("🚪 Deconnexion", width="stretch"):
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Utilisateurs",
        "📋 Assignation Boards",
        "➕ Creer Board",
        "📄 Illustrations PDF",
        "⚙️ Parametres"
    ])

    with tab1:
        render_user_management()

    with tab2:
        render_board_assignment()

    with tab3:
        render_board_creator()

    with tab4:
        _render_illustrations_tab()

    with tab5:
        render_admin_settings()


def _render_illustrations_tab() -> None:
    """Render illustrations upload tab for admin."""
    from services.monday_integration import MondayIntegration

    # Load boards if not loaded
    api_key = st.session_state.monday_api_key
    if not api_key:
        st.error("API Monday.com non configuree.")
        return

    if st.session_state.monday_boards is None:
        with st.spinner("Chargement des boards..."):
            monday = MondayIntegration(api_key=api_key)
            st.session_state.monday_boards = monday.get_boards()

    all_boards = st.session_state.monday_boards or []

    # Use the illustrations page component
    from ui.pages.employee.illustrations import render_illustrations_page
    user = st.session_state.current_user
    render_illustrations_page(user, all_boards)


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
