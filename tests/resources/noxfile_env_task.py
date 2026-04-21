from __future__ import annotations

import nox


dev = nox.env.manual(name="dev", loc=".venv")


@dev.task()
def tests(session: nox.Session) -> None:
    pass


@nox.session
def old_style_tests(session: nox.Session) -> None:
    pass
