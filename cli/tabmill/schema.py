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
    target_keywords: list[str] = Field(min_length=1)
    cta_text: str
    cta_url: str
    utm_campaign: str
    store_category: str
    analytics: bool = False
    privacy_line: str | None = None
    theme: dict[str, str] = {}


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
