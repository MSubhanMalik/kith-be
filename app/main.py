from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routes import all_routers
from app.middleware.error_handler import error_handler


app = FastAPI(title="Kith API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_origin_regex=r"(file|app|tauri|https?://localhost)://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(error_handler)

for router in all_routers:
    app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup():
    await init_db()
    from app.agent.registry import discover_tools
    discover_tools()


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/agent/tools")
async def list_agent_tools():
    from app.agent import get_tool_schemas
    return {"tools": get_tool_schemas()}


@app.get("/api/exports/download/{filename}")
async def download_export(filename: str):
    import os
    import tempfile
    from fastapi.responses import FileResponse
    path = os.path.join(tempfile.gettempdir(), "kith_exports", filename)
    if not os.path.exists(path):
        return {"error": "File not found"}
    return FileResponse(path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
