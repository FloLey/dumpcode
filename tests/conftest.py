"""Shared pytest fixtures for DumpCode tests."""

from fixtures.fs_fixtures import (  # noqa: F401
    deep_project,
    default_settings,
    project_env,
    settings_factory,
    tree_entry_factory,
)
from fixtures.git_fixtures import git_repo  # noqa: F401
from fixtures.mock_fixtures import ui_simulation  # noqa: F401
from fixtures.output_checker import (  # noqa: F401
    assert_sandwich_structure,
    validate_xml_improved,
)
from fixtures.xml_fixtures import validate_xml  # noqa: F401