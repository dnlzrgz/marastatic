# marastatic

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

<pre style="font-style: monospace;">
                                           __             __
                                          /\ \__         /\ \__  __
  ___ ___      __     _ __    __      ____\ \ ,_\    __  \ \ ,_\/\_\    ___
/' __` __`\  /'__`\  /\`'__\/'__`\   /',__\\ \ \/  /'__`\ \ \ \/\/\ \  /'___\
/\ \/\ \/\ \/\ \L\.\_\ \ \//\ \L\.\_/\__, `\\ \ \_/\ \L\.\_\ \ \_\ \ \/\ \__/
\ \_\ \_\ \_\ \__/.\_\\ \_\\ \__/.\_\/\____/ \ \__\ \__/.\_\\ \__\\ \_\ \____\
 \/_/\/_/\/_/\/__/\/_/ \/_/ \/__/\/_/\/___/   \/__/\/__/\/_/ \/__/ \/_/\/____/
</pre>

<p style="text-align: center;">
An extremely simple single-file static site generator in less than 300 lines of code written in Python.
</p>

## Why?

I was curious about how challenging it would be to build a very simple static site generator with as few dependencies as possible (spoiler: it’s not very hard). At the same time, I was exploring the idea of creating really simple, single-file scripts for day-to-day tasks that I could use whenever needed and customize easily. The end result is a thin and opinionated layer of logic built on top of `Jinja2`.

> [!WARNING]
> Before using marastatic, keep in mind that I built this project to really heavily on `Jinja2` templating and external scripts to handle tasks such as bundling, compression, and publishing.

## How does it works?

marastatic relies on a `config.toml` file to define paths for your static assets, templates, content, and the output build folder, as well as the base URL for your site. When you execute it, the following things happen:

1. All the markdown files in your content folder are scanned.
2. The files are processed to generate the HTML output using the templates located in the templates folder.
3. The script checks if an RSS feed needs to be created.
4. It also checks if a root `sitemap.xml` file needs to be generated.
5. Finally, it copies any static assets and non-markdown files found in the content folder to the output directory.

> [!TIP]  
> If you're interested in seeing a "real world" example, check out the repository for my personal [portfolio](https://github.com/dnlzrgz/portfolio).

## Downloading the script

The first step to start using marastatic is to download the script into the desired directory. This can be done in multiple ways, but the easiest method is to run:

```bash
curl -LO https://raw.githubusercontent.com/dnlzrgz/marastatic/refs/heads/master/marastatic.py
```

If you prefer it you can use `wget`:

```bash
wget https://raw.githubusercontent.com/dnlzrgz/marastatic/refs/heads/master/marastatic.py
```

## The configuration file

A significant part of the functionality of marastatic depends on a TOML-formatted file, which should contain at least the `site` section as defined below:

```toml
[site]
static_dir = "static/"
templates_dir = "templates/"
content_dir = "content/"
build_dir = "output/"
base_url = "https://marastatic.com"

[params]
title = "marastatic"
description = "A SSG in less than 300 lines of code."
keywords = ["script", "python", "ssg"]
```

### Running the script

Now, the only thing that you need to do is to run the script as follows:

```bash
# By default will look for a `config.toml`
uv run marastatic.py
```

Or

```bash
uv run marastatic.py --config-file config.toml
```

### `site` section

As stated before, the `site` section is required and it should contain all the necessary paths for reading the content, accessing the templates, and retrieving the assets. It should also define a `base_url`, which will be used to generate the URLs for each page on your site and that will be accessible via the `Jinja2` context in your templates. This last thing is useful for tasks such as listing sub-pages in an `index` or an `rss.xml` file and similar things.

> [!NOTE]  
> marastatic expects at least two types of templates for the root and each subfolder of your content directory: an `index.html` and a `single.html` templates. Additionally, if an `rss.xml` template is present, an RSS feed will be generated.

While it's not recommended (and is also impractical), you can access the `site` object inside your templates as follows:

```html
<h1>{{ config.site.assets_folder }}</h1>
```

### `params` section

The `params` section let's you define all the settings that you may need to access in your templates and is available globally to all your templates. Here you should add things like the canonical URL, SEO related things, contact email, copyright message and so on. Then, in your templates, you can do something like this:

```html
<meta name="description" content="{{ config.params.description }}" />
<meta name="keywords" content="{{ config.params.keywords | join(', ') }}" />
<link rel="canonical" content="{{ config.params.canonical_url }}" />
```

You can also add a subsection withing the `params` to handle any type of object or dictionary, as shown below:

```toml
[params]
title = "marastatic"

[params.author]
name = "John"
email = "john@doe.com"
```

Then in you template, you use it as follows:

```html
<p>Made by {{ context.params.author.name}}</p>
```

## "index" and "single" pages

marastatic expects two primary types of templates for rendering content: `index` and `single` pages. The `index` template should be used for listing multiple items, such as blog posts. To make this easier, the `index` pages have access to a `pages` object in the context, which lists all the sub-pages. As you can expect, the root "index" would have access to all the pages and sub-pages. On the other hand, `single` pages, are designed for rendering individual items like a blog post.

Keep in mind that the structure of the content folder and the templates folder structure must mirror each other, as shown below:

```txt
├── config.toml
├── content
│   ├── index.md
│   ├── about.md
│   └── posts
│       ├── hello_world.md
│       └── index.md
└── templates
    ├── single.html
    ├── index.html
    └── posts
        ├── index.html
        └── single.html
```

### Custom pages

If you want to have an `about` page but don't want it to use the root `single.html` template, you can define an additional template called `about.html` that will be used instead. This approach can be used to any page.

## RSS feeds

To generate an RSS feed for your entire site or for a specific section, you need to add an `rss.xml` template in the corresponding folder where you want the feed to exist. This `rss.xml` template has access to all the sub-pages, just like the `index.html` template, making it easier to generate a valid RSS feed. By placing an `rss.xml` template in the root directory, you can create a feed for the entire site, while placing it in a subfolder allows you to generate a feed for that specific section.

## `sitemap.xml`

The `sitemap.xml` file, similar to the RSS feed, is generated when you create a `sitemap.xml` template in the root of your templates folder. Like the `rss.xml` and root `index.html` templates, the `sitemap.xml` template has access to the pages object, allowing you to easily include all relevant pages in your sitemap.

> [!Note]
> While you can have an `rss.xml` file in each sub-folder and in the templates root, marastatic expects a `sitemap.xml` located exclusively in the root folder and no other location.

## Assets

marastatic manages static assets such as images, CSS files, and JS files by copying them from the specified `static_dir` to the output directory during the build process. Therefore, when using a static file, like for example an script, you should do it as follows:

```html
<script defer src="/static/js/alpine.js"></script>
```
