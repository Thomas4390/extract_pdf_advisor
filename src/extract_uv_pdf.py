# -*- coding: utf-8 -*-
"""
UV Insurance PDF Extraction Script
===================================

This script extracts insurance protection summary information from UV insurance
illustration PDFs ("SOMMAIRE DES PROTECTIONS ET DES PRIMES").

ARCHITECTURE OVERVIEW
---------------------
The extraction uses a position-based approach with pdfplumber:

1. FIND SUMMARY PAGE
   - Scan all pages looking for "SOMMAIRE DES PROTECTIONS ET DES PRIMES"

2. EXTRACT WORDS WITH POSITIONS
   - Get all words with their (x0, y0, x1, y1) bounding boxes

3. GROUP BY LINES
   - Words with similar Y positions are grouped into lines
   - Tolerance of 3px to handle slight vertical misalignments

4. CLASSIFY BY COLUMNS
   - Column boundaries based on observed X positions:
     * Description: X < 280
     * Insurance Amount: 280 <= X < 400
     * Annual Premium: 400 <= X < 510
     * Monthly Premium: X >= 510

5. PARSE EACH LINE
   - Insured info: detected by date pattern (YYYY-MM-DD)
   - Protection: must have NUMERIC amount in insurance_amount column
   - Prime totale: marks end of extraction
   - Multi-line names: continuation lines are merged

VALIDATION RULES
----------------
A protection row is ONLY included if:
1. It has a numeric insurance amount (e.g., "50 000 $", "1 000 $")
   - "Voir la description" is NOT numeric -> excluded
   - "Incluse" is NOT numeric -> excluded
2. OR it has a numeric annual premium (e.g., "556,50 $")
   - "Incluse" is NOT numeric -> excluded

This ensures rows like "Indemnité pour perte d'autonomie sévère" with
"Voir la description" and "Incluse" are properly excluded.

TESTED PACKAGES COMPARISON
--------------------------
- pdfplumber: Good for position-based extraction, flexible (CHOSEN)
- tabula-py: Works but sometimes merges columns incorrectly
- camelot: Best accuracy (97.6%) but requires ghostscript dependency

OUTPUT FORMAT
-------------
DataFrame with columns:
- last_name, first_name, sex, birth_date, age, smoker (insured info)
- protection_name, insurance_amount, annual_premium, monthly_premium, details
- DataFrame.attrs contains total_annual_premium and total_monthly_premium
"""

import re
import warnings
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pdfplumber

warnings.filterwarnings("ignore")


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class InsuredInfo:
    """Information about the insured person."""

    last_name: str
    first_name: str
    sex: str  # "Homme" or "Femme"
    birth_date: str  # Format: YYYY-MM-DD
    age: int
    smoker: bool


@dataclass
class ProtectionInfo:
    """Information about an insurance protection."""

    protection_name: str
    insurance_amount: str  # e.g., "50 000 $"
    annual_premium: str  # e.g., "556,50 $"
    monthly_premium: str  # e.g., "50,09 $"
    details: str = ""  # e.g., "(Primes payables jusqu'à 46 ans)"


@dataclass
class SummaryExtraction:
    """Complete extraction result from the summary page."""

    document_date: str
    advisor_name: str
    insured: InsuredInfo
    protections: list[ProtectionInfo]
    total_annual_premium: str
    total_monthly_premium: str


# =============================================================================
# COLUMN BOUNDARIES (based on observed PDF structure)
# =============================================================================

# These values are calibrated for UV insurance PDFs
# Adjust if PDF layout changes
COLUMN_BOUNDARIES = {
    "description": (0, 280),
    "insurance_amount": (280, 400),
    "annual_premium": (400, 510),
    "monthly_premium": (510, 600),
}


# =============================================================================
# PARSING FUNCTIONS
# =============================================================================


def extract_document_date(pdf: pdfplumber.PDF) -> str | None:
    """
    Extract the document date from the PDF.

    Looks for "Date:" followed by the date string (e.g., "17 novembre 2025").

    Args:
        pdf: pdfplumber PDF object

    Returns:
        Date string or None if not found
    """
    for page in pdf.pages:
        text = page.extract_text() or ""

        # Pattern: "Date: 17 novembre 2025" or similar
        match = re.search(r"Date\s*:\s*(.+?)(?:\n|$)", text)
        if match:
            return match.group(1).strip()

    return None


