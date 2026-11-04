from __future__ import annotations

import json
import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import ValidationError

from api.pack_pipeline.orchestrator import package_prompt_pack
from api.pack_pipeline.schema import PackPipelineInput, ProductManifest

ROOT = Path(__file__).resolve().parents[1]
GENERATED_ROOT = ROOT / "generated-packs"
SAMPLE_SLUG = "real-estate-listing-descriptions"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pack_pipeline.api")

app = FastAPI(
    title="Kwizzle Prompt Pack Pipeline",
    version="1.0.0",
    description="Packaging and listing optimizer for sellable prompt packs.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> PlainTextResponse:
    return PlainTextResponse("healthy\n")


@app.post("/api/packs", response_model=ProductManifest)
async def create_pack(body: PackPipelineInput) -> ProductManifest:
    run_dir = GENERATED_ROOT / str(uuid.uuid4())
    public_base = f"/generated-packs/{run_dir.name}"
    manifest, _artifacts = package_prompt_pack(
        body,
        output_dir=run_dir,
        public_base_path=public_base,
    )
    logger.info(
        json.dumps(
            {
                "event": "api_packs_created",
                "run_id": run_dir.name,
                "slug": manifest.slug,
                "duration_ms": manifest.instrumentation.duration_ms,
            }
        )
    )
    return manifest


@app.get("/api/packs/sample")
async def sample_manifest() -> JSONResponse:
    path = ROOT / "sample-packs" / SAMPLE_SLUG / "manifest.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Sample pack not found")
    return JSONResponse(content=json.loads(path.read_text(encoding="utf-8")))


MCP_TOOL_SCHEMA = {
    "name": "package_prompt_pack",
    "description": (
        "Given a niche and architected prompt pack JSON, produce PDF, cover SVG, "
        "marketplace listing copy, and a product manifest with download paths."
    ),
    "inputSchema": {
        "type": "object",
        "required": ["niche", "pack_title", "prompts"],
        "properties": {
            "niche": {"type": "string"},
            "pack_title": {"type": "string"},
            "pack_subtitle": {"type": "string"},
            "brand_name": {"type": "string"},
            "polish_listing_with_llm": {"type": "boolean"},
            "prompts": {"type": "array"},
        },
    },
}


@app.get("/api/mcp/tools")
async def mcp_list_tools() -> JSONResponse:
    return JSONResponse({"tools": [MCP_TOOL_SCHEMA]})


@app.post("/api/mcp/tools/package_prompt_pack")
async def mcp_call_package_prompt_pack(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    try:
        pack = PackPipelineInput.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    with tempfile.TemporaryDirectory(prefix="mcp-pack-") as tmp:
        out = Path(tmp)
        manifest, _ = package_prompt_pack(
            pack,
            output_dir=out,
            public_base_path="/api/mcp/runs/latest",
        )
        embedded = manifest.model_dump(mode="json")
        embedded["inline_artifacts"] = {
            "cover_svg": (out / "cover.svg").read_text(encoding="utf-8"),
            "listing_copy": json.loads(
                (out / "listing-copy.json").read_text(encoding="utf-8")
            ),
            "pdf_bytes_length": (out / "pack.pdf").stat().st_size,
        }
        return JSONResponse({"result": embedded})


@app.post("/api/mcp")
async def mcp_jsonrpc(request: Request) -> JSONResponse:
    """Minimal JSON-RPC 2.0 shim for MCP-style clients (tools/list, tools/call)."""
    try:
        message = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    rpc_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    def rpc_result(result: object) -> JSONResponse:
        return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": result})

    def rpc_error(code: int, msg: str) -> JSONResponse:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": msg}}
        )

    if method == "tools/list":
        return rpc_result({"tools": [MCP_TOOL_SCHEMA]})

    if method == "tools/call":
        name = params.get("name")
        if name != "package_prompt_pack":
            return rpc_error(-32601, f"Unknown tool: {name}")
        arguments = params.get("arguments") or {}
        try:
            pack = PackPipelineInput.model_validate(arguments)
        except ValidationError as exc:
            return rpc_error(-32602, str(exc.errors()))
        manifest, _ = package_prompt_pack(pack)
        return rpc_result(
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(manifest.model_dump(mode="json"), indent=2),
                    }
                ],
                "structuredContent": manifest.model_dump(mode="json"),
            }
        )

    return rpc_error(-32601, f"Method not found: {method}")


@app.get("/generated-packs/{run_id}/{filename}")
async def serve_generated(run_id: str, filename: str) -> FileResponse:
    allowed = {"pack.pdf", "cover.svg", "listing-copy.json", "manifest.json"}
    if filename not in allowed:
        raise HTTPException(status_code=404, detail="Not found")
    path = GENERATED_ROOT / run_id / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    media = "application/pdf" if filename.endswith(".pdf") else None
    return FileResponse(path, media_type=media)
