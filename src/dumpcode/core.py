"""Core dumping logic, file system traversal, and session management."""

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .constants import CONFIG_FILENAME
from .utils import get_git_modified_files


@dataclass
class DumpSettings:
    """Container for dump execution parameters.

    Attributes:
        start_path: Path to the root of the codebase to be dumped.
        output_file: Path where the resulting dump file will be saved.
        max_depth: Maximum recursion depth for directory traversal.
        dir_only: Whether to only include directory structures.
        ignore_errors: Whether to suppress encoding/read errors.
        structure_only: Whether to omit file contents in the dump.
        no_copy: Whether to skip OSC52 clipboard copying.
        use_xml: Whether to wrap output in semantic XML tags.
        git_changed_only: Whether to only dump files modified in git.
        question: Optional user instruction to append to the prompt.
        verbose: Whether to show detailed processing logs.
    """
    start_path: Path
    output_file: Path
    max_depth: Optional[int] = None
    dir_only: bool = False
    ignore_errors: bool = False
    structure_only: bool = False
    no_copy: bool = False
    use_xml: bool = True
    git_changed_only: bool = False
    question: Optional[str] = None
    active_profile: Optional[Dict[str, Any]] = None
    reset_version: bool = False
    verbose: bool = False


@dataclass
class TreeEntry:
    """Represents a single entry in the directory tree structure.
    
    Attributes:
        path: Full path to the file or directory
        depth: Depth in the tree (0 = root)
        is_last: Whether this entry is the last child of its parent
        is_dir: Whether this entry is a directory
        is_recursive_link: Whether this entry is a recursive symlink
        error_msg: Optional error message if there was an issue accessing this entry
        ancestor_is_last: List indicating if each ancestor at depth N is a last child
    """
    path: Path
    depth: int
    is_last: bool
    is_dir: bool
    is_recursive_link: bool = False
    error_msg: Optional[str] = None
    ancestor_is_last: Optional[List[bool]] = None


