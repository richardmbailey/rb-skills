from pathlib import Path
import pytest


def pytest_addoption(parser):
    parser.addoption("--suite", choices=("strong", "weak"), default="strong")
    parser.addoption("--evidence", help="New directory for preserved child evidence")


@pytest.fixture(scope="session")
def evidence_root(request, tmp_path_factory):
    selected = request.config.getoption("--evidence")
    if selected:
        path = Path(selected).resolve()
        path.mkdir(parents=True, exist_ok=False)
        return path
    return tmp_path_factory.mktemp("evidence")
