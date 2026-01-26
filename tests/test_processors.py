"""Unit tests for file content processors."""

import os
import pytest
from unittest.mock import patch
from dumpcode.processors import (
    get_file_content, 
    truncate_text_lines,
    is_binary_file,
    detect_file_encoding
)


def test_truncate_text_lines_csv(tmp_path):
    """Test truncate_text_lines with CSV file."""
    csv_file = tmp_path / "test.csv"
    # Create a CSV with 10 lines
    lines = [f"line{i},data{i},value{i}\n" for i in range(10)]
    csv_file.write_text("".join(lines))
    
    result = truncate_text_lines(csv_file, limit=5)
    
    # Should contain first 5 lines
    assert "line0" in result
    assert "line4" in result
    # Should NOT contain line5
    assert "line5" not in result
    # Should have truncation marker
    assert "[... truncated .csv ...]" in result


def test_truncate_text_lines_log(tmp_path):
    """Test truncate_text_lines with log file."""
    log_file = tmp_path / "test.log"
    # Create a log file with 20 lines
    lines = [f"2024-01-01 12:00:00 INFO: Log entry {i}\n" for i in range(20)]
    log_file.write_text("".join(lines))
    
    result = truncate_text_lines(log_file, limit=10)
    
    # Should contain first 10 lines
    assert "Log entry 0" in result
    assert "Log entry 9" in result
    # Should NOT contain line10
    assert "Log entry 10" not in result
    # Should have truncation marker
    assert "[... truncated .log ...]" in result


def test_truncate_text_lines_fewer_lines_than_limit(tmp_path):
    """Test truncate_text_lines when file has fewer lines than limit."""
    csv_file = tmp_path / "small.csv"
    # Create a CSV with only 3 lines
    lines = [f"line{i}\n" for i in range(3)]
    csv_file.write_text("".join(lines))
    
    result = truncate_text_lines(csv_file, limit=5)
    
    # Should contain all 3 lines
    assert "line0" in result
    assert "line1" in result
    assert "line2" in result
    # Should NOT have truncation marker since we didn't hit the limit
    assert "[... truncated" not in result


def test_truncate_text_lines_empty_file(tmp_path):
    """Test truncate_text_lines with empty file."""
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("")
    
    result = truncate_text_lines(csv_file, limit=5)
    
    # Should return data snippet message
    assert "[Data snippet from empty.csv]" in result


def test_get_file_content_csv_processing(tmp_path):
    """Test get_file_content with CSV file (should use truncation)."""
    csv_file = tmp_path / "data.csv"
    # Create a CSV with 8 lines
    lines = ["col1,col2,col3\n" for i in range(8)]
    csv_file.write_text("".join(lines))
    
    content, error = get_file_content(csv_file)
    
    assert error is None
    # Should be truncated to 5 lines (default for CSV)
    assert "col1,col2,col3\n" in content
    assert "[... truncated .csv ...]" in content


def test_get_file_content_jsonl_processing(tmp_path):
    """Test get_file_content with JSONL file (should use truncation)."""
    jsonl_file = tmp_path / "data.jsonl"
    # Create a JSONL file with 7 lines
    lines = [f'{{"id": {i}, "data": "value{i}"}}\n' for i in range(7)]
    jsonl_file.write_text("".join(lines))
    
    content, error = get_file_content(jsonl_file)
    
    assert error is None
    # Should be truncated to 5 lines (default for JSONL)
    assert '"id": 0' in content
    assert '"id": 4' in content
    assert '"id": 5' not in content  # Should be truncated
    assert "[... truncated .jsonl ...]" in content


def test_get_file_content_log_processing(tmp_path):
    """Test get_file_content with log file (should use truncation)."""
    log_file = tmp_path / "app.log"
    # Create a log file with 15 lines
    lines = [f"DEBUG: Message {i}\n" for i in range(15)]
    log_file.write_text("".join(lines))
    
    content, error = get_file_content(log_file)
    
    assert error is None
    # Should be truncated to 10 lines (default for log files)
    assert "DEBUG: Message 0" in content
    assert "DEBUG: Message 9" in content
    assert "DEBUG: Message 10" not in content  # Should be truncated
    assert "[... truncated .log ...]" in content


