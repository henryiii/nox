"""Resources for nox."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def get_nox_schema() -> Any:
    """Load and return the nox JSON schema.

    Returns:
        The JSON schema for [tool.nox] configuration.
    """
    schema_path = files("nox.resources").joinpath("nox.schema.json")
    return json.loads(schema_path.read_text())


__all__ = ["get_nox_schema"]


def __dir__() -> list[str]:
    return __all__
