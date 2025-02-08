from pathlib import Path
import pytest


@pytest.fixture
def fixtures_dir(pytestconfig) -> Path:
    """
    Returns the parth to the fixtures directory.
    """

    return pytestconfig.rootpath / "tests" / "fixtures"


@pytest.fixture
def toml_file(request, fixtures_dir) -> Path:
    """
    Returns the path to a TOML file based on parameterized filename.
    """
    return fixtures_dir / request.param
