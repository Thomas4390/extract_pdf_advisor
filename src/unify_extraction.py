# -*- coding: utf-8 -*-
"""
Insurance PDF Data Unification Script
=====================================

This script unifies insurance illustration data from multiple sources (UV and Assomption)
into a standardized DataFrame format for consistent analysis and reporting.

ARCHITECTURE OVERVIEW
---------------------
The unification follows a clean architecture pattern:

1. SOURCE EXTRACTION
   - Import data from source-specific extractors (extract_uv_pdf, extract_assomption_pdf)
   - Each extractor returns its native format

2. SCHEMA MAPPING
   - Map source-specific columns to unified schema
   - Handle missing fields with sensible defaults
   - Normalize data types and formats

3. DATA CLEANING
   - Parse currency values to float
   - Standardize date formats
   - Clean and normalize text fields

4. UNIFIED OUTPUT
   - Single DataFrame with consistent columns
   - Source identification for traceability
   - Metadata preserved in DataFrame.attrs

UNIFIED SCHEMA
--------------
Document Info:
    - insurer_name: str ("UV" | "Assomption") - source of data
    - report_date: str - document date
    - advisor_name: str
    - pdf_filename: str

Insured Info:
    - insured_number: str (person number, "1" for single person)
    - last_name: str
    - first_name: str
    - insured_name: str (computed: first_name + last_name)
    - sex: str ("Homme" | "Femme")
    - birth_date: str | None (UV only, format: YYYY-MM-DD)
    - age: int
    - smoker: bool

Protection Info:
    - product_name: str - protection/guarantee name
    - coverage_amount: float | None (insurance/capital amount)
    - policy_premium: float | None (annual premium)
    - monthly_premium: float | None
    - payment_duration: str | None (Assomption only)
    - details: str | None (UV only)

Totals (in DataFrame.attrs):
    - total_annual_premium: float
    - total_monthly_premium: float
    - payment_interval: str | None (Assomption only)

Author: Claude
Date: 2025-12-11
Version: 1.0.0
"""

import re
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd

# Import source extractors
from extract_uv_pdf import extract_summary_with_pdfplumber as extract_uv
from extract_assomption_pdf import extract_summary_with_pdfplumber as extract_assomption

warnings.filterwarnings("ignore")


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================


class InsuranceSource(Enum):
    """Supported insurance data sources."""

    UV = "UV"
    ASSOMPTION = "Assomption"


# Unified column order for output DataFrame
UNIFIED_COLUMNS = [
    # Document info
    "insurer_name",
    "report_date",
    "advisor_name",
    "pdf_filename",
    # Insured info
    "insured_number",
    "last_name",
    "first_name",
    "insured_name",
    "sex",
    "birth_date",
    "age",
    "smoker",
    # Protection info
    "product_name",
    "coverage_amount",
    "policy_premium",
    "monthly_premium",
    "payment_duration",
    "details",
]


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class UnifiedInsured:
    """Unified insured person information."""

    insured_number: str
    last_name: str
    first_name: str
    sex: str
    age: int
    smoker: bool
    birth_date: Optional[str] = None

    @property
    def insured_name(self) -> str:
        """Return full name as 'first_name last_name'."""
        return f"{self.first_name} {self.last_name}".strip()


@dataclass
class UnifiedProtection:
    """Unified protection/guarantee information."""

    product_name: str
    coverage_amount: Optional[float] = None
    policy_premium: Optional[float] = None  # Annual premium
    monthly_premium: Optional[float] = None
    payment_duration: Optional[str] = None
    details: Optional[str] = None


@dataclass
class UnifiedExtraction:
    """Unified extraction result from any source."""

    source: InsuranceSource
    document_date: str
    advisor_name: str
    pdf_filename: str
    insured_persons: list[UnifiedInsured]
    protections: list[UnifiedProtection]
    total_annual_premium: Optional[float] = None
    total_monthly_premium: Optional[float] = None
    payment_interval: Optional[str] = None


# =============================================================================
# DATE PARSING UTILITIES
# =============================================================================

# French month names for parsing
FRENCH_MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}

