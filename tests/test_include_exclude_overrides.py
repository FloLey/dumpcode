"""Tests for the include/exclude override system.

Covers:
- Config validation for new fields (include_patterns, additional_excludes, additional_includes)
- Behavior: include overrides re-include excluded paths
- Profile-scoped additional excludes/includes
- Directory traversal into excluded dirs containing included files
- Regression: existing behavior unchanged when new fields are absent/empty
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from dumpcode.config import validate_config, load_or_create_config
from dumpcode.constants import CONFIG_FILENAME
from dumpcode.core import DumpSession, DumpSettings
from dumpcode.engine import DumpEngine


# ---------------------------------------------------------------------------
# 1. Config Validation Tests
# ---------------------------------------------------------------------------

class TestIncludeExcludeValidation:
    """Validate new config fields."""

    def test_old_config_without_new_keys_is_valid(self):
        """Existing configs (no include_patterns, no additional_*) remain valid."""
        config = {
            "version": 1,
            "profiles": {"readme": {"description": "Generate README"}}
        }
        assert validate_config(config) is True

    def test_include_patterns_list_is_valid(self):
        config = {
            "version": 1,
            "include_patterns": ["results/**", "*.jsonl"],
            "profiles": {"readme": {"description": "x"}}
        }
        assert validate_config(config) is True

    def test_include_patterns_empty_list_is_valid(self):
        config = {
            "version": 1,
            "include_patterns": [],
            "profiles": {"readme": {"description": "x"}}
        }
        assert validate_config(config) is True

    def test_include_patterns_non_list_is_invalid(self):
        config = {
            "version": 1,
            "include_patterns": "results/**",
            "profiles": {"readme": {"description": "x"}}
        }
        assert validate_config(config) is False

    def test_profile_additional_excludes_list_is_valid(self):
        config = {
            "version": 1,
            "profiles": {
                "debug": {
                    "description": "Debug",
                    "additional_excludes": ["logs/**"]
                }
            }
        }
        assert validate_config(config) is True

    def test_profile_additional_excludes_non_list_is_invalid(self):
        config = {
            "version": 1,
            "profiles": {
                "debug": {
                    "description": "Debug",
                    "additional_excludes": "logs/**"
                }
            }
        }
        assert validate_config(config) is False

    def test_profile_additional_includes_list_is_valid(self):
        config = {
            "version": 1,
            "profiles": {
                "debug": {
                    "description": "Debug",
                    "additional_includes": ["results/**"]
                }
            }
        }
        assert validate_config(config) is True

    def test_profile_additional_includes_non_list_is_invalid(self):
        config = {
            "version": 1,
            "profiles": {
                "debug": {
                    "description": "Debug",
                    "additional_includes": "results/**"
                }
            }
        }
        assert validate_config(config) is False

    def test_profile_with_only_additional_includes_is_valid(self):
        """A profile having only additional_includes (no description/pre/post) is valid."""
        config = {
            "version": 1,
            "profiles": {
                "include-only": {
                    "additional_includes": ["results/**"]
                }
            }
        }
        assert validate_config(config) is True

    def test_profile_with_only_additional_excludes_is_valid(self):
        config = {
            "version": 1,
            "profiles": {
                "exclude-only": {
                    "additional_excludes": ["logs/**"]
                }
            }
        }
        assert validate_config(config) is True

    def test_profile_empty_additional_lists_are_valid(self):
        config = {
            "version": 1,
            "profiles": {
                "empty": {
                    "description": "Empty overrides",
                    "additional_excludes": [],
                    "additional_includes": []
                }
            }
        }
        assert validate_config(config) is True

    def test_full_config_with_all_new_fields(self):
        """Full config matching the spec example is valid."""
        config = {
            "version": 28,
            "ignore_patterns": [".git", "__pycache__"],
            "include_patterns": ["results/**", "results/**/*.jsonl"],
            "profiles": {
                "readme": {
                    "description": "Generate README",
                    "pre": ["..."],
                    "post": "...",
                },
                "debug-results": {
                    "description": "Include run artifacts",
                    "additional_excludes": ["results/**/runner_logs/**"],
                    "additional_includes": [
                        "results/**/run_report_*.md",
                        "results/**/orchestrator.log"
                    ]
                }
            },
        }
        assert validate_config(config) is True


class TestIncludeExcludeConfigLoad:
    """Test loading configs with new fields."""

    def test_load_config_with_include_patterns(self, tmp_path):
        config_data = {
            "version": 5,
            "ignore_patterns": ["*.pyc"],
            "include_patterns": ["results/**"],
            "profiles": {"test": {"description": "Test"}}
        }
        (tmp_path / CONFIG_FILENAME).write_text(json.dumps(config_data))

        config = load_or_create_config(tmp_path)
        assert config["include_patterns"] == ["results/**"]

    def test_load_config_missing_include_patterns_uses_default(self, tmp_path):
        """Backward compat: missing include_patterns yields empty list from DEFAULT_CONFIG."""
        config_data = {
            "version": 3,
            "profiles": {"test": {"description": "Test"}}
        }
        (tmp_path / CONFIG_FILENAME).write_text(json.dumps(config_data))

        config = load_or_create_config(tmp_path)
        assert config.get("include_patterns") == []


# ---------------------------------------------------------------------------
# 2. DumpSession Behavior Tests
# ---------------------------------------------------------------------------

class TestDumpSessionIncludeOverride:
    """Test that include patterns override exclusion rules."""

    def test_include_overrides_ignore_patterns(self, tmp_path):
        """Path excluded by ignore_patterns but in include_patterns is included."""
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        report = results_dir / "report.md"
        report.write_text("report content")

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"results"},
            max_depth=None,
            dir_only=False,
            included_patterns=["results/**"],
        )

        assert not session.is_excluded(results_dir)
        assert not session.is_excluded(report)

    def test_include_overrides_gitignore(self, tmp_path):
        """Path excluded by .gitignore but in include_patterns is included."""
        # Set up .gitignore
        (tmp_path / ".gitignore").write_text("results/\n")

        results_dir = tmp_path / "results"
        results_dir.mkdir()
        data_file = results_dir / "data.jsonl"
        data_file.write_text('{"key": "value"}')

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False,
            included_patterns=["results/**"],
        )

        assert not session.is_excluded(results_dir)
        assert not session.is_excluded(data_file)

    def test_include_overrides_combined_excludes(self, tmp_path):
        """Path excluded by both ignore_patterns and .gitignore is included by include_patterns."""
        (tmp_path / ".gitignore").write_text("dist/\n")

        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        bundle = dist_dir / "bundle.js"
        bundle.write_text("console.log('hi')")

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"dist"},
            max_depth=None,
            dir_only=False,
            included_patterns=["dist/bundle.js"],
        )

        assert not session.is_excluded(dist_dir)
        assert not session.is_excluded(bundle)

    def test_config_filename_always_excluded(self, tmp_path):
        """CONFIG_FILENAME is always excluded, even if matched by include patterns."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("{}")

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False,
            included_patterns=[CONFIG_FILENAME],
        )

        assert session.is_excluded(config_file)

    def test_no_include_patterns_behaves_as_before(self, tmp_path):
        """Without include patterns, behavior is unchanged."""
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        (results_dir / "data.jsonl").write_text("{}")

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"results"},
            max_depth=None,
            dir_only=False,
        )

        assert session.is_excluded(results_dir)

    def test_empty_include_patterns_behaves_as_before(self, tmp_path):
        """Empty include patterns list has no effect."""
        results_dir = tmp_path / "results"
        results_dir.mkdir()

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"results"},
            max_depth=None,
            dir_only=False,
            included_patterns=[],
        )

        assert session.is_excluded(results_dir)

    def test_include_does_not_affect_non_excluded_paths(self, tmp_path):
        """Include patterns do not change the status of paths that are not excluded."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        main_py = src_dir / "main.py"
        main_py.write_text("pass")

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False,
            included_patterns=["src/**"],
        )

        assert not session.is_excluded(main_py)

    def test_include_specific_file_in_excluded_dir(self, tmp_path):
        """Include a specific file inside an excluded directory."""
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        important = logs_dir / "important.log"
        important.write_text("critical error")
        debug = logs_dir / "debug.log"
        debug.write_text("debug info")

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"logs"},
            max_depth=None,
            dir_only=False,
            included_patterns=["logs/important.log"],
        )

        # The directory should be traversable (ancestor of included file)
        assert not session.is_excluded(logs_dir)
        # The specific file should be included
        assert not session.is_excluded(important)
        # Other files in the directory should remain excluded
        assert session.is_excluded(debug)

    def test_include_with_glob_pattern(self, tmp_path):
        """Include via glob pattern (e.g., *.jsonl) inside excluded directory."""
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        jsonl = results_dir / "output.jsonl"
        jsonl.write_text("{}")
        txt = results_dir / "notes.txt"
        txt.write_text("notes")

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"results"},
            max_depth=None,
            dir_only=False,
            included_patterns=["results/*.jsonl"],
        )

        assert not session.is_excluded(results_dir)
        assert not session.is_excluded(jsonl)
        assert session.is_excluded(txt)

    def test_include_with_double_star_glob(self, tmp_path):
        """Include with ** glob traverses nested directories."""
        results = tmp_path / "results"
        run1 = results / "run1"
        run1.mkdir(parents=True)
        report = run1 / "report.md"
        report.write_text("# Report")
        log = run1 / "debug.log"
        log.write_text("debug")

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"results"},
            max_depth=None,
            dir_only=False,
            included_patterns=["results/**/*.md"],
        )

        # Directories should be traversable
        assert not session.is_excluded(results)
        assert not session.is_excluded(run1)
        # .md file should be included
        assert not session.is_excluded(report)
        # .log file should remain excluded
        assert session.is_excluded(log)


class TestDumpSessionTreeWithIncludes:
    """Test that generate_tree correctly includes force-included files."""

    def test_tree_includes_force_included_files(self, tmp_path):
        """Files in excluded dirs matched by include patterns appear in tree and files_to_dump."""
        results = tmp_path / "results"
        results.mkdir()
        data = results / "data.jsonl"
        data.write_text('{"result": 1}')

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"results"},
            max_depth=None,
            dir_only=False,
            included_patterns=["results/**"],
        )

        session.generate_tree(tmp_path)

        dumped_names = [f.name for f in session.files_to_dump]
        assert "data.jsonl" in dumped_names
        assert session.file_count >= 1

    def test_tree_excludes_non_included_files_in_included_dir(self, tmp_path):
        """Only files matching include patterns are included, others remain excluded."""
        results = tmp_path / "results"
        results.mkdir()
        included_file = results / "report.md"
        included_file.write_text("# Report")
        excluded_file = results / "debug.log"
        excluded_file.write_text("debug")

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"results"},
            max_depth=None,
            dir_only=False,
            included_patterns=["results/*.md"],
        )

        session.generate_tree(tmp_path)

        dumped_names = [f.name for f in session.files_to_dump]
        assert "report.md" in dumped_names
        assert "debug.log" not in dumped_names

    def test_tree_without_include_patterns_unchanged(self, tmp_path):
        """Regression: no include patterns means behavior is unchanged."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("pass")

        results = tmp_path / "results"
        results.mkdir()
        (results / "data.jsonl").write_text("{}")

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"results"},
            max_depth=None,
            dir_only=False,
        )

        session.generate_tree(tmp_path)

        dumped_names = [f.name for f in session.files_to_dump]
        assert "main.py" in dumped_names
        assert "data.jsonl" not in dumped_names

    def test_tree_nested_include_traversal(self, tmp_path):
        """Include patterns with nested paths ensure all ancestor dirs are traversed."""
        deep = tmp_path / "output" / "run1" / "logs"
        deep.mkdir(parents=True)
        target = deep / "orchestrator.log"
        target.write_text("log line")

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"output"},
            max_depth=None,
            dir_only=False,
            included_patterns=["output/run1/logs/orchestrator.log"],
        )

        session.generate_tree(tmp_path)

        dumped_names = [f.name for f in session.files_to_dump]
        assert "orchestrator.log" in dumped_names


