"""Tests for [tool.nox] TOML configuration support."""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

import nox
from nox import _options, tasks
from nox.project import nox_toml_options


@pytest.fixture
def reset_nox_options() -> None:
    """Reset nox.options to defaults before each test."""
    nox.options = _options.options.noxfile_namespace()


def test_nox_toml_options_from_script_block(tmp_path: Path) -> None:
    """Test loading options from a PEP 723 script block."""
    noxfile = tmp_path / "noxfile.py"
    noxfile.write_text(
        textwrap.dedent(
            """\
            # /// script
            # dependencies = ["nox"]
            # [tool.nox]
            # default_venv_backend = "uv"
            # sessions = ["lint", "test"]
            # verbose = true
            # ///

            import nox
            """
        ),
        encoding="utf-8",
    )

    options = nox_toml_options(noxfile)
    assert options == {
        "default_venv_backend": "uv",
        "sessions": ["lint", "test"],
        "verbose": True,
    }


def test_nox_toml_options_from_pyproject_next_to_noxfile(
    tmp_path: Path,
) -> None:
    """Test loading options from pyproject.toml adjacent to noxfile."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """\
            [tool.nox]
            default_venv_backend = "virtualenv"
            sessions = ["format", "test"]
            """
        ),
        encoding="utf-8",
    )
    noxfile = tmp_path / "noxfile.py"
    noxfile.write_text("import nox", encoding="utf-8")

    options = nox_toml_options(noxfile)
    assert options == {
        "default_venv_backend": "virtualenv",
        "sessions": ["format", "test"],
    }


def test_nox_toml_options_script_block_takes_precedence(tmp_path: Path) -> None:
    """Test that script block [tool.nox] takes precedence over pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """\
            [tool.nox]
            default_venv_backend = "virtualenv"
            sessions = ["format"]
            """
        ),
        encoding="utf-8",
    )
    noxfile = tmp_path / "noxfile.py"
    noxfile.write_text(
        textwrap.dedent(
            """\
            # /// script
            # [tool.nox]
            # default_venv_backend = "uv"
            # sessions = ["lint"]
            # ///

            import nox
            """
        ),
        encoding="utf-8",
    )

    options = nox_toml_options(noxfile)
    assert options == {
        "default_venv_backend": "uv",
        "sessions": ["lint"],
    }


def test_nox_toml_options_empty_when_no_config(tmp_path: Path) -> None:
    """Test that empty dict is returned when no [tool.nox] is present."""
    noxfile = tmp_path / "noxfile.py"
    noxfile.write_text("import nox", encoding="utf-8")

    options = nox_toml_options(noxfile)
    assert options == {}


