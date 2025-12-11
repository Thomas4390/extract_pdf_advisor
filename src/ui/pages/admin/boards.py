# -*- coding: utf-8 -*-
"""
Board assignment components for admin dashboard.
"""

import streamlit as st

from services.monday_integration import MondayIntegration
from ui.components import (
    render_warning_box,
    render_info_box,
    render_divider,
    render_inline_success
)


def render_board_assignment() -> None:
    """Render board assignment section."""
    st.markdown("### Assignation des boards Monday.com")

    api_key = st.session_state.monday_api_key

    if not api_key:
        render_warning_box(
            "⚠️ Cle API Monday.com non configuree. Allez dans les parametres pour la configurer."
        )
        return

    # Load boards
    if st.session_state.monday_boards is None:
        with st.spinner("Chargement des boards..."):
            monday = MondayIntegration(api_key=api_key)
            st.session_state.monday_boards = monday.get_boards()

    boards = st.session_state.monday_boards

    if not boards:
        st.error("Aucun board trouve")
        if st.button("🔄 Reessayer"):
            st.session_state.monday_boards = None
            st.rerun()
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"✓ {len(boards)} boards disponibles")
    with col2:
        if st.button("🔄 Rafraichir"):
            st.session_state.monday_boards = None
            st.rerun()

    render_divider()

    # User selection
    users = st.session_state.auth_manager.get_all_users()
    employees = [u for u in users if u['role'] == 'employee']

    if not employees:
        render_info_box(
            "ℹ️ Creez d'abord des comptes employes pour leur assigner des boards."
        )
        return

    selected_user_id = st.selectbox(
        "Selectionner un employe",
        options=[u['user_id'] for u in employees],
        format_func=lambda x: next(
            (f"{u['name']} ({u['user_id']})" for u in employees if u['user_id'] == x),
            x
        )
    )

    if selected_user_id:
        _render_board_assignment_form(selected_user_id, boards)


def _render_board_assignment_form(user_id: str, boards: list) -> None:
    """Render the board assignment form for a specific user."""
    user_data = st.session_state.auth_manager.get_user(user_id)
    current_boards = user_data.get('assigned_boards', [])

    st.markdown(f"#### Boards pour {user_data['name']}")

    search = st.text_input(
        "🔍 Rechercher",
        placeholder="Filtrer par nom...",
        key="board_search"
    )

    monday = MondayIntegration()
    sorted_boards = monday.sort_and_filter_boards(boards, search)
    board_options = {b['id']: f"{b['name']}" for b in sorted_boards}

    with st.form("board_assignment_form"):
        selected_boards = st.multiselect(
            "Boards assignes",
            options=list(board_options.keys()),
            default=[b for b in current_boards if b in board_options],
            format_func=lambda x: board_options.get(x, x)
        )

        submitted = st.form_submit_button(
            "💾 Enregistrer",
            type="primary",
            width="stretch"
        )

        if submitted:
            success, msg = st.session_state.auth_manager.assign_boards_to_user(
                user_id,
                selected_boards
            )
            if success:
                render_inline_success(
                    "Boards assignes avec succes a",
                    user_data['name']
                )
            else:
                st.error(msg)
