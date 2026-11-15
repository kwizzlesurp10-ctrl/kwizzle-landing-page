#!/usr/bin/env python3
"""Build kwizzlesurp.com /.well-known/x402 from live upstream catalogs."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / ".well-known" / "x402"

BASE_ASSET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
PAY_TO = "0x0d25A44f74868eCE53B305C97139CF4B62963410"
NETWORK = "eip155:8453"
HUB_BASE_URL = "https://kwizzlesurp.com"
FETCH_TIMEOUT_S = 45

UPSTREAM_WELL_KNOWN: tuple[tuple[str, str], ...] = (
    ("x402-mcp", "https://x402-mcp.onrender.com/.well-known/x402"),
    ("alpha-sentinel", "https://alpha-sentinel-mcp.vercel.app/.well-known/x402"),
    ("x402orcle", "https://x402orcle.vercel.app/.well-known/x402"),
    ("x402-crediting-swarm", "https://x402-crediting-swarm.vercel.app/.well-known/x402"),
)


@dataclass(frozen=True)
class UpstreamFetch:
    service_id: str
    url: str
    document: dict[str, Any] | None
    error: str | None


def _fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "kwizzle-x402-build/1.0"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
        raw = resp.read()
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"expected JSON object from {url}")
    return parsed


def _is_paid_detail(entry: dict[str, Any]) -> bool:
    tier = str(entry.get("tier", "")).lower()
    if tier == "free":
        return False
    price = entry.get("price")
    if price == "free" or price is None:
        if entry.get("price_usd", 0) == 0 and entry.get("price_usdc", 0) == 0:
            return False
    network = entry.get("network")
    if network is None:
        return False
    url = entry.get("url") or entry.get("resource")
    return bool(url)


def _normalize_detail(entry: dict[str, Any], source: str, source_url: str) -> dict[str, Any]:
    url = entry.get("url") or entry.get("resource")
    if not url:
        raise ValueError("resource entry missing url")
    normalized: dict[str, Any] = {
        "name": entry.get("name") or entry.get("mcp_url") or url.rsplit("/", 1)[-1],
        "url": url,
        "method": (entry.get("method") or "POST").upper(),
        "network": entry.get("network") or NETWORK,
        "source_service": source,
        "source_discovery": source_url,
    }
    if entry.get("price") is not None:
        normalized["price"] = entry["price"]
    if entry.get("price_usd") is not None:
        normalized["price_usd"] = entry["price_usd"]
    if entry.get("price_usdc") is not None:
        normalized["price_usdc"] = entry["price_usdc"]
    if entry.get("amount") is not None:
        normalized["amount"] = entry["amount"]
    if entry.get("atomic_amount") is not None:
        normalized["atomic_amount"] = entry["atomic_amount"]
    desc = entry.get("description") or entry.get("what")
    if desc:
        normalized["description"] = desc
    if entry.get("params") is not None:
        normalized["params"] = entry["params"]
    if entry.get("tags") is not None:
        normalized["tags"] = entry["tags"]
    return normalized


def _details_from_bazaar_items(doc: dict[str, Any], source: str, source_url: str) -> list[dict[str, Any]]:
    items = doc.get("items")
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        resource = item.get("resource")
        if not resource:
            continue
        accepts = item.get("accepts") or []
        accept = accepts[0] if accepts else {}
        price = accept.get("price", "")
        if not price or str(price).lower() == "free":
            continue
        out.append(
            _normalize_detail(
                {
                    "url": resource,
                    "method": "POST" if item.get("type") == "http" else str(item.get("type", "POST")).upper(),
                    "price": price,
                    "network": accept.get("network") or NETWORK,
                    "description": item.get("description"),
                    "name": resource.rsplit("/", 1)[-1],
                },
                source,
                source_url,
            )
        )
    return out


def _collect_paid_details(doc: dict[str, Any], source: str, source_url: str) -> list[dict[str, Any]]:
    if "items" in doc and "resource_details" not in doc:
        return _details_from_bazaar_items(doc, source, source_url)

    details: list[dict[str, Any]] = []
    for key in ("resource_details", "catalog"):
        block = doc.get(key)
        if not isinstance(block, list):
            continue
        for entry in block:
            if not isinstance(entry, dict):
                continue
            if not _is_paid_detail(entry):
                continue
            try:
                details.append(_normalize_detail(entry, source, source_url))
            except ValueError:
                continue
    return details


def _dedupe_details(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for d in details:
        key = (d["url"], d.get("method", "GET"))
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    out.sort(key=lambda x: (x.get("source_service", ""), x["url"]))
    return out


def _load_fallback() -> dict[str, Any] | None:
    if not OUT_PATH.is_file():
        return None
    try:
        return json.loads(OUT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def build_document(fetches: list[UpstreamFetch]) -> dict[str, Any]:
    all_details: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []

    for fetch in fetches:
        meta: dict[str, Any] = {
            "id": fetch.service_id,
            "discovery_url": fetch.url,
            "ok": fetch.document is not None,
        }
        if fetch.error:
            meta["error"] = fetch.error
        if fetch.document:
            meta["upstream_service"] = fetch.document.get("service") or fetch.document.get("name")
            meta["base_url"] = fetch.document.get("base_url")
            paid = _collect_paid_details(fetch.document, fetch.service_id, fetch.url)
            meta["paid_resource_count"] = len(paid)
            all_details.extend(paid)
        sources.append(meta)

    catalog = _dedupe_details(all_details)
    resources = [e["url"] for e in catalog]

    return {
        "version": 1,
        "x402_version": 2,
        "service": "kwizzlesurp",
        "name": "KwizzleSurp x402 Commerce Hub",
        "base_url": HUB_BASE_URL,
        "networks": [NETWORK],
        "asset": BASE_ASSET,
        "asset_symbol": "USDC",
        "payTo": PAY_TO,
        "payment_header": "PAYMENT-SIGNATURE",
        "challenge_header": "PAYMENT-REQUIRED",
        "receipt_header": "PAYMENT-RESPONSE",
        "docs": f"{HUB_BASE_URL}/llms.txt",
        "agent_card": f"{HUB_BASE_URL}/.well-known/agent-card.json",
        "mcp": {"manifest": f"{HUB_BASE_URL}/.well-known/mcp.json"},
        "discovery": {
            "mcp_manifest": f"{HUB_BASE_URL}/.well-known/mcp.json",
            "agents_json": f"{HUB_BASE_URL}/.well-known/agent.json",
            "llms_txt": f"{HUB_BASE_URL}/llms.txt",
        },
        "aggregated_from": sources,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "resources": resources,
        "resource_details": catalog,
        "catalog": catalog,
    }


def fetch_upstream() -> list[UpstreamFetch]:
    results: list[UpstreamFetch] = []
    for service_id, url in UPSTREAM_WELL_KNOWN:
        try:
            doc = _fetch_json(url)
            results.append(UpstreamFetch(service_id, url, doc, None))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            results.append(UpstreamFetch(service_id, url, None, str(exc)))
    return results


def main() -> int:
    fetches = fetch_upstream()
    ok_count = sum(1 for f in fetches if f.document is not None)
    if ok_count == 0:
        fallback = _load_fallback()
        if fallback is None:
            print("No upstream catalogs available and no local fallback.", file=sys.stderr)
            return 1
        print("WARNING: using existing .well-known/x402 as fallback (all fetches failed)", file=sys.stderr)
        OUT_PATH.write_text(json.dumps(fallback, indent=2) + "\n", encoding="utf-8")
        return 0

    doc = build_document(fetches)
    if not doc["catalog"]:
        fallback = _load_fallback()
        if fallback and fallback.get("catalog"):
            print("WARNING: empty catalog from upstream; keeping previous catalog", file=sys.stderr)
            doc = fallback
        else:
            print("Built catalog is empty.", file=sys.stderr)
            return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(doc['catalog'])} paid resources, {ok_count}/{len(fetches)} upstream OK)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())