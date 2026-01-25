"""DumpEngine - Core orchestration engine for DumpCode."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Set

from .constants import DEFAULT_POST, DEFAULT_PRE, DEFAULT_PROFILES
from .core import DumpSession, DumpSettings
from .formatters import format_ascii_tree
from .processors import get_file_content
from .utils import copy_to_clipboard_osc52, setup_logger
from .writer import DumpWriter
from .config import increment_config_version


class DumpEngine:
    """Orchestrate the entire dumping process from file discovery to final output."""

    def __init__(self, config: Dict[str, Any], settings: DumpSettings):
        """Initialize the engine with configuration and session settings."""
        self.config = config
        self.settings = settings
        self.logger = setup_logger("dumpcode")

    def run(self) -> None:
        """Execute the complete dump process including tree walking and file writing."""
        output_file = self.settings.output_file.resolve()
        profile = self._get_active_profile()

        excluded = set(self.config.get("ignore_patterns", []))
        self._exclude_output_file(output_file, excluded)

        session = DumpSession(
            self.settings.start_path,
            excluded,
            self.settings.max_depth,
            self.settings.dir_only,
            self.settings.git_changed_only
        )
        
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Generating directory tree from: {self.settings.start_path}")
        
        session.generate_tree(self.settings.start_path)
        
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Tree generated: {session.dir_count} dirs, {session.file_count} files")
        
        tree_lines = format_ascii_tree(session.tree_entries)
        
        tree_lines.insert(0, f"Project Root: {self.settings.start_path.as_posix()}")
        tree_lines.insert(1, f"{self.settings.start_path.name}/")

        if self.settings.git_changed_only:
            session.filter_git_changed_files()

        use_xml = self.settings.use_xml

        try:
            out_dir = output_file.parent
            if out_dir and not out_dir.exists():
                out_dir.mkdir(parents=True)

            with open(output_file, "w", encoding="utf-8") as f:
                writer = DumpWriter(f, use_xml=use_xml)
                version = self.config.get("version", 1)

                pre_prompt = profile.get("pre") if profile else DEFAULT_PRE
                if pre_prompt:
                    writer.write_prompt(pre_prompt, tag="instructions")

                writer.start_dump(version)
                writer.write_tree(tree_lines)

                writer.start_files()
                if not self.settings.structure_only:
                    if session.files_to_dump:
                        for file_path in session.files_to_dump:
                            rel = file_path.relative_to(self.settings.start_path).as_posix()
                            if self.logger.isEnabledFor(logging.DEBUG):
                                self.logger.debug(f"Processing: {rel}")
                            content, error_msg = get_file_content(file_path, self.settings.ignore_errors)
                            writer.write_file(rel, content)
                            if error_msg:
                                session.log_skip(file_path, error_msg)
                                if self.logger.isEnabledFor(logging.DEBUG):
                                    self.logger.debug(f"Skipped {rel}: {error_msg}")
                    else:
                        writer.write_raw("    [No files found]\n")
                writer.end_files()

                if session.skipped_files:
                    writer.write_skips(session.skipped_files)

                writer.end_dump()

                post_prompt = self.settings.question or (profile.get("post") if profile else DEFAULT_POST)
                if post_prompt:
                    writer.write_prompt(post_prompt, tag="task")

            self._finalize(output_file, session, version, profile, writer.total_chars)

        except Exception as e:
            self.logger.error(f"Error during dump: {e}")
            raise

    def _get_active_profile(self) -> Optional[Dict[str, Any]]:
        """Return the profile already resolved by the CLI layer."""
        return self.settings.active_profile

    def _exclude_output_file(self, output_file: Path, excluded: Set[str]) -> None:
        """Exclude the output file from the dump traversal to avoid self-reference.

        Args:
            output_file: Path to the target output file.
            excluded: Set of current exclusion patterns to update.
        """
        try:
            output_rel = output_file.relative_to(self.settings.start_path)
            if not str(output_rel).startswith(".."):
                excluded.add(str(output_rel))
                excluded.add(output_file.name)
        except ValueError:
            pass

    def _finalize(
        self,
        output_file: Path,
        session: DumpSession,
        version: int,
        profile: Optional[Dict[str, Any]],
        total_chars: int
    ) -> None:
        """Handle post-processing including token estimation, clipboard copy, and logging.

        Args:
            output_file: Final dump path.
            session: Current DumpSession metadata.
            version: Configuration version used.
            profile: Active profile used, if any.
            total_chars: Count of total characters written.
        """
        self.logger.info(f"Dumped to {output_file} (Version {version})")
        self.logger.info(f"Directories: {session.dir_count}, Files: {session.file_count}")

        if profile:
            user_profiles = self.config.get("profiles", {})
            merged_profiles = {**DEFAULT_PROFILES, **user_profiles}
            profile_name = next(name for name, data in merged_profiles.items() if data == profile)
            self.logger.info(f"Profile '{profile_name}' prepended to output.")

        if self.settings.git_changed_only:
            self.logger.info("Only dumping git-modified files")

        try:
            tokens = total_chars // 4
            self.logger.info(f"Estimated Context: {tokens:,} tokens")
            if tokens > 180000:
                self.logger.warning("This dump is approaching the 200k limit.")
        except Exception as e:
            self.logger.warning(f"Could not estimate tokens: {e}")

        if not self.settings.no_copy:
            copy_to_clipboard_osc52(output_file, self.logger)
        
        increment_config_version(self.settings.start_path, self.logger)