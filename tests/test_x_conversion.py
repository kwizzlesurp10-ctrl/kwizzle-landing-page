from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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

ROOT = Path(__file__).resolve().parents[1]
SNIPPET = ROOT / "snippets" / "x-conversion-tracking-base.html"

HTML_PAGES = [
    ROOT / "index.html",
    ROOT / "packs" / "index.html",
    ROOT / "health" / "index.html",
    ROOT / ".well-known" / "mcp" / "index.html",
    ROOT / "docs" / "index.html",
    ROOT / "docs" / "automate-volatility-alerts.html",
    ROOT / "docs" / "integrate-predictive-alpha.html",
    ROOT / "docs" / "reduce-slippage-sentiment.html",
    ROOT / "docs" / "automate-volatility-alerts" / "index.html",
    ROOT / "docs" / "integrate-predictive-alpha" / "index.html",
    ROOT / "docs" / "reduce-slippage-sentiment" / "index.html",
]


def test_snippet_contains_single_q8lud_config() -> None:
    text = SNIPPET.read_text(encoding="utf-8")
    assert "X conversion tracking base code" in text
    assert "End X conversion tracking base code" in text
    assert text.count("twq('config','q8lud')") == 1
    assert "static.ads-twitter.com/uwt.js" in text


@pytest.mark.parametrize("page", HTML_PAGES, ids=lambda p: str(p.relative_to(ROOT)))
def test_public_html_includes_x_base_pixel_once(page: Path) -> None:
    html = page.read_text(encoding="utf-8")
    assert "<!-- X conversion tracking base code -->" in html
    assert html.count("twq('config','q8lud')") == 1
    assert html.count("static.ads-twitter.com/uwt.js") == 1
    head_end = html.index("</head>")
    snippet_pos = html.index("twq('config','q8lud')")
    assert snippet_pos < head_end


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
