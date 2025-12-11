# -*- coding: utf-8 -*-
"""
Admin board creator component.
Allows admin to create empty boards with predefined columns for illustrations.
"""

import streamlit as st

from ui.components import render_divider, render_info_box


# Default columns for illustration boards
ILLUSTRATION_COLUMNS = [
    {"name": "insurer_name", "type": "text", "label": "Nom de l'assureur"},
    {"name": "report_date", "type": "text", "label": "Date du rapport"},
    {"name": "advisor_name", "type": "text", "label": "Nom du conseiller"},
    {"name": "insured_number", "type": "text", "label": "Numero assure"},
    {"name": "last_name", "type": "text", "label": "Nom"},
    {"name": "first_name", "type": "text", "label": "Prenom"},
    {"name": "insured_name", "type": "text", "label": "Nom complet assure"},
    {"name": "sex", "type": "text", "label": "Sexe"},
    {"name": "birth_date", "type": "text", "label": "Date de naissance"},
    {"name": "age", "type": "numbers", "label": "Age"},
    {"name": "smoker", "type": "text", "label": "Fumeur"},
    {"name": "product_name", "type": "text", "label": "Nom du produit"},
    {"name": "coverage_amount", "type": "numbers", "label": "Montant couverture"},
    {"name": "policy_premium", "type": "numbers", "label": "Prime police"},
    {"name": "monthly_premium", "type": "numbers", "label": "Prime mensuelle"},
    {"name": "payment_duration", "type": "text", "label": "Duree paiement"},
    {"name": "details", "type": "text", "label": "Details"},
]


def render_board_creator() -> None:
    """Render the board creator interface for admin."""
    st.markdown("### Creer un nouveau board")

    _init_board_creator_state()

    api_key = st.session_state.monday_api_key
    if not api_key:
        st.error("API Monday.com non configuree. Configurez la cle API dans le menu de gauche.")
        return

    # Board creation form
    if st.session_state.board_creator_stage == 1:
        _render_board_config()
    elif st.session_state.board_creator_stage == 2:
        _render_board_created()


def _init_board_creator_state() -> None:
    """Initialize board creator state."""
    defaults = {
        'board_creator_stage': 1,
        'board_creator_new_board_id': None,
        'board_creator_new_board_name': None,
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _reset_board_creator_state() -> None:
    """Reset board creator state."""
    st.session_state.board_creator_stage = 1
    st.session_state.board_creator_new_board_id = None
    st.session_state.board_creator_new_board_name = None


def _render_board_config() -> None:
    """Render board configuration form."""
    st.markdown("#### 1. Configuration du board")

    board_name = st.text_input(
        "Nom du board",
        placeholder="Ex: Illustrations Assurance 2025",
        help="Le nom qui apparaitra dans Monday.com",
        key="board_creator_name_input"
    )

    # Show columns that will be created
    with st.expander("📋 Colonnes qui seront creees", expanded=False):
        cols_preview = st.columns(3)
        for i, col_def in enumerate(ILLUSTRATION_COLUMNS):
            col_idx = i % 3
            with cols_preview[col_idx]:
                col_type_icon = "🔢" if col_def["type"] == "numbers" else "📝"
                st.markdown(f"{col_type_icon} **{col_def['label']}**")

    render_divider()

    # User assignment section
    st.markdown("#### 2. Assigner des utilisateurs (optionnel)")

    auth_manager = st.session_state.auth_manager
    users = auth_manager.get_all_users()
    employees = [u for u in users if u['role'] == 'employee']

    selected_users = []
    if employees:
        user_options = {u['user_id']: f"{u['name']} (@{u['user_id']})" for u in employees}

        selected_users = st.multiselect(
            "Utilisateurs a assigner au board",
            options=list(user_options.keys()),
            format_func=lambda x: user_options.get(x, x),
            help="Ces utilisateurs auront acces au board une fois cree",
            key="board_creator_users_select"
        )

        if selected_users:
            st.info(f"✓ {len(selected_users)} utilisateur(s) seront assigne(s) au board")
    else:
        st.info("Aucun employe disponible. Creez des utilisateurs dans l'onglet 'Utilisateurs'.")

    render_divider()

    # Create button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        can_create = bool(board_name and board_name.strip())

        if st.button(
            "🚀 Creer le board",
            type="primary",
            width="stretch",
            disabled=not can_create
        ):
            _create_board(board_name.strip(), selected_users)


def _create_board(board_name: str, users_to_assign: list) -> None:
    """Create the board with columns and assign users."""
    api_key = st.session_state.monday_api_key

    progress = st.progress(0)
    status = st.empty()

    try:
        from monday_automation import MondayClient

        client = MondayClient(api_key=api_key)

        # Step 1: Create board
        status.text(f"Creation du board '{board_name}'...")
        progress.progress(10)

        board_result = client.create_board(
            board_name=board_name,
            board_kind="public",
            reuse_existing=False  # Always create new board
        )

        if not board_result.success or not board_result.board_id:
            st.error(f"Erreur lors de la creation du board: {board_result.error}")
            return

        board_id = board_result.board_id
        progress.progress(30)

        # Step 2: Create columns
        status.text("Creation des colonnes...")

        text_columns = [c["name"] for c in ILLUSTRATION_COLUMNS if c["type"] == "text"]
        number_columns = [c["name"] for c in ILLUSTRATION_COLUMNS if c["type"] == "numbers"]

        # Create text columns
        if text_columns:
            client.get_or_create_columns(
                board_id=int(board_id),
                column_names=text_columns,
                column_type="text"
            )

        progress.progress(50)

        # Create number columns
        if number_columns:
            client.get_or_create_columns(
                board_id=int(board_id),
                column_names=number_columns,
                column_type="numbers"
            )

        progress.progress(70)

        # Step 3: Assign users if any
        if users_to_assign:
            status.text(f"Assignation des {len(users_to_assign)} utilisateurs...")

            auth_manager = st.session_state.auth_manager

            for user_id in users_to_assign:
                # Get current boards for user
                current_boards = auth_manager.get_user_boards(user_id)
                # Add new board
                new_boards = list(set(current_boards + [str(board_id)]))
                # Update user
                auth_manager.assign_boards_to_user(user_id, new_boards)

        progress.progress(100)
        status.empty()

        # Save results
        st.session_state.board_creator_new_board_id = board_id
        st.session_state.board_creator_new_board_name = board_name
        st.session_state.board_creator_stage = 2

        # Refresh boards list
        st.session_state.monday_boards = None

        st.rerun()

    except Exception as e:
        st.error(f"Erreur: {e}")


def _render_board_created() -> None:
    """Render success screen after board creation."""
    board_id = st.session_state.board_creator_new_board_id
    board_name = st.session_state.board_creator_new_board_name

    st.balloons()

    st.success(f"Board '{board_name}' cree avec succes!")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Board ID", board_id)

    with col2:
        st.metric("Colonnes", len(ILLUSTRATION_COLUMNS))

    render_divider()

    render_info_box(
        f"Le board <strong>{board_name}</strong> est maintenant disponible dans Monday.com "
        f"avec {len(ILLUSTRATION_COLUMNS)} colonnes pre-configurees pour les illustrations d'assurance."
    )

    st.markdown("")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("➕ Creer un autre board", width="stretch"):
            _reset_board_creator_state()
            st.rerun()

    with col2:
        url = f"https://monday.com/boards/{board_id}"
        st.link_button("🔗 Ouvrir dans Monday.com", url, width="stretch")
