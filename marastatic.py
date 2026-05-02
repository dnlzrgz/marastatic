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

import argparse, os, shutil, subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import frontmatter, markdown, tomllib
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

G, R, B, RES = "\033[32m", "\033[31m", "\033[1m", "\033[0m"


def info(msg):
    print(f"{B}{'INFO':<4}{RES} {msg}")


def ok(msg):
    print(f"{B}{G}{'OK':<4}{RES} {msg}")


def err(msg):
    print(f"{B}{R}{'ERR':<4}{RES} {msg}")


@dataclass(slots=True, frozen=True)
class Ok[T]:
    value: T


@dataclass(slots=True, frozen=True)
class Err[E]:
    err: E


type Result[T, E] = Ok[T] | Err[E]


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
        for field_name in ("static_dir", "templates_dir", "content_dir"):
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
        md = markdown.Markdown(extensions=["fenced_code", "tables", "abbr"])
        return md.convert(self.raw_content)


@dataclass(slots=True, frozen=True)
class RenderOutput:
    dest_path: Path
    content: str


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


def load_page(config: Config, abs_path: Path) -> Page:
    rel_path = abs_path.relative_to(config.content_dir)
    source = frontmatter.load(abs_path)
    url = f"{config.base_url.rstrip('/')}/{rel_path.with_suffix('.html').as_posix()}"
    return Page(
        rel_path=rel_path,
        metadata=source.metadata,
        raw_content=source.content,
        url=url,
        dest_path=config.build_dir / rel_path.with_suffix(".html"),
    )


def load_all_pages(config: Config) -> list[Page]:
    return [load_page(config, path) for path in config.content_dir.rglob("*.md")]


def group_pages(pages: list[Page]) -> dict[str, list[Page]]:
    sections = defaultdict(list)
    for page in pages:
        if page.rel_path.stem != "index":
            sections[page.parent].append(page)

    return sections


def make_jinja_env(
    config: Config, pages: list[Page], sections: dict[str, list[Page]]
) -> Environment:
    env = Environment(
        loader=FileSystemLoader(config.templates_dir),
    )
    env.globals.update(
        config=config, pages=pages, sections=sections, now=datetime.now()
    )

    return env


def render_page(env: Environment, page: Page) -> Result[RenderOutput, str]:
    candidates = [
        page.rel_path.with_suffix(".html").as_posix(),
        f"{page.parent}/single.html",
        "single.html",
    ]

    try:
        template = env.get_or_select_template(candidates)
        return Ok(
            RenderOutput(
                dest_path=page.dest_path,
                content=template.render(page=page),
            )
        )
    except TemplateNotFound as e:
        return Err(f"no template found for '{page.rel_path}': {e}")
    except Exception as e:
        return Err(f"failed to render '{page.rel_path}': {e}")


def render_feed(
    env: Environment,
    section_name: str,
    pages: list[Page],
    build_dir: Path,
) -> Result[RenderOutput, str]:
    try:
        template = env.get_template(f"{section_name}/rss.xml")
        return Ok(
            RenderOutput(
                dest_path=build_dir / section_name / "rss.xml",
                content=template.render(pages=pages),
            )
        )
    except Exception as e:
        return Err(f"no RSS template for '{section_name}' found: {e}")


def render_meta(
    env: Environment,
    template_name: str,
    dest_path: Path,
) -> Result[RenderOutput, str]:
    try:
        return Ok(
            RenderOutput(
                dest_path=dest_path,
                content=env.get_template(template_name).render(),
            )
        )
    except Exception as e:
        return Err(f"no {template_name} template: {e}")


