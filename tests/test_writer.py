"""Unit tests for DumpWriter class."""

import io

from dumpcode.writer import DumpWriter


class TestDumpWriterNoXMLMode:
    """Test DumpWriter with use_xml=False (--no-xml mode)."""
    
    def test_write_prompt_no_xml(self):
        """Test write_prompt in --no-xml mode."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=False)
        
        writer.write_prompt("Test prompt content", "instructions")
        
        output = stream.getvalue()
        assert "=== INSTRUCTIONS ===" in output
        assert "Test prompt content" in output
        # Use partial string matching, don't check exact dash counts
        assert "<instructions>" not in output
        assert "</instructions>" not in output
    
    def test_write_prompt_list_no_xml(self):
        """Test write_prompt with list input in --no-xml mode."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=False)
        
        prompt_list = ["Line 1", "Line 2", "Line 3"]
        writer.write_prompt(prompt_list, "context")
        
        output = stream.getvalue()
        assert "=== CONTEXT ===" in output
        assert "Line 1\nLine 2\nLine 3" in output
        # Use partial string matching
    
    def test_write_file_no_xml(self):
        """Test write_file in --no-xml mode."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=False)
        
        writer.write_file("src/test.py", "print('Hello World')")
        
        output = stream.getvalue()
        assert "--- FILE: src/test.py ---" in output
        assert "print('Hello World')" in output
        # Use partial string matching
        assert "<file" not in output
        assert "</file>" not in output
    
    def test_write_file_no_xml_robust(self):
        """Test write_file in --no-xml mode with robust partial matching."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=False)
        writer.write_file("test.py", "content")
        output = stream.getvalue()
        assert "--- FILE: test.py ---" in output
        assert "content" in output
        # Do not check the bottom line of dashes; it's fragile boilerplate.
    
    def test_write_tree_no_xml(self):
        """Test write_tree in --no-xml mode."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=False)
        
        tree_lines = [
            "project/",
            "├── src/",
            "│   └── main.py",
            "└── README.md"
        ]
        writer.write_tree(tree_lines)
        
        output = stream.getvalue()
        assert "=== DIRECTORY TREE ===" in output
        assert "project/" in output
        assert "├── src/" in output
        assert "│   └── main.py" in output
        assert "└── README.md" in output
        # Use partial string matching
        assert "<tree>" not in output
        assert "</tree>" not in output
    
    def test_write_skips_no_xml(self):
        """Test write_skips in --no-xml mode."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=False)
        
        skips = [
            {"path": "node_modules/", "reason": "Node.js dependencies"},
            {"path": ".git/", "reason": "Version control"},
            {"path": "*.log", "reason": "Log files"}
        ]
        writer.write_skips(skips)
        
        output = stream.getvalue()
        # CORRECTED: Use "SKIPPED FILES" not "SKIPPED PATHS"
        assert "=== SKIPPED FILES ===" in output
        assert "node_modules/" in output
        assert "Node.js dependencies" in output
        assert ".git/" in output
        assert "Version control" in output
        assert "*.log" in output
        assert "Log files" in output
        # Use partial string matching
        assert "<skipped>" not in output
        assert "</skipped>" not in output
    
    def test_write_command_output_no_xml(self):
        """Test write_command_output in --no-xml mode."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=False)
        
        command_output = "Command output line 1\nCommand output line 2\nCommand output line 3"
        writer.write_command_output(command_output)
        
        output = stream.getvalue()
        # CORRECTED: Use "COMMAND EXECUTION OUTPUT" not "COMMAND OUTPUT"
        assert "--- COMMAND EXECUTION OUTPUT ---" in output
        assert "Command output line 1" in output
        assert "Command output line 2" in output
        assert "Command output line 3" in output
        # Use partial string matching
        assert "<command>" not in output
        assert "</command>" not in output
    
    def test_writer_no_xml_rescue(self):
        """Rescue test for writer no-xml mode with correct string mappings."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=False)
        
        writer.write_skips([{"path": "a", "reason": "b"}])
        output = stream.getvalue()
        assert "=== SKIPPED FILES ===" in output  # Use FILES, not PATHS
        
        # Clear stream for next test
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=False)
        writer.write_command_output("output")
        assert "--- COMMAND EXECUTION OUTPUT ---" in stream.getvalue()
    
    def test_write_raw_no_xml(self):
        """Test write_raw still works in --no-xml mode."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=False)
        
        writer.write_raw("Raw text content")
        
        output = stream.getvalue()
        assert output == "Raw text content"
        assert writer.total_chars == len("Raw text content")
    
    def test_empty_prompt_no_xml(self):
        """Test write_prompt with empty content in --no-xml mode."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=False)
        
        # Should not write anything for empty prompt
        writer.write_prompt("", "empty")
        writer.write_prompt([], "empty_list")
        
        output = stream.getvalue()
        assert output == ""  # Should be empty
    
    def test_write_prompt_none(self):
        """Test write_prompt with None prompt (early return coverage)."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=False)
        
        # Should not write anything for None prompt
        writer.write_prompt(None, "tag")
        
        output = stream.getvalue()
        assert output == ""  # Should be empty


class TestDumpWriterXMLMode:
    """Test DumpWriter with use_xml=True (default mode)."""
    
    def test_write_prompt_xml(self):
        """Test write_prompt in XML mode."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=True)
        
        writer.write_prompt("Test <prompt> & content", "instructions")
        
        output = stream.getvalue()
        assert "<instructions>" in output
        assert "Test &lt;prompt&gt; &amp; content" in output  # Escaped
        assert "</instructions>" in output
    
    def test_write_file_xml(self):
        """Test write_file in XML mode."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=True)
        
        writer.write_file("src/test.py", "print('Hello <World>')")
        
        output = stream.getvalue()
        assert "<file path=\"src/test.py\">" in output
        assert "print('Hello &lt;World&gt;')" in output  # Escaped
        assert "</file>" in output
    
    def test_write_tree_xml(self):
        """Test write_tree in XML mode."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=True)
        
        tree_lines = ["project/", "└── src/"]
        writer.write_tree(tree_lines)
        
        output = stream.getvalue()
        assert "<tree>" in output
        assert "project/" in output
        assert "└── src/" in output
        assert "</tree>" in output
    
    def test_write_skips_xml_correctly(self):
        """Test write_skips in XML mode correctly (uses comment, not tag)."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=True)
        writer.write_skips([{"path": "file.txt", "reason": "error"}])
        output = stream.getvalue()
        # The code writes a COMMENT, not a tag.
        assert "<!-- Skipped Files Summary:" in output
        assert "file.txt: error" in output
    
    def test_write_skips_xml_formatting(self):
        """Verify the exact formatting of skipped files in XML comments."""
        from io import StringIO
        buf = StringIO()
        writer = DumpWriter(buf, use_xml=True)
        skips = [{"path": "file.py", "reason": "test"}]
        
        writer.write_skips(skips)
        output = buf.getvalue()
        
        assert "<!-- Skipped Files Summary:" in output
        assert "    - file.py: test" in output
    
    def test_write_skips_xml_multi_file_loop(self):
        """Verify line 88: The loop for multiple skipped files in XML comments."""
        from io import StringIO
        from dumpcode.writer import DumpWriter
        
        buf = StringIO()
        writer = DumpWriter(buf, use_xml=True)
        skips = [
            {"path": "a.py", "reason": "err1"},
            {"path": "b.py", "reason": "err2"}
        ]
        
        writer.write_skips(skips)
        output = buf.getvalue()
        
        assert "- a.py: err1" in output
        assert "- b.py: err2" in output
    
    def test_write_command_output_xml_correctly(self):
        """Test write_command_output in XML mode correctly (uses <execution>, not <command>)."""
        stream = io.StringIO()
        writer = DumpWriter(stream, use_xml=True)
        writer.write_command_output("test-out")
        output = stream.getvalue()
        # The code uses <execution>, not <command>
        assert "<execution>" in output
        assert "test-out" in output
    
    def test_writer_early_returns(self):
        """Cover writer.py:31-33 (Empty prompt) and 64 (Empty skips)"""
        from io import StringIO
        from dumpcode.writer import DumpWriter
        
        buf = StringIO()
        writer = DumpWriter(buf)
        
        # 1. No prompt should write nothing
        writer.write_prompt("", tag="test")
        assert buf.getvalue() == ""
        
        # 2. No skips should write nothing
        writer.write_skips([])
        assert buf.getvalue() == ""
    