class DumpSession:
    """Encapsulate the state of a single dump execution.

    Manage directory traversal, exclusion logic, and file collection.
    """

    def __init__(
        self,
        root_path: Path,
        excluded_patterns: Set[str],
        max_depth: Optional[int],
        dir_only: bool,
        git_changed_only: bool = False,
    ) -> None:
        """Initialize the session with scanning constraints.

        Args:
            root_path: Base directory for the dump.
            excluded_patterns: Set of glob patterns to ignore.
            max_depth: Depth limit for directory traversal.
            dir_only: If True, skip file contents.
            git_changed_only: If True, only include files modified in git.
        """
        self.root_path = root_path
        self.excluded_patterns = excluded_patterns
        self.max_depth = max_depth
        self.dir_only = dir_only
        self.git_changed_only = git_changed_only

        self.dir_count = 0
        self.file_count = 0
        self.tree_entries: List[TreeEntry] = []
        self.files_to_dump: List[Path] = []
        self.skipped_files: List[Dict[str, str]] = []
        self.visited_paths: Set[Path] = set()
        self.gitignore_spec = self._load_gitignore(root_path)

    def _load_gitignore(self, root_path: Path) -> Optional[Any]:
        """Load .gitignore file using pathspec if available.

        Args:
            root_path: Base directory to search for .gitignore.

        Returns:
            A pathspec.PathSpec instance if gitignore exists and pathspec is installed,
            otherwise None.
        """
        gitignore_path = root_path / ".gitignore"
        if gitignore_path.exists():
            try:
                import pathspec
                with open(gitignore_path, "r") as f:
                    return pathspec.PathSpec.from_lines('gitwildmatch', f)
            except ImportError:
                return None
        return None

    def log_skip(self, path: Path, reason: str) -> None:
        """Log a file that was skipped during processing.

        Args:
            path: The Path object of the skipped file.
            reason: A description of why the file was skipped.
        """
        self.skipped_files.append({"path": str(path), "reason": reason})

    def is_excluded(self, item_path: Path) -> bool:
        """Check if a path should be ignored based on patterns and gitignore.

        Args:
            item_path: The path to check for exclusion.

        Returns:
            True if the path matches exclusion patterns, False otherwise.
        """
        name = item_path.name

        if name == CONFIG_FILENAME:
            return True

        if not self.excluded_patterns:
            return False

        rel_path = item_path.relative_to(self.root_path).as_posix()

        for pattern in self.excluded_patterns:
            clean_pattern = pattern.rstrip('/')

            if "/" not in clean_pattern:
                if fnmatch.fnmatch(name, clean_pattern):
                    return True

            if fnmatch.fnmatch(rel_path, clean_pattern):
                return True

            if rel_path.startswith(clean_pattern + "/") or rel_path == clean_pattern:
                return True

        if self.gitignore_spec:
            rel_path = item_path.relative_to(self.root_path).as_posix()
            if self.gitignore_spec.match_file(rel_path):
                return True

        return False

    def generate_tree(
        self,
        current_path: Path,
        depth: int = 0,
        ancestor_is_last: Optional[List[bool]] = None
    ) -> None:
        """Recursively walk the directory and build the tree representation.
        
        Args:
            current_path: Current directory being processed
            depth: Current depth in the tree (0 = root)
            ancestor_is_last: List indicating if each ancestor at depth N is a last child
        """
        if ancestor_is_last is None:
            ancestor_is_last = []
        
        if self.max_depth is not None and depth > self.max_depth:
            return

        try:
            real_path = current_path.resolve()
            if real_path in self.visited_paths:
                self.tree_entries.append(TreeEntry(
                    path=current_path,
                    depth=depth,
                    is_last=False,
                    is_dir=True,
                    is_recursive_link=True,
                    error_msg="[Recursive Link]",
                    ancestor_is_last=ancestor_is_last.copy()
                ))
                return
            self.visited_paths.add(real_path)
        except OSError:
            pass

        try:
            with os.scandir(current_path) as it:
                entries = sorted(it, key=lambda e: e.name.lower())
        except PermissionError:
            self.tree_entries.append(TreeEntry(
                path=current_path,
                depth=depth,
                is_last=False,
                is_dir=True,
                error_msg="[Permission Denied]",
                ancestor_is_last=ancestor_is_last.copy()
            ))
            return
        except FileNotFoundError:
            return

        valid_entries = []
        for entry in entries:
            entry_path = Path(entry.path)
            if not self.is_excluded(entry_path):
                valid_entries.append(entry)

        dirs = [e for e in valid_entries if e.is_dir()]
        files = [e for e in valid_entries if e.is_file()] if not self.dir_only else []

        items = dirs + files
        count = len(items)

        for i, entry in enumerate(items):
            is_last = (i == count - 1)
            entry_path = Path(entry.path)

            entry_ancestor_is_last = ancestor_is_last.copy()
            entry_ancestor_is_last.append(is_last)

            if entry.is_dir():
                self.tree_entries.append(TreeEntry(
                    path=entry_path,
                    depth=depth,
                    is_last=is_last,
                    is_dir=True,
                    ancestor_is_last=ancestor_is_last.copy()
                ))
                self.dir_count += 1

                self.generate_tree(
                    entry_path,
                    depth=depth + 1,
                    ancestor_is_last=entry_ancestor_is_last
                )
            else:
                self.tree_entries.append(TreeEntry(
                    path=entry_path,
                    depth=depth,
                    is_last=is_last,
                    is_dir=False,
                    ancestor_is_last=ancestor_is_last.copy()
                ))
                self.file_count += 1
                self.files_to_dump.append(entry_path)

    def filter_git_changed_files(self) -> None:
        """Filter files_to_dump to only include git-modified files."""
        if not self.git_changed_only:
            return

        git_files = get_git_modified_files(self.root_path)
        git_file_set = set(git_files)

        self.files_to_dump = [f for f in self.files_to_dump if f in git_file_set]
        self.file_count = len(self.files_to_dump)