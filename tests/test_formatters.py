"""Unit tests for the formatters module."""

from io import StringIO
from pathlib import Path

from dumpcode.formatters import format_ascii_tree
from dumpcode.writer import DumpWriter


def test_single_file_entry(tree_entry_factory):
    """Verify a simple root file."""
    entries = [
        tree_entry_factory(
            path=Path("root/file.txt"),
            depth=0,
            is_last=True,
            is_dir=False,
            ancestor_is_last=[]
        )
    ]
    lines = format_ascii_tree(entries)
    assert lines == ["└── file.txt"]


def test_single_directory_entry(tree_entry_factory):
    """Verify a simple root directory."""
    entries = [
        tree_entry_factory(
            path=Path("root/dir/"),
            depth=0,
            is_last=True,
            is_dir=True,
            ancestor_is_last=[]
        )
    ]
    lines = format_ascii_tree(entries)
    assert lines == ["└── dir/"]


def test_nested_last_child(tree_entry_factory):
    """Verify that when ancestors are all 'last children', the prefix is empty spaces."""
    # structure:
    # dir/ (last)
    #   subdir/ (last)
    #     file.txt (last)
    entries = [
        tree_entry_factory(
            path=Path("dir/subdir/file.txt"),
            depth=2,
            is_last=True,
            is_dir=False,
            # Ancestors at depth 0 and 1 are both LAST children
            ancestor_is_last=[True, True]
        )
    ]
    lines = format_ascii_tree(entries)
    # Expected: "    " + "    " + "└── " + "file.txt"
    assert lines == ["        └── file.txt"]


def test_nested_middle_child(tree_entry_factory):
    """Verify that when ancestors are NOT 'last children', the prefix contains vertical bars."""
    # structure:
    # dir/ (middle)
    #   subdir/ (middle)
    #     file.txt (last)
    entries = [
        tree_entry_factory(
            path=Path("dir/subdir/file.txt"),
            depth=2,
            is_last=True,
            is_dir=False,
            # Ancestors at depth 0 and 1 are NOT last children
            ancestor_is_last=[False, False]
        )
    ]
    lines = format_ascii_tree(entries)
    # Expected: "│   " + "│   " + "└── " + "file.txt"
    assert lines == ["│   │   └── file.txt"]


def test_mixed_ancestry(tree_entry_factory):
    """Verify mixed states correctly render the tree structure."""
    # structure:
    # root (middle) -> ancestor_is_last[0] = False
    #   sub (last)  -> ancestor_is_last[1] = True
    #     file      -> depth 2
    entries = [
        tree_entry_factory(
            path=Path("root/sub/file.txt"),
            depth=2,
            is_last=True,
            is_dir=False,
            ancestor_is_last=[False, True]
        )
    ]
    lines = format_ascii_tree(entries)
    # Depth 0 (False) -> "│   "
    # Depth 1 (True)  -> "    "
    # Pointer         -> "└── "
    assert lines == ["│       └── file.txt"]


def test_entry_with_error(tree_entry_factory):
    """Verify error messages are appended."""
    entry = tree_entry_factory(
        path=Path("restricted/"),
        depth=0,
        is_last=True,
        is_dir=True,
        error_msg="[Permission Denied]",
        ancestor_is_last=[]
    )
    lines = format_ascii_tree([entry])
    assert lines == ["└── restricted/ [Permission Denied]"]


def test_recursive_link_error(tree_entry_factory):
    """Verify recursive link error messages are appended."""
    entry = tree_entry_factory(
        path=Path("symlink/"),
        depth=0,
        is_last=False,
        is_dir=True,
        is_recursive_link=True,
        error_msg="[Recursive Link]",
        ancestor_is_last=[]
    )
    lines = format_ascii_tree([entry])
    assert lines == ["├── symlink/ [Recursive Link]"]


