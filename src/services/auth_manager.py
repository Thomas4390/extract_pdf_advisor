# -*- coding: utf-8 -*-
"""
Authentication manager with Google Sheets backend.
"""

import hashlib
import json
import secrets
from datetime import datetime
from typing import Dict, List, Optional

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

from models.user import User
from config import (
    SHEET_COLUMNS,
    DEFAULT_ADMIN_ID,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_NAME,
    DEFAULT_ADMIN_EMAIL,
    MIN_USER_ID_LENGTH,
    MIN_PASSWORD_LENGTH,
    ROLE_ADMIN
)


@st.cache_resource
def get_google_sheets_client():
    """Create and cache Google Sheets client."""
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Erreur connexion Google Sheets: {e}")
        return None


class AuthManager:
    """Manages user authentication with Google Sheets as backend."""

    def __init__(self):
        self.client = get_google_sheets_client()
        self.spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
        self._sheet = None
        self._ensure_admin_exists()

    @property
    def sheet(self):
        """Get or create the worksheet connection."""
        if self._sheet is None and self.client:
            try:
                spreadsheet = self.client.open_by_key(self.spreadsheet_id)
                self._sheet = spreadsheet.sheet1
            except Exception as e:
                st.error(f"Erreur acces Google Sheet: {e}")
        return self._sheet

    def _hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        password_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return f"{salt}:{password_hash}", salt

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        try:
            salt, _ = stored_hash.split(":")
            new_hash, _ = self._hash_password(password, salt)
            return new_hash == stored_hash
        except ValueError:
            return False

    def _row_to_user_dict(self, row: list) -> dict:
        """Convert a spreadsheet row to user dictionary."""
        while len(row) < 9:
            row.append("")

        boards_str = row[SHEET_COLUMNS['assigned_boards']]
        try:
            assigned_boards = json.loads(boards_str) if boards_str else []
        except json.JSONDecodeError:
            assigned_boards = []

        is_active_str = row[SHEET_COLUMNS['is_active']]
        is_active = is_active_str.lower() != 'false' if is_active_str else True

        return {
            'user_id': row[SHEET_COLUMNS['user_id']],
            'password_hash': row[SHEET_COLUMNS['password_hash']],
            'name': row[SHEET_COLUMNS['name']],
            'email': row[SHEET_COLUMNS['email']],
            'role': row[SHEET_COLUMNS['role']],
            'assigned_boards': assigned_boards,
            'created_at': row[SHEET_COLUMNS['created_at']],
            'last_login': row[SHEET_COLUMNS['last_login']] or None,
            'is_active': is_active
        }

    def _user_dict_to_row(self, user_data: dict) -> list:
        """Convert user dictionary to spreadsheet row."""
        return [
            user_data['user_id'],
            user_data['password_hash'],
            user_data['name'],
            user_data.get('email', ''),
            user_data['role'],
            json.dumps(user_data.get('assigned_boards', [])),
            user_data['created_at'],
            user_data.get('last_login') or '',
            str(user_data.get('is_active', True))
        ]

    def _find_user_row(self, user_id: str) -> Optional[int]:
        """Find the row number for a user (1-indexed)."""
        if not self.sheet:
            return None
        try:
            cell = self.sheet.find(user_id, in_column=1)
            return cell.row if cell else None
        except Exception:
            return None

    def _load_users(self) -> Dict[str, dict]:
        """Load all users from Google Sheet."""
        if not self.sheet:
            return {}

        try:
            all_records = self.sheet.get_all_values()
            users = {}
            for row in all_records[1:]:  # Skip header
                if row and row[0]:
                    user_data = self._row_to_user_dict(row)
                    users[user_data['user_id']] = user_data
            return users
        except Exception as e:
            st.error(f"Erreur chargement utilisateurs: {e}")
            return {}

    def _ensure_admin_exists(self) -> None:
        """Ensure admin user exists in the sheet."""
        if not self.sheet:
            return

        try:
            admin_row = self._find_user_row(DEFAULT_ADMIN_ID)
            if admin_row is None:
                password_hash, _ = self._hash_password(DEFAULT_ADMIN_PASSWORD)
                admin_data = {
                    "user_id": DEFAULT_ADMIN_ID,
                    "password_hash": password_hash,
                    "name": DEFAULT_ADMIN_NAME,
                    "email": DEFAULT_ADMIN_EMAIL,
                    "role": ROLE_ADMIN,
                    "assigned_boards": [],
                    "created_at": datetime.now().isoformat(),
                    "last_login": None,
                    "is_active": True
                }
                self.sheet.append_row(self._user_dict_to_row(admin_data))
        except Exception as e:
            st.error(f"Erreur creation admin: {e}")

    def authenticate(self, user_id: str, password: str) -> Optional[User]:
        """Authenticate user and return User object if successful."""
        users = self._load_users()
        user_data = users.get(user_id)

        if not user_data or not user_data.get("is_active", True):
            return None

        if self._verify_password(password, user_data["password_hash"]):
            user_data["last_login"] = datetime.now().isoformat()
            row_num = self._find_user_row(user_id)
            if row_num and self.sheet:
                self.sheet.update_cell(row_num, SHEET_COLUMNS['last_login'] + 1,
                                       user_data["last_login"])

            return User.from_dict(user_data)
        return None

    def create_user(self, user_id: str, password: str, name: str, email: str = "",
                    role: str = "employee", assigned_boards: List[str] = None) -> tuple:
        """Create a new user."""
        if not self.sheet:
            return False, "Connexion Google Sheets non disponible"

        users = self._load_users()

        if user_id in users:
            return False, f"L'utilisateur '{user_id}' existe deja"
        if len(user_id) < MIN_USER_ID_LENGTH:
            return False, f"L'ID doit contenir au moins {MIN_USER_ID_LENGTH} caracteres"
        if len(password) < MIN_PASSWORD_LENGTH:
            return False, f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caracteres"

        try:
            password_hash, _ = self._hash_password(password)
            user_data = {
                "user_id": user_id,
                "password_hash": password_hash,
                "name": name,
                "email": email,
                "role": role,
                "assigned_boards": assigned_boards or [],
                "created_at": datetime.now().isoformat(),
                "last_login": None,
                "is_active": True
            }
            self.sheet.append_row(self._user_dict_to_row(user_data))
            return True, f"Utilisateur '{user_id}' cree avec succes"
        except Exception as e:
            return False, f"Erreur creation: {e}"

    def update_user(self, user_id: str, name: str = None, email: str = None,
                    password: str = None, role: str = None,
                    assigned_boards: List[str] = None, is_active: bool = None) -> tuple:
        """Update an existing user."""
        if not self.sheet:
            return False, "Connexion Google Sheets non disponible"

        users = self._load_users()

        if user_id not in users:
            return False, f"Utilisateur '{user_id}' non trouve"

        user_data = users[user_id]

        if is_active is False and user_data["role"] == ROLE_ADMIN:
            admin_count = sum(1 for u in users.values()
                            if u["role"] == ROLE_ADMIN and u.get("is_active", True))
            if admin_count <= 1:
                return False, "Impossible de desactiver le seul administrateur"

        if name is not None:
            user_data["name"] = name
        if email is not None:
            user_data["email"] = email
        if password is not None:
            user_data["password_hash"], _ = self._hash_password(password)
        if role is not None:
            user_data["role"] = role
        if assigned_boards is not None:
            user_data["assigned_boards"] = assigned_boards
        if is_active is not None:
            user_data["is_active"] = is_active

        try:
            row_num = self._find_user_row(user_id)
            if row_num:
                self.sheet.update(f'A{row_num}:I{row_num}',
                                 [self._user_dict_to_row(user_data)])
            return True, f"Utilisateur '{user_id}' mis a jour"
        except Exception as e:
            return False, f"Erreur mise a jour: {e}"

    def delete_user(self, user_id: str) -> tuple:
        """Delete a user."""
        if not self.sheet:
            return False, "Connexion Google Sheets non disponible"

        users = self._load_users()

        if user_id not in users:
            return False, f"Utilisateur '{user_id}' non trouve"
        if user_id == DEFAULT_ADMIN_ID:
            return False, "Impossible de supprimer le compte admin principal"

        user_data = users[user_id]
        if user_data["role"] == ROLE_ADMIN:
            admin_count = sum(1 for u in users.values() if u["role"] == ROLE_ADMIN)
            if admin_count <= 1:
                return False, "Impossible de supprimer le seul administrateur"

        try:
            row_num = self._find_user_row(user_id)
            if row_num:
                self.sheet.delete_rows(row_num)
            return True, f"Utilisateur '{user_id}' supprime"
        except Exception as e:
            return False, f"Erreur suppression: {e}"

    def get_all_users(self) -> List[dict]:
        """Get all users (without password hashes)."""
        users = self._load_users()
        result = []
        for user_data in users.values():
            user_info = user_data.copy()
            user_info.pop("password_hash", None)
            result.append(user_info)
        return result

    def get_user(self, user_id: str) -> Optional[dict]:
        """Get a single user by ID (without password hash)."""
        users = self._load_users()
        if user_id in users:
            user_info = users[user_id].copy()
            user_info.pop("password_hash", None)
            return user_info
        return None

    def assign_boards_to_user(self, user_id: str, board_ids: List[str]) -> tuple:
        """Assign boards to a user."""
        return self.update_user(user_id, assigned_boards=board_ids)

    def get_user_boards(self, user_id: str) -> List[str]:
        """Get boards assigned to a user."""
        user = self.get_user(user_id)
        return user.get("assigned_boards", []) if user else []
