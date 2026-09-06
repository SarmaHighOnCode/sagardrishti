"""Root pytest configuration.

Puts `packages/` on sys.path so the domain packages import by name
(`import sagar_core`) regardless of where pytest is invoked from.

They are plain directories rather than installed distributions on
purpose: there is no publish step, nothing outside this repo consumes
them, and adding a pyproject + editable install per package would be
ceremony without payoff at this stage. `services/api` does the same
thing from its own conftest.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PACKAGES = Path(__file__).resolve().parent / "packages"
if str(_PACKAGES) not in sys.path:
    sys.path.insert(0, str(_PACKAGES))
