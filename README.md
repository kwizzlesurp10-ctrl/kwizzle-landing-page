# Kwizzle Parallax Landing Page

High-performance parallax landing page for Kwizzle (the Agent-to-Agent Commerce & Compliance API Gateway).

## Features
* **Tailwind CSS Styling**: Responsive modern slate and neon-emerald palette.
* **Scroll-Linked Parallax Layers**: Ultra-smooth background grid and multi-direction columns scrolling (performance optimized using GPU-accelerated translate offsets).
* **Live Gateway Status**: Uses client-side runtime fetching to ping the active `x402-mcp` Render endpoint (`/.well-known/mcp/server-card.json`) and report live EVM configuration, wallet connection state, and active Base rails.
* **Responsive Handoffs**: Direct button linking to `https://dashboard.kwizzle.com`.

## Hosting on Render
This repository is configured to be deployed as a **Static Site** on Render.
* **Build Command**: `(none)`
* **Publish Directory**: `.`