def extract_advisor_name(pdf: pdfplumber.PDF) -> str | None:
    """
    Extract the advisor name from the PDF.

    Looks for "Votre conseiller :" followed by the advisor name.

    Args:
        pdf: pdfplumber PDF object

    Returns:
        Advisor name or None if not found
    """
    for page in pdf.pages:
        text = page.extract_text() or ""

        # Pattern: "Votre conseiller : NAME"
        match = re.search(r"Votre conseiller\s*:\s*(.+?)(?:\n|$)", text)
        if match:
            return match.group(1).strip()

    return None


def parse_insured_line(text: str) -> InsuredInfo | None:
    """
    Parse the insured person information line.

    Expected format:
        "THOMAS JEAN VAUDESCAL, Homme, 1999-11-30, 26 an(s), non-fumeur"

    Args:
        text: The text line containing insured information

    Returns:
        InsuredInfo object or None if parsing fails
    """
    pattern = (
        r"^([A-ZÉÈÊËÀÂÄÙÛÜÔÖÎÏÇ\s-]+),\s*(Homme|Femme),\s*"
        r"(\d{4}-\d{2}-\d{2}),\s*(\d+)\s*an\(s\),\s*(non-fumeur|fumeur)"
    )

    match = re.match(pattern, text.strip())
    if not match:
        return None

    full_name = match.group(1).strip()
    parts = full_name.split()

    # Convention: last word is family name, rest is first name
    if len(parts) >= 2:
        last_name = parts[-1]
        first_name = " ".join(parts[:-1])
    else:
        last_name = full_name
        first_name = ""

    return InsuredInfo(
        last_name=last_name,
        first_name=first_name,
        sex=match.group(2),
        birth_date=match.group(3),
        age=int(match.group(4)),
        smoker=match.group(5) == "fumeur",
    )


def is_numeric_amount(value: str) -> bool:
    """
    Check if a value represents a numeric amount.

    Valid examples: "50 000 $", "1000$", "556,50 $", "12,87$"
    Invalid examples: "Voir la description", "Incluse", "", None

    Args:
        value: The string to check

    Returns:
        True if the value contains a numeric amount
    """
    if not value:
        return False

    # Remove spaces, $, and common formatting
    cleaned = value.replace(" ", "").replace("$", "").replace(",", ".").strip()

    # Check if it starts with a digit (handles decimals like "556.50")
    if not cleaned:
        return False

    # Must start with digit and be a valid number
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def normalize_amount(amount: str) -> str:
    """
    Normalize amount string for consistent formatting.

    Transformations:
    - "50000$" -> "50 000 $"
    - "Voirladescription" -> "Voir la description"

    Args:
        amount: Raw amount string from PDF

    Returns:
        Normalized amount string
    """
    if not amount:
        return ""

    # Remove extra spaces within the amount
    cleaned = amount.replace(" ", "").strip()

    # Fix known concatenation issues
    if cleaned == "Voirladescription":
        return "Voir la description"

    # Format numeric amounts with thousand separators
    if cleaned.endswith("$"):
        num_part = cleaned[:-1]
        if num_part.isdigit():
            formatted = "{:,}".format(int(num_part)).replace(",", " ")
            return f"{formatted} $"

    return amount.strip()


# =============================================================================
# LINE PROCESSING FUNCTIONS
# =============================================================================


def group_words_by_line(
    words: list[dict], tolerance: float = 3.0
) -> dict[float, list[dict]]:
    """
    Group words by their Y position to reconstruct lines.

    Words within `tolerance` pixels of each other vertically are
    considered to be on the same line.

    Args:
        words: List of word dictionaries from pdfplumber
        tolerance: Maximum Y difference to consider same line

    Returns:
        Dictionary mapping Y position to list of words on that line
    """
    lines: dict[float, list[dict]] = {}

    for word in words:
        y_key = round(word["top"], 0)

        # Find existing line within tolerance
        matched_y = None
        for existing_y in lines.keys():
            if abs(existing_y - y_key) <= tolerance:
                matched_y = existing_y
                break

        if matched_y is not None:
            lines[matched_y].append(word)
        else:
            lines[y_key] = [word]

    return lines


