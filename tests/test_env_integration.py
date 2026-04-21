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
import subprocess
import sys
import tempfile
import textwrap
from typing import TYPE_CHECKING
from unittest import mock

import pytest

import nox
from nox import env
from nox import registry
from nox.env import reset_envs

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def cleanup_registries() -> Generator[None, None, None]:
    """Ensure registries are empty before and after each test."""
    registry.reset()
    reset_envs()
    yield
    registry.reset()
    reset_envs()


class TestEnvTaskIntegration:
    @pytest.fixture
    def noxfile_env_task(self) -> Generator[str, None, None]:
        with tempfile.TemporaryDirectory() as tmpdir:
            noxfile = os.path.join(tmpdir, "noxfile_env_task.py")
            with open(noxfile, "w") as f:
                f.write(
                    textwrap.dedent("""\
                    import nox

                    dev = nox.env.manual(name='dev', loc='.venv')

                    @dev.task()
                    def tests(session):
                        pass

                    @nox.session
                    def old_style_tests(session):
                        pass
                    """)
                )
            yield noxfile

    def test_list_env_task(self, noxfile_env_task: str) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "nox", "--noxfile", noxfile_env_task, "-l"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "dev:tests" in result.stdout
        assert "old_style_tests" in result.stdout

    def test_select_env_task(self, noxfile_env_task: str) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "nox",
                "--noxfile",
                noxfile_env_task,
                "-s",
                "dev:tests",
                "-l",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.splitlines()
        dev_selected = False
        old_skipped = False
        for line in lines:
            if "* dev:tests" in line:
                dev_selected = True
            if "- old_style_tests" in line:
                old_skipped = True
        assert dev_selected
        assert old_skipped

    def test_select_old_style(self, noxfile_env_task: str) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "nox",
                "--noxfile",
                noxfile_env_task,
                "-s",
                "old_style_tests",
                "-l",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.splitlines()
        dev_skipped = False
        old_selected = False
        for line in lines:
            if "- dev:tests" in line:
                dev_skipped = True
            if "* old_style_tests" in line:
                old_selected = True
        assert dev_skipped
        assert old_selected


class TestEnvRequires:
    @pytest.fixture
    def noxfile_env_requires(self) -> Generator[str, None, None]:
        with tempfile.TemporaryDirectory() as tmpdir:
            noxfile = os.path.join(tmpdir, "noxfile_env_requires.py")
            with open(noxfile, "w") as f:
                f.write(
                    textwrap.dedent("""\
                    import nox

                    base = nox.env.manual(name="base")

                    @base.task()
                    def setup(session):
                        print("SETUP")

                    @nox.session(requires=["base:setup"])
                    def downstream(session):
                        print("DOWNSTREAM")
                    """)
                )
            yield noxfile

    def test_requires_with_env_task(self, noxfile_env_requires: str) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "nox",
                "--noxfile",
                noxfile_env_requires,
                "-s",
                "downstream",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "SETUP" in result.stdout
        assert "DOWNSTREAM" in result.stdout
