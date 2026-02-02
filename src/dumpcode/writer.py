"""Output writer for DumpCode."""

from typing import Dict, List, TextIO, Union
from xml.sax.saxutils import escape


class DumpWriter:
    """Write the codebase dump in a structured XML format."""

    def __init__(self, stream: TextIO, use_xml: bool = True):
        """Initialize the output writer.

        Args:
            stream: The file-like object to write to.
            use_xml: Whether to wrap output in XML tags.
        """
        self.stream = stream
        self.use_xml = use_xml
        self.total_chars = 0
        self.version = 1  # Defined for Mypy compatibility and default state

    def write_raw(self, text: str) -> None:
        """Write raw text to the stream and update the total character count.

        Args:
            text: String content to write.
        """
        self.total_chars += len(text)
        try:
            self.stream.write(text)
        except OSError:
            # Still count the characters even if write fails
            pass

    def write_prompt(self, prompt: Union[str, List[str]], tag: str) -> None:
        """Write prompt strings or lists into structured XML blocks.

        Args:
            prompt: String content or list of strings to write.
            tag: XML tag name to wrap the content in.
        """
        if not prompt:
            return

        full_text = "\n".join(prompt) if isinstance(prompt, list) else prompt
        clean_text = full_text.strip()
        
        if self.use_xml:
            escaped_text = escape(clean_text)
            self.write_raw(f"\n<{tag}>\n{escaped_text}\n</{tag}>\n\n")
        else:
            # Provide a clean text fallback for --no-xml mode
            self.write_raw(f"\n=== {tag.upper()} ===\n{clean_text}\n===================\n\n")

    def start_dump(self, version: int) -> None:
        """Write the opening XML dump tag with version attribute.

        Args:
            version: The configuration version number.
        """
        if self.use_xml:
            self.write_raw(f'<dump version="{version}">\n')
        else:
            self.write_raw(f"=== DUMP VERSION {version} ===\n\n")

    def write_tree(self, tree_lines: List[str]) -> None:
        """Write the directory tree structure.

        Args:
            tree_lines: List of strings representing the visual tree.
        """
        if self.use_xml:
            self.write_raw("  <tree>\n")
            for line in tree_lines:
                self.write_raw(f"    {line}\n")
            self.write_raw("  </tree>\n")
        else:
            self.write_raw("=== DIRECTORY TREE ===\n")
            for line in tree_lines:
                self.write_raw(f"{line}\n")
            self.write_raw("\n")

    def start_files(self) -> None:
        """Write the opening files container tag."""
        if self.use_xml:
            self.write_raw("  <files>\n")
        else:
            self.write_raw("=== FILES ===\n")

    def write_file(self, rel_path: str, content: str) -> None:
        """Write a single file's path and content wrapped in file tags.

        Args:
            rel_path: Relative path of the file.
            content: String content of the file.
        """
        if self.use_xml:
            escaped_path = escape(rel_path, entities={'"': "&quot;"})
            escaped_content = escape(content)
            self.write_raw(f'    <file path="{escaped_path}">\n{escaped_content}\n    </file>\n')
        else:
            self.write_raw(f"--- FILE: {rel_path} ---\n{content}\n\n")

    def end_files(self) -> None:
        """Write the closing files container tag."""
        if self.use_xml:
            self.write_raw("  </files>\n")
        # No closing needed for non-XML mode

    def write_skips(self, skips: List[Dict[str, str]]) -> None:
        """Write a summary of files that were skipped during processing.

        Args:
            skips: List of dictionaries containing 'path' and 'reason'.
        """
        if not skips:
            return
        
        if self.use_xml:
            self.write_raw("  <!-- Skipped Files Summary:\n")
            for s in skips:
                self.write_raw(f"    - {s['path']}: {s['reason']}\n")
            self.write_raw("  -->\n")
        else:
            self.write_raw("=== SKIPPED FILES ===\n")
            for s in skips:
                self.write_raw(f"- {s['path']}: {s['reason']}\n")
            self.write_raw("\n")

    def end_dump(self) -> None:
        """Write the closing XML dump tag."""
        if self.use_xml:
            self.write_raw("</dump>\n")
        # No closing needed for non-XML mode

    def write_command_output(self, output: str) -> None:
        """Write the output of an external command execution.
        
        Wraps content in <execution> tags and ensures XML safety.
        
        Args:
            output: The raw output string from the shell command.
        """
        if not output:
            return
        
        if self.use_xml:
            escaped_output = escape(output)
            self.write_raw(f"\n  <execution>\n{escaped_output}\n  </execution>\n")
        else:
            # Provide a clean text fallback for --no-xml mode
            self.write_raw(f"\n--- COMMAND EXECUTION OUTPUT ---\n{output}\n------------------------------\n")