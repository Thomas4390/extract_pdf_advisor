# -*- coding: utf-8 -*-
"""
User model definition.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class User:
    """User data structure."""
    user_id: str
    password_hash: str
    name: str
    email: str
    role: str
    assigned_boards: List[str]
    created_at: str
    last_login: Optional[str] = None
    is_active: bool = True

    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == "admin"

    @property
    def is_employee(self) -> bool:
        """Check if user is employee."""
        return self.role == "employee"

    def to_dict(self, include_password: bool = False) -> dict:
        """Convert user to dictionary."""
        data = {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'assigned_boards': self.assigned_boards,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'is_active': self.is_active
        }
        if include_password:
            data['password_hash'] = self.password_hash
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create User from dictionary."""
        return cls(
            user_id=data['user_id'],
            password_hash=data.get('password_hash', ''),
            name=data['name'],
            email=data.get('email', ''),
            role=data['role'],
            assigned_boards=data.get('assigned_boards', []),
            created_at=data['created_at'],
            last_login=data.get('last_login'),
            is_active=data.get('is_active', True)
        )