def test_get_file_content_regular_text_file(tmp_path):
    """Test get_file_content with regular text file (should not truncate)."""
    txt_file = tmp_path / "notes.txt"
    content_text = "This is a regular text file.\nIt should not be truncated.\n"
    txt_file.write_text(content_text)
    
    content, error = get_file_content(txt_file)
    
    assert error is None
    # Should contain full content
    assert "This is a regular text file." in content
    assert "It should not be truncated." in content
    # Should NOT have truncation marker
    assert "[... truncated" not in content


# Binary detection test cases
BINARY_EXTENSION_CASES = [
    ("test.jpg", b"fake jpeg data", True),
    ("test.png", b"fake png data", True),
    ("test.pdf", b"fake pdf data", True),
    ("test.zip", b"fake zip data", True),
    ("test.mp3", b"fake mp3 data", True),
    ("test.dll", b"fake dll data", True),
    ("test.exe", b"fake exe data", True),
]

TEXT_EXTENSION_CASES = [
    ("test.py", "def hello(): pass", False),
    ("test.js", "console.log('hello')", False),
    ("test.json", '{"key": "value"}', False),
    ("test.xml", "<root></root>", False),
    ("test.txt", "Hello world", False),
    ("test.md", "# Markdown", False),
    ("test.csv", "a,b,c\n1,2,3", False),
]

BINARY_CONTENT_CASES = [
    ("text_file.txt", "Hello, world!\nThis is a text file.\n", False),
    ("python_file.py", "def hello():\n    print('Hello')\n", False),
    ("binary_with_null.bin", b"Hello\x00World", True),
    ("empty.txt", "", False),
    ("large_text.txt", "x" * 2000, False),
    ("utf8_with_bom.txt", b"\xef\xbb\xbfHello World", False),
    ("unicode.txt", "Hello 🌍 World\nEmoji: 😀\n", False),
]

# Encoding detection test cases
ENCODING_CASES = [
    # (filename, content_bytes, expected_encoding)
    ("utf8.txt", "Hello, world! 🌍".encode("utf-8"), "utf-8"),
    ("utf8_bom.txt", b"\xef\xbb\xbfHello, world!", "utf-8-sig"),
    ("latin1.txt", b"Hello, world! \xe9 \xe0", ["latin-1", "iso-8859-1", "cp1252"]),
    ("ascii.txt", "Hello, world!".encode("ascii"), ["ascii", "utf-8"]),
    ("utf16le.txt", b"\xff\xfeH\x00e\x00l\x00l\x00o\x00", "utf-16-le"),
    ("utf16be.txt", b"\xfe\xff\x00H\x00e\x00l\x00l\x00o", "utf-16-be"),
    ("binary.bin", b"\x00\x01\x02\x03\x04", "utf-8"),
    ("empty.txt", b"", "utf-8"),
    ("unicode.txt", "Hello 🌍 World 😀 Emoji".encode("utf-8"), "utf-8"),
    ("cp1252.txt", b"Euro: \x80", ["cp1252", "latin-1", "iso-8859-1", "utf-8"]),
]


class TestBinaryDetection:
    """Parametrized tests for binary file detection."""
    
    @pytest.mark.parametrize("filename,content,expected", BINARY_EXTENSION_CASES)
    def test_binary_extensions(self, tmp_path, filename, content, expected):
        """Test that files with binary extensions are detected as binary."""
        binary_file = tmp_path / filename
        binary_file.write_bytes(content)
        assert is_binary_file(binary_file) == expected, f"Failed for {filename}"
    
    @pytest.mark.parametrize("filename,content,expected", TEXT_EXTENSION_CASES)
    def test_text_extensions(self, tmp_path, filename, content, expected):
        """Test that files with text extensions are not detected as binary."""
        text_file = tmp_path / filename
        text_file.write_text(content)
        assert is_binary_file(text_file) == expected, f"Failed for {filename}"
    
    @pytest.mark.parametrize("filename,content,expected", BINARY_CONTENT_CASES)
    def test_binary_content_detection(self, tmp_path, filename, content, expected):
        """Test binary detection based on file content."""
        test_file = tmp_path / filename
        
        if isinstance(content, bytes):
            test_file.write_bytes(content)
        else:
            test_file.write_text(content)
        
        assert is_binary_file(test_file) == expected, f"Failed for {filename}"
    
    def test_permission_error(self, tmp_path):
        """Test handling of files that can't be read."""
        protected_file = tmp_path / "protected.bin"
        protected_file.touch()
        os.chmod(protected_file, 0o000)
        
        try:
            assert is_binary_file(protected_file)
        finally:
            os.chmod(protected_file, 0o644)


