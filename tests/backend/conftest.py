import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Allow `import app...` without installing the backend package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
