# marastatic

<p style="text-align: center;">
A simple single-file static site generator in less than 300 lines written in Python.
</p>

## Motivation

I was curious about how challenging it would be to build a simple static site generator with as few dependencies as possible, portable, and easy to modify. I also wanted it to be a single-file script. The result is a thin, opinionated layer of logic on top of `Jinja2`.

> If you're interested in seeing a "real world" example, check out the repository for my personal [portfolio](https://github.com/dnlzrgz/home).

## How does it work?

`marastatic` follows a two-pass build process divided into the following phases:

1. It scans your `content` directory (which will be specified in your `config.toml`), parsing your markdown files' frontmatter and converting their content to HTML.
1. It groups your resulting pages into sections and prepares the `Jinja2` environment.
1. It iterates through every page, selecting the most appropriate template for rendering it.
1. Finally, it generates some files like `rss.xml` and a `sitemap.xml`. It also clones your static assets into the `build/` folder.

> [!WARNING]
> Heavy-lifting tasks for bundling, asset management and so on will not be handled by `marastatic` and you'll need to rely on external tools for those.

## Downloading the script

You can download `marastatic` directly into your project by running:

```bash
curl -LO https://raw.githubusercontent.com/dnlzrgz/marastatic/refs/heads/master/marastatic.py
```

## The configuration file

To start using `marastatic` create a `config.toml` file in your project root. The `site` section will contain your paths and `base_url` while `params` will be used to provide global data to your templates:

```toml
[site]
static_dir = "static/"
templates_dir = "templates/"
content_dir = "content/"
build_dir = "output/"
base_url = "https://example.com"

[params]
title = "marastatic"
description = "A SSG in less than 300 lines of code."
keywords = ["script", "python", "ssg"]
```

## Running the script

```bash
# Using uv
uv run marastatic.py

# Does the same thing
./marastatic.py --config-file project.toml
```

### Auto-rebuild

While `marastatic` doesn't include anything similar to a live-server experience (right now at least), it includes a basic file watcher to trigger instant rebuilds.

```bash
uv run marastatic.py --watch
```

## The templates

`marastatic` injects three main objects and one extra into all of your `Jinja2` templates:

1. `page`: the current page being rendered. You can access `{{ page.content }}` and `{{ page.metadata.title }}` for example.
2. `sections`: a dictionary that groups pages by the folder they're in. It's useful for loops like `{% for post in sections['blog'] %}`.
3. `config`: all the settings that exist on your `config.toml` file. For example, to access the params you can use `{{ config.params.title }}`.
4. `now`: a Python `datetime` object that represents the build time (sometimes it comes handy).

> Top-level files (like `about.md`) will be grouped under `sections['root`]`.

## Examples

### Example of folder structure

```text

├── config.toml
├── content
│   ├── index.md        # Uses templates/index.html
│   └── blog
│       ├── post-1.md   # Uses templates/blog/single.html
│       └── index.md    # Uses templates/blog/index.html
└── templates
    ├── base.html
    ├── index.html
    └── blog
        ├── index.html
        ├── single.html
        └── rss.xml
```
