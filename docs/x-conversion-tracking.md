# X conversion tracking (pixel `q8lud`)

Production site: **https://kwizzlesurp.com** (Render Docker: nginx static + FastAPI).

## Browser base pixel

Canonical snippet: `snippets/x-conversion-tracking-base.html` (inlined before `</head>` on every public HTML page).

- Loads `uwt.js` once and calls `twq('config','q8lud')`.
- `assets/js/x-twclid-capture.js` persists `twclid` from the landing URL (sessionStorage + cookie `kwizzle_twclid`) for server hooks.

## Server-side conversions

Module: `api/x_conversion/`.

- POST `https://ads-api.x.com/12/measurement/conversions/q8lud`
- Header `X-Pixel-Token` from env `X_PIXEL_TOKEN` (server-only).
- Event IDs configured via `X_CONVERSION_EVENTS` JSON (hook key → `tw-q8lud-…`).

`report_server_conversion()` **does not** call X unless both a configured event ID and token are present.

### Documented server hook keys (no guessed IDs wired)

| Hook key | Where | Notes |
|----------|--------|--------|
| `pack_created` | `POST /api/packs` success | Agent/API packaging flow; uses `conversion_id=pack:{run_id}` |

### Not server-confirmed on this repo

- No on-site signup, checkout, or lead forms.
- Primary CTAs are outbound links (`dashboard.kwizzle.com`, `x402-mcp.onrender.com/dashboard`, etc.) — browser `twq('event', …)` must be added after you supply real event IDs.

## Wiring new events

1. Set `X_PIXEL_TOKEN` on the Render web service.
2. Set `X_CONVERSION_EVENTS`, e.g. `{"pack_created":"tw-q8lud-<id>"}`.
3. For browser conversions, add `twq('event','tw-q8lud-<id>', { conversion_id: '…' })` on the confirmed UI action (reuse the same `conversion_id` if also reporting server-side).

Do not enable placeholder IDs in production.
