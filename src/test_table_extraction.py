# -*- coding: utf-8 -*-
"""
Script de test comparatif des packages d'extraction de tableaux PDF.
Compare: pdfplumber, camelot, tabula-py
"""

import pdfplumber
import pandas as pd
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

PDF_DIR = Path(__file__).parent.parent / "pdf"
PDF_FILES = list(PDF_DIR.glob("*.pdf"))
PDF_PATH = PDF_FILES[0] if PDF_FILES else None


def test_pdfplumber_extraction(pdf_path: Path) -> list[pd.DataFrame]:
    """Test extraction avec pdfplumber."""
    print("\n" + "=" * 60)
    print("TEST PDFPLUMBER")
    print("=" * 60)

    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # Extraire les tableaux de la page
            page_tables = page.extract_tables()

            if page_tables:
                print(f"\nPage {page_num}: {len(page_tables)} tableau(x) trouve(s)")

                for i, table in enumerate(page_tables):
                    if table:
                        df = pd.DataFrame(table[1:], columns=table[0] if table[0] else None)
                        tables.append({"page": page_num, "table_num": i + 1, "df": df})
                        print(f"\n  Tableau {i + 1}:")
                        print(df.to_string(index=False))

    return tables


def test_pdfplumber_custom(pdf_path: Path) -> list[pd.DataFrame]:
    """Test extraction pdfplumber avec parametres personnalises."""
    print("\n" + "=" * 60)
    print("TEST PDFPLUMBER (CUSTOM SETTINGS)")
    print("=" * 60)

    tables = []
    table_settings = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "snap_tolerance": 3,
        "join_tolerance": 3,
        "edge_min_length": 3,
        "min_words_vertical": 1,
        "min_words_horizontal": 1,
    }

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_tables = page.extract_tables(table_settings)

            if page_tables:
                print(f"\nPage {page_num}: {len(page_tables)} tableau(x) trouve(s)")

                for i, table in enumerate(page_tables):
                    if table and len(table) > 1:
                        df = pd.DataFrame(table[1:], columns=table[0] if table[0] else None)
                        tables.append({"page": page_num, "table_num": i + 1, "df": df})
                        print(f"\n  Tableau {i + 1}:")
                        print(df.to_string(index=False))

    return tables


def test_tabula_extraction(pdf_path: Path) -> list[pd.DataFrame]:
    """Test extraction avec tabula-py."""
    print("\n" + "=" * 60)
    print("TEST TABULA-PY")
    print("=" * 60)

    try:
        import tabula

        # Mode lattice (tableaux avec bordures)
        print("\n--- Mode Lattice ---")
        tables_lattice = tabula.read_pdf(
            str(pdf_path), pages="all", lattice=True, pandas_options={"header": None}
        )

        if tables_lattice:
            print(f"Lattice: {len(tables_lattice)} tableau(x) trouve(s)")
            for i, df in enumerate(tables_lattice):
                if not df.empty:
                    print(f"\n  Tableau {i + 1}:")
                    print(df.to_string(index=False))

        # Mode stream (tableaux sans bordures)
        print("\n--- Mode Stream ---")
        tables_stream = tabula.read_pdf(
            str(pdf_path), pages="all", stream=True, pandas_options={"header": None}
        )

        if tables_stream:
            print(f"Stream: {len(tables_stream)} tableau(x) trouve(s)")
            for i, df in enumerate(tables_stream):
                if not df.empty:
                    print(f"\n  Tableau {i + 1}:")
                    print(df.to_string(index=False))

        return tables_stream + tables_lattice

    except Exception as e:
        print(f"Erreur tabula: {e}")
        return []


def test_camelot_extraction(pdf_path: Path) -> list[pd.DataFrame]:
    """Test extraction avec camelot."""
    print("\n" + "=" * 60)
    print("TEST CAMELOT")
    print("=" * 60)

    try:
        import camelot

        # Mode lattice
        print("\n--- Mode Lattice ---")
        tables_lattice = camelot.read_pdf(str(pdf_path), pages="all", flavor="lattice")

        if tables_lattice:
            print(f"Lattice: {len(tables_lattice)} tableau(x) trouve(s)")
            for i, table in enumerate(tables_lattice):
                print(f"\n  Tableau {i + 1} (accuracy: {table.parsing_report['accuracy']:.1f}%):")
                print(table.df.to_string(index=False))

        # Mode stream
        print("\n--- Mode Stream ---")
        tables_stream = camelot.read_pdf(str(pdf_path), pages="all", flavor="stream")

        if tables_stream:
            print(f"Stream: {len(tables_stream)} tableau(x) trouve(s)")
            for i, table in enumerate(tables_stream):
                print(f"\n  Tableau {i + 1} (accuracy: {table.parsing_report['accuracy']:.1f}%):")
                print(table.df.to_string(index=False))

        return [t.df for t in tables_lattice] + [t.df for t in tables_stream]

    except Exception as e:
        print(f"Erreur camelot: {e}")
        import traceback

        traceback.print_exc()
        return []


def test_pdfplumber_page2_detailed(pdf_path: Path):
    """Extraction detaillee de la page 2 (Sommaire des protections)."""
    print("\n" + "=" * 60)
    print("ANALYSE DETAILLEE PAGE 2 - SOMMAIRE DES PROTECTIONS")
    print("=" * 60)

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[1]  # Page 2 (index 1)

        # Extraire tous les mots avec positions
        words = page.extract_words()

        # Afficher structure par ligne (grouper par y)
        lines = {}
        for word in words:
            y_key = round(word["top"], 0)
            if y_key not in lines:
                lines[y_key] = []
            lines[y_key].append(word)

        print("\nStructure par ligne:")
        for y in sorted(lines.keys()):
            line_words = sorted(lines[y], key=lambda w: w["x0"])
            text = " ".join([w["text"] for w in line_words])
            print(f"Y={y:6.1f}: {text}")

        # Tenter extraction de tableau avec differentes strategies
        print("\n--- Extraction tableau (text strategy) ---")
        tables = page.extract_tables(
            {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
            }
        )
        for i, table in enumerate(tables):
            if table:
                print(f"\nTableau {i + 1}:")
                for row in table:
                    print(row)


def main():
    if not PDF_PATH:
        print("Aucun fichier PDF trouve dans le dossier pdf/")
        return

    print(f"Fichier PDF: {PDF_PATH.name}")

    # Test 1: pdfplumber standard
    test_pdfplumber_extraction(PDF_PATH)

    # Test 2: pdfplumber custom
    test_pdfplumber_custom(PDF_PATH)

    # Test 3: Analyse detaillee page 2
    test_pdfplumber_page2_detailed(PDF_PATH)

    # Test 4: tabula-py
    test_tabula_extraction(PDF_PATH)

    # Test 5: camelot
    test_camelot_extraction(PDF_PATH)


if __name__ == "__main__":
    main()
