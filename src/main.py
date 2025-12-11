# -*- coding: utf-8 -*-
"""
Insurance Illustration Data Pipeline
=====================================

Main orchestration script that:
1. Extracts insurance illustration data from PDFs (UV, Assomption)
2. Unifies and transforms the data into a standard format
3. Uploads the data to Monday.com boards

This pipeline handles insurance illustrations/quotes, not commission data.

Author: Claude
Date: 2025-12-11
Version: 1.0.0
"""

import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import local modules
from unify_extraction import (
    InsuranceSource as UnifySource,
    extract_and_unify,
    UNIFIED_COLUMNS,
)
from monday_automation import MondayClient, CreateBoardResult, CreateGroupResult, CreateItemResult


# =============================================================================
# COLORED OUTPUT
# =============================================================================


class Colors:
    """ANSI color codes for terminal output."""
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_BLUE = '\033[94m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


class ColorPrint:
    """Utility class for colored console output."""

    @staticmethod
    def header(text: str):
        print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")

    @staticmethod
    def success(text: str):
        print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

    @staticmethod
    def error(text: str):
        print(f"{Colors.BRIGHT_RED}❌ {text}{Colors.RESET}")

    @staticmethod
    def warning(text: str):
        print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

    @staticmethod
    def info(text: str):
        print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

    @staticmethod
    def step(text: str):
        print(f"{Colors.BOLD}{Colors.MAGENTA}🔹 {text}{Colors.RESET}")

    @staticmethod
    def data(text: str):
        print(f"{Colors.WHITE}{text}{Colors.RESET}")

    @staticmethod
    def separator(char: str = "=", length: int = 80):
        print(f"{Colors.DIM}{char * length}{Colors.RESET}")

    @staticmethod
    def section(title: str):
        print()
        ColorPrint.separator("━", 80)
        print(f"{Colors.BOLD}{Colors.BRIGHT_BLUE}📋 {title}{Colors.RESET}")
        ColorPrint.separator("━", 80)


# =============================================================================
# CONFIGURATION
# =============================================================================


class InsuranceSource(Enum):
    """Enum for supported insurance sources."""
    UV = "UV"
    ASSOMPTION = "Assomption"


@dataclass
class PipelineConfig:
    """
    Configuration for the insurance illustration data pipeline.

    Attributes:
        source: Insurance source to process (UV or ASSOMPTION)
        pdf_path: Path to the PDF file to process
        group_name: Group name in Monday.com (e.g., "Novembre 2025")
        board_name: Name of the Monday.com board
        board_id: Optional existing board ID to use
        monday_api_key: Monday.com API key
        output_dir: Directory for intermediate results
        reuse_board: Whether to reuse existing board with same name
        reuse_group: Whether to reuse existing group with same name
    """
    source: InsuranceSource
    pdf_path: str
    group_name: Optional[str] = None
    board_name: str = "Illustrations Assurance"
    board_id: Optional[int] = None
    monday_api_key: str = ""
    output_dir: str = "./results"
    reuse_board: bool = True
    reuse_group: bool = True

    def __post_init__(self):
        """Validate configuration after initialization."""
        if isinstance(self.source, str):
            self.source = InsuranceSource(self.source)

        if not self.pdf_path:
            raise ValueError("PDF path is required")
        if not Path(self.pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")
        if not self.monday_api_key:
            raise ValueError("Monday.com API key is required")

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)


# =============================================================================
# MONDAY.COM COLUMN CONFIGURATION
# =============================================================================


# Columns to create in Monday.com (excluding metadata)
MONDAY_COLUMNS = [
    "insurer_name",
    "report_date",
    "advisor_name",
    "insured_number",
    "last_name",
    "first_name",
    "insured_name",
    "sex",
    "birth_date",
    "age",
    "smoker",
    "product_name",
    "coverage_amount",
    "policy_premium",
    "monthly_premium",
    "payment_duration",
    "details",
]

# Columns that should be numeric in Monday.com
NUMERIC_COLUMNS = {
    "age",
    "coverage_amount",
    "policy_premium",
    "monthly_premium",
}


# =============================================================================
# PIPELINE
# =============================================================================


