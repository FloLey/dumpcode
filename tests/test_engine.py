"""Integration tests for DumpEngine."""

from src.dumpcode.constants import DEFAULT_PROFILES
from src.dumpcode.core import DumpSettings
from src.dumpcode.engine import DumpEngine


def test_engine_output_sandwich(tmp_path):
    """Test the complete sandwich output structure."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "hello.py").write_text("print('hi')")
    
    out_file = tmp_path / "dump.txt"
    # Use a profile name that exists in DEFAULT_PROFILES
    test_profile = DEFAULT_PROFILES["readme"]
    
    settings = DumpSettings(
        start_path=tmp_path,
        output_file=out_file,
        use_xml=True,
        active_profile=test_profile
    )
    
    engine = DumpEngine(config={"ignore_patterns": []}, settings=settings)
    engine.run()
    
    content = out_file.read_text()
    
    # Verify semantic XML structure
    assert "<instructions>" in content
    assert "<task>" in content
    assert "<dump version=" in content
    assert "<tree>" in content
    assert "<files>" in content
    assert "<file path=\"src/hello.py\">" in content
    assert "print('hi')" in content
    assert "Act as a Senior Technical Writer" in content
    assert "Output the result in raw Markdown format" in content


def test_engine_without_profile(tmp_path):
    """Test engine with no active profile."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "test.py").write_text("def foo(): pass")
    
    out_file = tmp_path / "dump.txt"
    settings = DumpSettings(
        start_path=tmp_path,
        output_file=out_file,
        use_xml=True,  # Always XML now
        active_profile=None
    )
    
    engine = DumpEngine(config={"ignore_patterns": []}, settings=settings)
    engine.run()
    
    content = out_file.read_text()
    
    # Should use default prompts in XML structure
    assert "<instructions>" in content
    assert "<task>" in content
    assert "<dump version=" in content
    assert "<tree>" in content
    assert "<files>" in content
    assert "<file path=\"src/test.py\">" in content
    assert "def foo(): pass" in content
    assert "Act as an expert software developer and system architect." in content
    assert "Analyze the provided codebase" in content


def test_engine_structure_only(tmp_path):
    """Test engine with structure-only mode."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "file1.py").write_text("content1")
    (src / "file2.py").write_text("content2")
    
    out_file = tmp_path / "dump.txt"
    settings = DumpSettings(
        start_path=tmp_path,
        output_file=out_file,
        structure_only=True,
        use_xml=True,
        active_profile=None
    )
    
    engine = DumpEngine(config={"ignore_patterns": []}, settings=settings)
    engine.run()
    
    content = out_file.read_text()
    
    # Should have tree but no file contents (files section will be empty)
    assert "<tree>" in content
    assert "<files>" in content
    assert "<file path=" not in content  # No files in structure-only mode


def test_engine_with_ignore_patterns(tmp_path):
    """Test engine with ignore patterns."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "keep.py").write_text("keep this")
    (src / "ignore.py").write_text("ignore this")
    
    out_file = tmp_path / "dump.txt"
    settings = DumpSettings(
        start_path=tmp_path,
        output_file=out_file,
        use_xml=True,
        active_profile=None
    )
    
    engine = DumpEngine(
        config={"ignore_patterns": ["*.py"]},  # Ignore all Python files
        settings=settings
    )
    engine.run()
    
    content = out_file.read_text()
    
    # Should not have the ignored file
    assert "keep.py" not in content
    assert "ignore.py" not in content
    assert "<file path=" not in content


def test_engine_dir_only_mode(tmp_path):
    """Test engine with directory-only mode."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "dir1").mkdir()
    (src / "file1.py").write_text("content")
    
    out_file = tmp_path / "dump.txt"
    settings = DumpSettings(
        start_path=tmp_path,
        output_file=out_file,
        dir_only=True,
        use_xml=True,
        active_profile=None
    )
    
    engine = DumpEngine(config={"ignore_patterns": []}, settings=settings)
    engine.run()
    
    content = out_file.read_text()
    
    # Should have directories but no files in tree
    assert "src/" in content
    assert "dir1/" in content
    assert "file1.py" not in content
    # With dir_only=True, files_to_dump should be empty
    assert "<files>" in content
    assert "[No files found]" in content


def test_engine_max_depth(tmp_path):
    """Test engine with max depth limit."""
    # Create nested structure
    level1 = tmp_path / "level1"
    level1.mkdir()
    level2 = level1 / "level2"
    level2.mkdir()
    level3 = level2 / "level3"
    level3.mkdir()
    
    (level1 / "file1.txt").write_text("1")
    (level2 / "file2.txt").write_text("2")
    (level3 / "file3.txt").write_text("3")
    
    out_file = tmp_path / "dump.txt"
    settings = DumpSettings(
        start_path=tmp_path,
        output_file=out_file,
        max_depth=1,  # Only show level1
        use_xml=True,
        active_profile=None
    )
    
    engine = DumpEngine(config={"ignore_patterns": []}, settings=settings)
    engine.run()
    
    content = out_file.read_text()
    
    # Should have level1 but not deeper levels
    # Note: max_depth=1 means depth 0 (root), depth 1 (level1)
    # level1 should be included with its immediate children
    # level2 should appear as a directory but its contents shouldn't be explored
    assert "level1/" in content
    assert "file1.txt" in content
    # level2 should appear as a directory (since it's a child of level1)
    # but file2.txt (inside level2) should not appear
    assert "level2/" in content
    assert "file2.txt" not in content
    assert "level3/" not in content
    assert "file3.txt" not in content


def test_xml_safety_escaping(tmp_path):
    """Test that XML special characters are properly escaped in output."""
    # Create file with problematic name and content
    src = tmp_path / "src"
    src.mkdir()
    (src / 'bad"name.txt').write_text('x < y && z > a')
    
    out_file = tmp_path / "dump.txt"
    settings = DumpSettings(
        start_path=tmp_path,
        output_file=out_file,
        use_xml=True,
        active_profile=None
    )
    
    engine = DumpEngine(config={"ignore_patterns": []}, settings=settings)
    engine.run()
    
    content = out_file.read_text()
    
    # Verify XML escaping
    # Path should have double quotes escaped (path includes src/ prefix)
    assert 'path="src/bad&quot;name.txt"' in content
    # Content should have <, >, and & escaped
    assert 'x &lt; y &amp;&amp; z &gt; a' in content
    # Verify the XML is well-formed (no raw <, >, or & characters in content)
    assert '<file path="src/bad&quot;name.txt">' in content
    assert '</file>' in content