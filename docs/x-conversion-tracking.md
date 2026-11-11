# X conversion tracking (pixel `q8lud`)

Production site: **https://kwizzlesurp.com** (Render Docker: nginx static + FastAPI).

## Shared layout / build-time head injection

Source HTML in git **does not** embed the pixel. At build time, `scripts/build_static_site.py` injects the canonical snippet from `snippets/x-conversion-tracking-base.html` immediately before every public document’s `</head>`.

Discovery is centralized in `scripts/site_layout.py` (`discover_public_html_sources`). Any new `*.html` under `docs/`, `health/`, `packs/`, or `.well-known/mcp/`, plus root `index.html`, is included automatically.

### Commands

```bash
# Local assembled docroot (same step as Docker build)
python scripts/build_static_site.py --source . --output build/nginx-html
# or: npm run build:site
```

Render/Docker runs the same script during `docker build` (see `Dockerfile`).

## Browser base pixel

- Loads `uwt.js` once and calls `twq('config','q8lud')` (snippet unchanged).
- `assets/js/x-twclid-capture.js` persists landing `twclid` (sessionStorage + cookie `kwizzle_twclid`) for server hooks.

## Server-side conversions

Module: `api/x_conversion/`.

- POST `https://ads-api.x.com/12/measurement/conversions/q8lud`
- Header `X-Pixel-Token` from env `X_PIXEL_TOKEN` (server-only).
- Event IDs via `X_CONVERSION_EVENTS` JSON (hook key → `tw-q8lud-…`).

`report_server_conversion()` **does not** call X unless both a configured event ID and token are present.

### Documented server hook keys (no guessed IDs wired)

| Hook key | Where | Notes |
|----------|--------|--------|
| `pack_created` | `POST /api/packs` success | Agent/API flow; enable only with a real event_id |

### Not server-confirmed on this repo

- No on-site signup, checkout, or lead forms.
- Primary CTAs are outbound links — browser `twq('event', …)` after you supply real event IDs.

## Wiring new events

1. Set `X_PIXEL_TOKEN` on the Render web service.
2. Set `X_CONVERSION_EVENTS`, e.g. `{"pack_created":"tw-q8lud-<id>"}`.
3. For browser conversions, add `twq('event','tw-q8lud-<id>', { conversion_id: '…' })` on the confirmed UI action.

Do not enable placeholder IDs in production.
