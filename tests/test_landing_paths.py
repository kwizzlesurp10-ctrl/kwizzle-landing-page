from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_robots_txt_points_at_sitemap() -> None:
    text = (ROOT / "robots.txt").read_text(encoding="utf-8")
    assert "User-agent: *" in text
    assert "Sitemap: https://kwizzlesurp.com/sitemap.xml" in text


def test_sitemap_is_xml_not_html() -> None:
    raw = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    assert raw.lstrip().startswith("<?xml")
    assert "<html" not in raw.lower()
    root = ET.fromstring(raw)
    locs = [el.text for el in root.iter() if el.tag.endswith("loc")]
    assert "https://kwizzlesurp.com/" in locs


def test_favicon_is_binary_icon() -> None:
    data = (ROOT / "favicon.ico").read_bytes()
    assert data[:4] == b"\x00\x00\x01\x00"
    assert b"<!DOCTYPE html>" not in data


def test_status_widget_reads_health_not_schema() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "https://x402-mcp.onrender.com/health" in html
    assert "wallet_configured" in html
    assert "pay_to_configured" in html
    assert "eip155:8453" in html
    assert re.search(r'id="network-status"[^>]*>Checking\.\.\.', html)
    assert "config.EVM_PRIVATE_KEY" not in html


def test_render_routes_do_not_swallow_static_files() -> None:
    yaml = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "destination: /index.html" not in yaml
    assert "source: /health" in yaml
    assert "x402-mcp.onrender.com/health" in yaml


def test_health_and_manifest_handoff_pages_exist() -> None:
    health = (ROOT / "health" / "index.html").read_text(encoding="utf-8")
    manifest = (ROOT / ".well-known" / "mcp" / "index.html").read_text(encoding="utf-8")
    assert "https://x402-mcp.onrender.com/health" in health
    assert "https://x402-mcp.onrender.com/.well-known/mcp" in manifest
