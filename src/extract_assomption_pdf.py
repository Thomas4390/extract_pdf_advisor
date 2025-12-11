# -*- coding: utf-8 -*-
"""
Assomption Insurance PDF Extraction Script
==========================================

This script extracts insurance guarantee summary information from Assomption
insurance illustration PDFs ("Sommaire des garanties").

ARCHITECTURE OVERVIEW
---------------------
The extraction uses a position-based approach with pdfplumber:

1. FIND SUMMARY PAGE
   - Scan all pages looking for "Sommaire des garanties" with "Personne a assurer"

2. EXTRACT WORDS WITH POSITIONS
   - Get all words with their (x0, y0, x1, y1) bounding boxes

3. GROUP BY LINES
   - Words with similar Y positions are grouped into lines
   - Tolerance of 3px to handle slight vertical misalignments

4. CLASSIFY BY COLUMNS
   - Column boundaries based on observed X positions:
     * Description: X < 350
     * Capital assure: 350 <= X < 420
     * Duree de paiement: 420 <= X < 520
     * Prime annuelle: X >= 520

5. PARSE EACH LINE
   - Insured info: detected by pattern "N - Name, age N, Homme/Femme, ..."
   - Guarantee: must have NUMERIC capital or premium
   - "Sommaire" or "Prime annuelle totale": marks end of table

EXTRACTED DATA
--------------
- Advisor name (from "Votre conseiller :" line)
- Insured info: name, age, sex, smoker status
- Guarantees: protection name, capital assure, duree, prime annuelle
- Totals: prime annuelle totale, intervalle de paiement, prime mensuelle

OUTPUT FORMAT
-------------
DataFrame with columns:
- advisor_name (advisor information)
- last_name, first_name, sex, age, smoker (insured info)
- protection_name, capital_assure, duree_paiement, prime_annuelle (guarantees)
- DataFrame.attrs contains total_annual_premium, total_monthly_premium, payment_interval
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

    number: str  # e.g., "1"
    last_name: str
    first_name: str
    sex: str  # "Homme" or "Femme"
    age: int
    smoker: bool


@dataclass
class GuaranteeInfo:
    """Information about an insurance guarantee."""

    protection_name: str
    capital_assure: str  # e.g., "25 000,00 $"
    duree_paiement: str  # e.g., "74 ans"
    prime_annuelle: str  # e.g., "325,25 $"


@dataclass
class SummaryExtraction:
    """Complete extraction result from the summary page."""

    document_date: str
    advisor_name: str
    insured_persons: list[InsuredInfo]  # Changed from single insured to list
    guarantees: list[GuaranteeInfo]
    total_annual_premium: str
    total_monthly_premium: str
    payment_interval: str


# =============================================================================
# COLUMN BOUNDARIES (based on observed PDF structure)
# =============================================================================

# These values are calibrated for Assomption insurance PDFs
# Adjust if PDF layout changes
COLUMN_BOUNDARIES = {
    "description": (0, 350),
    "capital_assure": (350, 420),
    "duree_paiement": (420, 520),
    "prime_annuelle": (520, 600),
}


# =============================================================================
# PARSING FUNCTIONS
# =============================================================================


def extract_document_date(pdf: pdfplumber.PDF) -> str | None:
    """
    Extract the document date from the PDF.

    For Assomption PDFs, the date is typically the first line of the page
    (e.g., "lundi 17 novembre 2025").

    Args:
        pdf: pdfplumber PDF object

    Returns:
        Date string or None if not found
    """
    for page in pdf.pages:
        text = page.extract_text() or ""
        if not text:
            continue

        # Get first line of the page
        first_line = text.strip().split("\n")[0].strip()

        # Check if first line looks like a date (contains month name in French)
        french_months = [
            "janvier", "fevrier", "février", "mars", "avril", "mai", "juin",
            "juillet", "aout", "août", "septembre", "octobre", "novembre", "decembre", "décembre"
        ]

        first_line_lower = first_line.lower()
        for month in french_months:
            if month in first_line_lower:
                return first_line

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
        match = re.search(r"Votre conseiller\s*:\s*(.+?)(?:\n|Telephone|$)", text)
        if match:
            return match.group(1).strip()

    return None


def parse_single_insured(match: re.Match) -> InsuredInfo:
    """
    Parse a single insured person from a regex match.

    Args:
        match: Regex match object with groups (number, name, age, sex, smoker_status)

    Returns:
        InsuredInfo object
    """
    number = match.group(1)
    full_name = match.group(2).strip()
    age = int(match.group(3))
    sex = match.group(4)
    smoker_status = match.group(5)

    # Parse name: convention is last word is family name
    name_parts = full_name.split()
    if len(name_parts) >= 2:
        last_name = name_parts[-1]
        first_name = " ".join(name_parts[:-1])
    else:
        last_name = full_name
        first_name = ""

    # Determine smoker status
    is_smoker = "fumeur" in smoker_status.lower() and "non" not in smoker_status.lower()

    return InsuredInfo(
        number=number,
        last_name=last_name,
        first_name=first_name,
        sex=sex,
        age=age,
        smoker=is_smoker,
    )


def parse_all_insured_persons(text: str) -> list[InsuredInfo]:
    """
    Parse all insured persons from the text.

    Expected format (can have multiple persons):
        "1 - Thomas Jean Vaudescal, age 26, Homme , Non-fumeur"
        "2 - Yasmine Vaudescal, age 26, Femme , Non-fumeur"

    Args:
        text: The text containing insured information

    Returns:
        List of InsuredInfo objects (empty if none found)
    """
    # Handle various dash types (regular dash, en-dash, em-dash, special unicode dash)
    pattern = (
        r"(\d+)\s*[\u2010-\u2015\-]\s*([^,]+),\s*[aA\u00e2]ge\s*(\d+),\s*(Homme|Femme)\s*,\s*"
        r"(Non[\u2010-\u2015\-]fumeur|Fumeur|Non-fumeur)"
    )

    matches = re.finditer(pattern, text)
    insured_persons = []

    for match in matches:
        insured = parse_single_insured(match)
        insured_persons.append(insured)

    return insured_persons


def parse_insured_line(text: str) -> InsuredInfo | None:
    """
    Parse the first insured person information line.

    DEPRECATED: Use parse_all_insured_persons() for multiple persons support.

    Expected format:
        "1 - Thomas Jean Vaudescal, age 26, Homme , Non-fumeur"

    Args:
        text: The text containing insured information

    Returns:
        InsuredInfo object or None if parsing fails
    """
    persons = parse_all_insured_persons(text)
    return persons[0] if persons else None


def is_numeric_amount(value: str) -> bool:
    """
    Check if a value represents a numeric amount.

    Valid examples: "50 000 $", "1000$", "556,50 $", "12,87$"
    Invalid examples: "", None, "ans"

    Args:
        value: The string to check

    Returns:
        True if the value contains a numeric amount with "$"
    """
    if not value:
        return False

    # Must contain $ and at least one digit
    return "$" in value and bool(re.search(r"\d", value))


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
    col_boundaries: dict[str, tuple[float, float]] | None = None,
) -> dict[str, str]:
    """
    Extract text from a line based on column X boundaries.

    Args:
        line_words: List of words in the line (sorted by x0)
        col_boundaries: Dictionary mapping column names to (x_min, x_max)

    Returns:
        Dictionary mapping column names to extracted text
    """
    if col_boundaries is None:
        col_boundaries = COLUMN_BOUNDARIES

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
    Extract the guarantee summary from an Assomption insurance PDF.

    This function:
    1. Finds the page containing "Sommaire des garanties" with "Personne a assurer"
    2. Extracts advisor name from "Votre conseiller :"
    3. Extracts insured info from "N - Name, age N, ..."
    4. Extracts guarantees from the table
    5. Extracts totals (prime annuelle totale, prime mensuelle)

    Args:
        pdf_path: Path to the PDF file

    Returns:
        SummaryExtraction object or None if extraction fails
    """
    with pdfplumber.open(pdf_path) as pdf:
        # Step 1: Extract document date and advisor name
        document_date = extract_document_date(pdf) or ""
        advisor_name = extract_advisor_name(pdf) or ""

        # Step 2: Find the summary page with the table
        summary_page = None
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "Sommaire des garanties" in text and "Personne" in text and "assurer" in text:
                summary_page = page
                break

        if not summary_page:
            print(f"Warning: 'Sommaire des garanties' page not found in {pdf_path.name}")
            return None

        text = summary_page.extract_text() or ""

        # Step 3: Extract all insured persons
        insured_persons = parse_all_insured_persons(text)
        if not insured_persons:
            print(f"Warning: Could not parse insured info from {pdf_path.name}")
            return None

        # Step 4: Extract words and group by lines
        words = summary_page.extract_words()
        lines = group_words_by_line(words)

        # Step 5: Process each line for guarantees and totals
        guarantees: list[GuaranteeInfo] = []
        total_annual_premium = ""
        total_monthly_premium = ""
        payment_interval = ""

        in_table = False

        for y in sorted(lines.keys()):
            line_words = sorted(lines[y], key=lambda w: w["x0"])
            full_line = " ".join([w["text"] for w in line_words])

            # Start table after "Police ..." line (e.g., "Police Vie Entiere...", "Police Protection Bronze")
            if full_line.strip().startswith("Police ") and not in_table:
                in_table = True
                continue

            # Extract totals
            if "Prime annuelle totale" in full_line:
                match = re.search(r"(\d[\d\s,]*\d?\s*\$)", full_line)
                if match:
                    total_annual_premium = match.group(1).strip()
                continue

            if full_line.strip().startswith("Prime totale"):
                match = re.search(r"(\d[\d\s,]*\d?\s*\$)", full_line)
                if match:
                    total_monthly_premium = match.group(1).strip()
                continue

            if "Intervalle de paiement" in full_line:
                match = re.search(r"Intervalle de paiement\s+(\w+)", full_line)
                if match:
                    payment_interval = match.group(1).strip()
                continue

            if not in_table:
                continue

            # Skip header lines
            if any(h in full_line for h in [
                "Assurance demandee", "Capital assure", "des primes", "initiale",
                "Assurance demandée", "Capital assuré"
            ]):
                continue
            if full_line.strip().startswith("sur "):
                continue

            # End at "Sommaire"
            if full_line.strip() == "Sommaire":
                in_table = False
                continue

            # Extract row data
            row = extract_row_by_columns(line_words)
            desc = row["description"].strip()
            capital = row["capital_assure"].strip()
            duree = row["duree_paiement"].strip()
            prime = row["prime_annuelle"].strip()

            # Check if this is a data row (has numeric values)
            has_capital = is_numeric_amount(capital)
            has_prime = is_numeric_amount(prime)

            if desc and (has_capital or has_prime):
                guarantees.append(GuaranteeInfo(
                    protection_name=desc,
                    capital_assure=capital,
                    duree_paiement=duree,
                    prime_annuelle=prime,
                ))

        return SummaryExtraction(
            document_date=document_date,
            advisor_name=advisor_name,
            insured_persons=insured_persons,
            guarantees=guarantees,
            total_annual_premium=total_annual_premium,
            total_monthly_premium=total_monthly_premium,
            payment_interval=payment_interval,
        )


