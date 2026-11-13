from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_GLOBS = (
    "*.html",
    "*.txt",
    "*.md",
    ".well-known/*.json",
    "docs/**/*.html",
)


def _public_files() -> list[Path]:
    files: list[Path] = []
    files.extend(ROOT.glob("index.html"))
    files.extend(ROOT.glob("llms.txt"))
    files.extend(ROOT.glob("*.md"))
    files.extend(ROOT.glob(".well-known/*.json"))
    files.extend(ROOT.glob("docs/**/*.html"))
    return [p for p in files if p.is_file()]


def test_no_keith_severson_in_public_content() -> None:
    offenders: list[str] = []
    for path in _public_files():
        text = path.read_text(encoding="utf-8")
        if "Keith Severson" in text or "Kwizz Severson" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], offenders


def test_no_standalone_kwizz_brand_in_public_html() -> None:
    """Reject handle/brand 'Kwizz' but allow Kwizzle, KwizzleSurp, kwizzlesurp URLs."""
    pattern = re.compile(r"(?<![a-zA-Z])Kwizz(?![a-zA-Z])")
    offenders: list[str] = []
    for path in _public_files():
        if path.suffix not in {".html", ".txt", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], offenders


def test_landing_footer_has_panda_dragon_credit() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "a Panda &amp; Dragon Project" in html
