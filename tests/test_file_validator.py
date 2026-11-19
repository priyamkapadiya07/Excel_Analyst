"""
Tests for file validator module.
"""

import pytest
from utils.file_validator import validate_file, sanitize_filename


def test_sanitize_filename():
    assert sanitize_filename("my_data.xlsx") == "my_data.xlsx"
    assert sanitize_filename("../../../etc/passwd.csv") == "passwd.csv"
    assert sanitize_filename("bad:file*name?.xlsx") == "bad_file_name_.xlsx"
    assert sanitize_filename("") == "uploaded_dataset"


def test_validate_empty_file():
    result = validate_file("empty.csv", b"")
    assert not result.is_valid
    assert "empty" in result.error_message.lower()


def test_validate_unsupported_extension():
    result = validate_file("script.py", b"print('hello')")
    assert not result.is_valid
    assert "unsupported" in result.error_message.lower()


def test_validate_oversized_file():
    dummy_bytes = b"0" * 1024
    result = validate_file("test.csv", dummy_bytes, max_size_bytes=500)
    assert not result.is_valid
    assert "exceeds" in result.error_message.lower()


def test_validate_valid_csv():
    csv_bytes = b"col1,col2\nval1,val2\n"
    result = validate_file("test.csv", csv_bytes)
    assert result.is_valid
    assert result.file_type == "csv"


def test_validate_invalid_binary_csv():
    # Null bytes in CSV
    csv_bytes = b"col1,col2\x00\x01\x02\nval1,val2"
    result = validate_file("corrupt.csv", csv_bytes)
    assert not result.is_valid
    assert "null binary" in result.error_message.lower()


def test_validate_fake_xlsx():
    # Plain text file disguised as xlsx
    fake_xlsx = b"Not really a zip file"
    result = validate_file("fake.xlsx", fake_xlsx)
    assert not result.is_valid
    assert "openxml" in result.error_message.lower()


def test_validate_valid_xlsx_signature():
    # ZIP signature PK\x03\x04
    zip_header = b"PK\x03\x04\x14\x00\x00\x00"
    result = validate_file("real.xlsx", zip_header)
    assert result.is_valid
    assert result.file_type == "xlsx"