def extract_row_by_columns(
    line_words: list[dict],
    col_boundaries: dict[str, tuple[float, float]] = COLUMN_BOUNDARIES,
) -> dict[str, str]:
    """
    Extract text from a line based on column X boundaries.

    Args:
        line_words: List of words in the line (sorted by x0)
        col_boundaries: Dictionary mapping column names to (x_min, x_max)

    Returns:
        Dictionary mapping column names to extracted text
    """
    row: dict[str, list[str]] = {col: [] for col in col_boundaries.keys()}

    for word in line_words:
        x = word["x0"]
        for col, (x_min, x_max) in col_boundaries.items():
            if x_min <= x < x_max:
                row[col].append(word["text"])
                break

    return {col: " ".join(words_list) for col, words_list in row.items()}


# =============================================================================
# MAIN EXTRACTION FUNCTION
# =============================================================================


def extract_summary_with_pdfplumber(pdf_path: Path) -> SummaryExtraction | None:
    """
    Extract the protection summary from a UV insurance PDF.

    This function:
    1. Finds the page containing "SOMMAIRE DES PROTECTIONS ET DES PRIMES"
    2. Extracts all words with their positions
    3. Groups words into lines and classifies by columns
    4. Parses insured info, protections, and totals

    Validation Rules:
    - Protection rows MUST have numeric insurance_amount OR numeric annual_premium
    - "Voir la description", "Incluse" are NOT considered numeric
    - Multi-line protection names are merged

    Args:
        pdf_path: Path to the PDF file

    Returns:
        SummaryExtraction object or None if extraction fails
    """
    with pdfplumber.open(pdf_path) as pdf:
        # Step 1: Extract document date and advisor name
        document_date = extract_document_date(pdf) or ""
        advisor_name = extract_advisor_name(pdf) or ""

        # Step 2: Find the summary page
        summary_page = None
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "SOMMAIRE DES PROTECTIONS ET DES PRIMES" in text:
                summary_page = page
                break

        if not summary_page:
            print(f"Warning: 'SOMMAIRE DES PROTECTIONS' page not found in {pdf_path.name}")
            return None

        # Step 3: Extract words and group by lines
        words = summary_page.extract_words()
        lines = group_words_by_line(words)

        # Step 4: Process each line
        insured_info: InsuredInfo | None = None
        protections: list[ProtectionInfo] = []
        total_annual_premium = ""
        total_monthly_premium = ""
        current_protection: ProtectionInfo | None = None
        extraction_complete = False

        for y in sorted(lines.keys()):
            if extraction_complete:
                break

            line_words = sorted(lines[y], key=lambda w: w["x0"])
            full_line = " ".join([w["text"] for w in line_words])
            row_text = extract_row_by_columns(line_words)

            # --- Parse insured info (detected by date pattern) ---
            if not insured_info and re.search(r"\d{4}-\d{2}-\d{2}", full_line):
                insured_info = parse_insured_line(full_line)
                continue

            # --- Parse "Prime totale" (marks end of extraction) ---
            if "Prime totale" in row_text["description"]:
                total_annual_premium = row_text["annual_premium"].strip()
                total_monthly_premium = row_text["monthly_premium"].strip()
                extraction_complete = True
                continue

            # --- Skip non-relevant lines ---
            desc = row_text["description"].strip()
            if not desc:
                continue
            if desc == "Assurance individuelle":
                continue
            if "SOMMAIRE" in desc:
                continue

            # --- Handle detail lines (e.g., "(Primes payables jusqu'à 46 ans)") ---
            if desc.startswith("(") and current_protection:
                current_protection.details = desc
                continue

            # --- Parse protection lines ---
            amount_raw = row_text["insurance_amount"]
            annual_raw = row_text["annual_premium"]
            monthly_raw = row_text["monthly_premium"]

            amount = normalize_amount(amount_raw)
            annual = annual_raw.strip()
            monthly = monthly_raw.strip()

            # VALIDATION: Must have NUMERIC amount OR NUMERIC annual premium
            has_numeric_amount = is_numeric_amount(amount)
            has_numeric_premium = is_numeric_amount(annual)

            if has_numeric_amount or has_numeric_premium:
                # This is a valid protection row
                current_protection = ProtectionInfo(
                    protection_name=desc,
                    insurance_amount=amount,
                    annual_premium=annual,
                    monthly_premium=monthly,
                )
                protections.append(current_protection)

            elif current_protection and desc and not desc.startswith("("):
                # This might be a continuation of the previous protection name
                # (multi-line protection names like "Avenant Assurance dette...")
                if not amount_raw and not annual_raw:
                    current_protection.protection_name += " " + desc

        if not insured_info:
            print(f"Warning: Could not parse insured info from {pdf_path.name}")
            return None

        return SummaryExtraction(
            document_date=document_date,
            advisor_name=advisor_name,
            insured=insured_info,
            protections=protections,
            total_annual_premium=total_annual_premium,
            total_monthly_premium=total_monthly_premium,
        )


