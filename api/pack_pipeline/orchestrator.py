from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from api.pack_pipeline.cover import render_cover_svg
from api.pack_pipeline.instrumentation import timed_run
from api.pack_pipeline.listing import build_listing_copy, maybe_polish_listing_copy
from api.pack_pipeline.pdf import build_pack_pdf
from api.pack_pipeline.schema import (
    ArtifactLinks,
    PackPipelineInput,
    ProductManifest,
    RunInstrumentation,
    slugify,
)


def package_prompt_pack(
    pack: PackPipelineInput,
    *,
    output_dir: Path | None = None,
    public_base_path: str | None = None,
) -> tuple[ProductManifest, dict[str, bytes | str]]:
    run_id = str(uuid.uuid4())
    slug = slugify(pack.pack_title)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    with timed_run(run_id=run_id, niche=pack.niche) as metrics:
        listing = build_listing_copy(pack)
        listing = maybe_polish_listing_copy(listing, pack, metrics)

        pdf_bytes = build_pack_pdf(pack)
        cover_svg = render_cover_svg(pack)
        listing_json = listing.model_dump(mode="json")

        artifacts_bytes: dict[str, bytes | str] = {
            "pack.pdf": pdf_bytes,
            "cover.svg": cover_svg,
            "listing-copy.json": json.dumps(listing_json, indent=2) + "\n",
        }

        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "pack.pdf").write_bytes(pdf_bytes)
            (output_dir / "cover.svg").write_text(cover_svg, encoding="utf-8")
            (output_dir / "listing-copy.json").write_text(
                artifacts_bytes["listing-copy.json"], encoding="utf-8"
            )
            (output_dir / "input.snapshot.json").write_text(
                pack.model_dump_json(indent=2) + "\n", encoding="utf-8"
            )

        base = public_base_path or f"/sample-packs/{slug}"
        artifacts = ArtifactLinks(
            pdf=f"{base}/pack.pdf",
            cover_svg=f"{base}/cover.svg",
            cover_png=None,
            listing_json=f"{base}/listing-copy.json",
            manifest=f"{base}/manifest.json",
        )

        metrics.finish()
        manifest = ProductManifest(
            niche=pack.niche,
            pack_title=pack.pack_title,
            slug=slug,
            generated_at=generated_at,
            listing=listing,
            artifacts=artifacts,
            instrumentation=RunInstrumentation(
                duration_ms=metrics.duration_ms,
                llm_enabled=metrics.llm_enabled,
                llm_model=metrics.llm_model,
                prompt_tokens=metrics.prompt_tokens,
                completion_tokens=metrics.completion_tokens,
                total_tokens=metrics.total_tokens,
            ),
            prompt_count=len(pack.prompts),
        )

        manifest_json = manifest.model_dump(mode="json")
        artifacts_bytes["manifest.json"] = json.dumps(manifest_json, indent=2) + "\n"

        if output_dir is not None:
            (output_dir / "manifest.json").write_text(
                artifacts_bytes["manifest.json"], encoding="utf-8"
            )

    return manifest, artifacts_bytes
