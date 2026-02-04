#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python=">=3.14"
# dependencies=[
#   "jinja2>=3.1.6",
#   "markdown>=3.10.1",
#   "python-frontmatter>=1.1.0",
#   "rich>=14.3.1",
#   "watchfiles>=1.1.1",
# ]
# ///

import argparse
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from shutil import copytree, ignore_patterns
from time import perf_counter
from typing import Any

import frontmatter
import markdown
import tomllib
from jinja2 import Environment as Jinja2Environment
from jinja2 import FileSystemLoader
from rich.console import Console
from watchfiles import watch

console = Console()


@dataclass(slots=True, frozen=True)
class Config:
    base_url: str

    static_dir: Path
    templates_dir: Path
    content_dir: Path
    build_dir: Path

    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        for field_name in ["static_dir", "templates_dir", "content_dir"]:
            path = getattr(self, field_name)
            if not path.exists() or not path.is_dir():
                raise FileNotFoundError(
                    f"{field_name} '{path}' is not a valid directory."
                )

        self.build_dir.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True, frozen=True)
class Page:
    rel_path: Path
    metadata: dict
    content: str
    url: str
    dest_path: Path

    @property
    def parent(self) -> str:
        return self.rel_path.parent.name or "root"


def list_content(path: Path) -> list[Path]:
    return [f.relative_to(path) for f in path.rglob("*.md")]


def load_config(config_file: Path) -> Config:
    if not config_file.exists():
        raise FileNotFoundError(f"Config file {config_file} not found.")

    with config_file.open("rb") as f:
        data = tomllib.load(f)

    site_data = data.get("site", {})
    return Config(
        base_url=site_data["base_url"],
        static_dir=Path(site_data["static_dir"]),
        templates_dir=Path(site_data["templates_dir"]),
        content_dir=Path(site_data["content_dir"]),
        build_dir=Path(site_data["build_dir"]),
        params=data.get("params", {}),
    )


def copy_static_files(config: Config) -> None:
    content_dir = config.content_dir
    output_dir = config.build_dir
    static_dir = config.static_dir
    copytree(
        content_dir,
        output_dir,
        ignore=ignore_patterns("*.md", "*.xml"),
        dirs_exist_ok=True,
    )
    console.print(
        f"[green bold]Ok[/]: Cloned non-markdown files to '{output_dir.name}'"
    )

    copytree(
        static_dir,
        output_dir.joinpath(static_dir.name),
        dirs_exist_ok=True,
    )
    console.print(
        f"[green bold]Ok[/]: Cloned static folder '{static_dir.name}' into '{output_dir.name}'"
    )


def get_url(base_url: str, rel_path: Path) -> str:
    path_str = rel_path.with_suffix(".html").as_posix()
    return f"{base_url.rstrip('/')}/{path_str}"


def get_all_pages(config: Config) -> list[Page]:
    pages = []
    md = markdown.Markdown(
        extensions=[
            "fenced_code",
            "tables",
            "abbr",
        ],
    )

    for rel_path in list_content(config.content_dir):
        abs_path = config.content_dir / rel_path

        source = frontmatter.load(abs_path)
        html_content = md.reset().convert(source.content)

        page = Page(
            rel_path=rel_path,
            metadata=source.metadata,
            content=html_content,
            url=get_url(config.base_url, rel_path),
            dest_path=config.build_dir / rel_path.with_suffix(".html"),
        )

        pages.append(page)

    return pages


def prepare_jinja_env(
    config: Config, pages: list[Page]
) -> tuple[Jinja2Environment, dict[str, list[Page]]]:
    jinja_env = Jinja2Environment(loader=FileSystemLoader(config.templates_dir))

    sections = defaultdict(list)
    for page in pages:
        if page.rel_path.stem != "index":
            sections[page.parent].append(page)

    jinja_env.globals.update(
        config=config,
        pages=pages,
        sections=sections,
        now=datetime.now(),
    )

    return jinja_env, sections


def generate_rss_feeds(
    config: Config, jinja_env: Jinja2Environment, sections: dict[str, list[Page]]
) -> None:
    for section_name, pages in sections.items():
        if section_name == "root":
            continue

        try:
            rss_template = jinja_env.get_template(f"{section_name}/rss.xml")
            rss_path = config.build_dir / section_name / "rss.xml"
            rss_path.parent.mkdir(parents=True, exist_ok=True)
            rss_path.write_text(
                rss_template.render(pages=pages),
                encoding="utf-8",
            )

            console.print(f"[green bold]Ok[/]: Created RSS feed for '{section_name}'")
        except Exception:
            console.print(
                f"[yellow bold]Warn[/]: No rss feed template found for '{section_name}'."
            )


def generate_sitemap(config: Config, jinja_env: Jinja2Environment) -> None:
    try:
        sitemap = jinja_env.get_template("sitemap.xml").render()
        (config.build_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        console.print("[green bold]Ok[/]: Created sitemap.xml")
    except Exception:
        console.print("[yellow bold]Warn[/]: No sitemap.xml template found.")


def generate_pages(jinja_env: Jinja2Environment, pages: list[Page]) -> None:
    for page in pages:
        template_names = [
            page.rel_path.with_suffix(".html").as_posix(),
            f"{page.parent}/single.html",
            "single.html",
        ]

        try:
            template = jinja_env.get_or_select_template(template_names)
            ouput = template.render(page=page)

            page.dest_path.parent.mkdir(parents=True, exist_ok=True)
            page.dest_path.write_text(ouput, encoding="utf-8")
            console.print(f"[bold green]Ok[/]: Rendered '{page.url}' successfully")
        except Exception as e:
            console.print(
                f"[red bold]Err[/]: No template found for '{page.rel_path}': {e}"
            )


def clean(build_dir: Path) -> None:
    console.print(f"🧹 Cleaning '{build_dir.name}'...")
    shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"🧹 Cleaned '{build_dir.name}'!")


def build(config: Config) -> None:
    start_time = perf_counter()

    console.print(f"✨ Building {config.base_url}")

    console.print("🌱 Scanning content directory...")
    pages = get_all_pages(config)
    console.print(f"[bold green]Ok[/]: {len(pages)} pages found!")

    console.print("🧰 Preparing Jinja2 environment...")
    jinja_env, sections = prepare_jinja_env(config, pages)

    console.print("🖨️ Rendering pages...")
    generate_pages(jinja_env, pages)

    console.print("📡 Generating RSS feeds and Sitemap...")
    generate_rss_feeds(config, jinja_env, sections)
    generate_sitemap(config, jinja_env)

    console.print("📦 Copying static files...")
    copy_static_files(config)

    end_time = perf_counter()
    duration = end_time - start_time
    console.print(f"🚀 Build complete in {duration:.2f}s!")


def watch_and_rebuild(config: Config) -> None:
    console.print("📡 Watching for changes...")

    paths = [config.content_dir, config.templates_dir, config.static_dir]
    for _ in watch(*paths):
        console.print("📡 Changes detected! Rebuilding...")
        console.quiet = True
        clean(config.build_dir)
        build(config)
        console.quiet = False


def main():
    parser = argparse.ArgumentParser(
        prog="marastatic",
        description="Single-file static site generator.",
    )
    parser.add_argument("--config-file", type=Path, default="config.toml")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    try:
        config = load_config(args.config_file)
        if args.clean:
            clean(config.build_dir)

        build(config)
        if args.watch:
            watch_and_rebuild(config)
    except Exception as e:
        console.print(f"[bold red]Err[/]: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("👋🏻 bye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
