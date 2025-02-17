# /// script
# requires-python=">=3.12"
# dependencies = [
#   "jinja2>=3.1.5",
#   "markdown>=3.7",
#   "pydantic>=2.10.6",
#   "python-frontmatter>=1.1.0",
#   "rich>=13.9.4",
#   "typer>=0.15.1",
# ]
# ///

import tomllib
from shutil import copytree, ignore_patterns
from pathlib import Path
from typing import Annotated, Generator, Optional
import frontmatter
import typer
import markdown
from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader
from pydantic import BaseModel, DirectoryPath, HttpUrl, field_validator, ValidationError
from rich import print
from rich.console import Console

app = typer.Typer()
console = Console()


class SiteConfig(BaseModel):
    static_dir: DirectoryPath
    templates_dir: DirectoryPath
    content_dir: DirectoryPath
    build_dir: DirectoryPath
    base_url: HttpUrl
    dateField: str

    @field_validator(
        "static_dir",
        "templates_dir",
        "content_dir",
        "build_dir",
        mode="before",
    )
    @classmethod
    def check_directory_exists(cls, v) -> Path:
        path = Path(v)
        if not path.exists():
            raise ValueError(f"dir '{v}' does not exist.")
        if not path.is_dir():
            raise ValueError(f"'{v}' is not a valid directory.")

        return path


class Config(BaseModel):
    site: SiteConfig
    params: dict | None = None


def list_site_content(path: Path) -> Generator:
    for file in path.rglob("*.md"):
        if file.is_file():
            yield [file.absolute(), file.relative_to(path).as_posix()]


@app.command()
def build(
    config_file: Annotated[
        Optional[Path],
        typer.Option(),
    ] = None,
) -> None:
    if not config_file or not config_file.exists():
        print("[red bold]Error:[/] config file does not exists or was not provided.")
        raise typer.Abort()

    if not config_file.is_file():
        print(
            f"[red bold]Error:[/] config file '{config_file.name}' is not a valid file."
        )
        raise typer.Abort()

    with console.status(
        "building site...",
        spinner="earth",
    ) as status:
        status.update("reading configuration file...")

        try:
            raw_toml = config_file.read_text()
            parsed_toml = tomllib.loads(raw_toml)
            config = Config(**parsed_toml)
        except tomllib.TOMLDecodeError as e:
            console.print(
                f"[red bold]Error:[/] something went wrong while parsing TOML from '{config_file.name}': {e}"
            )
            raise typer.Abort()
        except ValidationError as e:
            console.print(f"[red bold]Error:[/] config validation failed: {e}")
            raise typer.Abort()
        except Exception as e:
            console.print(
                f"[red bold]Error:[/] something went wrong while reading configuration file '{config_file.name}': {e}"
            )
            raise typer.Abort()

        status.update("loading templates...")
        jinja_env = Jinja2Environment(
            loader=FileSystemLoader(config.site.templates_dir),
        )

        content_path = Path(config.site.content_dir)
        output_path = Path(config.site.build_dir)
        static_dir = Path(config.site.static_dir)

        status.update("generating files...")
        # TODO: if file is an index, it should be able to have access to all the files in its directory.
        # TODO: same goes for RSS, and sitemap.xml files.
        for file_path, relative_path in list_site_content(content_path):
            source = frontmatter.load(file_path)
            html_content = markdown.markdown(source.content)

            relative_path = Path(relative_path)
            template_name = f"{relative_path.stem}.html"
            template_path = f"{relative_path.parent}/{template_name}"

            try:
                template = jinja_env.get_template(template_path)
            except Exception:
                template_path = f"{relative_path.parent}/single.html"
                template = jinja_env.get_template(template_path)

            output_content = template.render(
                site=config.site,
                params=config.params,
                metadata=source.metadata,
                content=html_content,
            )

            output_file_path = output_path / relative_path.with_suffix(".html")
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            output_file_path.write_text(output_content, encoding="utf-8")

            console.print(f"[bold green]Ok:[/] created '{output_file_path}'.")

        status.update("cloning non-Markdown files...")
        copytree(
            content_path,
            output_path,
            ignore=ignore_patterns("*.md"),
            dirs_exist_ok=True,
        )
        console.print(
            f"[bold green]Ok:[/] cloned non-Markdown files to '{output_path.name}' build folder."
        )

        status.update("cloning assets...")
        copytree(
            static_dir,
            output_path.joinpath(static_dir.name),
            dirs_exist_ok=True,
        )
        console.print(
            f"[bold green]Ok:[/] cloned static folder '{static_dir.name}' into '{output_path.name}' build folder."
        )


def main():
    app()


if __name__ == "__main__":
    main()
