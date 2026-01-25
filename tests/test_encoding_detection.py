"""Unit tests for file encoding detection."""

from src.dumpcode.processors import detect_file_encoding


class TestEncodingDetection:
    """Test the detect_file_encoding function."""
    
    def test_utf8_file(self, tmp_path):
        """Test detection of UTF-8 files."""
        utf8_file = tmp_path / "test.txt"
        utf8_file.write_text("Hello, world! 🌍", encoding="utf-8")
        
        with open(utf8_file, "rb") as f:
            header = f.read(4096)
        encoding = detect_file_encoding(header)
        assert encoding == "utf-8"
    
    def test_utf8_bom(self, tmp_path):
        """Test detection of UTF-8 files with BOM."""
        utf8_bom_file = tmp_path / "test_bom.txt"
        with open(utf8_bom_file, "wb") as f:
            f.write(b"\xef\xbb\xbfHello, world!")  # UTF-8 BOM
        
        with open(utf8_bom_file, "rb") as f:
            header = f.read(4096)
        encoding = detect_file_encoding(header)
        assert encoding == "utf-8-sig"
    
    def test_latin1_file(self, tmp_path):
        """Test detection of Latin-1 files."""
        latin1_file = tmp_path / "test_latin1.txt"
        with open(latin1_file, "wb") as f:
            f.write(b"Hello, world! \xe9 \xe0")
        
        with open(latin1_file, "rb") as f:
            header = f.read(4096)
        encoding = detect_file_encoding(header)
        assert encoding in ["latin-1", "iso-8859-1", "cp1252"]
    
    def test_ascii_file(self, tmp_path):
        """Test detection of ASCII files."""
        ascii_file = tmp_path / "test_ascii.txt"
        ascii_file.write_text("Hello, world!", encoding="ascii")
        
        with open(ascii_file, "rb") as f:
            header = f.read(4096)
        encoding = detect_file_encoding(header)
        assert encoding == "ascii" or encoding == "utf-8"
    
    def test_utf16_le(self, tmp_path):
        """Test detection of UTF-16 Little Endian files."""
        utf16le_file = tmp_path / "test_utf16le.txt"
        with open(utf16le_file, "wb") as f:
            f.write(b"\xff\xfeH\x00e\x00l\x00l\x00o\x00")
        
        with open(utf16le_file, "rb") as f:
            header = f.read(4096)
        encoding = detect_file_encoding(header)
        assert encoding == "utf-16-le"
    
    def test_utf16_be(self, tmp_path):
        """Test detection of UTF-16 Big Endian files."""
        utf16be_file = tmp_path / "test_utf16be.txt"
        with open(utf16be_file, "wb") as f:
            f.write(b"\xfe\xff\x00H\x00e\x00l\x00l\x00o")
        
        with open(utf16be_file, "rb") as f:
            header = f.read(4096)
        encoding = detect_file_encoding(header)
        assert encoding == "utf-16-be"
    
    def test_binary_file(self, tmp_path):
        """Test that binary files default to UTF-8."""
        binary_file = tmp_path / "test.bin"
        with open(binary_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04")
        
        with open(binary_file, "rb") as f:
            header = f.read(4096)
        encoding = detect_file_encoding(header)
        assert encoding == "utf-8"
    
    def test_empty_file(self, tmp_path):
        """Test detection on empty files."""
        empty_file = tmp_path / "empty.txt"
        empty_file.touch()
        
        with open(empty_file, "rb") as f:
            header = f.read(4096)
        encoding = detect_file_encoding(header)
        assert encoding == "utf-8"
    
    def test_unicode_file(self, tmp_path):
        """Test detection of files with Unicode characters."""
        unicode_file = tmp_path / "test_unicode.txt"
        unicode_file.write_text("Hello 🌍 World 😀 Emoji", encoding="utf-8")
        
        with open(unicode_file, "rb") as f:
            header = f.read(4096)
        encoding = detect_file_encoding(header)
        assert encoding == "utf-8"
    
    def test_windows_cp1252(self, tmp_path):
        """Test detection of Windows CP1252 encoding."""
        cp1252_file = tmp_path / "test_cp1252.txt"
        with open(cp1252_file, "wb") as f:
            f.write(b"Euro: \x80")
        
        with open(cp1252_file, "rb") as f:
            header = f.read(4096)
        encoding = detect_file_encoding(header)
        assert encoding in ["cp1252", "latin-1", "iso-8859-1", "utf-8"]