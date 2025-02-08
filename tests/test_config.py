import tomllib
import pytest
from marastatic.config import Config


@pytest.mark.parametrize(
    "toml_file",
    ["config.toml", "config_with_params.toml"],
    indirect=True,
)
def test_config_load(toml_file):
    assert toml_file.exists()

    toml_content = toml_file.read_text()
    parsed_toml = tomllib.loads(toml_content)
    config = Config(**parsed_toml)

    for key, _ in parsed_toml.items():
        assert hasattr(config, key), (
            f"Config object is missing attribute: {key} present in TOML file"
        )
