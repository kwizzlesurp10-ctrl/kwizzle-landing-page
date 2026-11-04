from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.pack_pipeline.listing import build_listing_copy
from api.pack_pipeline.schema import PackPipelineInput

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "sample-packs" / "real-estate-listing-descriptions" / "input.json"


@pytest.fixture
def sample_pack() -> PackPipelineInput:
    raw = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
    return PackPipelineInput.model_validate(raw)


def test_listing_copy_has_tier_prices(sample_pack: PackPipelineInput) -> None:
    listing = build_listing_copy(sample_pack)
    prices = {tier.id: tier.price_usd for tier in listing.pricing_tiers}
    assert prices["starter"] == 9
    assert prices["pro"] == 27
    assert prices["agency"] == 47
    assert prices["resell"] == 97
    assert len(listing.title_variants) >= 3
    assert sample_pack.niche.lower() in listing.short_description.lower()
    assert len(listing.tags) >= 5


def test_package_prompt_pack_writes_pdf_and_manifest(sample_pack: PackPipelineInput) -> None:
    from api.pack_pipeline.orchestrator import package_prompt_pack

    out = ROOT / "sample-packs" / "real-estate-listing-descriptions"
    manifest, artifacts = package_prompt_pack(
        sample_pack,
        output_dir=out,
        public_base_path="/sample-packs/real-estate-listing-descriptions",
    )
    assert manifest.prompt_count == 3
    assert manifest.instrumentation.duration_ms >= 0
    assert manifest.instrumentation.llm_enabled is False
    pdf = artifacts["pack.pdf"]
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"
    assert (out / "manifest.json").is_file()
    assert (out / "cover.svg").read_text(encoding="utf-8").startswith("<svg")


def test_api_create_pack(sample_pack: PackPipelineInput) -> None:
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    response = client.post("/api/packs", json=json.loads(sample_pack.model_dump_json()))
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "listing-description-architect"
    assert "artifacts" in body
    assert body["instrumentation"]["llm_enabled"] is False


def test_mcp_tools_list() -> None:
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    response = client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    assert tools[0]["name"] == "package_prompt_pack"