class TestEncodingDetection:
    """Parametrized tests for file encoding detection."""
    
    @pytest.mark.parametrize("filename,content_bytes,expected", ENCODING_CASES)
    def test_encoding_detection(self, tmp_path, filename, content_bytes, expected):
        """Test detection of various file encodings."""
        test_file = tmp_path / filename
        test_file.write_bytes(content_bytes)
        
        with open(test_file, "rb") as f:
            header = f.read(4096)
        
        encoding = detect_file_encoding(header)
        
        if isinstance(expected, list):
            assert encoding in expected, f"Expected one of {expected}, got {encoding}"
        else:
            assert encoding == expected, f"Expected {expected}, got {encoding}"


@pytest.mark.edge_case
def test_detect_encoding_empty_header():
    """Cover processors.py:17 (Heuristic for zero-byte files/headers)"""
    from dumpcode.processors import detect_file_encoding
    assert detect_file_encoding(b"") == "utf-8"


@pytest.mark.edge_case
def test_is_binary_file_permission_error(tmp_path):
    """Cover processors.py:59-60 (Default to True if stat/open fails)"""
    from dumpcode.processors import is_binary_file
    from pathlib import Path
    p = tmp_path / "locked.bin"
    p.touch()
    with patch.object(Path, "stat", side_effect=Exception("Locked")):
        assert is_binary_file(p) is True


@pytest.mark.edge_case
def test_truncate_text_lines_crash(tmp_path):
    """Cover processors.py:98-99 (Fallback message on file read crash)"""
    from dumpcode.processors import truncate_text_lines
    p = tmp_path / "crash.csv"
    p.touch()
    with patch("builtins.open", side_effect=RuntimeError("Hard Drive Failure")):
        res = truncate_text_lines(p)
        assert "[Data snippet from crash.csv]" in res


# Consolidated tests from test_coverage_final_push.py
def test_processors_utf16_be_detection():
    """Cover processors.py:33 (UTF-16 BE detection)"""
    from dumpcode.processors import detect_file_encoding
    # The BOM for UTF-16 BE is \xfe\xff
    assert detect_file_encoding(b'\xfe\xff\x00A') == 'utf-16-be'


def test_processors_is_binary_stat_crash(tmp_path):
    """Cover processors.py:60 (Default to binary if file cannot be stat-ed)"""
    from dumpcode.processors import is_binary_file
    from pathlib import Path
    p = tmp_path / "locked.txt"
    p.touch()
    with patch.object(Path, "stat", side_effect=OSError("Lock")):
        assert is_binary_file(p) is True


# Consolidated tests from test_coverage_gaps.py
class TestProcessorGaps:
    def test_detect_utf16_be(self):
        """Cover processors.py:33 (UTF-16-BE detection)"""
        from dumpcode.processors import detect_file_encoding
        header = b'\xfe\xff\x00A\x00B'
        assert detect_file_encoding(header) == 'utf-16-be'

    def test_get_file_content_generic_exception(self, tmp_path):
        """Cover processors.py:134-136 (Generic error fallback)"""
        from dumpcode.processors import get_file_content
        p = tmp_path / "bug.txt"
        p.touch()
        with patch("builtins.open", side_effect=OSError("Drive Unplugged")):
            content, error = get_file_content(p)
            assert "Error reading file: Drive Unplugged" in content
            assert error == "Error reading file: Drive Unplugged"


# Consolidated tests from test_final_coverage.py
def test_processors_utf16_and_binary_errors(tmp_path):
    """Cover processors.py:33 (UTF-16 BE) and 59 (Binary stat error)"""
    from dumpcode.processors import detect_file_encoding, is_binary_file
    from pathlib import Path
    
    # UTF-16 BE
    assert detect_file_encoding(b'\xfe\xff\x00A') == 'utf-16-be'
    
    # Binary detection crash
    with patch.object(Path, "stat", side_effect=Exception("Lock Error")):
        assert is_binary_file(Path("any.txt")) is True