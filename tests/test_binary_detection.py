"""Unit tests for binary file detection."""

import os

from src.dumpcode.processors import is_binary_file


class TestBinaryFileDetection:
    """Test the is_binary_file function."""
    
    def test_text_file(self, tmp_path):
        """Test that text files are not detected as binary."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("Hello, world!\nThis is a text file.\n")
        
        assert not is_binary_file(text_file)
    
    def test_python_file(self, tmp_path):
        """Test that Python source files are not detected as binary."""
        py_file = tmp_path / "test.py"
        py_file.write_text("def hello():\n    print('Hello')\n")
        
        assert not is_binary_file(py_file)
    
    def test_binary_with_null_bytes(self, tmp_path):
        """Test that files with null bytes are detected as binary."""
        binary_file = tmp_path / "test.bin"
        with open(binary_file, "wb") as f:
            f.write(b"Hello\x00World")
        
        assert is_binary_file(binary_file)
    
    def test_empty_file(self, tmp_path):
        """Test that empty files are not detected as binary."""
        empty_file = tmp_path / "empty.txt"
        empty_file.touch()
        
        assert not is_binary_file(empty_file)
    
    def test_large_text_file(self, tmp_path):
        """Test that large text files are not detected as binary."""
        large_file = tmp_path / "large.txt"
        # Create a file larger than 1024 bytes (the read chunk size)
        content = "x" * 2000
        large_file.write_text(content)
        
        assert not is_binary_file(large_file)
    
    def test_permission_error(self, tmp_path):
        """Test handling of files that can't be read."""
        protected_file = tmp_path / "protected.bin"
        protected_file.touch()
        os.chmod(protected_file, 0o000)
        
        try:
            assert is_binary_file(protected_file)
        finally:
            os.chmod(protected_file, 0o644)
    
    def test_utf8_with_bom(self, tmp_path):
        """Test that UTF-8 files with BOM are not detected as binary."""
        utf8_file = tmp_path / "utf8.txt"
        with open(utf8_file, "wb") as f:
            f.write(b"\xef\xbb\xbfHello World")
        
        assert not is_binary_file(utf8_file)
    
    def test_binary_extensions(self, tmp_path):
        """Test that files with binary extensions are detected as binary."""
        binary_files = [
            ("test.jpg", b"fake jpeg data"),
            ("test.png", b"fake png data"),
            ("test.pdf", b"fake pdf data"),
            ("test.zip", b"fake zip data"),
            ("test.mp3", b"fake mp3 data"),
            ("test.dll", b"fake dll data"),
            ("test.exe", b"fake exe data"),
        ]
        
        for filename, content in binary_files:
            binary_file = tmp_path / filename
            binary_file.write_bytes(content)
            assert is_binary_file(binary_file), f"Failed for {filename}"
    
    def test_text_extensions(self, tmp_path):
        """Test that files with text extensions are not detected as binary."""
        text_files = [
            ("test.py", "def hello(): pass"),
            ("test.js", "console.log('hello')"),
            ("test.json", '{"key": "value"}'),
            ("test.xml", "<root></root>"),
            ("test.txt", "Hello world"),
            ("test.md", "# Markdown"),
            ("test.csv", "a,b,c\n1,2,3"),
        ]
        
        for filename, content in text_files:
            text_file = tmp_path / filename
            text_file.write_text(content)
            assert not is_binary_file(text_file), f"Failed for {filename}"
    
    def test_unicode_text(self, tmp_path):
        """Test that Unicode text files are not detected as binary."""
        unicode_file = tmp_path / "unicode.txt"
        unicode_file.write_text("Hello 🌍 World\nEmoji: 😀\n")
        
        assert not is_binary_file(unicode_file)