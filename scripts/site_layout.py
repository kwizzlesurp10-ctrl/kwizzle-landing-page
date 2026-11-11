from __future__ import annotations

import re
from pathlib import Path

X_PIXEL_MARKER_START = "<!-- X conversion tracking base code -->"
X_PIXEL_MARKER_END = "<!-- End X conversion tracking base code -->"
SNIPPET_RELATIVE = Path("snippets/x-conversion-tracking-base.html")

# Directories mirrored into the nginx docroot by build_static_site (HTML inside is injected).
PUBLIC_HTML_SUBTREES = ("docs", "health", "packs")
PUBLIC_MCP_HTML_DIR = Path(".well-known/mcp")

_STATIC_COPY_DIRS = ("assets", "docs", "health", "packs", "sample-packs", ".well-known")
_STATIC_COPY_FILES = (
    "favicon.ico",
    "favicon.svg",
    "robots.txt",
    "sitemap.xml",
    "llms.txt",
    "schema_org_snippet.html",
)

_PIXEL_BLOCK_RE = re.compile(
    re.escape(X_PIXEL_MARKER_START) + r".*?" + re.escape(X_PIXEL_MARKER_END) + r"\s*",
    re.DOTALL,
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def snippet_path(root: Path | None = None) -> Path:
    base = root or repository_root()
    return base / SNIPPET_RELATIVE


def load_canonical_x_pixel_snippet(root: Path | None = None) -> str:
    path = snippet_path(root)
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    return text


def discover_public_html_sources(root: Path) -> list[Path]:
    """
    Every routable HTML document that receives shared head injections.
    New pages under docs/, health/, packs/, or .well-known/mcp/ are included automatically.
    """
    sources: list[Path] = []
    root_index = root / "index.html"
    if root_index.is_file():
        sources.append(root_index)

    for sub in PUBLIC_HTML_SUBTREES:
        base = root / sub
        if base.is_dir():
            sources.extend(sorted(base.rglob("*.html")))

    mcp_dir = root / PUBLIC_MCP_HTML_DIR
    if mcp_dir.is_dir():
        sources.extend(sorted(mcp_dir.rglob("*.html")))

    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in sources:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)
    return deduped


def is_injectable_html_document(html: str) -> bool:
    lowered = html.lstrip()[:256].lower()
    if "<html" not in lowered and "<!doctype" not in lowered:
        return False
    return "</head>" in html.lower()


def strip_x_pixel_block(html: str) -> str:
    return _PIXEL_BLOCK_RE.sub("", html)


def inject_x_pixel_before_head_close(html: str, snippet: str) -> str:
    if not is_injectable_html_document(html):
        return strip_x_pixel_block(html)
    cleaned = strip_x_pixel_block(html)
    head_idx = cleaned.lower().rfind("</head>")
    if head_idx == -1:
        raise ValueError("missing </head>")
    return cleaned[:head_idx] + snippet + cleaned[head_idx:]


def static_copy_dirs() -> tuple[str, ...]:
    return _STATIC_COPY_DIRS


def static_copy_files() -> tuple[str, ...]:
    return _STATIC_COPY_FILES
