#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python=">=3.14"
# dependencies=[
#   "jinja2>=3.1.6",
#   "markdown>=3.10.1",
#   "python-frontmatter>=1.1.0",
# ]
# ///

import argparse
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import frontmatter
import markdown
import tomllib
from jinja2 import Environment, FileSystemLoader

# Logging helpers
G, Y, R, B, RES = "\033[32m", "\033[33m", "\033[31m", "\033[1m", "\033[0m"


def info(msg):
    print(f"{B}# {RES}{'INFO':<4} {msg}")


def ok(msg):
    print(f"{B}{G}+ {RES}{'OK':<4} {msg}")


def warm(msg):
    print(f"{B}{Y}! {RES}{'WARN':<4} {msg}")


def err(msg):
    print(f"{B}{R}x {RES}{'ERR':<4} {msg}")


MARKDOWN_CONVERTER = markdown.Markdown(extensions=["fenced_code", "tables", "abbr"])


@dataclass(slots=True, frozen=True)
class Config:
    base_url: str

    static_dir: Path
    templates_dir: Path
    content_dir: Path
    archetypes_dir: Path | None
    build_dir: Path

    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        for field_name in [
            "static_dir",
            "templates_dir",
            "content_dir",
        ]:
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
    raw_content: str
    url: str
    dest_path: Path

    @property
    def parent(self) -> str:
        return self.rel_path.parent.name or "root"

    @property
    def content(self) -> str:
        return MARKDOWN_CONVERTER.reset().convert(self.raw_content)


def load_config(config_file: Path) -> Config:
    if not config_file.exists():
        raise FileNotFoundError(f"Config file {config_file} not found.")

    with config_file.open("rb") as f:
        data = tomllib.load(f)

    site_data = data.get("site", {})
    archetypes_dir = site_data.get("archetypes_dir")
    return Config(
        base_url=site_data["base_url"],
        static_dir=Path(site_data["static_dir"]),
        templates_dir=Path(site_data["templates_dir"]),
        content_dir=Path(site_data["content_dir"]),
        archetypes_dir=Path(archetypes_dir) if archetypes_dir else None,
        build_dir=Path(site_data["build_dir"]),
        params=data.get("params", {}),
    )


def create_content(
    config: Config,
    archetype: str,
    destination: Path,
    open: bool = False,
) -> None:
    if not config.archetypes_dir:
        err("archetypes directory not defined.")
        return

    archetype_file = config.archetypes_dir / f"{archetype}.md"
    if not archetype_file.exists():
        raise FileNotFoundError(f"Archetype file {archetype_file} not found.")

    target = config.content_dir / destination
    if target.exists():
        warm(f"'{target}' already exists.")
        return

    target.write_text(archetype_file.read_text())
    ok(f"created new {archetype} at '{target}'!")

    if open:
        import os
        import subprocess

        editor = os.environ.get("EDITOR")
        if not editor:
            err("no editor found in $EDITOR environment variables.")
            return
        try:
            info(f"opening '{target}'...")
            subprocess.run([editor, str(target)])
        except Exception as e:
            err(f"could not open the editor: {e}")


def copy_static_files(config: Config) -> None:
    content_dir = config.content_dir
    output_dir = config.build_dir
    static_dir = config.static_dir
    shutil.copytree(
        content_dir,
        output_dir,
        ignore=shutil.ignore_patterns("*.md", "*.xml"),
        dirs_exist_ok=True,
    )
    ok(f"cloned non-markdown files to '{output_dir.name}'")

    shutil.copytree(
        static_dir,
        output_dir.joinpath(static_dir.name),
        dirs_exist_ok=True,
    )
    ok(f"cloned static folder '{static_dir.name}' into '{output_dir.name}'")


def get_all_pages(config: Config) -> list[Page]:
    base_url = config.base_url
    pages = []
    for abs_path in config.content_dir.rglob("*.md"):
        rel_path = abs_path.relative_to(config.content_dir)
        source = frontmatter.load(abs_path)
        url = f"{base_url.rstrip('/')}/{rel_path.with_suffix('.html').as_posix()}"
        page = Page(
            rel_path=rel_path,
            metadata=source.metadata,
            raw_content=source.content,
            url=url,
            dest_path=config.build_dir / rel_path.with_suffix(".html"),
        )

        pages.append(page)

    return pages


def prepare_jinja_env(
    config: Config, pages: list[Page]
) -> tuple[Environment, dict[str, list[Page]]]:
    jinja_env = Environment(loader=FileSystemLoader(config.templates_dir))

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
    config: Config, jinja_env: Environment, sections: dict[str, list[Page]]
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

            ok(f"created RSS feed for '{section_name}'")
        except Exception as e:
            warm(f"no rss feed template found for '{section_name}': {e}")


def generate_sitemap(config: Config, jinja_env: Environment) -> None:
    try:
        sitemap = jinja_env.get_template("sitemap.xml").render()
        (config.build_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        ok("created sitemap.xml")
    except Exception as e:
        warm(f"no sitemap.xml template found: {e}")


def generate_robots(config: Config, jinja_env: Environment) -> None:
    try:
        robots = jinja_env.get_template("robots.txt").render()
        (config.build_dir / "robots.txt").write_text(robots, encoding="utf-8")
        ok("created robots.txt")
    except Exception as e:
        warm(f"no robots.txt template found: {e}")


def generate_pages(jinja_env: Environment, pages: list[Page]) -> None:
    for page in pages:
        template_names = [
            page.rel_path.with_suffix(".html").as_posix(),
            f"{page.parent}/single.html",
            "single.html",
        ]

        try:
            template = jinja_env.get_or_select_template(template_names)
            output = template.render(page=page)

            page.dest_path.parent.mkdir(parents=True, exist_ok=True)
            page.dest_path.write_text(output, encoding="utf-8")
            ok(f"rendered '{page.url}' successfully")
        except Exception as e:
            err(f"no template found for '{page.rel_path}': {e}")


def clean(build_dir: Path) -> None:
    shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    info(f"cleaned '{build_dir.name}'!")


def build(config: Config) -> None:
    info(f"building {config.base_url}")

    pages = get_all_pages(config)
    ok(f"{len(pages)} pages found!")

    jinja_env, sections = prepare_jinja_env(config, pages)
    generate_pages(jinja_env, pages)
    generate_rss_feeds(config, jinja_env, sections)
    generate_sitemap(config, jinja_env)
    generate_robots(config, jinja_env)
    copy_static_files(config)

    info("build complete!")


def main():
    parser = argparse.ArgumentParser(
        prog="marastatic",
        description="single-file static site generator.",
    )
    parser.add_argument("--config-file", type=Path, default="config.toml")

    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands.",
    )

    build_parser = subparsers.add_parser("build", help="Build the site.")
    build_parser.add_argument("-c", "--clean", action="store_true")

    new_parser = subparsers.add_parser("new", help="Create new content.")
    new_parser.add_argument("archetype", type=str, help="Archetype name.")
    new_parser.add_argument("destination", type=Path, help="Relative path to content.")
    new_parser.add_argument(
        "-o",
        "--open",
        action="store_true",
        help="Open the file in your default editor.",
    )

    args = parser.parse_args()
    command = args.command or "build"
    config = load_config(args.config_file)

    if command == "new":
        create_content(config, args.archetype, args.destination, args.open)
    else:
        if getattr(args, "clean", False):
            clean(config.build_dir)

        build(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        info("\nbye!")
    except Exception as e:
        err(e)
