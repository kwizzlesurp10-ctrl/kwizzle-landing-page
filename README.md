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
This repository is configured to be deployed as a **Static Site** on Render.
* **Build Command**: `(none)`
* **Publish Directory**: `.`
