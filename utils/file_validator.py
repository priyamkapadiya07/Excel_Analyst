"""
File validation utilities for validating uploaded datasets.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re
from config.settings import SUPPORTED_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES


@dataclass
class ValidationResult:
    is_valid: bool
    error_message: Optional[str] = None
    file_type: Optional[str] = None
    file_size_bytes: int = 0


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal or invalid characters.
    """
    # Remove path components
    clean_name = Path(filename).name
    # Replace dangerous characters with underscore
    clean_name = re.sub(r"[^\w\s\.-]", "_", clean_name).strip()
    return clean_name or "uploaded_dataset"


def validate_file(
    file_name: str,
    file_bytes: bytes,
    max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES,
) -> ValidationResult:
    """
    Validate uploaded file for size, extension, and basic magic signatures.
    """
    if not file_bytes or len(file_bytes) == 0:
        return ValidationResult(
            is_valid=False,
            error_message="The uploaded file is empty.",
            file_size_bytes=0,
        )

    size = len(file_bytes)
    if size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        actual_mb = size / (1024 * 1024)
        return ValidationResult(
            is_valid=False,
            error_message=f"File size ({actual_mb:.2f} MB) exceeds maximum allowed limit ({max_mb:.0f} MB).",
            file_size_bytes=size,
        )

    suffix = Path(file_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return ValidationResult(
            is_valid=False,
            error_message=f"Unsupported file format '{suffix}'. Allowed formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            file_size_bytes=size,
        )

    # Magic byte checks
    if suffix == ".xlsx":
        # ZIP file signature: PK\x03\x04
        if not file_bytes.startswith(b"PK\x03\x04"):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid XLSX file: File header does not match Excel OpenXML format.",
                file_size_bytes=size,
            )
        file_type = "xlsx"
    elif suffix == ".xls":
        # OLE Compound Document signature: \xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1
        if not file_bytes.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid XLS file: File header does not match Excel 97-2004 format.",
                file_size_bytes=size,
            )
        file_type = "xls"
    elif suffix == ".csv":
        # Check if CSV contains binary/null bytes (often indicating binary executable disguised as CSV)
        if b"\x00" in file_bytes[:1024]:
            return ValidationResult(
                is_valid=False,
                error_message="Invalid CSV file: Contains null binary characters.",
                file_size_bytes=size,
            )
        file_type = "csv"
    else:
        file_type = suffix.lstrip(".")

    return ValidationResult(
        is_valid=True,
        file_type=file_type,
        file_size_bytes=size,
    )
