import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

THIS_DIR = Path(__file__).parent
APP_DIR_PARENT = (THIS_DIR / ".." / "app").resolve()
sys.path.insert(0, str(APP_DIR_PARENT))


@pytest.fixture(scope="function")
def client():
    app = TestClient()
    return app
