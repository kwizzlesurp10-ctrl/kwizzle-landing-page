from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.x_conversion.client import XConversionClient
from api.x_conversion.identifiers import (
    build_identifiers,
    hash_email_identifier,
    normalize_email,
    normalize_phone_e164,
    sha256_hex_normalized,
)
from api.x_conversion.registry import load_conversion_event_registry
from api.x_conversion.reporting import report_server_conversion
from api.x_conversion.result import Err, Ok
from scripts.build_static_site import build_static_site
from scripts.site_layout import (
    discover_public_html_sources,
    inject_x_pixel_before_head_close,
    load_canonical_x_pixel_snippet,
    strip_x_pixel_block,
)

ROOT = Path(__file__).resolve().parents[1]
SNIPPET = ROOT / "snippets" / "x-conversion-tracking-base.html"
X_PIXEL_MARKER_START = "<!-- X conversion tracking base code -->"


@pytest.fixture(scope="module")
def built_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("nginx-html")
    build_static_site(source=ROOT, output=out)
    return out


def test_snippet_contains_single_q8lud_config() -> None:
    text = SNIPPET.read_text(encoding="utf-8")
    assert "X conversion tracking base code" in text
    assert "End X conversion tracking base code" in text
    assert text.count("twq('config','q8lud')") == 1
    assert "static.ads-twitter.com/uwt.js" in text


def test_source_html_must_not_embed_pixel_copies() -> None:
    """Authors edit source HTML only; pixel is injected at build time."""
    for src in discover_public_html_sources(ROOT):
        html = src.read_text(encoding="utf-8")
        assert "twq('config','q8lud')" not in html, f"remove embedded pixel from source: {src.relative_to(ROOT)}"
        assert X_PIXEL_MARKER_START not in html


def test_future_page_under_docs_is_discovered_and_injected(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    new_page = docs_dir / "future-playbook.html"
    new_page.write_text(
        "<!DOCTYPE html><html><head><title>t</title></head><body>x</body></html>",
        encoding="utf-8",
    )
    found = discover_public_html_sources(tmp_path)
    assert new_page in found
    snippet = load_canonical_x_pixel_snippet(ROOT)
    injected = inject_x_pixel_before_head_close(new_page.read_text(encoding="utf-8"), snippet)
    assert injected.count("twq('config','q8lud')") == 1


@pytest.mark.parametrize(
    "rel",
    [
        p.relative_to(ROOT).as_posix()
        for p in discover_public_html_sources(ROOT)
    ],
)
def test_built_public_html_includes_x_base_pixel_once(built_site: Path, rel: str) -> None:
    page = built_site / rel
    assert page.is_file(), f"missing built page {rel}"
    html = page.read_text(encoding="utf-8")
    assert "<!-- X conversion tracking base code -->" in html
    assert html.count("twq('config','q8lud')") == 1
    assert html.count("static.ads-twitter.com/uwt.js") == 1
    head_end = html.index("</head>")
    snippet_pos = html.index("twq('config','q8lud')")
    assert snippet_pos < head_end


def test_build_static_site_cli_matches_library(built_site: Path) -> None:
    assert (built_site / "index.html").is_file()
    assert (built_site / "assets" / "js" / "x-twclid-capture.js").is_file()
    assert len(list(discover_public_html_sources(ROOT))) == len(
        [p for p in discover_public_html_sources(ROOT) if (built_site / p.relative_to(ROOT)).is_file()]
    )


def test_strip_x_pixel_block_idempotent() -> None:
    snippet = SNIPPET.read_text(encoding="utf-8")
    html = f"<!DOCTYPE html><html><head><meta/></head><body></body></html>"
    once = inject_x_pixel_before_head_close(html, snippet)
    twice = inject_x_pixel_before_head_close(once, snippet)
    assert once.count("twq('config','q8lud')") == 1
    assert twice.count("twq('config','q8lud')") == 1
    assert strip_x_pixel_block(twice).count("twq('config','q8lud')") == 0


def test_email_normalization_and_hash() -> None:
    assert isinstance(normalize_email("  User@Example.COM "), Ok)
    normalized = normalize_email("  User@Example.COM ")
    assert isinstance(normalized, Ok)
    assert normalized.value == "user@example.com"
    hashed = hash_email_identifier("User@Example.COM")
    assert isinstance(hashed, Ok)
    assert hashed.value["hashed_email"] == sha256_hex_normalized("user@example.com")
    assert isinstance(normalize_email("not-an-email"), Err)


def test_phone_e164_rejects_ambiguous() -> None:
    ok = normalize_phone_e164("+14155552671")
    assert isinstance(ok, Ok)
    assert ok.value == "+14155552671"
    assert isinstance(normalize_phone_e164("4155552671"), Ok)
    assert isinstance(normalize_phone_e164("123"), Err)
    assert isinstance(normalize_phone_e164("+1"), Err)


def test_build_identifiers_requires_at_least_one() -> None:
    assert isinstance(build_identifiers(), Err)
    pair = build_identifiers(ip_address="203.0.113.1", user_agent="KwizzleTest/1.0")
    assert isinstance(pair, Ok)
    assert len(pair.value) == 1
    assert "ip_address" in pair.value[0]


def test_registry_empty_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("X_CONVERSION_EVENTS", raising=False)
    reg = load_conversion_event_registry()
    assert reg.events == {}


def test_registry_parses_valid_event_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "X_CONVERSION_EVENTS",
        json.dumps({"pack_created": "tw-q8lud-abc123real"}),
    )
    reg = load_conversion_event_registry()
    assert reg.event_id_for("pack_created") == "tw-q8lud-abc123real"


