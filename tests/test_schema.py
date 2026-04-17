"""Tests for nox.schema.json validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from nox.resources import get_nox_schema


@pytest.fixture
def schema() -> Any:
    """Load the nox schema."""
    return get_nox_schema()


def test_empty_object_is_valid(schema: Any) -> None:
    """Empty object should be valid (no required fields)."""
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft7Validator(schema)
    errors = list(validator.iter_errors({}))
    assert len(errors) == 0


def test_full_valid_configuration(schema: Any) -> None:
    """A full valid configuration should validate."""
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft7Validator(schema)
    config: dict[str, Any] = {
        "default_venv_backend": "uv",
        "force_venv_backend": "virtualenv",
        "sessions": ["lint", "test"],
        "pythons": ["3.10", "3.11"],
        "tags": ["ci"],
        "keywords": "not slow",
        "envdir": ".nox",
        "reuse_venv": "yes",
        "reuse_existing_virtualenvs": True,
        "stop_on_first_error": True,
        "error_on_missing_interpreters": True,
        "error_on_external_run": False,
        "download_python": "auto",
        "report": "report.json",
        "verbose": True,
    }
    errors = list(validator.iter_errors(config))
    assert len(errors) == 0


def test_enum_values(schema: Any) -> None:
    """Test that enum values are validated."""
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft7Validator(schema)

    # Valid backends
    for backend in ["conda", "mamba", "micromamba", "none", "uv", "venv", "virtualenv"]:
        errors = list(validator.iter_errors({"default_venv_backend": backend}))
        assert len(errors) == 0, f"Failed for backend: {backend}"

    # Invalid backend
    errors = list(validator.iter_errors({"default_venv_backend": "invalid"}))
    assert len(errors) == 1

    # Valid reuse_venv values
    for value in ["no", "yes", "always", "never"]:
        errors = list(validator.iter_errors({"reuse_venv": value}))
        assert len(errors) == 0, f"Failed for value: {value}"

    # Invalid reuse_venv
    errors = list(validator.iter_errors({"reuse_venv": "sometimes"}))
    assert len(errors) == 1

    # Valid download_python values
    for value in ["auto", "never", "always"]:
        errors = list(validator.iter_errors({"download_python": value}))
        assert len(errors) == 0, f"Failed for value: {value}"

    # Invalid download_python
    errors = list(validator.iter_errors({"download_python": "sometimes"}))
    assert len(errors) == 1


def test_array_types(schema: Any) -> None:
    """Test that array fields accept only strings."""
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft7Validator(schema)

    # Valid sessions
    errors = list(validator.iter_errors({"sessions": ["lint", "test"]}))
    assert len(errors) == 0

    # Invalid sessions (int in array)
    errors = list(validator.iter_errors({"sessions": ["lint", 123]}))
    assert len(errors) == 1


def test_additional_properties_rejected(schema: Any) -> None:
    """Extra properties should be rejected."""
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft7Validator(schema)
    errors = list(validator.iter_errors({"unknown_option": "value"}))
    assert len(errors) == 1


def test_schema_file_exists() -> None:
    """Schema file should exist."""
    # Check the path directly
    schema_path = Path(__file__).parent.parent / "nox" / "resources" / "nox.schema.json"
    assert schema_path.exists()


def test_schema_matches_nox_options() -> None:
    """Schema should have all nox.options attributes."""
    import nox
    from nox import _options

    nox.options = _options.options.noxfile_namespace()
    valid_keys = set(nox.options.__class__.__annotations__.keys())

    with (
        Path(__file__)
        .parent.parent.joinpath("nox", "resources", "nox.schema.json")
        .open() as f
    ):
        schema = json.load(f)
    schema_keys = set(schema.get("properties", {}).keys())

    assert valid_keys == schema_keys, (
        f"Missing: {valid_keys - schema_keys}, Extra: {schema_keys - valid_keys}"
    )
