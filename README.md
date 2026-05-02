# marastatic

<p style="text-align: center;">
A simple single-file static site generator written in Python.
</p>

## Motivation

I was curious about how challenging it would be to build a simple static site generator with as few dependencies as possible, portable, and easy to modify. I also wanted it to be a single-file script. The result is a thin, opinionated layer of logic on top of `Jinja2`.

## How does it work?

`marastatic` follows a simple build process divided into the following phases:

1. Scan your `content_dir` directory (defined in your `config.toml` file).
2. Group the resulting "pages" into sections and prepares the `Jinja2` environment for your templates.
3. Collect all render jobs (pages, RSS feeds, sitemap, robots.txt).
4. Write everything to disk, reporting successes and failures.
5. Clone your static assets folder into the `build_dir` folder.

> [!WARNING]
> Anything outside the steps mentioned above will have to be handled by external tools.

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

# Custom config file
./marastatic.py --config-file project.toml
```

## Templates

`marastatic` injects the following variables into all of your `Jinja2` templates:

- `page`: the current page being rendered, with `{{ page.content }}` for the HTML content and `{{ page.metadata.title }}` and so on for anything defined in the frontmatter.
- `sections`: a dictionary that groups non-index pages by the folder they live in. Useful for listing posts for example. Top-level files like `about.md` are grouped under `sections['root']`
- `config`: your full `config.toml` configuration.
- `now`: a `datetime` object that represents the build time.

### Template resolution

For each page, `marastatic` looks for a template in this order:

1. An exact match (e.g. `templates/blog/post-about-something.html`).
2. A section default (e.g. `templates/blog/single.html`).
3. A global fallback (e.g. `templates/single.html`).
