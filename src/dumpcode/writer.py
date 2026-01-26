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

    def write_raw(self, text: str) -> None:
        """Write raw text to the stream and update the total character count.

        Args:
            text: String content to write.
        """
        self.total_chars += len(text)
        self.stream.write(text)

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
        escaped_text = escape(clean_text)
        self.write_raw(f"\n<{tag}>\n{escaped_text}\n</{tag}>\n\n")

    def start_dump(self, version: int) -> None:
        """Write the opening XML dump tag with version attribute.

        Args:
            version: The configuration version number.
        """
        self.write_raw(f'<dump version="{version}">\n')

    def write_tree(self, tree_lines: List[str]) -> None:
        """Write the directory tree structure.

        Args:
            tree_lines: List of strings representing the visual tree.
        """
        self.write_raw("  <tree>\n")
        for line in tree_lines:
            self.write_raw(f"    {line}\n")
        self.write_raw("  </tree>\n")

    def start_files(self) -> None:
        """Write the opening files container tag."""
        self.write_raw("  <files>\n")

    def write_file(self, rel_path: str, content: str) -> None:
        """Write a single file's path and content wrapped in file tags.

        Args:
            rel_path: Relative path of the file.
            content: String content of the file.
        """
        escaped_path = escape(rel_path, entities={'"': "&quot;"})
        escaped_content = escape(content)
        self.write_raw(f'    <file path="{escaped_path}">\n{escaped_content}\n    </file>\n')

    def end_files(self) -> None:
        """Write the closing files container tag."""
        self.write_raw("  </files>\n")

    def write_skips(self, skips: List[Dict[str, str]]) -> None:
        """Write a summary of files that were skipped during processing.

        Args:
            skips: List of dictionaries containing 'path' and 'reason'.
        """
        if not skips:
            return
        self.write_raw("  <!-- Skipped Files Summary:\n")
        for s in skips:
            self.write_raw(f"    - {s['path']}: {s['reason']}\n")
        self.write_raw("  -->\n")

    def end_dump(self) -> None:
        """Write the closing XML dump tag."""
        self.write_raw("</dump>\n")

    def write_command_output(self, output: str) -> None:
        """Write the output of an external command execution.
        
        Wraps content in <execution> tags and ensures XML safety.
        """
        if not output:
            return
        
        escaped_output = escape(output)
        self.write_raw(f"\n  <execution>\n{escaped_output}\n  </execution>\n")