# -*- coding: utf-8 -*-
"""
Monday.com API integration service.
"""

from typing import List, Optional

import streamlit as st

from config import BOARD_PRIORITY_KEYWORDS


class MondayIntegration:
    """Handles Monday.com API interactions."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def get_boards(self) -> List[dict]:
        """Get all boards from Monday.com."""
        if not self.api_key:
            return []
        try:
            from monday_automation import MondayClient
            client = MondayClient(api_key=self.api_key)
            return client.list_boards()
        except Exception as e:
            st.error(f"Erreur API Monday.com: {e}")
            return []

    def get_board_details(self, board_id: str) -> Optional[dict]:
        """Get detailed info about a specific board."""
        if not self.api_key:
            return None
        try:
            from monday_automation import MondayClient
            client = MondayClient(api_key=self.api_key)
            groups = client.list_groups(board_id=int(board_id))
            items = client.list_items(board_id=int(board_id), limit=500)
            return {
                "groups_count": len(groups),
                "items_count": len(items),
                "groups": groups
            }
        except Exception:
            return None

    def sort_and_filter_boards(self, boards: list, search_query: str = "") -> list:
        """Sort and filter boards by priority and search query."""
        if not boards:
            return []

        filtered = boards
        if search_query and search_query.strip():
            search_lower = search_query.lower().strip()
            filtered = [b for b in boards if search_lower in b['name'].lower()]

        def get_priority(name: str) -> tuple:
            name_lower = name.lower()
            for priority, keywords in BOARD_PRIORITY_KEYWORDS.items():
                if any(kw in name_lower for kw in keywords):
                    return (priority, name_lower)
            return (2, name_lower)

        return sorted(filtered, key=lambda b: get_priority(b['name']))