# ---------------------------------------------------------------------------
# 3. Engine Integration Tests (profile additional_excludes / additional_includes)
# ---------------------------------------------------------------------------

class TestEngineIncludeExcludeOverrides:
    """Test engine-level integration of include/exclude overrides."""

    def test_profile_additional_excludes(self, tmp_path):
        """Profile additional_excludes adds to ignore_patterns."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("print('main')")
        (src / "debug.py").write_text("print('debug')")

        out_file = tmp_path / "dump.txt"
        profile = {
            "description": "Test",
            "additional_excludes": ["src/debug.py"],
        }

        settings = DumpSettings(
            start_path=tmp_path,
            output_file=out_file,
            use_xml=True,
            active_profile=profile,
            no_copy=True,
        )

        config = {
            "ignore_patterns": [],
            "profiles": {"test-excl": profile},
        }
        engine = DumpEngine(config=config, settings=settings)
        engine.run()

        content = out_file.read_text()
        assert "main.py" in content
        assert "debug.py" not in content

    def test_profile_additional_includes(self, tmp_path):
        """Profile additional_includes re-includes excluded paths."""
        results = tmp_path / "results"
        results.mkdir()
        report = results / "report.md"
        report.write_text("# Results")

        out_file = tmp_path / "dump.txt"
        profile = {
            "description": "Debug results",
            "additional_includes": ["results/**"],
        }

        settings = DumpSettings(
            start_path=tmp_path,
            output_file=out_file,
            use_xml=True,
            active_profile=profile,
            no_copy=True,
        )

        config = {
            "ignore_patterns": ["results"],
            "profiles": {"debug-results": profile},
        }
        engine = DumpEngine(config=config, settings=settings)
        engine.run()

        content = out_file.read_text()
        assert "report.md" in content
        assert "# Results" in content

    def test_top_level_include_patterns(self, tmp_path):
        """Top-level include_patterns in config re-includes excluded paths."""
        results = tmp_path / "results"
        results.mkdir()
        data = results / "data.jsonl"
        data.write_text('{"x": 1}')

        out_file = tmp_path / "dump.txt"

        settings = DumpSettings(
            start_path=tmp_path,
            output_file=out_file,
            use_xml=True,
            active_profile=None,
            no_copy=True,
        )

        engine = DumpEngine(
            config={
                "ignore_patterns": ["results"],
                "include_patterns": ["results/**"],
            },
            settings=settings,
        )
        engine.run()

        content = out_file.read_text()
        assert "data.jsonl" in content

    def test_combined_top_level_and_profile_includes(self, tmp_path):
        """Top-level + profile includes are merged."""
        results = tmp_path / "results"
        results.mkdir()
        (results / "data.jsonl").write_text("{}")
        logs = tmp_path / "logs"
        logs.mkdir()
        (logs / "app.log").write_text("log")

        out_file = tmp_path / "dump.txt"
        profile = {
            "description": "Full debug",
            "additional_includes": ["logs/**"],
        }

        settings = DumpSettings(
            start_path=tmp_path,
            output_file=out_file,
            use_xml=True,
            active_profile=profile,
            no_copy=True,
        )

        config = {
            "ignore_patterns": ["results", "logs"],
            "include_patterns": ["results/**"],
            "profiles": {"full-debug": profile},
        }
        engine = DumpEngine(config=config, settings=settings)
        engine.run()

        content = out_file.read_text()
        assert "data.jsonl" in content
        assert "app.log" in content

    def test_inactive_profile_rules_have_no_effect(self, tmp_path):
        """Rules from a profile that is NOT active have no effect."""
        results = tmp_path / "results"
        results.mkdir()
        (results / "data.jsonl").write_text("{}")

        out_file = tmp_path / "dump.txt"

        settings = DumpSettings(
            start_path=tmp_path,
            output_file=out_file,
            use_xml=True,
            active_profile=None,  # No active profile
            no_copy=True,
        )

        # The config has a profile with additional_includes, but it's not active
        engine = DumpEngine(
            config={
                "ignore_patterns": ["results"],
                "include_patterns": [],
                "profiles": {
                    "debug": {
                        "description": "Debug",
                        "additional_includes": ["results/**"],
                    }
                }
            },
            settings=settings,
        )
        engine.run()

        content = out_file.read_text()
        assert "data.jsonl" not in content

    def test_profile_additional_excludes_plus_includes(self, tmp_path):
        """Profile can both add excludes and re-include specific paths."""
        results = tmp_path / "results"
        results.mkdir()
        report = results / "run_report.md"
        report.write_text("# Report")
        runner_logs = results / "runner_logs"
        runner_logs.mkdir()
        (runner_logs / "verbose.log").write_text("verbose")

        out_file = tmp_path / "dump.txt"
        profile = {
            "description": "Debug results",
            "additional_excludes": ["results/runner_logs"],
            "additional_includes": ["results/run_report.md"],
        }

        settings = DumpSettings(
            start_path=tmp_path,
            output_file=out_file,
            use_xml=True,
            active_profile=profile,
            no_copy=True,
        )

        config = {
            "ignore_patterns": ["results"],
            "profiles": {"debug-results": profile},
        }
        engine = DumpEngine(config=config, settings=settings)
        engine.run()

        content = out_file.read_text()
        assert "run_report.md" in content
        assert "verbose.log" not in content


# ---------------------------------------------------------------------------
# 4. Regression Tests
# ---------------------------------------------------------------------------

class TestIncludeExcludeRegression:
    """Ensure existing behavior is unaffected when new fields are absent/empty."""

    def test_no_new_fields_output_matches_current(self, tmp_path):
        """Config without new fields produces identical behavior."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "hello.py").write_text("print('hi')")

        out_file = tmp_path / "dump.txt"

        settings = DumpSettings(
            start_path=tmp_path,
            output_file=out_file,
            use_xml=True,
            active_profile=None,
            no_copy=True,
        )

        engine = DumpEngine(
            config={"ignore_patterns": ["*.pyc"]},
            settings=settings,
        )
        engine.run()

        content = out_file.read_text()
        assert "hello.py" in content
        assert "print('hi')" in content

    def test_empty_include_patterns_no_change(self, tmp_path):
        """Empty include_patterns has no effect on output."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("pass")
        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("home = /usr")

        out_file = tmp_path / "dump.txt"

        settings = DumpSettings(
            start_path=tmp_path,
            output_file=out_file,
            use_xml=True,
            active_profile=None,
            no_copy=True,
        )

        engine = DumpEngine(
            config={
                "ignore_patterns": ["venv"],
                "include_patterns": [],
            },
            settings=settings,
        )
        engine.run()

        content = out_file.read_text()
        assert "main.py" in content
        assert "pyvenv.cfg" not in content

    def test_tree_and_files_consistent(self, tmp_path):
        """Tree entries and files_to_dump agree on the same include/exclude decisions."""
        results = tmp_path / "results"
        results.mkdir()
        included = results / "report.md"
        included.write_text("report")
        excluded = results / "debug.log"
        excluded.write_text("debug")

        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns={"results"},
            max_depth=None,
            dir_only=False,
            included_patterns=["results/*.md"],
        )

        session.generate_tree(tmp_path)

        # Check files_to_dump
        dumped_names = {f.name for f in session.files_to_dump}
        assert "report.md" in dumped_names
        assert "debug.log" not in dumped_names

        # Check tree entries match
        tree_file_names = {e.path.name for e in session.tree_entries if not e.is_dir}
        assert "report.md" in tree_file_names
        assert "debug.log" not in tree_file_names


# ---------------------------------------------------------------------------
# 5. Force-include helper method tests
# ---------------------------------------------------------------------------

class TestForceIncludedHelper:
    """Direct tests for _is_force_included logic."""

    def test_direct_pathspec_match(self, tmp_path):
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False,
            included_patterns=["results/data.jsonl"],
        )
        assert session._is_force_included("results/data.jsonl") is True
        assert session._is_force_included("results/other.txt") is False

    def test_glob_pathspec_match(self, tmp_path):
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False,
            included_patterns=["results/**/*.jsonl"],
        )
        assert session._is_force_included("results/run1/output.jsonl") is True
        # A .txt file doesn't match *.jsonl via pathspec
        assert session._is_force_included("results/run1/output.txt", is_dir=False) is False
        # But as a directory, the ancestor check still applies (results/run1 could contain .jsonl)
        assert session._is_force_included("results/run1", is_dir=True) is True

    def test_ancestor_directory_match(self, tmp_path):
        """Directories that are ancestors of include patterns match."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False,
            included_patterns=["results/run1/report.md"],
        )
        assert session._is_force_included("results", is_dir=True) is True
        assert session._is_force_included("results/run1", is_dir=True) is True
        assert session._is_force_included("src", is_dir=True) is False

    def test_ancestor_with_double_star(self, tmp_path):
        """Directories match when pattern has ** component."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False,
            included_patterns=["results/**/*.md"],
        )
        assert session._is_force_included("results", is_dir=True) is True
        assert session._is_force_included("results/run1", is_dir=True) is True
        assert session._is_force_included("results/run1/subdir", is_dir=True) is True

    def test_ancestor_with_wildcard_component(self, tmp_path):
        """Directories match when pattern has * in intermediate components."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False,
            included_patterns=["results/*/output.jsonl"],
        )
        assert session._is_force_included("results", is_dir=True) is True
        assert session._is_force_included("results/run1", is_dir=True) is True
        assert session._is_force_included("results/run2", is_dir=True) is True
        assert session._is_force_included("other", is_dir=True) is False

    def test_ancestor_check_does_not_apply_to_files(self, tmp_path):
        """Files are not force-included by ancestor matching, only by pathspec."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False,
            included_patterns=["results/**/*.md"],
        )
        # A .log file should NOT be force-included even though its path
        # is "under" the pattern directory
        assert session._is_force_included("results/run1/debug.log", is_dir=False) is False
        # But a .md file should match via pathspec
        assert session._is_force_included("results/run1/report.md", is_dir=False) is True

    def test_no_include_patterns(self, tmp_path):
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False,
            included_patterns=[],
        )
        assert session._is_force_included("anything") is False

    def test_basename_only_pattern(self, tmp_path):
        """Basename-only patterns don't match as directory ancestors."""
        session = DumpSession(
            root_path=tmp_path,
            excluded_patterns=set(),
            max_depth=None,
            dir_only=False,
            included_patterns=["*.jsonl"],
        )
        # *.jsonl has no directory components, so no ancestor matching
        assert session._is_force_included("results") is False
        # But file matching works via pathspec
        assert session._is_force_included("data.jsonl") is True
