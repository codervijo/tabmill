"""Typed extension.yaml schema (goal #5). Structure + types here; friendly field checks in
`extension.validate`. Unknown keys are errors so typos (`permision:`) can't pass silently."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

Template = Literal["popup", "side-panel", "devtools", "context-menu", "maps-overlay"]


class Permission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    justification: str = ""


class Screenshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caption: str
    page: str | None = None  # extension page to capture; default: the template's UI page


class Change(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD (lamill.io hub contract)
    notes: str


class Recipe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    slug: str
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    summary: str
    single_purpose: str
    template: Template
    permissions: list[Permission] = Field(min_length=1)
    optional_permissions: list[Permission] = []
    host_permissions: list[Permission] = []
    dependencies: dict[str, str] = {}
    dev_dependencies: dict[str, str] = {}
    remote_code: Literal[False] = False  # MV3: no remotely hosted code, ever
    portfolio_site: str
    landing_page_url: str = ""
    landing_path: str = ""  # tool page path on portfolio_site; default /<first keyword>
    target_keywords: list[str] = Field(min_length=1)
    cta_text: str
    cta_url: str
    utm_campaign: str
    store_category: str
    analytics: bool = False
    privacy_line: str | None = None
    theme: dict[str, str] = {}
    screenshots: list[Screenshot] = Field(default=[], max_length=5)  # store allows 1–5
    changelog: list[Change] = []  # shown on the lamill.io hub page (D-028)
    data_collected: list[str] = []  # what leaves the browser; empty = nothing (hub privacy page)


def structure_errors(data: dict[str, object]) -> list[str]:
    """Pydantic errors as one line each: `field.path`: message."""
    try:
        Recipe.model_validate(data)
    except ValidationError as e:
        out = []
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            if err["type"] == "missing":
                out.append(f"missing field `{loc}`")
            elif err["type"] == "extra_forbidden":
                out.append(f"unknown field `{loc}` (typo?)")
            else:
                out.append(f"`{loc}`: {err['msg']}")
        return out
    return []
