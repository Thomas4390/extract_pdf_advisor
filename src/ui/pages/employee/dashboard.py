# -*- coding: utf-8 -*-
"""
Employee dashboard page.
"""

import streamlit as st

from services.monday_integration import MondayIntegration
from utils.session import logout
from ui.components import (
    render_user_header,
    render_empty_state,
    render_stat_card,
    render_board_card,
    render_gradient_header,
    render_info_box,
    render_divider,
    render_api_key_input
)
from config import MIN_PASSWORD_LENGTH


def render_employee_dashboard() -> None:
    """Render employee dashboard with board selection."""
    user = st.session_state.current_user
    auth_manager = st.session_state.auth_manager

    _render_sidebar(user)

    # Get assigned boards
    assigned_board_ids = auth_manager.get_user_boards(user.user_id)

    if not assigned_board_ids:
        render_empty_state(
            "📋",
            "Aucun board assigne",
            "Contactez votre administrateur pour obtenir l'acces aux boards."
        )
        return

    # Load boards
    api_key = st.session_state.monday_api_key
    if not api_key:
        st.error("API Monday.com non configuree. Contactez l'administrateur.")
        return

    if st.session_state.monday_boards is None:
        with st.spinner("Chargement..."):
            monday = MondayIntegration(api_key=api_key)
            st.session_state.monday_boards = monday.get_boards()

    all_boards = st.session_state.monday_boards or []
    user_boards = [b for b in all_boards if b['id'] in assigned_board_ids]

    # Render view based on selection
    if st.session_state.employee_view == 'dashboard':
        _render_dashboard_view(user, user_boards)
    elif st.session_state.employee_view == 'illustrations':
        _render_illustrations_view(user, user_boards)
    else:
        _render_add_data_view(user, user_boards)


def _render_sidebar(user) -> None:
    """Render employee sidebar."""
    with st.sidebar:
        render_user_header(user.name, user.role, icon="👤")

        render_api_key_input()

        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

        st.markdown("#### Navigation")

        if st.button(
            "📊 Tableau de bord",
            width="stretch",
            type="primary" if st.session_state.employee_view == 'dashboard' else "secondary"
        ):
            st.session_state.employee_view = 'dashboard'
            st.session_state.selected_board_id = None
            st.rerun()

        if st.button(
            "📄 Illustrations PDF",
            width="stretch",
            type="primary" if st.session_state.employee_view == 'illustrations' else "secondary"
        ):
            st.session_state.employee_view = 'illustrations'
            st.rerun()

        if st.button(
            "➕ Ajouter des donnees",
            width="stretch",
            type="primary" if st.session_state.employee_view == 'add_data' else "secondary"
        ):
            st.session_state.employee_view = 'add_data'
            st.rerun()

        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)

        if st.button("🚪 Deconnexion", width="stretch"):
            logout()


def _render_illustrations_view(user, user_boards: list) -> None:
    """Render illustrations upload view."""
    from ui.pages.employee.illustrations import render_illustrations_page
    render_illustrations_page(user, user_boards)


def _render_dashboard_view(user, user_boards: list) -> None:
    """Render employee dashboard view with statistics."""
    st.markdown(f"""
    <h1 style="margin-bottom: 0.5rem;">
        Bonjour, <span class="gradient-header">{user.name}</span> 👋
    </h1>
    <p style="color: #666; margin-bottom: 2rem;">Voici vos boards et statistiques</p>
    """, unsafe_allow_html=True)

    # Stats
    col1, col2, col3 = st.columns(3)

    with col1:
        render_stat_card(str(len(user_boards)), "Boards assignes")

    with col2:
        render_stat_card("-", "Total Items")

    with col3:
        render_stat_card("-", "Total Groupes")

    render_divider()

    st.markdown("### 📋 Vos Boards")

    if not user_boards:
        st.info("Aucun board disponible.")
        return

    monday = MondayIntegration(api_key=st.session_state.monday_api_key)

    for board in user_boards:
        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                render_board_card(
                    board['name'],
                    board['id'],
                    board.get('board_kind', 'N/A')
                )

            with col2:
                if st.button("📊 Stats", key=f"stats_{board['id']}"):
                    with st.spinner("Chargement..."):
                        details = monday.get_board_details(board['id'])
                        if details:
                            st.info(
                                f"**{board['name']}**\n\n"
                                f"- Groupes: {details['groups_count']}\n"
                                f"- Items: {details['items_count']}"
                            )


def _render_add_data_view(user, user_boards: list) -> None:
    """Render view for adding data to boards."""
    render_gradient_header(
        "Ajouter des donnees",
        "Selectionnez un board pour y ajouter des informations"
    )

    if not user_boards:
        st.warning("Aucun board disponible.")
        return

    # Board selection
    st.markdown("### 1. Selectionner un board")

    board_options = {b['id']: b['name'] for b in user_boards}

    selected_id = st.selectbox(
        "Board de destination",
        options=list(board_options.keys()),
        format_func=lambda x: board_options.get(x, x),
        key="employee_board_select"
    )

    if selected_id:
        st.session_state.selected_board_id = selected_id
        selected_board = next((b for b in user_boards if b['id'] == selected_id), None)

        if selected_board:
            render_info_box(f"✓ Board selectionne: <strong>{selected_board['name']}</strong>")

            render_divider()

            st.markdown("### 2. Informations du board")

            monday = MondayIntegration(api_key=st.session_state.monday_api_key)

            with st.spinner("Chargement des details..."):
                details = monday.get_board_details(selected_id)

                if details:
                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric("Groupes", details['groups_count'])

                    with col2:
                        st.metric("Items", details['items_count'])

                    if details['groups']:
                        st.markdown("#### Groupes disponibles")
                        for group in details['groups']:
                            st.markdown(f"- {group['title']}")

            render_divider()

            st.markdown("### 3. Ajouter des donnees")

            render_info_box(
                "ℹ️ Cette fonctionnalite sera disponible prochainement.<br>"
                "Vous pourrez uploader des fichiers PDF ou entrer des donnees manuellement."
            )

    # Change password in expander
    _render_password_change_expander(user)


def _render_password_change_expander(user) -> None:
    """Render password change in an expander."""
    with st.expander("🔑 Changer mon mot de passe"):
        with st.form("employee_password_form"):
            current_pw = st.text_input("Actuel", type="password")
            new_pw = st.text_input("Nouveau", type="password")
            confirm_pw = st.text_input("Confirmer", type="password")

            if st.form_submit_button("Changer"):
                if not all([current_pw, new_pw, confirm_pw]):
                    st.error("Remplissez tous les champs")
                elif new_pw != confirm_pw:
                    st.error("Les mots de passe ne correspondent pas")
                elif len(new_pw) < MIN_PASSWORD_LENGTH:
                    st.error(f"Minimum {MIN_PASSWORD_LENGTH} caracteres")
                else:
                    if st.session_state.auth_manager.authenticate(user.user_id, current_pw):
                        success, _ = st.session_state.auth_manager.update_user(
                            user.user_id,
                            password=new_pw
                        )
                        if success:
                            st.success("Mot de passe modifie!")
                    else:
                        st.error("Mot de passe actuel incorrect")
