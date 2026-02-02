"""DumpEngine - Core orchestration engine for DumpCode."""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from .constants import DEFAULT_PROFILES
from .core import DumpSession, DumpSettings
from .formatters import format_ascii_tree
from .utils import copy_to_clipboard_osc52, setup_logger, run_shell_command
from .writer import DumpWriter
from .config import increment_config_version


class DumpEngine:
    """Orchestrate the entire dumping process from file discovery to final output."""

    def __init__(
        self, 
        config: Dict[str, Any], 
        settings: DumpSettings,
        session_cls: type[DumpSession] = DumpSession,
        writer_cls: type[DumpWriter] = DumpWriter,
        cmd_runner: Optional[Callable[[str], tuple[int, str]]] = None
    ):
        """Initialize the engine with configuration and session settings.
        
        Args:
            config: Configuration dictionary
            settings: Dump settings
            session_cls: DumpSession class to use (dependency injection point)
            writer_cls: DumpWriter class to use (dependency injection point)
            cmd_runner: Optional callable to run shell commands (defaults to utils.run_shell_command)
        """
        self.config = config
        self.settings = settings
        self.session_cls = session_cls
        self.writer_cls = writer_cls
        self.logger = setup_logger("dumpcode", verbose=settings.verbose)
        self.cmd_runner = cmd_runner or run_shell_command

    def run(self) -> None:
        """Execute the complete dump process including tree walking and file writing."""
        # 1. Setup
        output_file = self.settings.output_file.resolve()
        profile = self._get_active_profile()
        session = self._initialize_session(output_file)
        
        # 2. Collect Data
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

        # 3. Write Output (The Sandwich)
        try:
            out_dir = output_file.parent
            if out_dir and not out_dir.exists():
                out_dir.mkdir(parents=True)

            with open(output_file, "w", encoding="utf-8") as f:
                writer = self.writer_cls(f, use_xml=self.settings.use_xml)
                writer.version = self.config.get("version", 1)
                
                self._write_instructions_block(writer, profile)
                self._write_core_dump_block(writer, session, tree_lines)
                self._write_execution_block(writer, profile)
                self._write_task_block(writer, profile)

            # 4. Post-processing (AI, Clipboard, Versioning)
            self._finalize(output_file, session, profile, writer.total_chars)

        except Exception as e:
            self.logger.error(f"Error during dump: {e}")
            raise

    def _get_active_profile(self) -> Optional[Dict[str, Any]]:
        """Return the prompt profile selected during CLI argument parsing.

        Returns:
            The profile configuration dictionary or None if no profile flag was used.
        """
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

    def _handle_ai_mode(self, output_file: Path, total_chars: int) -> None:
        """Handle AI auto-mode if enabled.
        
        Args:
            output_file: Path to the generated dump file
            total_chars: Total characters in the dump
        """
        # Import here to avoid circular imports and allow graceful failure
        try:
            from .ai import AIOrchestrator
        except ImportError:
            self.logger.error(
                "AI module not available. "
                "Install with: pip install 'dumpcode[ai]'"
            )
            return
        
        # Use AIOrchestrator to handle the AI interaction
        orchestrator = AIOrchestrator(self.settings, self.logger)
        response = orchestrator.run_ai_interaction(output_file)
        
        if response and not response.error and not self.settings.no_copy:
            # Copy AI response to clipboard instead of prompt
            ai_response_path = self.settings.start_path / "ai_response.md"
            from .utils import copy_to_clipboard_osc52
            copy_to_clipboard_osc52(ai_response_path, self.logger)

    def _initialize_session(self, output_file: Path) -> DumpSession:
        """Initialize the DumpSession with exclusion patterns and filesystem metadata.
        
        Args:
            output_file: Path to the target output file
            
        Returns:
            A configured DumpSession instance
        """
        excluded = set(self.config.get("ignore_patterns", []))
        self._exclude_output_file(output_file, excluded)
        
        return self.session_cls(
            self.settings.start_path,
            excluded,
            self.settings.max_depth,
            self.settings.dir_only,
            self.settings.git_changed_only
        )
    
    def _write_instructions_block(self, writer: DumpWriter, profile: Optional[Dict[str, Any]]) -> None:
        """Write the instructions block (pre-prompt)."""
        from .constants import DEFAULT_PRE
        
        pre_prompt = profile.get("pre") if profile else DEFAULT_PRE
        if pre_prompt:
            writer.write_prompt(pre_prompt, tag="instructions")
    
    def _write_core_dump_block(self, writer: DumpWriter, session: DumpSession, tree_lines: List[str]) -> None:
        """Write the core dump block (tree and file contents)."""
        from .processors import get_file_content
        
        writer.start_dump(writer.version)
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
    
    def _write_execution_block(self, writer: DumpWriter, profile: Optional[Dict[str, Any]]) -> None:
        """Write the execution block (run commands)."""
        if profile and "run_commands" in profile:
            commands = profile["run_commands"]
            
            if isinstance(commands, list):
                for cmd in commands:
                    if self.logger:
                        self.logger.info(f"Running: {cmd}")
                    
                    exit_code, output = self.cmd_runner(cmd)
                    
                    if exit_code != 0:
                        self.logger.warning(
                            f"⚠️  Command failed (Exit Code {exit_code}): {cmd}"
                        )
                        # Hint for "Command not found" (127 is standard, some shells use 1)
                        if exit_code == 127: 
                            self.logger.warning("   (Hint: Is the tool installed in your environment?)")
                        # Additional hints for common errors
                        elif "pytest" in cmd and "--cov" in cmd:
                            self.logger.warning("   (Hint: Install pytest-cov: pip install pytest-cov)")

                    # Write output regardless of success (we want to see linter errors)
                    writer.write_command_output(output)
    
    def _write_task_block(self, writer: DumpWriter, profile: Optional[Dict[str, Any]]) -> None:
        """Write the task block (post-prompt)."""
        from .constants import DEFAULT_POST
        
        post_prompt = self.settings.question or (profile.get("post") if profile else DEFAULT_POST)
        if post_prompt:
            writer.write_prompt(post_prompt, tag="task")

    def _finalize(
        self,
        output_file: Path,
        session: DumpSession,
        profile: Optional[Dict[str, Any]],
        total_chars: int
    ) -> None:
        """Handle post-processing including token estimation, clipboard copy, and logging.

        Args:
            output_file: Final dump path.
            session: Current DumpSession metadata.
            profile: Active profile used, if any.
            total_chars: Count of total characters written.
        """
        version = self.config.get("version", 1)
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

        if self.settings.auto_mode:
            self._handle_ai_mode(output_file, total_chars)
            # Skip normal clipboard copy if AI mode succeeded
            # (the AI handler does its own clipboard copy)
        elif not self.settings.no_copy:
            # Normal clipboard copy
            copy_to_clipboard_osc52(output_file, self.logger)
        
        increment_config_version(self.settings.start_path, self.logger)