@pytest.mark.asyncio
async def test_client_missing_token_does_not_http() -> None:
    client = XConversionClient(pixel_token="")
    result = await client.send_conversion(
        event_id="tw-q8lud-testevt",
        conversion_id="dedup-1",
        ip_address="203.0.113.2",
        user_agent="agent",
    )
    assert isinstance(result, Err)
    assert result.error == "missing_pixel_token"


@pytest.mark.asyncio
async def test_client_request_shape_mocked() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"request": {"status": "queued"}}

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)

    client = XConversionClient(pixel_token="test-token-not-real", http_client=mock_http)
    when = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)
    result = await client.send_conversion(
        event_id="tw-q8lud-liveid",
        conversion_id="conv-dedup-99",
        conversion_time=when,
        event_source_url="https://kwizzlesurp.com/packs/",
        twclid="clid-abc",
    )
    assert isinstance(result, Ok)
    mock_http.post.assert_awaited_once()
    call = mock_http.post.await_args
    assert call.args[0] == "https://ads-api.x.com/12/measurement/conversions/q8lud"
    headers = call.kwargs["headers"]
    assert headers["X-Pixel-Token"] == "test-token-not-real"
    assert headers["Content-Type"] == "application/json"
    body = call.kwargs["json"]
    assert len(body["conversions"]) == 1
    conv = body["conversions"][0]
    assert conv["event_id"] == "tw-q8lud-liveid"
    assert conv["conversion_id"] == "conv-dedup-99"
    assert conv["conversion_time"] == "2026-11-08T12:00:00Z"
    assert conv["event_source_url"] == "https://kwizzlesurp.com/packs/"
    assert conv["identifiers"][0]["twclid"] == "clid-abc"


@pytest.mark.asyncio
async def test_report_skips_when_hook_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("X_CONVERSION_EVENTS", raising=False)
    result = await report_server_conversion(
        "pack_created",
        conversion_id="pack:unused",
        ip_address="203.0.113.3",
        user_agent="ua",
    )
    assert isinstance(result, Ok)
    assert result.value is None


@pytest.mark.asyncio
async def test_report_fails_without_token_when_event_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "X_CONVERSION_EVENTS",
        json.dumps({"pack_created": "tw-q8lud-realonly"}),
    )
    monkeypatch.delenv("X_PIXEL_TOKEN", raising=False)
    result = await report_server_conversion(
        "pack_created",
        conversion_id="pack:1",
        ip_address="203.0.113.4",
        user_agent="ua",
    )
    assert isinstance(result, Err)
    assert result.error == "missing_pixel_token"


@pytest.mark.asyncio
async def test_client_api_error_returns_err() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "unauthorized"

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)

    client = XConversionClient(pixel_token="bad", http_client=mock_http)
    result = await client.send_conversion(
        event_id="tw-q8lud-liveid",
        conversion_id="c1",
        ip_address="1.1.1.1",
        user_agent="ua",
    )
    assert isinstance(result, Err)
    assert result.error == "api_error_401"


def test_dockerfile_runs_static_site_build() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "build_static_site.py" in dockerfile


@pytest.mark.integration
def test_docker_image_serves_single_twq_config_in_head() -> None:
    if not shutil.which("docker"):
        pytest.skip("docker not available")
    subprocess.run(
        ["docker", "build", "-t", "kwizzle-landing-pixel-test", str(ROOT)],
        check=True,
        capture_output=True,
    )
    cid = subprocess.check_output(
        [
            "docker",
            "run",
            "-d",
            "-p",
            "18080:80",
            "kwizzle-landing-pixel-test",
        ],
        text=True,
    ).strip()
    try:
        import httpx

        for path in ("/", "/packs/", "/docs/"):
            resp = httpx.get(f"http://127.0.0.1:18080{path}", timeout=10.0)
            assert resp.status_code == 200
            assert resp.text.count("twq('config','q8lud')") == 1
            head_end = resp.text.index("</head>")
            assert resp.text.index("twq('config','q8lud')") < head_end
    finally:
        subprocess.run(["docker", "rm", "-f", cid], check=True, capture_output=True)