def test_multiple_entries_flat(tree_entry_factory):
    """Verify multiple entries at same depth."""
    entries = [
        tree_entry_factory(
            path=Path("file1.txt"),
            depth=0,
            is_last=False,
            is_dir=False,
            ancestor_is_last=[]
        ),
        tree_entry_factory(
            path=Path("file2.txt"),
            depth=0,
            is_last=True,
            is_dir=False,
            ancestor_is_last=[]
        )
    ]
    lines = format_ascii_tree(entries)
    assert lines == ["├── file1.txt", "└── file2.txt"]


def test_complex_tree_structure(tree_entry_factory):
    """Verify a more complex tree structure with mixed depths and types."""
    entries = [
        # Depth 0, middle child (directory)
        tree_entry_factory(
            path=Path("src/"),
            depth=0,
            is_last=False,
            is_dir=True,
            ancestor_is_last=[]
        ),
        # Depth 1, middle child (file) under src/
        tree_entry_factory(
            path=Path("src/utils.py"),
            depth=1,
            is_last=False,
            is_dir=False,
            ancestor_is_last=[False]  # parent (src/) is middle child
        ),
        # Depth 1, last child (directory) under src/
        tree_entry_factory(
            path=Path("src/tests/"),
            depth=1,
            is_last=True,
            is_dir=True,
            ancestor_is_last=[False]  # parent (src/) is middle child
        ),
        # Depth 2, last child (file) under src/tests/
        tree_entry_factory(
            path=Path("src/tests/test_example.py"),
            depth=2,
            is_last=True,
            is_dir=False,
            ancestor_is_last=[False, True]  # src/ is middle, tests/ is last
        ),
        # Depth 0, last child (file)
        tree_entry_factory(
            path=Path("README.md"),
            depth=0,
            is_last=True,
            is_dir=False,
            ancestor_is_last=[]
        )
    ]
    lines = format_ascii_tree(entries)
    expected = [
        "├── src/",
        "│   ├── utils.py",
        "│   └── tests/",
        "│       └── test_example.py",
        "└── README.md"
    ]
    assert lines == expected


def test_writer_write_skips():
    """Test DumpWriter.write_skips method."""
    output = StringIO()
    writer = DumpWriter(output, use_xml=True)
    
    skips = [
        {"path": "bad.txt", "reason": "permission denied"},
        {"path": "secret.key", "reason": "security exclusion"},
        {"path": "corrupt.dat", "reason": "encoding error"}
    ]
    
    writer.write_skips(skips)
    
    result = output.getvalue()
    assert "<!-- Skipped Files Summary:" in result
    assert "- bad.txt: permission denied" in result
    assert "- secret.key: security exclusion" in result
    assert "- corrupt.dat: encoding error" in result
    assert "-->" in result


def test_writer_write_skips_empty():
    """Test DumpWriter.write_skips with empty list."""
    output = StringIO()
    writer = DumpWriter(output, use_xml=True)
    
    writer.write_skips([])
    
    result = output.getvalue()
    assert result == ""  # Should not write anything for empty skips


def test_writer_write_skips_without_xml():
    """Test DumpWriter.write_skips when use_xml is False."""
    output = StringIO()
    writer = DumpWriter(output, use_xml=False)
    
    skips = [{"path": "test.txt", "reason": "test reason"}]
    writer.write_skips(skips)
    
    result = output.getvalue()
    # Even without XML mode, skips should still be written as XML comments
    assert "<!-- Skipped Files Summary:" in result
    assert "- test.txt: test reason" in result


def test_writer_write_skips_format():
    """Test the exact format of write_skips output."""
    output = StringIO()
    writer = DumpWriter(output, use_xml=True)
    
    skips = [{"path": "example.py", "reason": "could not read"}]
    writer.write_skips(skips)
    
    result = output.getvalue()
    expected = "  <!-- Skipped Files Summary:\n    - example.py: could not read\n  -->\n"
    assert result == expected