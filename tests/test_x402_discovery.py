from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RETIRED_PAYTO = "0x05e1720bB82F86B5bc7940a99FDC702E32256357"
ACTIVE_PAYTO = "0x0d25A44f74868eCE53B305C97139CF4B62963410"

LIVE_US_CITY_CODES = (
    "mn",
    "sea",
    "nyc",
    "chi",
    "den",
    "sf",
    "lax",
    "bos",
    "phi",
    "orl",
    "nola",
    "moco",
    "gain",
    "kc",
    "atx",
    "bna",
    "sd",
)

STALE_CITY_CODES = ("sp", "phx", "mia", "phl", "det", "bal", "dc", "pdx", "`la`")

TEXT_SCAN_IGNORE = {
    ROOT / ".git",
    ROOT / "node_modules",
    ROOT / "tests",
    ROOT / "sample-packs" / "real-estate-listing-descriptions" / "pack.pdf",
}


def _iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(ignored in path.parents or path == ignored for ignored in TEXT_SCAN_IGNORE):
            continue
        if path.suffix.lower() in {".png", ".webp", ".ico", ".pdf", ".min.css", ".pyc"}:
            continue
        files.append(path)
    return files


def test_retired_payto_address_not_in_repository() -> None:
    offenders: list[str] = []
    for path in _iter_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if RETIRED_PAYTO.lower() in text.lower():
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"retired payTo still present in: {offenders}"


def test_active_payto_in_agent_discovery_files() -> None:
    for rel in (".well-known/agent.json", ".well-known/agent-card.json", "llms.txt"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert ACTIVE_PAYTO in text
        assert "Operator Reserve" not in text
        assert "operatorFunding" not in text

    agent = json.loads((ROOT / ".well-known/agent.json").read_text(encoding="utf-8"))
    assert agent["settlement"]["payTo"] == ACTIVE_PAYTO


def test_llms_city_list_matches_live_catalog() -> None:
    llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
    section = llms.split("## Supported US Municipal Jurisdictions")[1].split("## ")[0]
    for code in LIVE_US_CITY_CODES:
        assert f"`{code}`" in section, f"missing city code {code!r} in llms.txt"
    for stale in STALE_CITY_CODES:
        assert stale not in section, f"stale city entry {stale!r} still in llms.txt"


def test_nginx_proxies_paid_and_discovery_paths() -> None:
    proxy_conf = (ROOT / "nginx-x402-proxy.conf").read_text(encoding="utf-8")
    for fragment in (
        "/.well-known/x402",
        "/openapi.json",
        "/.well-known/mcp",
        "/mcp/",
        "/us/",
        "/mn/",
        "/base/",
        "/health",
    ):
        assert fragment in proxy_conf
    docker_conf = (ROOT / "nginx-docker.conf").read_text(encoding="utf-8")
    assert "include /etc/nginx/conf.d/x402-proxy.conf" in docker_conf


def test_render_routes_redirect_get_safe_discovery_only() -> None:
    yaml = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "destination: /index.html" not in yaml
    assert "x402-mcp.onrender.com/.well-known/x402" in yaml
    assert re.search(r"source: /health\b", yaml)
    assert "source: /mcp/" not in yaml, "POST MCP must use nginx proxy, not edge redirect"
