"""OutputChecker helper for validating dumpcode output structure."""

import re
import xml.etree.ElementTree as ET
from xml.parsers.expat import ExpatError
from typing import List

import pytest


class OutputChecker:
    """Helper class for validating dumpcode output structure."""
    
    REQUIRED_TAGS = ["<instructions>", "<dump", "<files>", "<task>"]
    
    @classmethod
    def validate_sandwich_structure(cls, content: str) -> None:
        """Validate the 'sandwich' structure of dumpcode output.
        
        Args:
            content: The output content to validate
            
        Raises:
            AssertionError: If any required tag is missing
        """
        missing_tags = []
        for tag in cls.REQUIRED_TAGS:
            if tag not in content:
                missing_tags.append(tag)
        
        if missing_tags:
            raise AssertionError(
                f"Missing required tags in output: {missing_tags}\n"
                f"Content preview: {content[:500]}..."
            )
    
    @classmethod
    def validate_xml_structure(cls, content: str) -> None:
        """Validate XML structure using proper XML parsing instead of regex.
        
        Args:
            content: The output content to validate
            
        Raises:
            AssertionError: If XML is not well-formed
        """
        # Wrap the entire content in a dummy root tag
        wrapped_content = f"<dummy_root>{content}</dummy_root>"
        
        try:
            # Try to parse as a single XML document
            ET.fromstring(wrapped_content)
        except ExpatError as e:
            # If parsing fails, try to identify which section is broken
            cls._diagnose_xml_issue(content, e)
    
    @classmethod
    def _diagnose_xml_issue(cls, content: str, original_error: ExpatError) -> None:
        """Diagnose XML parsing issues by testing individual sections.
        
        Args:
            content: The output content
            original_error: The original parsing error
            
        Raises:
            AssertionError: With detailed error information
        """
        # Try to find XML sections
        sections = cls._extract_xml_sections(content)
        
        if not sections:
            raise AssertionError(
                f"No XML sections found in content. Original error: {original_error}\n"
                f"Content preview: {content[:500]}..."
            )
        
        # Test each section individually
        broken_sections = []
        for i, section in enumerate(sections):
            try:
                ET.fromstring(f"<dummy>{section}</dummy>")
            except ExpatError as e:
                broken_sections.append((i, section, str(e)))
        
        if broken_sections:
            error_msg = f"Found {len(broken_sections)} broken XML section(s):\n"
            for i, section, error in broken_sections:
                error_msg += f"\nSection {i} error: {error}\n"
                error_msg += f"Section content (first 200 chars): {section[:200]}...\n"
            raise AssertionError(error_msg)
        else:
            # All sections parse individually, issue might be with inter-section content
            raise AssertionError(
                f"XML parsing failed but all sections parse individually. "
                f"Original error: {original_error}\n"
                f"Content preview: {content[:500]}..."
            )
    
    @classmethod
    def _extract_xml_sections(cls, content: str) -> List[str]:
        """Extract XML sections from content.
        
        Args:
            content: The output content
            
        Returns:
            List of XML section strings
        """
        sections = []
        # Look for XML tags and try to extract complete elements
        # This is a simple heuristic - for more robust extraction,
        # we could use an incremental parser
        tag_pattern = r'<([a-zA-Z][a-zA-Z0-9_-]*)(?:\s+[^>]*)?>'
        pos = 0
        
        while pos < len(content):
            # Find next opening tag
            match = re.search(tag_pattern, content[pos:])
            if not match:
                break
            
            tag_name = match.group(1)
            start = pos + match.start()
            
            # Look for closing tag
            closing_pattern = f'</{tag_name}>'
            closing_match = re.search(closing_pattern, content[start:])
            
            if closing_match:
                end = start + closing_match.end()
                sections.append(content[start:end])
                pos = end
            else:
                # No closing tag found, move past this tag
                pos = start + len(match.group(0))
        
        return sections


@pytest.fixture
def assert_sandwich_structure():
    """Fixture that returns a function to validate sandwich structure."""
    def _validate(content: str) -> None:
        OutputChecker.validate_sandwich_structure(content)
    return _validate


@pytest.fixture
def validate_xml_improved():
    """Improved XML validation fixture using proper XML parsing."""
    def _validate(content: str) -> None:
        OutputChecker.validate_xml_structure(content)
    return _validate