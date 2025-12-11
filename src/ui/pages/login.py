# -*- coding: utf-8 -*-
"""
Login page rendering.
"""

import streamlit as st

from config import APP_NAME
from ui.styles import apply_login_styles


def render_login_page() -> None:
    """Render modern login page with enhanced design."""
    apply_login_styles()

    # Background gradient
    st.markdown('<div class="login-bg"></div>', unsafe_allow_html=True)

    # Center the login form
    col1, col2, col3 = st.columns([1, 1.8, 1])

    with col2:
        st.markdown('<div style="height: 2rem;"></div>', unsafe_allow_html=True)

        # Glass card container
        st.markdown(f"""
        <div class="glass-card">
            <div class="logo-container">
                <span class="logo-icon">📊</span>
            </div>
            <h1 class="login-title">{APP_NAME}</h1>
            <p class="login-subtitle">Plateforme de gestion des commissions d'assurance</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

        # Login form in a styled container
        with st.container():
            st.markdown("""
            <div style="background: white; border-radius: 20px; padding: 0.5rem;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.1); border: 1px solid #e8e8e8;">
            """, unsafe_allow_html=True)

            with st.form("login_form", clear_on_submit=False):
                st.markdown('<p class="input-label">👤 Identifiant</p>', unsafe_allow_html=True)
                st.text_input(
                    "Identifiant",
                    placeholder="Entrez votre identifiant",
                    key="login_user_id",
                    label_visibility="collapsed"
                )

                st.markdown('<p class="input-label">🔒 Mot de passe</p>', unsafe_allow_html=True)
                st.text_input(
                    "Mot de passe",
                    type="password",
                    placeholder="Entrez votre mot de passe",
                    key="login_password",
                    label_visibility="collapsed"
                )

                st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)

                submitted = st.form_submit_button(
                    "🚀 Se connecter",
                    type="primary",
                    width="stretch"
                )

                if submitted:
                    _handle_login()

            st.markdown('</div>', unsafe_allow_html=True)

        _render_features()
        _render_hint()


def _handle_login() -> None:
    """Handle login form submission."""
    user_id = st.session_state.login_user_id
    password = st.session_state.login_password

    if not user_id or not password:
        st.error("Veuillez remplir tous les champs")
        return

    user = st.session_state.auth_manager.authenticate(user_id, password)
    if user:
        st.session_state.authenticated = True
        st.session_state.current_user = user
        st.rerun()
    else:
        st.error("Identifiant ou mot de passe incorrect")


def _render_features() -> None:
    """Render feature cards."""
    st.markdown('<div style="height: 1.5rem;"></div>', unsafe_allow_html=True)

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.markdown("""
        <div class="feature-item">
            <div class="feature-icon">📋</div>
            <span class="feature-text">Gestion des boards</span>
        </div>
        """, unsafe_allow_html=True)
    with col_f2:
        st.markdown("""
        <div class="feature-item">
            <div class="feature-icon">👥</div>
            <span class="feature-text">Multi-utilisateurs</span>
        </div>
        """, unsafe_allow_html=True)

    col_f3, col_f4 = st.columns(2)
    with col_f3:
        st.markdown("""
        <div class="feature-item">
            <div class="feature-icon">🔐</div>
            <span class="feature-text">Acces securise</span>
        </div>
        """, unsafe_allow_html=True)
    with col_f4:
        st.markdown("""
        <div class="feature-item">
            <div class="feature-icon">📈</div>
            <span class="feature-text">Statistiques</span>
        </div>
        """, unsafe_allow_html=True)


def _render_hint() -> None:
    """Render login hint box."""
    st.markdown("""
    <div class="login-hint">
        <div class="login-hint-title">Premiere connexion</div>
        <div class="login-hint-content">
            Identifiant: <code>admin</code> &nbsp;|&nbsp; Mot de passe: <code>admin123</code>
        </div>
    </div>
    """, unsafe_allow_html=True)