# =============================================================================
# DATAFRAME CONVERSION
# =============================================================================


def summary_to_dataframe(extraction: SummaryExtraction) -> pd.DataFrame:
    """
    Convert extraction result to a pandas DataFrame.

    Creates one row per protection with insured info repeated.
    Totals are stored in DataFrame.attrs.

    Args:
        extraction: SummaryExtraction object

    Returns:
        DataFrame with columns:
        - advisor_name
        - last_name, first_name, sex, birth_date, age, smoker
        - protection_name, insurance_amount, annual_premium, monthly_premium, details
    """
    rows = []

    for prot in extraction.protections:
        row = {
            "document_date": extraction.document_date,
            "advisor_name": extraction.advisor_name,
            "last_name": extraction.insured.last_name,
            "first_name": extraction.insured.first_name,
            "sex": extraction.insured.sex,
            "birth_date": extraction.insured.birth_date,
            "age": extraction.insured.age,
            "smoker": extraction.insured.smoker,
            "protection_name": prot.protection_name,
            "insurance_amount": prot.insurance_amount,
            "annual_premium": prot.annual_premium,
            "monthly_premium": prot.monthly_premium,
            "details": prot.details,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Store totals as DataFrame attributes
    df.attrs["total_annual_premium"] = extraction.total_annual_premium
    df.attrs["total_monthly_premium"] = extraction.total_monthly_premium

    return df


# =============================================================================
# PUBLIC API
# =============================================================================


def extract_to_dataframe(pdf_path: str | Path) -> pd.DataFrame:
    """
    Main function: extract summary from PDF and return DataFrame.

    This is the primary entry point for using this module.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        DataFrame with columns:
        - last_name, first_name, sex, birth_date, age, smoker
        - protection_name, insurance_amount, annual_premium, monthly_premium, details

        DataFrame.attrs contains:
        - total_annual_premium
        - total_monthly_premium

    Raises:
        ValueError: If extraction fails

    Example::

        df = extract_to_dataframe("insurance.pdf")
        print(df[["protection_name", "insurance_amount", "annual_premium"]])
        print(f"Total: {df.attrs['total_annual_premium']}")
    """
    pdf_path = Path(pdf_path)

    extraction = extract_summary_with_pdfplumber(pdf_path)

    if not extraction:
        raise ValueError(f"Unable to extract summary from PDF: {pdf_path}")

    return summary_to_dataframe(extraction)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main():
    """Main entry point for testing."""
    pdf_dir = Path(__file__).parent.parent / "pdf" / "uv"
    pdf_files = sorted(pdf_dir.glob("*.pdf"))  # All PDFs in uv folder

    if not pdf_files:
        print("No UV PDF files found in pdf/uv/ folder")
        return

    for pdf_path in pdf_files:
        print(f"\n{'='*70}")
        print(f"PDF: {pdf_path.name}")
        print("=" * 70)

        extraction = extract_summary_with_pdfplumber(pdf_path)

        if not extraction:
            print("  -> Extraction failed")
            continue

        print(f"\nDocument date: {extraction.document_date}")
        print(f"Advisor: {extraction.advisor_name}")
        print(f"\nInsured: {extraction.insured.first_name} {extraction.insured.last_name}")
        print(f"  Sex: {extraction.insured.sex}")
        print(f"  Birth date: {extraction.insured.birth_date}")
        print(f"  Age: {extraction.insured.age} years")
        print(f"  Smoker: {'Yes' if extraction.insured.smoker else 'No'}")

        print(f"\nProtections ({len(extraction.protections)}):")
        for i, prot in enumerate(extraction.protections, 1):
            print(f"  {i}. {prot.protection_name}")
            print(f"     Amount: {prot.insurance_amount}")
            print(f"     Annual: {prot.annual_premium} | Monthly: {prot.monthly_premium}")
            if prot.details:
                print(f"     Details: {prot.details}")

        print(f"\nTotals:")
        print(f"  Annual:  {extraction.total_annual_premium}")
        print(f"  Monthly: {extraction.total_monthly_premium}")

        # Show DataFrame
        print("\n--- DataFrame ---")
        df = summary_to_dataframe(extraction)
        # Select key columns for display
        display_cols = ["protection_name", "insurance_amount", "annual_premium", "monthly_premium"]
        print(df[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
