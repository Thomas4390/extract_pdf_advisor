# -*- coding: utf-8 -*-
"""
Reusable UI components for the application.
"""

import streamlit as st


def render_stat_card(value: str, label: str) -> None:
    """Render a statistics card with gradient value."""
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_board_card(name: str, board_id: str, board_kind: str = "N/A") -> None:
    """Render a board card with name and ID."""
    st.markdown(f"""
    <div class="board-card">
        <div class="board-name">{name}</div>
        <div class="board-id">ID: {board_id} - Type: {board_kind}</div>
    </div>
    """, unsafe_allow_html=True)


def render_badge(text: str, badge_type: str = "default") -> str:
    """Return HTML for a badge.

    Args:
        text: Badge text
        badge_type: One of 'admin', 'employee', 'active', 'inactive'

    Returns:
        HTML string for the badge
    """
    badge_class = f"badge-{badge_type}" if badge_type != "default" else "badge"
    return f'<span class="badge {badge_class}">{text}</span>'


def render_success_banner(message: str) -> None:
    """Render a success banner."""
    st.markdown(f"""
    <div class="success-banner">
        <span style="font-size: 1.25rem;">✓</span>
        <span>{message}</span>
    </div>
    """, unsafe_allow_html=True)


def render_inline_success(message: str, details: str = "") -> None:
    """Render an inline success message (e.g., under a button)."""
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                color: white; padding: 1rem 1.5rem; border-radius: 12px;
                margin-top: 1rem; display: flex; align-items: center; gap: 0.75rem;
                font-weight: 500; box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);">
        <span style="font-size: 1.5rem;">✓</span>
        <span>{message}{f' <strong>{details}</strong>' if details else ''}</span>
    </div>
    """, unsafe_allow_html=True)


def render_info_box(message: str) -> None:
    """Render an information box."""
    st.markdown(f"""
    <div class="info-box">
        {message}
    </div>
    """, unsafe_allow_html=True)


def render_warning_box(message: str) -> None:
    """Render a warning box."""
    st.markdown(f"""
    <div class="warning-box">
        {message}
    </div>
    """, unsafe_allow_html=True)


def render_divider() -> None:
    """Render a styled divider."""
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)


def render_gradient_header(title: str, subtitle: str = "") -> None:
    """Render a header with gradient text."""
    st.markdown(f"""
    <h1 style="margin-bottom: 0.5rem;">
        <span class="gradient-header">{title}</span>
    </h1>
    {f'<p style="color: #666; margin-bottom: 2rem;">{subtitle}</p>' if subtitle else ''}
    """, unsafe_allow_html=True)


def render_user_header(name: str, role: str, icon: str = "👤") -> None:
    """Render user header in sidebar."""
    role_display = "Administrateur" if role == "admin" else "Employe"
    st.markdown(f"""
    <div style="padding: 1rem 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 1rem;">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{icon}</div>
        <div style="font-weight: 600; font-size: 1.1rem;">{name}</div>
        <div style="font-size: 0.8rem; opacity: 0.7;">{role_display}</div>
    </div>
    """, unsafe_allow_html=True)


def render_user_row(name: str, user_id: str, email: str, role: str,
                    is_active: bool, boards_count: int) -> None:
    """Render a user row with badges."""
    role_badge = render_badge("Admin" if role == "admin" else "Employe",
                              "admin" if role == "admin" else "employee")
    status_badge = render_badge("Actif" if is_active else "Inactif",
                                "active" if is_active else "inactive")

    st.markdown(f"""
    <div style="padding: 0.5rem 0;">
        <div style="font-weight: 600; font-size: 1rem; margin-bottom: 0.25rem;">
            {name}
        </div>
        <div style="font-size: 0.8rem; color: #888;">
            @{user_id} - {email}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_empty_state(icon: str, title: str, message: str) -> None:
    """Render an empty state placeholder."""
    st.markdown(f"""
    <div style="text-align: center; padding: 4rem 2rem;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">{icon}</div>
        <h2>{title}</h2>
        <p style="color: #666;">{message}</p>
    </div>
    """, unsafe_allow_html=True)


def render_form_header(title: str, color_scheme: str = "green") -> None:
    """Render a styled form header.

    Args:
        title: Header title
        color_scheme: 'green' for create, 'yellow' for edit
    """
    if color_scheme == "green":
        bg = "linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)"
        border = "#4caf50"
        shadow = "rgba(76, 175, 80, 0.2)"
        text_color = "#2e7d32"
    else:
        bg = "linear-gradient(135deg, #fff3cd 0%, #ffe5a0 100%)"
        border = "#ffc107"
        shadow = "rgba(255, 193, 7, 0.2)"
        text_color = "#856404"

    st.markdown(f"""
    <div style="background: {bg};
                padding: 1.5rem; border-radius: 16px; margin-bottom: 1.5rem;
                border: 1px solid {border}; box-shadow: 0 4px 15px {shadow};">
        <h4 style="margin-top: 0; color: {text_color};">{title}</h4>
    </div>
    """, unsafe_allow_html=True)


def render_spacer(height: str = "1rem") -> None:
    """Render a vertical spacer."""
    st.markdown(f"<div style='height: {height}'></div>", unsafe_allow_html=True)


def render_horizontal_rule() -> None:
    """Render a subtle horizontal rule."""
    st.markdown(
        "<hr style='margin: 0.5rem 0; border: none; border-top: 1px solid #f0f0f0;'>",
        unsafe_allow_html=True
    )
