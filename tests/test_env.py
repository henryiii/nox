# Copyright 2024 Alethea Katherine Flowers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest import mock

import pytest

import nox
from nox import registry
from nox.env import reset_envs
from nox.manifest import Manifest

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def cleanup_registries() -> Generator[None, None, None]:
    """Ensure registries are empty before and after each test."""
    try:
        registry.reset()
        reset_envs()
        yield
    finally:
        registry.reset()
        reset_envs()


class TestManualEnv:
    def test_manual_env(self) -> None:
        dev = nox.env.manual(name="dev", loc=".venv", install=["-e.[test]"])
        assert dev.name == "dev"
        assert dev.loc == ".venv"
        assert dev.install == ["-e.[test]"]
        assert dev.command == ""

    def test_manual_env_default_loc(self) -> None:
        dev = nox.env.manual(name="dev")
        assert dev.loc is None

    def test_register_env(self) -> None:
        dev = nox.env.manual(name="dev")
        envs = nox.env.get_envs()
        assert "dev" in envs
        assert envs["dev"] is dev


class TestTaskDecorator:
    def test_task_on_env(self) -> None:
        dev = nox.env.manual(name="dev")

        @dev.task()
        def lint(session: nox.Session) -> None:
            pass

        assert "lint" in dev.tasks
        assert lint.env_name == "dev"
        assert lint.task_name == "lint"

    def test_task_decorator_with_options(self) -> None:
        dev = nox.env.manual(name="dev")

        @dev.task(python="3.12", tags=["check"])
        def lint(session: nox.Session) -> None:
            pass

        assert lint.python == "3.12"
        assert lint.tags == ["check"]

    def test_registry_task_keys(self) -> None:
        dev = nox.env.manual(name="dev")

        @dev.task()
        def lint(session: nox.Session) -> None:
            pass

        reg = registry.get()
        assert "dev:lint" in reg


class TestBackwardsCompat:
    def test_session_creates_implicit_env(self) -> None:
        @nox.session
        def tests(session: nox.Session) -> None:
            pass

        envs = nox.env.get_envs()
        assert "tests" in envs

    def test_session_registry(self) -> None:
        @nox.session
        def tests(session: nox.Session) -> None:
            pass

        reg = registry.get()
        assert "tests" in reg
        assert reg["tests"].env_name == "tests"
        assert reg["tests"].task_name == "tests"


class TestEnvdir:
    def create_mock_config(self) -> mock.Mock:
        cfg = mock.Mock()
        cfg.force_venv_backend = None
        cfg.default_venv_backend = None
        cfg.extra_pythons = None
        cfg.force_pythons = None
        cfg.posargs = []
        cfg.envdir = ".nox"
        return cfg

    def test_envdir_backwards_compat(self) -> None:
        @nox.session
        def test(session: nox.Session) -> None:
            pass

        manifest = Manifest(registry.get(), self.create_mock_config())
        runner = manifest["test"]
        assert runner.envdir == ".nox/test"

    def test_envdir_custom_loc(self) -> None:
        dev = nox.env.manual(name="dev", loc=".venv")

        @dev.task()
        def lint(session: nox.Session) -> None:
            pass

        manifest = Manifest(registry.get(), self.create_mock_config())
        runner = manifest["dev:lint"]
        assert runner.envdir == os.path.abspath(".venv")

    def test_envdir_with_slug(self) -> None:
        dev = nox.env.manual(name="dev", loc=".nox/{slug}")

        @dev.task()
        def lint(session: nox.Session) -> None:
            pass

        manifest = Manifest(registry.get(), self.create_mock_config())
        runner = manifest["dev:lint"]
        # Loc with {slug} is resolved under envdir, and normalized.
        # `.nox/dev-lint` normalizes to `nox-dev-lint`.
        assert runner.envdir == ".nox/nox-dev-lint"
