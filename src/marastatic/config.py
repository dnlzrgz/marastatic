from pydantic import BaseModel, Field


class SiteConfig(BaseModel):
    assets_dir: str = Field(
        ...,
        description="Directory containing static assets (CSS, JS, images, icons, etc.)",
    )
    templates_dir: str = Field(..., description="Directory containing Jinja2 templates")
    content_dir: str = Field(
        ..., description="Directory containing markdown/content files to be processed."
    )
    build_dir: str = Field(
        ..., description="Directory where the generated site will be output."
    )
    base_url: str = Field(..., description="Base URL of the published site")
    enable_robots_txt: bool = Field(
        False, description="Enable/disable generation of robots.txt file."
    )
    enable_sitemap: bool = Field(
        False, description="Enable/disable generation of sitemap.xml file."
    )
    dateField: str = Field(
        ..., description="Field name in frontmatter to use for publication date."
    )


class Config(BaseModel):
    site: SiteConfig
    params: dict | None = None