class IllustrationPipeline:
    """
    Main pipeline for processing insurance illustration data and uploading to Monday.com.

    Steps:
    1. Extract data from PDF using appropriate extractor
    2. Unify data into standard format
    3. Setup Monday.com board and columns
    4. Upload data to Monday.com
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.monday_client = MondayClient(api_key=config.monday_api_key)

        # State variables
        self.extracted_data: Optional[pd.DataFrame] = None
        self.board_id: Optional[int] = None
        self.group_id: Optional[str] = None
        self.column_mapping: Dict[str, str] = {}
        self.upload_results: List[CreateItemResult] = []

    def run(self) -> bool:
        """
        Run the complete pipeline.

        Returns:
            True if successful, False otherwise
        """
        ColorPrint.separator("=", 80)
        ColorPrint.header("🚀 INSURANCE ILLUSTRATION DATA PIPELINE")
        ColorPrint.separator("=", 80)
        ColorPrint.info(f"Source: {self.config.source.value}")
        ColorPrint.info(f"PDF Path: {self.config.pdf_path}")
        ColorPrint.info(f"Board Name: {self.config.board_name}")
        ColorPrint.info(f"Group: {self.config.group_name or 'Default'}")
        ColorPrint.separator("=", 80)

        try:
            # Step 1: Extract data from PDF
            if not self._step1_extract_data():
                ColorPrint.error("Step 1 failed: Data extraction")
                return False

            # Step 2: Validate data
            if not self._step2_validate_data():
                ColorPrint.error("Step 2 failed: Data validation")
                return False

            # Step 3: Setup Monday.com board
            if not self._step3_setup_monday_board():
                ColorPrint.error("Step 3 failed: Monday.com board setup")
                return False

            # Step 4: Upload data to Monday.com
            if not self._step4_upload_to_monday():
                ColorPrint.error("Step 4 failed: Data upload to Monday.com")
                return False

            print()
            ColorPrint.separator("=", 80)
            ColorPrint.success("PIPELINE COMPLETED SUCCESSFULLY")
            ColorPrint.separator("=", 80)

            return True

        except Exception as e:
            print()
            ColorPrint.error(f"Pipeline failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _step1_extract_data(self) -> bool:
        """
        Step 1: Extract and unify data from PDF.

        Returns:
            True if successful, False otherwise
        """
        ColorPrint.section("STEP 1: EXTRACT DATA FROM PDF")

        try:
            pdf_path = Path(self.config.pdf_path)
            ColorPrint.info(f"Processing {self.config.source.value} PDF: {pdf_path.name}")

            # Map to unify_extraction source
            if self.config.source == InsuranceSource.UV:
                unify_source = UnifySource.UV
            else:
                unify_source = UnifySource.ASSOMPTION

            # Extract and unify data
            self.extracted_data = extract_and_unify(pdf_path, source=unify_source)

            if self.extracted_data is None or self.extracted_data.empty:
                ColorPrint.error("No data extracted from PDF")
                return False

            ColorPrint.success(f"Extracted {len(self.extracted_data)} records")
            ColorPrint.info(f"Columns: {list(self.extracted_data.columns)}")

            # Display sample
            print()
            ColorPrint.step("Sample data (first 3 rows):")
            print(self.extracted_data.head(3).to_string())

            return True

        except Exception as e:
            ColorPrint.error(f"Error in data extraction: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _step2_validate_data(self) -> bool:
        """
        Step 2: Validate extracted data.

        Returns:
            True if successful, False otherwise
        """
        ColorPrint.section("STEP 2: VALIDATE DATA")

        try:
            if self.extracted_data is None or self.extracted_data.empty:
                ColorPrint.error("No data to validate")
                return False

            # Check required columns
            required_cols = ["insured_name", "product_name"]
            missing_cols = [col for col in required_cols if col not in self.extracted_data.columns]

            if missing_cols:
                ColorPrint.error(f"Missing required columns: {missing_cols}")
                return False

            # Check for empty insured names
            empty_names = self.extracted_data["insured_name"].isna().sum()
            if empty_names > 0:
                ColorPrint.warning(f"{empty_names} rows with empty insured_name")

            # Check for empty product names
            empty_products = self.extracted_data["product_name"].isna().sum()
            if empty_products > 0:
                ColorPrint.warning(f"{empty_products} rows with empty product_name")

            ColorPrint.success("Data validation complete")
            ColorPrint.info(f"Ready to upload {len(self.extracted_data)} records")

            return True

        except Exception as e:
            ColorPrint.error(f"Error in data validation: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _step3_setup_monday_board(self) -> bool:
        """
        Step 3: Setup Monday.com board, group, and columns.

        Returns:
            True if successful, False otherwise
        """
        ColorPrint.section("STEP 3: SETUP MONDAY.COM BOARD & COLUMNS")

        try:
            # Create or reuse board
            if self.config.board_id:
                self.board_id = self.config.board_id
                ColorPrint.info(f"Using existing board ID: {self.board_id}")
            else:
                ColorPrint.info(f"Creating/reusing board: {self.config.board_name}")
                board_result = self.monday_client.create_board(
                    board_name=self.config.board_name,
                    board_kind="public",
                    reuse_existing=self.config.reuse_board
                )

                if not board_result.success:
                    ColorPrint.error(f"Failed to create/reuse board: {board_result.error}")
                    return False

                self.board_id = int(board_result.board_id)
                ColorPrint.success(f"Board ready: {board_result.board_name} (ID: {self.board_id})")

            # Create or reuse group
            if self.config.group_name:
                ColorPrint.info(f"Creating/reusing group: {self.config.group_name}")
                group_result = self.monday_client.create_group(
                    board_id=self.board_id,
                    group_name=self.config.group_name,
                    group_color="#0086c0",
                    reuse_existing=self.config.reuse_group
                )

                if not group_result.success:
                    ColorPrint.error(f"Failed to create/reuse group: {group_result.error}")
                    return False

                self.group_id = group_result.group_id
                ColorPrint.success(f"Group ready: {group_result.group_title} (ID: {self.group_id})")
            else:
                ColorPrint.info("No group specified - items will be added to default group")
                self.group_id = None

            # Setup columns
            if self.extracted_data is not None and not self.extracted_data.empty:
                ColorPrint.info("Setting up columns...")

                # Filter columns that exist in our data
                data_columns = [
                    col for col in MONDAY_COLUMNS
                    if col in self.extracted_data.columns
                ]

                # Exclude pdf_filename from Monday columns (internal metadata)
                data_columns = [col for col in data_columns if col != "pdf_filename"]

                ColorPrint.info(f"Found {len(data_columns)} columns to create/map")

                # Create columns one by one to preserve order
                self.column_mapping = {}

                for col_name in data_columns:
                    col_type = "numbers" if col_name in NUMERIC_COLUMNS else "text"

                    col_mapping = self.monday_client.get_or_create_columns(
                        board_id=self.board_id,
                        column_names=[col_name],
                        column_type=col_type
                    )
                    self.column_mapping.update(col_mapping)

                ColorPrint.success(f"Columns configured: {len(self.column_mapping)} columns ready")

            return True

        except Exception as e:
            ColorPrint.error(f"Error in Monday.com board setup: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _step4_upload_to_monday(self) -> bool:
        """
        Step 4: Upload data to Monday.com.

        Returns:
            True if successful, False otherwise
        """
        ColorPrint.section("STEP 4: UPLOAD DATA TO MONDAY.COM")

        try:
            if self.extracted_data is None or self.extracted_data.empty:
                ColorPrint.error("No data to upload")
                return False

            # Prepare items
            items_to_create = self._prepare_monday_items(self.extracted_data)

            ColorPrint.info(f"Uploading {len(items_to_create)} items to Monday.com...")

            # Upload items in batch
            self.upload_results = self.monday_client.create_items_batch(
                board_id=self.board_id,
                items=items_to_create,
                group_id=self.group_id
            )

            # Analyze results
            successful = sum(1 for r in self.upload_results if r.success)
            failed = len(self.upload_results) - successful

            print()
            ColorPrint.step("Upload Summary:")
            ColorPrint.info(f"Total items:   {len(self.upload_results)}")
            ColorPrint.success(f"Successful: {successful}")
            if failed > 0:
                ColorPrint.error(f"Failed:     {failed}")

            return successful > 0

        except Exception as e:
            ColorPrint.error(f"Error in data upload: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _prepare_monday_items(self, df: pd.DataFrame) -> List[Dict]:
        """
        Prepare DataFrame rows as Monday.com items.

        Item name will be: "insured_name - product_name"

        Args:
            df: DataFrame with extracted data

        Returns:
            List of item dictionaries for batch creation
        """
        items = []

        # Metadata columns to skip
        metadata_columns = ["pdf_filename"]

        for _, row in df.iterrows():
            # Create item name from insured_name and product_name
            insured_name = str(row.get("insured_name", "Unknown"))
            product_name = str(row.get("product_name", "Unknown"))
            item_name = f"{insured_name} - {product_name}"

            # Prepare column values
            column_values = {}

            for col_name, col_value in row.items():
                if col_name in metadata_columns:
                    continue

                if col_name not in self.column_mapping:
                    continue

                column_id = self.column_mapping[col_name]

                # Handle empty/NaN values
                if pd.isna(col_value) or col_value is None or col_value == "":
                    continue

                # Convert to string
                value_str = str(col_value)

                # Skip invalid string values
                if value_str in ["None", "nan", "NaN", "NaT"]:
                    continue

                column_values[column_id] = value_str

            # Create item dictionary
            item = {"name": item_name}

            if column_values:
                item["column_values"] = column_values

            items.append(item)

        # Show preview
        if items:
            ColorPrint.info("Example item structure:")
            ColorPrint.data(f"  Name: {items[0]['name']}")
            if "column_values" in items[0]:
                ColorPrint.data(f"  Columns: {len(items[0]['column_values'])} values")

        return items


# =============================================================================
# EXAMPLE CONFIGURATIONS
# =============================================================================


def create_uv_config(api_key: str, pdf_path: str, group_name: Optional[str] = None) -> PipelineConfig:
    """Create configuration for UV Assurance illustration processing."""
    return PipelineConfig(
        source=InsuranceSource.UV,
        pdf_path=pdf_path,
        group_name=group_name,
        board_name="Illustrations UV",
        monday_api_key=api_key,
        output_dir="./results/uv"
    )


def create_assomption_config(api_key: str, pdf_path: str, group_name: Optional[str] = None) -> PipelineConfig:
    """Create configuration for Assomption Vie illustration processing."""
    return PipelineConfig(
        source=InsuranceSource.ASSOMPTION,
        pdf_path=pdf_path,
        group_name=group_name,
        board_name="Illustrations Assomption",
        monday_api_key=api_key,
        output_dir="./results/assomption"
    )


# =============================================================================
# MAIN EXECUTION
# =============================================================================


def main():
    """Main execution function."""

    # Load Monday.com API key from environment
    MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")

    if not MONDAY_API_KEY:
        ColorPrint.error("ERROR: MONDAY_API_KEY environment variable not set!")
        ColorPrint.info("Please set your Monday.com API key:")
        ColorPrint.info("  1. Create a .env file with: MONDAY_API_KEY=your_key_here")
        ColorPrint.info("  2. Or set it as a system environment variable")
        sys.exit(1)

    # ==========================================================================
    # CONFIGURATION - MODIFY THIS SECTION
    # ==========================================================================

    # Example: Process a UV illustration PDF
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "pdf" / "uv" / "RI-UV-800801-20251117.pdf"

    if not pdf_path.exists():
        ColorPrint.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)

    config = create_uv_config(
        api_key=MONDAY_API_KEY,
        pdf_path=str(pdf_path),
        group_name="Novembre 2025"
    )

    # ==========================================================================
    # EXECUTION
    # ==========================================================================

    print()
    ColorPrint.separator("=", 80)
    ColorPrint.header("CONFIGURATION SUMMARY")
    ColorPrint.separator("=", 80)
    ColorPrint.info(f"Source:       {config.source.value}")
    ColorPrint.info(f"PDF Path:     {config.pdf_path}")
    ColorPrint.info(f"Board Name:   {config.board_name}")
    ColorPrint.info(f"Group:        {config.group_name or 'None'}")
    ColorPrint.info(f"Output Dir:   {config.output_dir}")
    ColorPrint.separator("=", 80)
    print()

    # Run pipeline
    pipeline = IllustrationPipeline(config)
    success = pipeline.run()

    print()
    if success:
        ColorPrint.success("Pipeline completed successfully!")
        return 0
    else:
        ColorPrint.error("Pipeline failed. Check output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
