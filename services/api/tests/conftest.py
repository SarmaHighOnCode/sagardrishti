from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# services/api is not an installed package (no pyproject/setup.py of its
# own) — add its directory to sys.path so `from app.main import app` works
# whether pytest is invoked from the repo root or from services/api/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
