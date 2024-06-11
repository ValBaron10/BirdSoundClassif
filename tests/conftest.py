"""Register pytest plugins, fixtures, and hooks to be used during test execution.

Docs: https://stackoverflow.com/questions/34466027/in-pytest-what-is-the-use-of-conftest-py-files
"""

import sys
from pathlib import Path
from tests.utils.docker import start_inference_container


THIS_DIR = Path(__file__).parent
APP_DIR_PARENT = (THIS_DIR / ".." / "app").resolve()
sys.path.insert(0, str(APP_DIR_PARENT))


# module import paths to python files containing fixtures
pytest_plugins = [
    # e.g. "tests/fixtures/example_fixture.py" should be registered as:
    "tests.fixtures.utils_fixtures",
    "tests.fixtures.container_fixtures"
]
