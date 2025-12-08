# -*- coding: utf-8 -*-
"""
Configuration et constantes de l'application.
"""

# Application info
APP_NAME = "Commission Pipeline"
APP_VERSION = "6.0.0"
APP_ICON = "📊"

# Default admin credentials
DEFAULT_ADMIN_ID = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_NAME = "Administrateur"
DEFAULT_ADMIN_EMAIL = "admin@company.com"

# Validation rules
MIN_USER_ID_LENGTH = 3
MIN_PASSWORD_LENGTH = 6

# Google Sheets column mapping
SHEET_COLUMNS = {
    'user_id': 0,
    'password_hash': 1,
    'name': 2,
    'email': 3,
    'role': 4,
    'assigned_boards': 5,
    'created_at': 6,
    'last_login': 7,
    'is_active': 8
}

# User roles
ROLE_ADMIN = "admin"
ROLE_EMPLOYEE = "employee"

# Board priority keywords for sorting
BOARD_PRIORITY_KEYWORDS = {
    0: ['paiement', 'historique'],
    1: ['vente', 'production']
}
