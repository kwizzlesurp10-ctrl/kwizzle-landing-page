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
        "/openapi.json",
        "/.well-known/mcp",
        "/mcp/",
        "/us/",
        "/mn/",
        "/base/",
    ):
        assert fragment in proxy_conf
    assert "proxy_pass https://x402-mcp.onrender.com/.well-known/x402" not in proxy_conf
    template = (ROOT / "nginx-docker.conf.template").read_text(encoding="utf-8")
    assert "location = /.well-known/x402" in template
    assert "error_page 404 /index.html" not in template
    assert "proxy_pass https://x402-mcp.onrender.com/health" not in proxy_conf
    assert "/etc/nginx/snippets/x402-proxy-params.conf" in proxy_conf
    params = (ROOT / "nginx-x402-proxy-params.conf").read_text(encoding="utf-8")
    assert "proxy_ssl_server_name on" in params
    assert "proxy_ssl_name x402-mcp.onrender.com" in params
    assert "proxy_set_header Host x402-mcp.onrender.com" in params
    assert "proxy_buffer_size 32k" in params
    template = (ROOT / "nginx-docker.conf.template").read_text(encoding="utf-8")
    assert "include /etc/nginx/snippets/x402-proxy.conf" in template
    assert "listen ${PORT}" in template
    assert "127.0.0.1:8000/health" in template


def test_dockerfile_installs_nginx_snippets_and_validates_config() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert (
        "COPY nginx-x402-proxy.conf /etc/nginx/snippets/x402-proxy.conf" in dockerfile
    )
    assert (
        "COPY nginx-x402-proxy-params.conf /etc/nginx/snippets/x402-proxy-params.conf"
        in dockerfile
    )
    assert "nginx-docker.conf.template" in dockerfile
    assert "nginx-test" in dockerfile
    assert "ENV PORT=10000" in dockerfile
    entrypoint = (ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")
    assert 'PORT="${PORT:-10000}"' in entrypoint
    assert "nginx-test" in entrypoint


def test_render_routes_redirect_get_safe_discovery_only() -> None:
    yaml = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "destination: /index.html" not in yaml
    assert "source: /.well-known/x402" not in yaml, "aggregated x402 is served from the Docker image"
    assert re.search(r"source: /health\b", yaml)
    assert "source: /mcp/" not in yaml, "POST MCP must use nginx proxy, not edge redirect"


def test_well_known_x402_is_valid_aggregated_json() -> None:
    path = ROOT / ".well-known" / "x402"
    assert path.is_file(), "run scripts/build_x402_discovery.py to refresh the catalog"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["service"] == "kwizzlesurp"
    assert doc["x402_version"] == 2
    assert doc["payTo"] == ACTIVE_PAYTO
    assert doc["asset"].lower() == "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
    assert "eip155:8453" in doc["networks"]
    catalog = doc["catalog"]
    assert len(catalog) >= 40
    for entry in catalog:
        assert entry.get("url")
        assert entry.get("network")
        assert entry.get("source_service") in {
            "x402-mcp",
            "alpha-sentinel",
            "x402orcle",
            "x402-crediting-swarm",
        }
        assert entry.get("price") not in (None, "free")
    urls = {e["url"] for e in catalog}
    assert "https://alpha-sentinel-mcp.vercel.app/tools/fetch_price" in urls
    assert "https://x402orcle.vercel.app/api/consult/oracle_ask" in urls
    assert "https://x402-crediting-swarm.vercel.app/api/swarm" in urls
    assert any("/us/mn/property-check" in u for u in urls)


def test_vercel_serves_x402_without_spa_fallback() -> None:
    vercel = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    header_rules = {h["source"]: h["headers"] for h in vercel["headers"]}
    x402_headers = {item["key"]: item["value"] for item in header_rules["/.well-known/x402"]}
    assert x402_headers["Content-Type"] == "application/json; charset=utf-8"
    assert x402_headers["Access-Control-Allow-Origin"] == "*"
    rewrite = vercel["rewrites"][0]["source"]
    assert ".well-known/" in rewrite
