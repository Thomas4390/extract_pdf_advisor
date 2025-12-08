# -*- coding: utf-8 -*-
"""Pages package."""

from .login import render_login_page
from .admin import render_admin_dashboard
from .employee import render_employee_dashboard

__all__ = ['render_login_page', 'render_admin_dashboard', 'render_employee_dashboard']