# French day names to strip
FRENCH_DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def parse_french_date(date_str: str | None) -> Optional[str]:
    """
    Parse a French date string and return YYYY-MM-DD format.

    Handles formats:
        - "17 novembre 2025" -> "2025-11-17"
        - "lundi 17 novembre 2025" -> "2025-11-17"
        - "17 novembre, 2025" -> "2025-11-17"

    Args:
        date_str: French date string

    Returns:
        Date in YYYY-MM-DD format or None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None

    # Clean the string
    cleaned = date_str.lower().strip()

    # Remove day name if present
    for day in FRENCH_DAYS:
        if cleaned.startswith(day):
            cleaned = cleaned[len(day):].strip()
            break

    # Remove commas and extra spaces
    cleaned = cleaned.replace(",", "").strip()
    cleaned = " ".join(cleaned.split())  # Normalize spaces

    # Try to parse: "17 novembre 2025"
    parts = cleaned.split()
    if len(parts) >= 3:
        try:
            day = int(parts[0])
            month_name = parts[1].lower()
            year = int(parts[2])

            month = FRENCH_MONTHS.get(month_name)
            if month:
                return f"{year:04d}-{month:02d}-{day:02d}"
        except (ValueError, IndexError):
            pass

    return None


# =============================================================================
# CURRENCY PARSING UTILITIES
# =============================================================================


def parse_currency(value: str | None) -> Optional[float]:
    """
    Parse a currency string to float.

    Handles formats:
        - "50 000 $" -> 50000.0
        - "556,50 $" -> 556.50
        - "25 000,00 $" -> 25000.00
        - "1000$" -> 1000.0

    Args:
        value: Currency string to parse

    Returns:
        Float value or None if parsing fails
    """
    if not value or not isinstance(value, str):
        return None

    # Remove currency symbol and whitespace
    cleaned = value.replace("$", "").replace(" ", "").strip()

    if not cleaned:
        return None

    # Handle French decimal separator (comma -> dot)
    # But be careful: "25000,00" has comma as decimal, "25 000" has space as thousand sep
    if "," in cleaned:
        # If there's a comma, it's likely a decimal separator
        cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return None


# =============================================================================
# SOURCE CONVERTERS
# =============================================================================


def convert_uv_extraction(extraction, pdf_path: Path) -> UnifiedExtraction:
    """
    Convert UV extraction result to unified format.

    Args:
        extraction: SummaryExtraction from extract_uv_pdf
        pdf_path: Path to the source PDF file

    Returns:
        UnifiedExtraction object
    """
    # Convert insured info
    insured = extraction.insured
    unified_insured = UnifiedInsured(
        insured_number="1",  # UV has single insured
        last_name=insured.last_name,
        first_name=insured.first_name,
        sex=insured.sex,
        age=insured.age,
        smoker=insured.smoker,
        birth_date=insured.birth_date,
    )

    # Convert protections
    unified_protections = []
    for prot in extraction.protections:
        unified_prot = UnifiedProtection(
            product_name=prot.protection_name,
            coverage_amount=parse_currency(prot.insurance_amount),
            policy_premium=parse_currency(prot.annual_premium),
            monthly_premium=parse_currency(prot.monthly_premium),
            payment_duration=None,  # UV doesn't have this
            details=prot.details if prot.details else None,
        )
        unified_protections.append(unified_prot)

    # Parse and format document date to YYYY-MM-DD
    formatted_date = parse_french_date(extraction.document_date) or extraction.document_date

    return UnifiedExtraction(
        source=InsuranceSource.UV,
        document_date=formatted_date,
        advisor_name=extraction.advisor_name,
        pdf_filename=pdf_path.name,
        insured_persons=[unified_insured],
        protections=unified_protections,
        total_annual_premium=parse_currency(extraction.total_annual_premium),
        total_monthly_premium=parse_currency(extraction.total_monthly_premium),
        payment_interval=None,  # UV doesn't have this
    )


def convert_assomption_extraction(extraction, pdf_path: Path) -> UnifiedExtraction:
    """
    Convert Assomption extraction result to unified format.

    Args:
        extraction: SummaryExtraction from extract_assomption_pdf
        pdf_path: Path to the source PDF file

    Returns:
        UnifiedExtraction object
    """
    # Convert insured persons (Assomption supports multiple)
    unified_insured_list = []
    for person in extraction.insured_persons:
        unified_insured = UnifiedInsured(
            insured_number=person.number,
            last_name=person.last_name,
            first_name=person.first_name,
            sex=person.sex,
            age=person.age,
            smoker=person.smoker,
            birth_date=None,  # Assomption doesn't have birth_date
        )
        unified_insured_list.append(unified_insured)

    # Convert guarantees
    unified_protections = []
    for guarantee in extraction.guarantees:
        unified_prot = UnifiedProtection(
            product_name=guarantee.protection_name,
            coverage_amount=parse_currency(guarantee.capital_assure),
            policy_premium=parse_currency(guarantee.prime_annuelle),
            monthly_premium=None,  # Assomption doesn't have per-protection monthly
            payment_duration=guarantee.duree_paiement if guarantee.duree_paiement else None,
            details=None,  # Assomption doesn't have details
        )
        unified_protections.append(unified_prot)

    # Parse and format document date to YYYY-MM-DD
    formatted_date = parse_french_date(extraction.document_date) or extraction.document_date

    return UnifiedExtraction(
        source=InsuranceSource.ASSOMPTION,
        document_date=formatted_date,
        advisor_name=extraction.advisor_name,
        pdf_filename=pdf_path.name,
        insured_persons=unified_insured_list,
        protections=unified_protections,
        total_annual_premium=parse_currency(extraction.total_annual_premium),
        total_monthly_premium=parse_currency(extraction.total_monthly_premium),
        payment_interval=extraction.payment_interval if extraction.payment_interval else None,
    )


# =============================================================================
# DATAFRAME CONVERSION
# =============================================================================


def unified_to_dataframe(extraction: UnifiedExtraction) -> pd.DataFrame:
    """
    Convert a UnifiedExtraction to a pandas DataFrame.

    Creates one row per protection per insured person.
    Each insured person gets their own set of protection rows.

    Args:
        extraction: UnifiedExtraction object

    Returns:
        DataFrame with unified columns
    """
    rows = []

    # Create rows for each insured person with all protections
    for insured in extraction.insured_persons:
        for prot in extraction.protections:
            row = {
                # Document info
                "insurer_name": extraction.source.value,
                "report_date": extraction.document_date,
                "advisor_name": extraction.advisor_name,
                "pdf_filename": extraction.pdf_filename,
                # Insured info
                "insured_number": insured.insured_number,
                "last_name": insured.last_name,
                "first_name": insured.first_name,
                "insured_name": insured.insured_name,
                "sex": insured.sex,
                "birth_date": insured.birth_date,
                "age": insured.age,
                "smoker": insured.smoker,
                # Protection info
                "product_name": prot.product_name,
                "coverage_amount": prot.coverage_amount,
                "policy_premium": prot.policy_premium,
                "monthly_premium": prot.monthly_premium,
                "payment_duration": prot.payment_duration,
                "details": prot.details,
            }
            rows.append(row)

    df = pd.DataFrame(rows, columns=UNIFIED_COLUMNS)

    # Store totals and metadata as DataFrame attributes
    df.attrs["total_annual_premium"] = extraction.total_annual_premium
    df.attrs["total_monthly_premium"] = extraction.total_monthly_premium
    df.attrs["payment_interval"] = extraction.payment_interval
    df.attrs["source"] = extraction.source.value
    df.attrs["pdf_filename"] = extraction.pdf_filename

    # Store all insured persons for reference
    df.attrs["insured_persons"] = [
        {
            "insured_number": p.insured_number,
            "last_name": p.last_name,
            "first_name": p.first_name,
            "insured_name": p.insured_name,
            "sex": p.sex,
            "birth_date": p.birth_date,
            "age": p.age,
            "smoker": p.smoker,
        }
        for p in extraction.insured_persons
    ]

    return df


# =============================================================================
# MAIN EXTRACTION FUNCTIONS
# =============================================================================


def extract_and_unify_uv(pdf_path: str | Path) -> pd.DataFrame | None:
    """
    Extract and unify data from a UV insurance PDF.

    Args:
        pdf_path: Path to the UV PDF file

    Returns:
        Unified DataFrame or None if extraction fails
    """
    pdf_path = Path(pdf_path)

    extraction = extract_uv(pdf_path)
    if not extraction:
        return None

    unified = convert_uv_extraction(extraction, pdf_path)
    return unified_to_dataframe(unified)


def extract_and_unify_assomption(pdf_path: str | Path) -> pd.DataFrame | None:
    """
    Extract and unify data from an Assomption insurance PDF.

    Args:
        pdf_path: Path to the Assomption PDF file

    Returns:
        Unified DataFrame or None if extraction fails
    """
    pdf_path = Path(pdf_path)

    extraction = extract_assomption(pdf_path)
    if not extraction:
        return None

    unified = convert_assomption_extraction(extraction, pdf_path)
    return unified_to_dataframe(unified)


def extract_and_unify(
    pdf_path: str | Path,
    source: InsuranceSource | str | None = None,
) -> pd.DataFrame | None:
    """
    Extract and unify data from any supported insurance PDF.

    Auto-detects source if not specified by checking PDF content.

    Args:
        pdf_path: Path to the PDF file
        source: Source type (UV, Assomption) or None for auto-detect

    Returns:
        Unified DataFrame or None if extraction fails

    Example::

        # Auto-detect source
        df = extract_and_unify("insurance.pdf")

        # Specify source explicitly
        df = extract_and_unify("uv_doc.pdf", source=InsuranceSource.UV)
        df = extract_and_unify("assomption_doc.pdf", source="Assomption")
    """
    pdf_path = Path(pdf_path)

    # Convert string source to enum if needed
    if isinstance(source, str):
        source = InsuranceSource(source)

    # Auto-detect source if not specified
    if source is None:
        source = detect_source(pdf_path)
        if source is None:
            print(f"Warning: Could not auto-detect source for {pdf_path.name}")
            return None

    # Extract based on source
    if source == InsuranceSource.UV:
        return extract_and_unify_uv(pdf_path)
    elif source == InsuranceSource.ASSOMPTION:
        return extract_and_unify_assomption(pdf_path)
    else:
        print(f"Warning: Unknown source type: {source}")
        return None


def detect_source(pdf_path: Path) -> InsuranceSource | None:
    """
    Auto-detect the insurance source by examining PDF content.

    Detection rules:
    - UV: Contains "SOMMAIRE DES PROTECTIONS ET DES PRIMES"
    - Assomption: Contains "Sommaire des garanties"

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Detected InsuranceSource or None if unknown
    """
    import pdfplumber

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:3]:  # Check first 3 pages
                text = page.extract_text() or ""

                if "SOMMAIRE DES PROTECTIONS ET DES PRIMES" in text:
                    return InsuranceSource.UV

                if "Sommaire des garanties" in text:
                    return InsuranceSource.ASSOMPTION

    except Exception as e:
        print(f"Warning: Error detecting source for {pdf_path.name}: {e}")

    return None


# =============================================================================
# BATCH PROCESSING
# =============================================================================


def process_directory(
    directory: str | Path,
    source: InsuranceSource | str | None = None,
    recursive: bool = False,
) -> pd.DataFrame:
    """
    Process all PDF files in a directory and return unified DataFrame.

    Args:
        directory: Directory containing PDF files
        source: Source type or None for auto-detect
        recursive: If True, search subdirectories

    Returns:
        Combined DataFrame from all processed PDFs
    """
    directory = Path(directory)

    if recursive:
        pdf_files = list(directory.rglob("*.pdf"))
    else:
        pdf_files = list(directory.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {directory}")
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    all_dfs = []
    success_count = 0
    fail_count = 0

    for pdf_path in sorted(pdf_files):
        print(f"Processing: {pdf_path.name}...", end=" ")

        df = extract_and_unify(pdf_path, source=source)

        if df is not None and not df.empty:
            all_dfs.append(df)
            success_count += 1
            print(f"OK ({len(df)} protections)")
        else:
            fail_count += 1
            print("FAILED")

    print(f"\nProcessed: {success_count} success, {fail_count} failed")

    if not all_dfs:
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    # Combine all DataFrames
    combined = pd.concat(all_dfs, ignore_index=True)

    # Store summary in attrs
    combined.attrs["files_processed"] = success_count
    combined.attrs["files_failed"] = fail_count
    combined.attrs["total_protections"] = len(combined)

    return combined


def process_all_sources(
    uv_directory: str | Path | None = None,
    assomption_directory: str | Path | None = None,
) -> pd.DataFrame:
    """
    Process PDFs from both UV and Assomption directories.

    Args:
        uv_directory: Directory containing UV PDFs
        assomption_directory: Directory containing Assomption PDFs

    Returns:
        Combined unified DataFrame from all sources
    """
    all_dfs = []

    if uv_directory:
        uv_dir = Path(uv_directory)
        if uv_dir.exists():
            print("\n" + "=" * 60)
            print("Processing UV PDFs")
            print("=" * 60)
            uv_df = process_directory(uv_dir, source=InsuranceSource.UV)
            if not uv_df.empty:
                all_dfs.append(uv_df)

    if assomption_directory:
        assomption_dir = Path(assomption_directory)
        if assomption_dir.exists():
            print("\n" + "=" * 60)
            print("Processing Assomption PDFs")
            print("=" * 60)
            assomption_df = process_directory(assomption_dir, source=InsuranceSource.ASSOMPTION)
            if not assomption_df.empty:
                all_dfs.append(assomption_df)

    if not all_dfs:
        return pd.DataFrame(columns=UNIFIED_COLUMNS)

    combined = pd.concat(all_dfs, ignore_index=True)

    # Calculate summary statistics
    combined.attrs["total_files"] = sum(df.attrs.get("files_processed", 0) for df in all_dfs)
    combined.attrs["total_protections"] = len(combined)

    return combined


# =============================================================================
# REPORTING
# =============================================================================


def generate_summary_report(df: pd.DataFrame) -> str:
    """
    Generate a summary report of the unified extraction.

    Args:
        df: Unified DataFrame

    Returns:
        Formatted report string
    """
    if df.empty:
        return "No data to report."

    lines = [
        "=" * 70,
        "UNIFIED EXTRACTION SUMMARY REPORT",
        "=" * 70,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    # Overall statistics
    lines.append("OVERALL STATISTICS")
    lines.append("-" * 40)
    lines.append(f"  Total protections: {len(df)}")
    lines.append(f"  Unique PDFs: {df['pdf_filename'].nunique()}")
    lines.append(f"  Unique insured persons: {df['insured_name'].nunique()}")

    # By source breakdown
    lines.append("")
    lines.append("BY SOURCE")
    lines.append("-" * 40)
    source_counts = df.groupby("insurer_name").agg({
        "pdf_filename": "nunique",
        "product_name": "count",
        "policy_premium": "sum",
    }).rename(columns={
        "pdf_filename": "PDFs",
        "product_name": "Protections",
        "policy_premium": "Total Annual Premium",
    })

    for source, row in source_counts.iterrows():
        lines.append(f"  {source}:")
        lines.append(f"    PDFs: {int(row['PDFs'])}")
        lines.append(f"    Protections: {int(row['Protections'])}")
        if pd.notna(row["Total Annual Premium"]):
            lines.append(f"    Total Annual Premium: ${row['Total Annual Premium']:,.2f}")

    # Financial summary
    lines.append("")
    lines.append("FINANCIAL SUMMARY")
    lines.append("-" * 40)

    total_coverage = df["coverage_amount"].sum()
    total_annual = df["policy_premium"].sum()
    total_monthly = df["monthly_premium"].sum()

    if pd.notna(total_coverage):
        lines.append(f"  Total Coverage Amount: ${total_coverage:,.2f}")
    if pd.notna(total_annual):
        lines.append(f"  Total Policy Premiums (Annual): ${total_annual:,.2f}")
    if pd.notna(total_monthly):
        lines.append(f"  Total Monthly Premiums: ${total_monthly:,.2f}")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================


def export_to_csv(df: pd.DataFrame, output_path: str | Path) -> Path:
    """
    Export unified DataFrame to CSV.

    Args:
        df: Unified DataFrame
        output_path: Output file path

    Returns:
        Path to saved file
    """
    output_path = Path(output_path)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Exported to CSV: {output_path}")
    return output_path


def export_to_excel(df: pd.DataFrame, output_path: str | Path) -> Path:
    """
    Export unified DataFrame to Excel with formatting.

    Args:
        df: Unified DataFrame
        output_path: Output file path

    Returns:
        Path to saved file
    """
    output_path = Path(output_path)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Unified Data", index=False)

        # Auto-adjust column widths
        worksheet = writer.sheets["Unified Data"]
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max(),
                len(col)
            ) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

    print(f"Exported to Excel: {output_path}")
    return output_path


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main():
    """Main entry point for testing unified extraction."""
    base_dir = Path(__file__).parent.parent
    uv_dir = base_dir / "pdf" / "uv"
    assomption_dir = base_dir / "pdf" / "assomption"

    print("=" * 70)
    print("INSURANCE PDF UNIFIED EXTRACTION")
    print("=" * 70)
    print(f"UV Directory: {uv_dir}")
    print(f"Assomption Directory: {assomption_dir}")

    # Process all sources
    df = process_all_sources(
        uv_directory=uv_dir,
        assomption_directory=assomption_dir,
    )

    if df.empty:
        print("\nNo data extracted!")
        return

    # Display results
    print("\n" + "=" * 70)
    print("UNIFIED DATAFRAME")
    print("=" * 70)

    # Configure pandas display
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    pd.set_option("display.max_colwidth", 40)

    # Show key columns
    display_cols = [
        "insurer_name",
        "insured_name",
        "product_name",
        "coverage_amount",
        "policy_premium",
        "monthly_premium",
    ]
    print(df.to_string(index=False))

    # Generate and print report
    print("\n" + generate_summary_report(df))

    # Export to results directory
    results_dir = base_dir / "results"
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_to_csv(df, results_dir / f"unified_extraction_{timestamp}.csv")
    export_to_excel(df, results_dir / f"unified_extraction_{timestamp}.xlsx")


if __name__ == "__main__":
    main()
