from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from api.pack_pipeline.schema import (
    ListingCopy,
    PackPipelineInput,
    PricingTier,
    slugify,
)

if TYPE_CHECKING:
    from api.pack_pipeline.instrumentation import RunMetrics


def _niche_keywords(niche: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9]{3,}", niche.lower())
    unique: list[str] = []
    for word in words:
        if word not in unique:
            unique.append(word)
    return unique[:12]


def build_listing_copy(pack: PackPipelineInput) -> ListingCopy:
    slug = slugify(pack.pack_title)
    prompt_count = len(pack.prompts)
    niche = pack.niche
    title_base = pack.pack_title

    title_variants = [
        f"{title_base} — {prompt_count}-Prompt AI Pack for {niche}",
        f"{title_base}: Done-for-You ChatGPT Prompts ({niche})",
        f"Instant {niche.title()} Prompt Pack — {prompt_count} Multi-Step Workflows",
        f"{title_base} | Copy-Paste AI Prompt System + Examples",
    ]

    short_description = (
        f"Ship faster with {prompt_count} architected, multi-step prompts built for "
        f"{niche}. Each prompt includes [SLOT] variables, constraints, format rules, "
        f"and a worked example so you get consistent outputs on day one."
    )

    long_description = (
        f"Stop staring at a blank chat box. This pack gives {niche} a repeatable "
        f"prompt system: Role / Goal / Constraints / Format structure, slot-by-slot "
        f"guidance, and real example outputs you can adapt immediately.\n\n"
        f"What's inside:\n"
        f"• Branded PDF with cover, quick-start guide, full prompt library, and one-page cheat sheet\n"
        f"• {prompt_count} production-ready prompts with [SLOT] placeholders explained\n"
        f"• Worked examples for every prompt so you know what \"good\" looks like\n"
        f"• Listing-ready metadata (tags, SEO keywords, tiered pricing suggestions)\n\n"
        f"Ideal for solo operators, agencies, and creators who sell digital products or "
        f"need reliable AI workflows without tuning from scratch."
    )

    bullet_benefits = [
        f"Built specifically for {niche} — not generic \"write anything\" fluff",
        f"{prompt_count} multi-step prompts with Role, Goal, Constraints, and Format blocks",
        "Slot cheat sheet: every [SLOT] documented with examples",
        "Worked example output per prompt for instant quality calibration",
        "One-page quick reference for daily use",
        "Deterministic structure — consistent results across team members",
        "Commercial-use friendly tiers (see pricing options below)",
    ]

    tags = list(
        dict.fromkeys(
            [
                "ai prompts",
                "chatgpt prompts",
                "prompt pack",
                "digital download",
                slug.replace("-", " "),
                * _niche_keywords(niche)[:8],
            ]
        )
    )[:15]

    seo_keywords = list(
        dict.fromkeys(
            [
                f"{niche} ai prompts",
                f"{niche} chatgpt template",
                "multi step prompt pack",
                "prompt engineering workbook",
                "ai workflow templates",
                * _niche_keywords(niche),
            ]
        )
    )[:20]

    pricing_tiers = [
        PricingTier(
            id="starter",
            label="Starter — personal use",
            price_usd=9,
            includes=[
                "PDF prompt pack + quick reference",
                "Personal / single-seat use",
                "Updates for 30 days",
            ],
        ),
        PricingTier(
            id="pro",
            label="Pro — commercial client work",
            price_usd=27,
            includes=[
                "Everything in Starter",
                "Use with paying clients & deliverables",
                "Team share (up to 5 seats)",
            ],
        ),
        PricingTier(
            id="agency",
            label="Agency — team license",
            price_usd=47,
            includes=[
                "Everything in Pro",
                "Unlimited internal seats",
                "White-label PDF cover (text swap)",
            ],
        ),
        PricingTier(
            id="resell",
            label="Resell rights add-on",
            price_usd=97,
            includes=[
                "Permission to resell the pack as your own product",
                "Must not undercut listed tier pricing",
                "Requires Agency tier as base",
            ],
        ),
    ]

    platform_notes = {
        "gumroad": "Use title variant #1, 3–5 tags from the tags list, enable PDF stamp if desired.",
        "etsy": "Lead with niche in title; max 13 tags — pick highest-intent SEO keywords.",
        "payhip": "Use long description as product body; attach PDF + cover PNG.",
    }

    return ListingCopy(
        title_variants=title_variants,
        short_description=short_description,
        long_description=long_description,
        bullet_benefits=bullet_benefits,
        tags=tags,
        seo_keywords=seo_keywords,
        pricing_tiers=pricing_tiers,
        platform_notes=platform_notes,
    )


def maybe_polish_listing_copy(
    listing: ListingCopy,
    pack: PackPipelineInput,
    metrics: RunMetrics,
) -> ListingCopy:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    flag = os.environ.get("PACK_PIPELINE_LLM_POLISH", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if not pack.polish_listing_with_llm or not flag or not api_key:
        return listing

    try:
        import httpx
    except ImportError:
        return listing

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    system = (
        "You polish marketplace listing copy for digital prompt packs. "
        "Return JSON with keys: short_description, long_description, bullet_benefits (array). "
        "Keep factual claims; do not invent features."
    )
    user_payload = {
        "niche": pack.niche,
        "listing": listing.model_dump(),
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": str(user_payload)},
                ],
            },
        )
        response.raise_for_status()
        body = response.json()
        usage = body.get("usage") or {}
        metrics.record_llm_usage(
            model=model,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
        )
        content = body["choices"][0]["message"]["content"]
        import json

        polished = json.loads(content)
        return listing.model_copy(
            update={
                "short_description": polished.get(
                    "short_description", listing.short_description
                ),
                "long_description": polished.get(
                    "long_description", listing.long_description
                ),
                "bullet_benefits": polished.get(
                    "bullet_benefits", listing.bullet_benefits
                ),
            }
        )
