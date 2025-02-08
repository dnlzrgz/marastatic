from pathlib import Path
import tomllib
from typing import Annotated, Optional
import typer
from rich import print
from marastatic.config import Config

app = typer.Typer()


@app.command()
def build(
    config_file: Annotated[
        Optional[Path],
        typer.Option(),
    ] = None,
) -> None:
    if not config_file or not config_file.exists():
        raise typer.Abort()

    if not config_file.is_file():
        raise typer.Abort()

    config = config_file.read_text()
    toml = tomllib.loads(config)
    other_config = Config(**toml)
    print(other_config.model_dump_json(indent=2))


def main():
    app()


if __name__ == "__main__":
    main()
