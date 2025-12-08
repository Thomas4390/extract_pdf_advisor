# -*- coding: utf-8 -*-
"""UI package."""

from .styles import apply_global_styles, apply_login_styles
from .components import (
    render_stat_card,
    render_board_card,
    render_badge,
    render_success_banner,
    render_info_box,
    render_warning_box,
    render_divider,
    render_gradient_header
)

__all__ = [
    'apply_global_styles',
    'apply_login_styles',
    'render_stat_card',
    'render_board_card',
    'render_badge',
    'render_success_banner',
    'render_info_box',
    'render_warning_box',
    'render_divider',
    'render_gradient_header'
]
