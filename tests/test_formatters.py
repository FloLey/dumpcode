"""Unit tests for the formatters module."""

from pathlib import Path

from src.dumpcode.core import TreeEntry
from src.dumpcode.formatters import format_ascii_tree


def test_single_file_entry():
    """Verify a simple root file."""
    entries = [
        TreeEntry(
            path=Path("root/file.txt"),
            depth=0,
            is_last=True,
            is_dir=False,
            ancestor_is_last=[]
        )
    ]
    lines = format_ascii_tree(entries)
    assert lines == ["└── file.txt"]


def test_single_directory_entry():
    """Verify a simple root directory."""
    entries = [
        TreeEntry(
            path=Path("root/dir/"),
            depth=0,
            is_last=True,
            is_dir=True,
            ancestor_is_last=[]
        )
    ]
    lines = format_ascii_tree(entries)
    assert lines == ["└── dir/"]


def test_nested_last_child():
    """Verify that when ancestors are all 'last children', the prefix is empty spaces."""
    # structure:
    # dir/ (last)
    #   subdir/ (last)
    #     file.txt (last)
    entries = [
        TreeEntry(
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


def test_nested_middle_child():
    """Verify that when ancestors are NOT 'last children', the prefix contains vertical bars."""
    # structure:
    # dir/ (middle)
    #   subdir/ (middle)
    #     file.txt (last)
    entries = [
        TreeEntry(
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


def test_mixed_ancestry():
    """Verify mixed states correctly render the tree structure."""
    # structure:
    # root (middle) -> ancestor_is_last[0] = False
    #   sub (last)  -> ancestor_is_last[1] = True
    #     file      -> depth 2
    entries = [
        TreeEntry(
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


def test_entry_with_error():
    """Verify error messages are appended."""
    entry = TreeEntry(
        path=Path("restricted/"),
        depth=0,
        is_last=True,
        is_dir=True,
        error_msg="[Permission Denied]",
        ancestor_is_last=[]
    )
    lines = format_ascii_tree([entry])
    assert lines == ["└── restricted/ [Permission Denied]"]


def test_recursive_link_error():
    """Verify recursive link error messages are appended."""
    entry = TreeEntry(
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


def test_multiple_entries_flat():
    """Verify multiple entries at same depth."""
    entries = [
        TreeEntry(
            path=Path("file1.txt"),
            depth=0,
            is_last=False,
            is_dir=False,
            ancestor_is_last=[]
        ),
        TreeEntry(
            path=Path("file2.txt"),
            depth=0,
            is_last=True,
            is_dir=False,
            ancestor_is_last=[]
        )
    ]
    lines = format_ascii_tree(entries)
    assert lines == ["├── file1.txt", "└── file2.txt"]


def test_complex_tree_structure():
    """Verify a more complex tree structure with mixed depths and types."""
    entries = [
        # Depth 0, middle child (directory)
        TreeEntry(
            path=Path("src/"),
            depth=0,
            is_last=False,
            is_dir=True,
            ancestor_is_last=[]
        ),
        # Depth 1, middle child (file) under src/
        TreeEntry(
            path=Path("src/utils.py"),
            depth=1,
            is_last=False,
            is_dir=False,
            ancestor_is_last=[False]  # parent (src/) is middle child
        ),
        # Depth 1, last child (directory) under src/
        TreeEntry(
            path=Path("src/tests/"),
            depth=1,
            is_last=True,
            is_dir=True,
            ancestor_is_last=[False]  # parent (src/) is middle child
        ),
        # Depth 2, last child (file) under src/tests/
        TreeEntry(
            path=Path("src/tests/test_example.py"),
            depth=2,
            is_last=True,
            is_dir=False,
            ancestor_is_last=[False, True]  # src/ is middle, tests/ is last
        ),
        # Depth 0, last child (file)
        TreeEntry(
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