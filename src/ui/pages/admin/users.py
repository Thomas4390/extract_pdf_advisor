# -*- coding: utf-8 -*-
"""
User management components for admin dashboard.
"""

import streamlit as st

from config import ROLE_ADMIN, ROLE_EMPLOYEE
from ui.components import (
    render_badge,
    render_form_header,
    render_horizontal_rule
)


def render_user_management() -> None:
    """Render user management section."""
    auth_manager = st.session_state.auth_manager

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### Gestion des utilisateurs")
    with col2:
        if st.button("➕ Nouvel utilisateur", type="primary", width="stretch"):
            st.session_state.show_create_user = True

    if st.session_state.show_create_user:
        _render_create_user_form()

    if st.session_state.edit_user_id:
        _render_edit_user_form(st.session_state.edit_user_id)

    st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)

    users = auth_manager.get_all_users()

    for user_data in users:
        _render_user_row(user_data, auth_manager)


def _render_user_row(user_data: dict, auth_manager) -> None:
    """Render a single user row."""
    role_badge = "badge-admin" if user_data['role'] == ROLE_ADMIN else "badge-employee"
    role_text = "Admin" if user_data['role'] == ROLE_ADMIN else "Employe"
    status_badge = "badge-active" if user_data.get('is_active', True) else "badge-inactive"
    status_text = "Actif" if user_data.get('is_active', True) else "Inactif"
    boards_count = len(user_data.get('assigned_boards', []))

    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

    with col1:
        st.markdown(f"""
        <div style="padding: 0.5rem 0;">
            <div style="font-weight: 600; font-size: 1rem; margin-bottom: 0.25rem;">
                {user_data['name']}
            </div>
            <div style="font-size: 0.8rem; color: #888;">
                @{user_data['user_id']} - {user_data.get('email', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="padding: 0.75rem 0;">
            <span class="badge {role_badge}">{role_text}</span>
            <span class="badge {status_badge}">{status_text}</span>
            <span style="font-size: 0.8rem; color: #666; margin-left: 0.5rem;">
                {boards_count} boards
            </span>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        if user_data['user_id'] != 'admin':
            if st.button("✏️", key=f"edit_{user_data['user_id']}", help="Modifier"):
                st.session_state.edit_user_id = user_data['user_id']
                st.rerun()

    with col4:
        if user_data['user_id'] != 'admin':
            if st.button("🗑️", key=f"del_{user_data['user_id']}", help="Supprimer"):
                success, msg = auth_manager.delete_user(user_data['user_id'])
                if success:
                    st.session_state.success_message = msg
                    st.rerun()
                else:
                    st.error(msg)

    render_horizontal_rule()


def _render_create_user_form() -> None:
    """Render create user form with board assignment."""
    render_form_header("➕ Nouvel utilisateur", color_scheme="green")

    boards = st.session_state.monday_boards or []
    board_options = {b['id']: b['name'] for b in boards}

    with st.form("create_user_form"):
        col1, col2 = st.columns(2)

        with col1:
            new_user_id = st.text_input("Identifiant *", placeholder="ex: jdupont")
            new_name = st.text_input("Nom complet *", placeholder="ex: Jean Dupont")
            new_role = st.selectbox(
                "Role",
                [ROLE_EMPLOYEE, ROLE_ADMIN],
                format_func=lambda x: "Employe" if x == ROLE_EMPLOYEE else "Administrateur"
            )

        with col2:
            new_email = st.text_input("Email (optionnel)", placeholder="jean.dupont@company.com")
            new_password = st.text_input("Mot de passe *", type="password")
            new_password_confirm = st.text_input("Confirmer *", type="password")

        st.markdown("---")
        st.markdown("#### 📋 Assigner des boards (optionnel)")

        if boards:
            new_boards = st.multiselect(
                "Selectionner les boards",
                options=list(board_options.keys()),
                format_func=lambda x: board_options.get(x, x),
                help="Selectionnez les boards auxquels ce nouvel utilisateur aura acces"
            )
        else:
            st.info("Configurez la cle API Monday.com pour assigner des boards.")
            new_boards = []

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            cancel = st.form_submit_button("Annuler", width="stretch")
        with col_btn2:
            submit = st.form_submit_button("Creer", type="primary", width="stretch")

        if cancel:
            st.session_state.show_create_user = False
            st.rerun()

        if submit:
            if not all([new_user_id, new_name, new_password]):
                st.error("Remplissez les champs obligatoires")
            elif new_password != new_password_confirm:
                st.error("Les mots de passe ne correspondent pas")
            else:
                success, msg = st.session_state.auth_manager.create_user(
                    user_id=new_user_id,
                    password=new_password,
                    name=new_name,
                    email=new_email,
                    role=new_role,
                    assigned_boards=new_boards
                )
                if success:
                    st.session_state.show_create_user = False
                    st.session_state.success_message = msg
                    st.rerun()
                else:
                    st.error(msg)


def _render_edit_user_form(user_id: str) -> None:
    """Render edit user form with board assignment."""
    user_data = st.session_state.auth_manager.get_user(user_id)
    if not user_data:
        st.session_state.edit_user_id = None
        return

    render_form_header(f"✏️ Modifier: {user_data['name']}", color_scheme="yellow")

    boards = st.session_state.monday_boards or []
    current_boards = user_data.get('assigned_boards', [])
    board_options = {b['id']: b['name'] for b in boards}

    with st.form("edit_user_form"):
        col1, col2 = st.columns(2)

        with col1:
            edit_name = st.text_input("Nom complet", value=user_data['name'])
            edit_role = st.selectbox(
                "Role",
                [ROLE_EMPLOYEE, ROLE_ADMIN],
                index=0 if user_data['role'] == ROLE_EMPLOYEE else 1,
                format_func=lambda x: "Employe" if x == ROLE_EMPLOYEE else "Admin"
            )
            edit_active = st.checkbox("Compte actif", value=user_data.get('is_active', True))

        with col2:
            edit_email = st.text_input("Email", value=user_data.get('email', ''))
            edit_password = st.text_input(
                "Nouveau mot de passe",
                type="password",
                help="Laisser vide pour ne pas modifier"
            )

        st.markdown("---")
        st.markdown("#### 📋 Boards assignes")

        if boards:
            edit_boards = st.multiselect(
                "Selectionner les boards",
                options=list(board_options.keys()),
                default=[b for b in current_boards if b in board_options],
                format_func=lambda x: board_options.get(x, x),
                help="Selectionnez les boards auxquels cet utilisateur aura acces"
            )
        else:
            st.info("Configurez la cle API Monday.com pour assigner des boards.")
            edit_boards = current_boards

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            cancel = st.form_submit_button("Annuler", width="stretch")
        with col_btn2:
            submit = st.form_submit_button("Enregistrer", type="primary", width="stretch")

        if cancel:
            st.session_state.edit_user_id = None
            st.rerun()

        if submit:
            success, msg = st.session_state.auth_manager.update_user(
                user_id=user_id,
                name=edit_name,
                email=edit_email,
                password=edit_password if edit_password else None,
                role=edit_role,
                is_active=edit_active,
                assigned_boards=edit_boards
            )
            if success:
                st.session_state.edit_user_id = None
                st.session_state.success_message = f"Utilisateur '{user_data['name']}' mis a jour avec succes"
                st.rerun()
            else:
                st.error(msg)