def collect(
    config: Config,
    env: Environment,
    pages: list[Page],
    sections: dict[str, list[Page]],
) -> list[Result[RenderOutput, str]]:
    page_renders = [render_page(env, page) for page in pages]
    feed_renders = [
        render_feed(env, name, section_pages, config.build_dir)
        for name, section_pages in sections.items()
        if name != "root"
    ]
    meta_renders = [
        render_meta(env, "sitemap.xml", config.build_dir / "sitemap.xml"),
        render_meta(env, "robots.txt", config.build_dir / "robots.txt"),
    ]

    return [*page_renders, *feed_renders, *meta_renders]


def write(output: RenderOutput) -> Result[str, str]:
    try:
        output.dest_path.parent.mkdir(parents=True, exist_ok=True)
        output.dest_path.write_text(output.content, encoding="utf-8")
        return Ok(str(output.dest_path))
    except Exception as e:
        return Err(str(e))


def write_all(results: list[Result[RenderOutput, str]]) -> tuple[list[str], list[str]]:
    successes, failures = [], []

    for result in results:
        match result:
            case Ok(value=output):
                match write(output):
                    case Ok(value=uri):
                        successes.append(uri)
                    case Err(err=e):
                        failures.append(e)
            case Err(err=e):
                failures.append(e)

    return successes, failures


def copy_static_files(config: Config) -> None:
    shutil.copytree(
        config.content_dir,
        config.build_dir,
        ignore=shutil.ignore_patterns("*.md", "*.xml"),
        dirs_exist_ok=True,
    )
    shutil.copytree(
        config.static_dir,
        config.build_dir / config.static_dir.name,
        dirs_exist_ok=True,
    )


def clean_build_dir(build_dir: Path) -> None:
    shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)


def cmd_build(config: Config, do_clean: bool) -> None:
    if do_clean:
        clean_build_dir(config.build_dir)
        info(f"cleaned '{config.build_dir.name}'")

    info(f"building {config.base_url}")

    pages = load_all_pages(config)
    ok(f"{len(pages)} pages found")

    sections = group_pages(pages)
    env = make_jinja_env(config, pages, sections)
    renders = collect(config, env, pages, sections)

    successes, failures = write_all(renders)

    for label in successes:
        ok(f"rendered '{label}'")

    for failure in failures:
        err(failure)

    copy_static_files(config)
    ok(f"copied static files to '{config.build_dir.name}'")
    info("build complete!")


def cmd_new(
    config: Config,
    archetype: str,
    destination: Path,
    open_editor: bool,
) -> None:
    if not config.archetypes_dir:
        err("archetypes directory not defined.")
        return

    archetype_file = config.archetypes_dir / f"{archetype}.md"
    if not archetype_file.exists():
        raise FileNotFoundError(f"Archetype file {archetype_file} not found.")

    target = config.content_dir / destination
    if target.exists():
        err(f"'{target}' already exists.")
        return

    target.write_text(archetype_file.read_text())
    ok(f"created new {archetype} at '{target}'!")

    if open_editor:
        editor = os.environ.get("EDITOR")
        if not editor:
            err("no editor found in $EDITOR environment variables.")
            return
        try:
            info(f"opening '{target}'...")
            subprocess.run([editor, str(target)])
        except Exception as e:
            err(f"could not open the editor: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="marastatic",
        description="single-file static site generator.",
    )
    parser.add_argument("--config-file", type=Path, default="config.toml")
    subparsers = parser.add_subparsers(dest="command", help="Available commands.")

    build_parser = subparsers.add_parser("build", help="Build the site.")
    build_parser.add_argument("-c", "--clean", action="store_true")

    new_parser = subparsers.add_parser("new", help="Create new content.")
    new_parser.add_argument("archetype", type=str)
    new_parser.add_argument("destination", type=Path)
    new_parser.add_argument("-o", "--open", action="store_true")

    args = parser.parse_args()
    config = load_config(args.config_file)

    match args.command or "build":
        case "build":
            cmd_build(config, getattr(args, "clean", False))
        case "new":
            cmd_new(config, args.archetype, args.destination, args.open)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        info("\nbye!")
    except Exception as e:
        err(e)
