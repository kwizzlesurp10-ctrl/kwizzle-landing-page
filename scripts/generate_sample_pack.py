#!/usr/bin/env python3
"""Generate committed sample pack artifacts from input.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.pack_pipeline.orchestrator import package_prompt_pack  # noqa: E402
from api.pack_pipeline.schema import PackPipelineInput  # noqa: E402

SAMPLE_DIR = ROOT / "sample-packs" / "real-estate-listing-descriptions"


def main() -> None:
    raw = json.loads((SAMPLE_DIR / "input.json").read_text(encoding="utf-8"))
    pack = PackPipelineInput.model_validate(raw)
    public_base = "/sample-packs/real-estate-listing-descriptions"
    manifest, _ = package_prompt_pack(
        pack,
        output_dir=SAMPLE_DIR,
        public_base_path=public_base,
    )
    print(f"Generated sample pack: {manifest.slug} ({manifest.prompt_count} prompts)")
    print(f"PDF: {SAMPLE_DIR / 'pack.pdf'}")


if __name__ == "__main__":
    main()
