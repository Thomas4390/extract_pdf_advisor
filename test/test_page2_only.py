# -*- coding: utf-8 -*-
"""
Test extraction uniquement de la page 2 (Sommaire des protections).
Focus sur les 3 packages principaux.
"""

import pdfplumber
import pandas as pd
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

PDF_DIR = Path(__file__).parent.parent / "pdf"
PDF_FILES = list(PDF_DIR.glob("*.pdf"))
PDF_PATH = PDF_FILES[0] if PDF_FILES else None


def test_tabula_page2(pdf_path: Path):
    """Test tabula sur page 2."""
    print("\n" + "=" * 70)
    print("TABULA - PAGE 2")
    print("=" * 70)

    try:
        import tabula

        # Stream mode - pour tableaux sans bordures
        print("\n--- Stream mode ---")
        tables = tabula.read_pdf(
            str(pdf_path),
            pages="2",
            stream=True,
            guess=True,
            pandas_options={"header": None},
        )

        for i, df in enumerate(tables):
            print(f"\nTableau {i + 1} ({df.shape[0]} lignes x {df.shape[1]} colonnes):")
            print(df.to_string())

        # Avec area specifiee (zone du tableau)
        print("\n--- Stream mode avec area ---")
        tables = tabula.read_pdf(
            str(pdf_path),
            pages="2",
            stream=True,
            area=[120, 30, 270, 580],  # top, left, bottom, right
            pandas_options={"header": None},
        )

        for i, df in enumerate(tables):
            print(f"\nTableau {i + 1} ({df.shape[0]} lignes x {df.shape[1]} colonnes):")
            print(df.to_string())

    except Exception as e:
        print(f"Erreur: {e}")
        import traceback

        traceback.print_exc()


def test_camelot_page2(pdf_path: Path):
    """Test camelot sur page 2."""
    print("\n" + "=" * 70)
    print("CAMELOT - PAGE 2")
    print("=" * 70)

    try:
        import camelot

        # Stream mode
        print("\n--- Stream mode ---")
        tables = camelot.read_pdf(str(pdf_path), pages="2", flavor="stream")

        print(f"Nombre de tableaux trouves: {len(tables)}")
        for i, table in enumerate(tables):
            print(f"\nTableau {i + 1} (accuracy: {table.parsing_report['accuracy']:.1f}%):")
            print(table.df.to_string())

        # Stream avec parametres ajustes
        print("\n--- Stream mode (row_tol=15) ---")
        tables = camelot.read_pdf(
            str(pdf_path), pages="2", flavor="stream", row_tol=15, edge_tol=50
        )

        for i, table in enumerate(tables):
            print(f"\nTableau {i + 1} (accuracy: {table.parsing_report['accuracy']:.1f}%):")
            print(table.df.to_string())

    except Exception as e:
        print(f"Erreur: {e}")
        import traceback

        traceback.print_exc()


def test_pdfplumber_page2(pdf_path: Path):
    """Test pdfplumber sur page 2 avec extraction manuelle."""
    print("\n" + "=" * 70)
    print("PDFPLUMBER - PAGE 2 (extraction par position)")
    print("=" * 70)

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[1]

        # Extraire mots avec positions
        words = page.extract_words()

        # Grouper par ligne (y position)
        lines = {}
        for word in words:
            y_key = round(word["top"], 0)
            if y_key not in lines:
                lines[y_key] = []
            lines[y_key].append(word)

        # Afficher les lignes pertinentes (zone du tableau)
        print("\nLignes du tableau (Y entre 120 et 260):")
        for y in sorted(lines.keys()):
            if 120 <= y <= 260:
                line_words = sorted(lines[y], key=lambda w: w["x0"])
                text = " | ".join([f"{w['text']}({w['x0']:.0f})" for w in line_words])
                print(f"Y={y:5.0f}: {text}")

        # Definir les colonnes basees sur les positions X
        # D'apres l'image: Montant d'assurance (~280-375), Prime annuelle (~400-468), Prime mensuelle (~500-576)
        print("\n--- Extraction structuree ---")

        col_boundaries = {
            "description": (0, 280),
            "montant_assurance": (280, 400),
            "prime_annuelle": (400, 510),
            "prime_mensuelle": (510, 600),
        }

        extracted_rows = []
        for y in sorted(lines.keys()):
            if 140 <= y <= 260:  # Zone des donnees
                line_words = sorted(lines[y], key=lambda w: w["x0"])
                row = {col: [] for col in col_boundaries.keys()}

                for word in line_words:
                    x = word["x0"]
                    for col, (x_min, x_max) in col_boundaries.items():
                        if x_min <= x < x_max:
                            row[col].append(word["text"])
                            break

                # Joindre les mots de chaque colonne
                row_text = {col: " ".join(words) for col, words in row.items()}
                if any(row_text.values()):
                    extracted_rows.append({"y": y, **row_text})

        df = pd.DataFrame(extracted_rows)
        print(df.to_string(index=False))


def main():
    if not PDF_PATH:
        print("Aucun fichier PDF trouve")
        return

    print(f"PDF: {PDF_PATH.name}")

    test_pdfplumber_page2(PDF_PATH)
    test_tabula_page2(PDF_PATH)
    test_camelot_page2(PDF_PATH)


if __name__ == "__main__":
    main()
