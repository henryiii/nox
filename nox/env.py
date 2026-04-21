# Copyright 2016 Alethea Katherine Flowers
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

import copy
import functools
import typing
import warnings
from typing import Any, overload

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from nox._typing import Python

__all__ = ["Env", "ManualEnv", "get_envs", "manual", "reset_envs"]


def __dir__() -> list[str]:
    return __all__


class Env:
    """Base class for environments.

    An environment defines how a virtual environment should be created,
    configured, and where it should be located.
    """

    def __init__(self, name: str, loc: str | None = None) -> None:
        self._name = name
        self._loc = loc
        self._tasks: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def loc(self) -> str | None:
        return self._loc

    @loc.setter
    def loc(self, value: str | None) -> None:
        self._loc = value

    @property
    def tasks(self) -> dict[str, Any]:
        return self._tasks

    def _resolve_loc(self, slug: str) -> str:
        """Resolve the environment location, substituting {slug}."""
        if self._loc is None:
            return slug
        return self._loc.replace("{slug}", slug)


class ManualEnv(Env):
    """A manually configured environment.

    The user specifies packages to install and a setup command.
    """

    def __init__(
        self,
        name: str,
        loc: str | None = None,
        install: Sequence[str] | None = None,
        command: str = "",
    ) -> None:
        super().__init__(name, loc)
        self._install = list(install or [])
        self._command = command

    @property
    def install(self) -> list[str]:
        return self._install

    @property
    def command(self) -> str:
        return self._command

    def task(
        self,
        func: Callable[..., Any] | None = None,
        /,
        *,
        python: Any = None,
        name: str | None = None,
        venv_backend: str | None = None,
        venv_params: Sequence[str] = (),
        tags: Sequence[str] | None = None,
        default: bool = True,
        requires: Sequence[str] | None = None,
        download_python: Any = None,
    ) -> Any:
        """Decorator to register a task on this environment."""
        from nox.registry import session_decorator  # noqa: PLC0415

        if func is None:
            return functools.partial(
                self.task,
                python=python,
                name=name,
                venv_backend=venv_backend,
                venv_params=venv_params,
                tags=tags,
                default=default,
                requires=requires,
                download_python=download_python,
            )

        task_name = name or func.__name__
        reg_name = f"{self.name}:{task_name}"

        decorated = session_decorator(  # type: ignore[call-overload]
            func,
            python=python,
            name=reg_name,
            venv_backend=venv_backend,
            venv_params=venv_params,
            tags=tags,
            default=default,
            requires=requires,
            download_python=download_python,
        )
        # Attach env info so the manifest knows this is a task bound to an env
        decorated.env_name = self.name
        decorated.task_name = task_name
        self._tasks[task_name] = decorated
        return decorated


_ENV_REGISTRY: dict[str, Env] = {}


def reset_envs() -> None:
    _ENV_REGISTRY.clear()


def get_envs() -> dict[str, Env]:
    return copy.copy(_ENV_REGISTRY)


def _register_env(env: Env) -> Env:
    """Register an environment in the global registry."""
    if env.name in _ENV_REGISTRY:
        msg = (
            f"The env {env.name!r} has already been registered; "
            "this will be an error in a future version of nox. "
            "Overriding the old env for now."
        )
        warnings.warn(msg, FutureWarning, stacklevel=2)
    _ENV_REGISTRY[env.name] = env
    return env


def manual(
    name: str,
    *,
    loc: str | None = None,
    install: Sequence[str] | None = None,
    command: str = "",
) -> ManualEnv:
    """Create and register a manual environment.

    Args:
        name: The name of the environment.
        loc: The location of the environment. Supports ``{slug}`` substitution.
        install: A list of packages to install.
        command: A setup command to run.
    """
    env = ManualEnv(name=name, loc=loc, install=install, command=command)
    return typing.cast("ManualEnv", _register_env(env))




