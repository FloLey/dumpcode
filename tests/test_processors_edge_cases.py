"""Unit tests for processors.py encoding edge cases."""

from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path

from dumpcode.processors import detect_file_encoding, is_binary_file


class TestProcessorsEncodingEdgeCases:
    """Test encoding detection and binary file handling edge cases."""
    
    def test_detect_utf16_be(self):
        """Test detection of UTF-16 Big Endian BOM."""
        # Input: UTF-16 Big Endian BOM followed by "AB"
        test_bytes = b'\xfe\xff\x00A\x00B'
        
        result = detect_file_encoding(test_bytes)
        
        assert result == 'utf-16-be'
    
    def test_detect_utf16_le(self):
        """Test detection of UTF-16 Little Endian BOM."""
        # Input: UTF-16 Little Endian BOM followed by "AB"
        test_bytes = b'\xff\xfeA\x00B\x00'
        
        result = detect_file_encoding(test_bytes)
        
        assert result == 'utf-16-le'
    
    def test_detect_utf8_bom(self):
        """Test detection of UTF-8 BOM."""
        # Input: UTF-8 BOM followed by "test"
        test_bytes = b'\xef\xbb\xbftest'
        
        result = detect_file_encoding(test_bytes)
        
        assert result == 'utf-8-sig'
    
    def test_detect_utf8_no_bom(self):
        """Test detection of UTF-8 without BOM."""
        # Input: Plain UTF-8 text
        test_bytes = b'test data'
        
        result = detect_file_encoding(test_bytes)
        
        assert result == 'utf-8'
    
    def test_detect_latin1(self):
        """Test detection of Latin-1 (ISO-8859-1)."""
        # Input: Latin-1 compatible bytes
        test_bytes = b'\xe9\xe8\xe7'  # accented characters in Latin-1
        
        result = detect_file_encoding(test_bytes)
        
        assert result == 'latin-1'
    
    def test_is_binary_file_stat_failure(self):
        """Test that is_binary_file returns True when stat fails (safe default)."""
        mock_path = Path("/test/file.bin")
        
        # Mock Path.stat to raise OSError
        with patch("pathlib.Path.stat", side_effect=OSError("Permission denied")):
            result = is_binary_file(mock_path)
        
        # Should return True as safe default
        assert result is True
    
    def test_is_binary_file_null_bytes(self):
        """Test that is_binary_file detects null bytes."""
        mock_path = Path("/test/file.bin")
        
        # Mock file reading to return data with null bytes
        with patch("builtins.open", mock_open(read_data=b'text\x00with\x00nulls')):
            result = is_binary_file(mock_path)
        
        assert result is True
    
    def test_is_binary_file_text_content(self):
        """Test that is_binary_file returns False for text files."""
        # Use a real Path but mock the open behavior
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 100 # Not empty
            with patch("builtins.open", mock_open(read_data=b"Normal Text")):
                assert is_binary_file(Path("test.txt")) is False
    
    def test_is_binary_file_empty_file(self):
        """Test that is_binary_file handles empty files."""
        mock_path = Path("/test/empty.txt")
        
        # Mock file reading to return empty data
        with patch("builtins.open", mock_open(read_data=b'')):
            result = is_binary_file(mock_path)
        
        # Empty files are not binary
        assert result is False
    
    def test_is_binary_file_empty_file_fixed(self):
        """Test is_binary_file with empty file using correct stat mocking."""
        mock_path = MagicMock(spec=Path)
        mock_path.suffix = ".txt"
        # The logic checks stat().st_size BEFORE opening the file
        mock_stat = MagicMock()
        mock_stat.st_size = 0
        mock_path.stat.return_value = mock_stat
        
        assert is_binary_file(mock_path) is False
    
    def test_is_binary_file_read_error(self):
        """Test that is_binary_file returns True when file read fails."""
        mock_path = Path("/test/corrupted.bin")
        
        # Mock open to raise OSError
        with patch("builtins.open", side_effect=OSError("Cannot read file")):
            result = is_binary_file(mock_path)
        
        # Should return True as safe default
        assert result is True