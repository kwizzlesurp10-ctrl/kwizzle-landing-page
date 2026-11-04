from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PromptSlot(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    example: str | None = Field(default=None, max_length=500)


class ArchitectedPrompt(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=2000)
    goal: str = Field(min_length=1, max_length=4000)
    constraints: list[str] = Field(min_length=1, max_length=20)
    format_spec: str = Field(alias="format", min_length=1, max_length=4000)
    template: str = Field(min_length=1, max_length=12000)
    slots: list[PromptSlot] = Field(default_factory=list, max_length=30)
    example_output: str = Field(min_length=1, max_length=12000)

    model_config = {"populate_by_name": True}

    @field_validator("constraints")
    @classmethod
    def non_empty_constraints(cls, value: list[str]) -> list[str]:
        cleaned = [c.strip() for c in value if c.strip()]
        if not cleaned:
            raise ValueError("At least one non-empty constraint is required")
        return cleaned


class PackPipelineInput(BaseModel):
    niche: str = Field(min_length=3, max_length=300)
    pack_title: str = Field(min_length=3, max_length=200)
    pack_subtitle: str | None = Field(default=None, max_length=300)
    brand_name: str = Field(default="Kwizzle Prompt Lab", max_length=120)
    prompts: list[ArchitectedPrompt] = Field(min_length=1, max_length=50)
    polish_listing_with_llm: bool = Field(default=False)

    @field_validator("niche", "pack_title")
    @classmethod
    def strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value cannot be empty")
        return stripped


class PricingTier(BaseModel):
    id: Literal["starter", "pro", "agency", "resell"]
    label: str
    price_usd: int
    includes: list[str]


class ListingCopy(BaseModel):
    title_variants: list[str]
    short_description: str
    long_description: str
    bullet_benefits: list[str]
    tags: list[str]
    seo_keywords: list[str]
    pricing_tiers: list[PricingTier]
    platform_notes: dict[str, str]


class ArtifactLinks(BaseModel):
    pdf: str
    cover_svg: str
    cover_png: str | None = None
    listing_json: str
    manifest: str


class RunInstrumentation(BaseModel):
    duration_ms: int
    llm_enabled: bool
    llm_model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ProductManifest(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    niche: str
    pack_title: str
    slug: str
    generated_at: str
    listing: ListingCopy
    artifacts: ArtifactLinks
    instrumentation: RunInstrumentation
    prompt_count: int


def slugify(text: str) -> str:
    lowered = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug[:80] or "prompt-pack"
