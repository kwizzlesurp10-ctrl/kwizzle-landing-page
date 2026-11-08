#!/usr/bin/env python3
"""Assemble the nginx static docroot with shared head injections (X base pixel)."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.site_layout import (  # noqa: E402
    discover_public_html_sources,
    inject_x_pixel_before_head_close,
    load_canonical_x_pixel_snippet,
    static_copy_dirs,
    static_copy_files,
)


def build_static_site(*, source: Path, output: Path) -> list[Path]:
    source = source.resolve()
    output = output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    snippet = load_canonical_x_pixel_snippet(source)

    for name in static_copy_files():
        src_file = source / name
        if src_file.is_file():
            shutil.copy2(src_file, output / name)

    for dirname in static_copy_dirs():
        src_dir = source / dirname
        if not src_dir.is_dir():
            continue
        _copy_dir_non_html(src_dir, output / dirname)

    built_html: list[Path] = []
    for html_src in discover_public_html_sources(source):
        rel = html_src.relative_to(source)
        dest = output / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        html = html_src.read_text(encoding="utf-8")
        dest.write_text(inject_x_pixel_before_head_close(html, snippet), encoding="utf-8")
        built_html.append(dest)

    twclid_src = source / "assets" / "js" / "x-twclid-capture.js"
    if twclid_src.is_file():
        twclid_dest = output / "assets" / "js" / "x-twclid-capture.js"
        if not twclid_dest.is_file():
            twclid_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(twclid_src, twclid_dest)

    return built_html


def _copy_dir_non_html(src_dir: Path, dest_dir: Path) -> None:
    for path in sorted(src_dir.rglob("*")):
        rel = path.relative_to(src_dir)
        dest = dest_dir / rel
        if path.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            continue
        if path.suffix.lower() == ".html":
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=_REPO_ROOT,
        help="Repository root containing source HTML",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_REPO_ROOT / "build" / "nginx-html",
        help="nginx document root to write",
    )
    args = parser.parse_args(argv)

    snippet_file = args.source / "snippets" / "x-conversion-tracking-base.html"
    if not snippet_file.is_file():
        print(f"missing snippet at {snippet_file}", file=sys.stderr)
        return 1

    built = build_static_site(source=args.source, output=args.output)
    print(f"built {args.output} ({len(built)} HTML documents with shared head injection)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
