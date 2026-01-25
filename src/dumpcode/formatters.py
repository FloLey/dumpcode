"""Tree formatting utilities for DumpCode."""

from typing import List

from .core import TreeEntry


# ASCII tree drawing constants
PREFIX_MIDDLE = "├── "
PREFIX_LAST = "└── "
PREFIX_PASS = "│   "
PREFIX_EMPTY = "    "


def format_ascii_tree(entries: List[TreeEntry]) -> List[str]:
    """Convert a list of TreeEntry objects into ASCII tree lines.
    
    Args:
        entries: List of TreeEntry objects representing the directory structure
        
    Returns:
        List of formatted ASCII tree lines
    """
    lines = []
    
    for entry in entries:
        prefix_parts = []
        if entry.ancestor_is_last:
            for depth in range(entry.depth):
                if depth < len(entry.ancestor_is_last):
                    if entry.ancestor_is_last[depth]:
                        prefix_parts.append(PREFIX_EMPTY)
                    else:
                        prefix_parts.append(PREFIX_PASS)
        
        prefix = "".join(prefix_parts)
        pointer = PREFIX_LAST if entry.is_last else PREFIX_MIDDLE
        
        if entry.is_dir:
            name = f"{entry.path.name}/"
        else:
            name = entry.path.name
        
        if entry.error_msg:
            line = f"{prefix}{pointer}{name} {entry.error_msg}"
        else:
            line = f"{prefix}{pointer}{name}"
        
        lines.append(line)
    
    return lines