# -*- coding: utf-8 -*-
"""
Employee illustrations upload page.
Handles PDF extraction and upload to Monday.com.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from services.monday_integration import MondayIntegration
from ui.components import (
    render_gradient_header,
    render_info_box,
    render_divider,
    render_stat_card,
)


def render_illustrations_page(user, user_boards: list) -> None:
    """Render the illustrations upload page."""
    render_gradient_header(
        "Illustrations d'assurance",
        "Uploadez des illustrations PDF pour extraction et envoi vers Monday.com"
    )

    # Initialize session state for illustrations
    _init_illustrations_state()

    # Get API key
    api_key = st.session_state.monday_api_key
    if not api_key:
        st.error("API Monday.com non configuree. Contactez l'administrateur.")
        return

    # Render based on current stage
    if st.session_state.illustration_stage == 1:
        _render_stage_upload(user_boards)
    elif st.session_state.illustration_stage == 2:
        _render_stage_preview()
    elif st.session_state.illustration_stage == 3:
        _render_stage_upload_results()


def _init_illustrations_state() -> None:
    """Initialize session state for illustrations."""
    defaults = {
        'illustration_stage': 1,
        'illustration_pdf_path': None,
        'illustration_source': None,
        'illustration_data': None,
        'illustration_board_id': None,
        'illustration_board_name': None,
        'illustration_group_name': None,
        'illustration_upload_results': None,
        'illustration_create_new_board': False,
        'illustration_new_board_name': None,
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _reset_illustrations_state() -> None:
    """Reset illustrations state to start over."""
    # Clean up temp file
    if st.session_state.illustration_pdf_path:
        try:
            os.remove(st.session_state.illustration_pdf_path)
        except Exception:
            pass

    st.session_state.illustration_stage = 1
    st.session_state.illustration_pdf_path = None
    st.session_state.illustration_source = None
    st.session_state.illustration_data = None
    st.session_state.illustration_board_id = None
    st.session_state.illustration_board_name = None
    st.session_state.illustration_group_name = None
    st.session_state.illustration_upload_results = None
    st.session_state.illustration_create_new_board = False
    st.session_state.illustration_new_board_name = None


def _render_stepper() -> None:
    """Render progress stepper."""
    stages = [
        ("1", "Upload PDF", "📤"),
        ("2", "Previsualisation", "🔍"),
        ("3", "Resultat", "✅"),
    ]

    cols = st.columns(3)
    for i, (num, name, icon) in enumerate(stages):
        stage_num = i + 1
        with cols[i]:
            if stage_num == st.session_state.illustration_stage:
                st.markdown(f"""
                <div style="text-align: center; padding: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 10px; color: white;">
                    <div style="font-size: 1.5rem;">{icon}</div>
                    <div style="font-weight: 600;">{name}</div>
                </div>
                """, unsafe_allow_html=True)
            elif stage_num < st.session_state.illustration_stage:
                st.markdown(f"""
                <div style="text-align: center; padding: 10px; background: #d4edda;
                border-radius: 10px; color: #155724;">
                    <div style="font-size: 1.5rem;">✅</div>
                    <div style="font-weight: 500;">{name}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="text-align: center; padding: 10px; background: #f8f9fa;
                border-radius: 10px; color: #6c757d;">
                    <div style="font-size: 1.5rem;">{icon}</div>
                    <div>{name}</div>
                </div>
                """, unsafe_allow_html=True)

    st.write("")


def _render_stage_upload(user_boards: list) -> None:
    """Render stage 1: PDF upload and configuration."""
    _render_stepper()

    # Upload section
    st.markdown("### 1. Upload du fichier PDF")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Deposez votre fichier PDF",
            type=['pdf'],
            help="Fichier PDF d'illustration d'assurance (UV ou Assomption)",
            key="illustration_pdf_upload"
        )

        if uploaded_file:
            st.success(f"Fichier charge: {uploaded_file.name}")

    with col2:
        source = st.selectbox(
            "Source",
            options=["UV", "Assomption"],
            help="Type de document PDF"
        )

    if not uploaded_file:
        st.info("Commencez par uploader un fichier PDF pour continuer.")
        return

    render_divider()

    # Board selection
    st.markdown("### 2. Destination Monday.com")

    # Option to create new board
    create_new_board = st.checkbox(
        "Creer un nouveau board",
        value=st.session_state.get('illustration_create_new_board', False),
        key="illustration_create_new_board_checkbox",
        help="Cochez pour creer un nouveau board au lieu d'utiliser un board existant"
    )

    selected_board_id = None
    selected_board_name = ""
    new_board_name = None

    if create_new_board:
        # New board creation
        new_board_name = st.text_input(
            "Nom du nouveau board",
            placeholder="Ex: Illustrations Assurance 2025",
            help="Le board sera cree automatiquement",
            key="illustration_new_board_name_input"
        )

        if new_board_name:
            st.info(f"📋 Un nouveau board **{new_board_name}** sera cree")
            selected_board_name = new_board_name
    else:
        # Existing board selection
        if not user_boards:
            st.warning("Aucun board disponible. Contactez votre administrateur ou creez un nouveau board.")
            return

        board_options = {b['id']: b['name'] for b in user_boards}

        selected_board_id = st.selectbox(
            "Board de destination",
            options=list(board_options.keys()),
            format_func=lambda x: board_options.get(x, x),
            key="illustration_board_select"
        )

        selected_board_name = board_options.get(selected_board_id, "")

    # Group name (optional)
    group_name = st.text_input(
        "Nom du groupe (optionnel)",
        placeholder="Ex: Novembre 2025",
        help="Les items seront crees dans ce groupe",
        key="illustration_group_name_input"
    )

    render_divider()

    # Validation
    can_proceed = True
    if create_new_board and not new_board_name:
        can_proceed = False
    elif not create_new_board and not selected_board_id:
        can_proceed = False

    # Extract button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Extraire les donnees", type="primary", width="stretch", disabled=not can_proceed):
            if not can_proceed:
                if create_new_board:
                    st.error("Veuillez entrer un nom pour le nouveau board")
                else:
                    st.error("Veuillez selectionner un board")
                return

            # Save file to temp
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getbuffer())
                pdf_path = tmp.name

            st.session_state.illustration_pdf_path = pdf_path
            st.session_state.illustration_source = source
            st.session_state.illustration_board_id = selected_board_id
            st.session_state.illustration_board_name = selected_board_name
            st.session_state.illustration_group_name = group_name if group_name else None
            st.session_state.illustration_create_new_board = create_new_board
            st.session_state.illustration_new_board_name = new_board_name

            # Extract data
            with st.spinner("Extraction en cours..."):
                try:
                    from unify_extraction import extract_and_unify, InsuranceSource

                    unify_source = InsuranceSource.UV if source == "UV" else InsuranceSource.ASSOMPTION

                    df = extract_and_unify(pdf_path, source=unify_source)

                    if df is not None and not df.empty:
                        st.session_state.illustration_data = df
                        st.session_state.illustration_stage = 2
                        st.rerun()
                    else:
                        st.error("Aucune donnee extraite du PDF")

                except Exception as e:
                    st.error(f"Erreur lors de l'extraction: {e}")


def _render_stage_preview() -> None:
    """Render stage 2: Data preview."""
    _render_stepper()

    df = st.session_state.illustration_data

    if df is None or df.empty:
        st.error("Aucune donnee disponible")
        if st.button("Recommencer"):
            _reset_illustrations_state()
            st.rerun()
        return

    # Configuration summary
    st.markdown("### Configuration")
    cols = st.columns(4)
    cols[0].metric("Source", st.session_state.illustration_source)

    board_name = st.session_state.illustration_board_name
    board_display = board_name[:15] + "..." if len(board_name) > 15 else board_name
    if st.session_state.get('illustration_create_new_board', False):
        board_display = f"🆕 {board_display}"
    cols[1].metric("Board", board_display)

    cols[2].metric("Groupe", st.session_state.illustration_group_name or "Defaut")
    cols[3].metric("Lignes", len(df))

    render_divider()

    # Data preview
    st.markdown("### Donnees extraites")

    # Show all columns
    st.dataframe(df, width="stretch", height=400)

    # Download CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Telecharger CSV",
        data=csv,
        file_name=f"extraction_{st.session_state.illustration_source}.csv",
        mime="text/csv"
    )

    render_divider()

    # Actions
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("Retour", width="stretch"):
            st.session_state.illustration_stage = 1
            st.rerun()

    with col3:
        if st.button("Uploader vers Monday", type="primary", width="stretch"):
            _execute_upload()


def _execute_upload() -> None:
    """Execute upload to Monday.com."""
    df = st.session_state.illustration_data
    api_key = st.session_state.monday_api_key
    board_id = st.session_state.illustration_board_id
    group_name = st.session_state.illustration_group_name
    create_new_board = st.session_state.get('illustration_create_new_board', False)
    new_board_name = st.session_state.get('illustration_new_board_name')

    progress = st.progress(0)
    status = st.empty()

    try:
        from monday_automation import MondayClient

        client = MondayClient(api_key=api_key)

        # Create new board if requested
        if create_new_board and new_board_name:
            status.text(f"Creation du board '{new_board_name}'...")
            progress.progress(10)

            board_result = client.create_board(
                board_name=new_board_name,
                board_kind="public"
            )

            if board_result.success and board_result.board_id:
                board_id = str(board_result.board_id)
                st.session_state.illustration_board_id = board_id
                st.session_state.illustration_board_name = new_board_name
            else:
                st.error(f"Erreur lors de la creation du board: {board_result.error}")
                return

        # Create group if specified
        status.text("Configuration du groupe...")
        progress.progress(20)

        group_id = None
        if group_name:
            group_result = client.create_group(
                board_id=int(board_id),
                group_name=group_name,
                group_color="#0086c0",
                reuse_existing=True
            )
            if group_result.success:
                group_id = group_result.group_id

        progress.progress(40)

        # Setup columns
        status.text("Configuration des colonnes...")

        column_names = [
            "insurer_name", "report_date", "advisor_name", "insured_number",
            "last_name", "first_name", "insured_name", "sex", "birth_date",
            "age", "smoker", "product_name", "coverage_amount", "policy_premium",
            "monthly_premium", "payment_duration", "details"
        ]

        numeric_cols = {"age", "coverage_amount", "policy_premium", "monthly_premium"}

        column_mapping = {}
        for col in column_names:
            if col in df.columns:
                col_type = "numbers" if col in numeric_cols else "text"
                mapping = client.get_or_create_columns(
                    board_id=int(board_id),
                    column_names=[col],
                    column_type=col_type
                )
                column_mapping.update(mapping)

        progress.progress(60)

        # Prepare items
        status.text("Preparation des items...")

        items = []
        for _, row in df.iterrows():
            insured_name = str(row.get("insured_name", "Unknown"))
            product_name = str(row.get("product_name", "Unknown"))
            item_name = f"{insured_name} - {product_name}"

            column_values = {}
            for col_name, col_value in row.items():
                if col_name == "pdf_filename":
                    continue
                if col_name not in column_mapping:
                    continue

                column_id = column_mapping[col_name]

                if pd.isna(col_value) or col_value is None or col_value == "":
                    continue

                value_str = str(col_value)
                if value_str in ["None", "nan", "NaN", "NaT"]:
                    continue

                column_values[column_id] = value_str

            item = {"name": item_name}
            if column_values:
                item["column_values"] = column_values
            items.append(item)

        progress.progress(70)

        # Upload items
        status.text(f"Upload des {len(items)} items...")

        results = client.create_items_batch(
            board_id=int(board_id),
            items=items,
            group_id=group_id
        )

        progress.progress(100)
        status.empty()

        # Analyze results
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        st.session_state.illustration_upload_results = {
            'success': successful > 0,
            'board_id': board_id,
            'group_id': group_id,
            'items_uploaded': successful,
            'items_failed': failed
        }

        st.session_state.illustration_stage = 3
        st.rerun()

    except Exception as e:
        st.error(f"Erreur lors de l'upload: {e}")


def _render_stage_upload_results() -> None:
    """Render stage 3: Upload results."""
    _render_stepper()

    results = st.session_state.illustration_upload_results

    if not results:
        st.error("Aucun resultat disponible")
        if st.button("Recommencer"):
            _reset_illustrations_state()
            st.rerun()
        return

    if results['success']:
        st.balloons()
        st.success("Upload termine avec succes!")

        cols = st.columns(3)
        cols[0].metric("Items crees", results['items_uploaded'])
        cols[1].metric("Echecs", results['items_failed'])
        cols[2].metric("Board ID", results['board_id'])

        render_divider()

        if results['items_failed'] == 0:
            st.info(f"""
            **{results['items_uploaded']}** items ont ete crees dans le board
            **{st.session_state.illustration_board_name}**
            """)
        else:
            st.warning(f"""
            {results['items_uploaded']} items crees, {results['items_failed']} echecs
            """)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Nouvelle extraction", type="primary", width="stretch"):
                _reset_illustrations_state()
                st.rerun()

        with col2:
            if results['board_id']:
                url = f"https://monday.com/boards/{results['board_id']}"
                st.link_button("Ouvrir Monday.com", url, width="stretch")
    else:
        st.error("L'upload a echoue")
        if st.button("Recommencer"):
            _reset_illustrations_state()
            st.rerun()
