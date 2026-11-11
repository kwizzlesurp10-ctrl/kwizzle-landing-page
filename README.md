# Kwizzle Parallax Landing Page

High-performance parallax landing page for Kwizzle (the Agent-to-Agent Commerce & Compliance API Gateway).

## Features
* **Tailwind CSS Styling**: Responsive modern slate and neon-emerald palette.
* **Scroll-Linked Parallax Layers**: Ultra-smooth background grid and multi-direction columns scrolling (performance optimized using GPU-accelerated translate offsets).
* **Live Gateway Status**: Uses client-side runtime fetching to ping the active `x402-mcp` Render endpoint (`/.well-known/mcp/server-card.json`) and report live EVM configuration, wallet connection state, and active Base rails.
* **Responsive Handoffs**: Direct button linking to `https://dashboard.kwizzle.com`.

---

## Run with Docker (Recommended)

### Using Docker Compose (Single Command)
Run the following command from the repository root:
```bash
docker compose up -d
```
Then visit **[http://localhost:8080](http://localhost:8080)** in your browser.

To stop the container:
```bash
docker compose down
```

### Using Standard Docker CLI
Build and run the container manually:
```bash
# Build image
docker build -t kwizzle-landing-page .

# Run container on port 8080
docker run -d --name kwizzle-landing-page -p 8080:80 kwizzle-landing-page
```

---

## Hosting on Render

**Production (`https://kwizzlesurp.com`)** deploys from this repo on Render as a **Docker Web Service** (`render.yaml`, `Dockerfile`). nginx serves the static site; uvicorn serves the FastAPI prompt-pack API behind `/api/*`.

If the dashboard still shows a **Static Site**, migrate to **Web → Docker** (apply the blueprint or recreate the service) so `POST /api/packs` works on the same host. Cloudflare DNS can stay pointed at Render.

Optional env vars: `OPENAI_API_KEY`, `PACK_PIPELINE_LLM_POLISH=true`, `OPENAI_MODEL` (default `gpt-4o-mini`). The pipeline runs without them.

**X Ads conversion tracking (pixel `q8lud`):** the base pixel is injected at **build time** into every public HTML document via `scripts/build_static_site.py` (Docker runs the same step). Server reporting uses `X_PIXEL_TOKEN` and `X_CONVERSION_EVENTS` (see `.env.example` and `docs/x-conversion-tracking.md`). No credentials are committed; event IDs must be supplied before live API calls run.

```bash
python scripts/build_static_site.py --source . --output build/nginx-html
```

---

## Prompt pack pipeline

Extension for autonomous sellable prompt packs: branded PDF, cover SVG, marketplace listing copy, and JSON manifest.

**Sample (committed):** `sample-packs/real-estate-listing-descriptions/` — view at [/packs/](http://localhost:8080/packs/) when running locally.

**API:** `POST /api/packs` with body like `sample-packs/real-estate-listing-descriptions/input.json`.

**MCP for agents:** `POST /api/mcp` with JSON-RPC `tools/list` / `tools/call` (`package_prompt_pack`).

```bash
pip install -r requirements.txt
pytest
python scripts/generate_sample_pack.py   # refresh committed sample artifacts
```

| Route | Purpose |
|-------|---------|
| `POST /api/packs` | Package a prompt pack; returns manifest + `/generated-packs/{id}/` links |
| `GET /api/packs/sample` | Sample manifest |
| `POST /api/mcp` | MCP JSON-RPC shim |
| `GET /packs/` | Sample pack preview page |

Structured JSON logs record per-run `duration_ms` and token usage when LLM polish is enabled.