# =============================================================================
# DATAFRAME CONVERSION
# =============================================================================


def summary_to_dataframe(extraction: SummaryExtraction) -> pd.DataFrame:
    """
    Convert extraction result to a pandas DataFrame.

    Creates one row per guarantee with insured info and advisor repeated.
    All insured persons are included in a separate structure.
    Totals are stored in DataFrame.attrs.

    Args:
        extraction: SummaryExtraction object

    Returns:
        DataFrame with columns:
        - advisor_name
        - insured_number, last_name, first_name, sex, age, smoker (for primary insured)
        - protection_name, capital_assure, duree_paiement, prime_annuelle
    """
    rows = []

    # Use primary insured (first person) for each guarantee row
    primary_insured = extraction.insured_persons[0] if extraction.insured_persons else None

    for guarantee in extraction.guarantees:
        row = {
            "document_date": extraction.document_date,
            "advisor_name": extraction.advisor_name,
            "insured_number": primary_insured.number if primary_insured else "",
            "last_name": primary_insured.last_name if primary_insured else "",
            "first_name": primary_insured.first_name if primary_insured else "",
            "sex": primary_insured.sex if primary_insured else "",
            "age": primary_insured.age if primary_insured else 0,
            "smoker": primary_insured.smoker if primary_insured else False,
            "protection_name": guarantee.protection_name,
            "capital_assure": guarantee.capital_assure,
            "duree_paiement": guarantee.duree_paiement,
            "prime_annuelle": guarantee.prime_annuelle,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Store totals as DataFrame attributes
    df.attrs["total_annual_premium"] = extraction.total_annual_premium
    df.attrs["total_monthly_premium"] = extraction.total_monthly_premium
    df.attrs["payment_interval"] = extraction.payment_interval

    # Store all insured persons as DataFrame attribute
    df.attrs["insured_persons"] = [
        {
            "number": p.number,
            "last_name": p.last_name,
            "first_name": p.first_name,
            "sex": p.sex,
            "age": p.age,
            "smoker": p.smoker,
        }
        for p in extraction.insured_persons
    ]

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
        - advisor_name
        - last_name, first_name, sex, age, smoker
        - protection_name, capital_assure, duree_paiement, prime_annuelle

        DataFrame.attrs contains:
        - total_annual_premium
        - total_monthly_premium
        - payment_interval

    Raises:
        ValueError: If extraction fails

    Example::

        df = extract_to_dataframe("assomption.pdf")
        print(df[["protection_name", "capital_assure", "prime_annuelle"]])
        print(f"Total annual: {df.attrs['total_annual_premium']}")
        print(f"Advisor: {df['advisor_name'].iloc[0]}")
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
    pdf_dir = Path(__file__).parent.parent / "pdf" / "assomption"

    # Test with Assomption PDFs
    pdf_files = sorted(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in pdf/assomption/ folder")
        return

    for pdf_path in pdf_files:
        print(f"\n{'='*70}")
        print(f"PDF: {pdf_path.name}")
        print("=" * 70)

        try:
            extraction = extract_summary_with_pdfplumber(pdf_path)
        except Exception as e:
            print(f"  -> Error: {e}")
            continue

        if not extraction:
            print("  -> Extraction failed (no summary page found)")
            continue

        print(f"\nDocument date: {extraction.document_date}")
        print(f"Advisor: {extraction.advisor_name}")

        print(f"\nInsured Persons ({len(extraction.insured_persons)}):")
        for person in extraction.insured_persons:
            smoker_str = "Yes" if person.smoker else "No"
            print(f"  {person.number}. {person.first_name} {person.last_name}")
            print(f"     Sex: {person.sex}, Age: {person.age} years, Smoker: {smoker_str}")

        print(f"\nGuarantees ({len(extraction.guarantees)}):")
        for i, g in enumerate(extraction.guarantees, 1):
            print(f"  {i}. {g.protection_name}")
            print(f"     Capital: {g.capital_assure}")
            print(f"     Duree: {g.duree_paiement}")
            print(f"     Prime annuelle: {g.prime_annuelle}")

        print(f"\nTotals:")
        print(f"  Annual premium:  {extraction.total_annual_premium}")
        print(f"  Monthly premium: {extraction.total_monthly_premium}")
        print(f"  Payment interval: {extraction.payment_interval}")

        # Show DataFrame
        print("\n--- DataFrame ---")
        df = summary_to_dataframe(extraction)
        if not df.empty:
            display_cols = ["protection_name", "capital_assure", "prime_annuelle"]
            print(df[display_cols].to_string(index=False))
        else:
            print("(No guarantees extracted)")


if __name__ == "__main__":
    main()