def test_nox_toml_options_empty_when_no_pyproject(tmp_path: Path) -> None:
    """Test that empty dict is returned when no pyproject.toml exists."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    noxfile = subdir / "noxfile.py"
    noxfile.write_text("import nox", encoding="utf-8")

    options = nox_toml_options(noxfile)
    assert options == {}


def test_apply_toml_options_as_defaults(tmp_path: Path) -> None:
    """Test that TOML options are applied as defaults to nox.options."""
    # Reset options first
    nox.options = _options.options.noxfile_namespace()

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """\
            [tool.nox]
            default_venv_backend = "uv"
            sessions = ["lint", "test"]
            verbose = true
            """
        ),
        encoding="utf-8",
    )
    noxfile = tmp_path / "noxfile.py"
    noxfile.write_text("import nox", encoding="utf-8")

    # Create a mock global_config
    class MockConfig:
        def __init__(self) -> None:
            self.noxfile: str = str(noxfile)

    config = MockConfig()

    # Apply TOML options
    toml_options = nox_toml_options(config.noxfile)
    tasks._apply_toml_options_as_defaults(toml_options)

    # Check that options were applied
    assert nox.options.default_venv_backend == "uv"
    assert nox.options.sessions == ["lint", "test"]
    assert nox.options.verbose is True


def test_noxfile_options_override_toml_options(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that nox.options set in Python code override TOML options."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """\
            [tool.nox]
            default_venv_backend = "uv"
            sessions = ["lint"]
            """
        ),
        encoding="utf-8",
    )
    noxfile_path = tmp_path / "noxfile.py"
    noxfile_path.write_text(
        textwrap.dedent(
            """\
            import nox

            # This should override the TOML setting
            nox.options.default_venv_backend = "virtualenv"

            print(f"venv_backend={nox.options.default_venv_backend!r}")
            print(f"sessions={nox.options.sessions!r}")

            @nox.session
            def test(session):
                pass
            """
        ),
        encoding="utf-8",
    )

    # Load the nox module and check options
    original_path = sys.path.copy()
    try:
        sys.path.insert(0, str(tmp_path))

        # This simulates what load_nox_module does
        toml_opts = nox_toml_options(str(noxfile_path))

        # Reset options to defaults
        globals()["nox"].options = _options.options.noxfile_namespace()
        # Reset registry to avoid session pollution
        nox.registry.reset()

        # Apply TOML options BEFORE executing the module (simulating load_nox_module)
        tasks._apply_toml_options_as_defaults(toml_opts)

        # Now load and execute the module
        spec = importlib.util.spec_from_file_location(
            "user_nox_module", str(noxfile_path)
        )
        assert spec is not None
        user_module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(user_module)

        # Check that Python code override worked
        captured = capsys.readouterr()
        assert "venv_backend='virtualenv'" in captured.out
        # sessions from TOML should still be present
        assert "sessions=['lint']" in captured.out

    finally:
        sys.path = original_path


def test_toml_options_reuse_venv_string_value(tmp_path: Path) -> None:
    """Test that reuse_venv can be set as a string value in TOML."""
    noxfile = tmp_path / "noxfile.py"
    noxfile.write_text(
        textwrap.dedent(
            """\
            # /// script
            # [tool.nox]
            # reuse_venv = "always"
            # ///

            import nox
            """
        ),
        encoding="utf-8",
    )

    options = nox_toml_options(noxfile)
    assert options == {"reuse_venv": "always"}

    # Reset and apply
    nox.options = _options.options.noxfile_namespace()
    tasks._apply_toml_options_as_defaults(options)

    assert nox.options.reuse_venv == "always"


def test_toml_options_skip_empty_lists(tmp_path: Path) -> None:
    """Test that empty list values in TOML don't override defaults."""
    noxfile = tmp_path / "noxfile.py"
    noxfile.write_text(
        textwrap.dedent(
            """\
            # /// script
            # [tool.nox]
            # sessions = []
            # ///

            import nox
            """
        ),
        encoding="utf-8",
    )

    options = nox_toml_options(noxfile)
    assert options == {"sessions": []}

    # Reset to defaults (sessions is None by default)
    nox.options = _options.options.noxfile_namespace()
    assert nox.options.sessions is None

    # Apply TOML options - empty list should be skipped
    tasks._apply_toml_options_as_defaults(options)

    # Should still be None because empty list is skipped
    assert nox.options.sessions is None


def test_toml_options_invalid_option_name(tmp_path: Path) -> None:
    """Test that invalid option names in TOML are silently ignored."""
    noxfile = tmp_path / "noxfile.py"
    noxfile.write_text(
        textwrap.dedent(
            """\
            # /// script
            # [tool.nox]
            # invalid_option = "value"
            # default_venv_backend = "uv"
            # ///

            import nox
            """
        ),
        encoding="utf-8",
    )

    options = nox_toml_options(noxfile)
    assert options == {"invalid_option": "value", "default_venv_backend": "uv"}

    # Reset and apply
    nox.options = _options.options.noxfile_namespace()
    tasks._apply_toml_options_as_defaults(options)

    # Invalid option should be ignored, valid one should be set
    assert not hasattr(nox.options, "invalid_option")
    assert nox.options.default_venv_backend == "uv"


def test_nox_toml_options_from_pyproject_directly(tmp_path: Path) -> None:
    """Test loading options from pyproject.toml when used directly as noxfile."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """\
            [tool.nox]
            default_venv_backend = "conda"
            sessions = ["build"]

            [build-system]
            requires = ["setuptools"]
            """
        ),
        encoding="utf-8",
    )

    options = nox_toml_options(pyproject)
    assert options == {
        "default_venv_backend": "conda",
        "sessions": ["build"],
    }


def test_nox_toml_options_nonexistent_file(tmp_path: Path) -> None:
    """Test that non-existent files return empty dict."""
    nonexistent = tmp_path / "nonexistent.py"
    options = nox_toml_options(nonexistent)
    assert options == {}


def test_nox_toml_options_unrecognized_extension(tmp_path: Path) -> None:
    """Test that files with unrecognized extensions return empty dict."""
    txt_file = tmp_path / "config.txt"
    txt_file.write_text("[tool.nox]\ndefault_venv_backend = 'uv'", encoding="utf-8")
    options = nox_toml_options(txt_file)
    assert options == {}
