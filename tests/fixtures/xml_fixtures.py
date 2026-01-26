"""XML validation fixtures for DumpCode tests."""

import pytest

from .output_checker import OutputChecker


@pytest.fixture
def validate_xml():
    """Fixture to validate XML content using improved XML parsing.
    
    The dumpcode output format contains multiple XML fragments:
    - <instructions>...</instructions>
    - <dump>...</dump>
    - <task>...</task>
    
    This validator uses proper XML parsing instead of regex.
    
    Returns:
        A function that validates XML content
    """
    def _validate(content: str) -> None:
        """Validate that content is well-formed XML.
        
        Args:
            content: String content to validate as XML
            
        Raises:
            AssertionError: If content is not valid XML
        """
        OutputChecker.validate_xml_structure(content)
    
    return _validate