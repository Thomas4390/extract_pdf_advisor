# -*- coding: utf-8 -*-
"""
Admin settings components.
"""

import streamlit as st

from config import MIN_PASSWORD_LENGTH


def render_admin_settings() -> None:
    """Render admin settings."""
    st.markdown("### Parametres")

    col1, col2 = st.columns(2)

    with col1:
        _render_password_change_form()

    with col2:
        _render_api_key_settings()


def _render_password_change_form() -> None:
    """Render password change form."""
    user = st.session_state.current_user

    st.markdown("#### 🔑 Changer mon mot de passe")

    with st.form("change_password_form"):
        current_password = st.text_input("Mot de passe actuel", type="password")
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm_password = st.text_input("Confirmer", type="password")

        if st.form_submit_button("Changer", type="primary"):
            if not all([current_password, new_password, confirm_password]):
                st.error("Remplissez tous les champs")
            elif new_password != confirm_password:
                st.error("Les mots de passe ne correspondent pas")
            elif len(new_password) < MIN_PASSWORD_LENGTH:
                st.error(f"Minimum {MIN_PASSWORD_LENGTH} caracteres")
            else:
                if st.session_state.auth_manager.authenticate(user.user_id, current_password):
                    success, msg = st.session_state.auth_manager.update_user(
                        user.user_id,
                        password=new_password
                    )
                    if success:
                        st.session_state.success_message = "Mot de passe modifie"
                        st.rerun()
                else:
                    st.error("Mot de passe actuel incorrect")


def _render_api_key_settings() -> None:
    """Render Monday.com API key settings."""
    st.markdown("#### 🔐 API Monday.com")

    api_key = st.session_state.monday_api_key

    if api_key:
        st.success("✓ Cle API configuree")
        if st.button("Modifier la cle"):
            st.session_state.monday_api_key = ""
            st.session_state.monday_boards = None
            st.rerun()
    else:
        new_key = st.text_input("Cle API", type="password")
        if st.button("Enregistrer", type="primary"):
            if new_key:
                st.session_state.monday_api_key = new_key
                st.session_state.success_message = "Cle API enregistree"
                st.rerun()
