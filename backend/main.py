"""FastAPI application entry point for ATS Domain Review."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from config import app_settings
from database import init_database, close_database
from routers import domains, reports, auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle handler."""
    await init_database()
    yield
    await close_database()


app = FastAPI(
    title="ATS Domain Review",
    description="Domain health and security assessment API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(domains.router)
app.include_router(reports.router)
app.include_router(auth_router.router)


@app.get("/api/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ats-domain-review"}


# Static files for uploaded logos
static_dir = Path(app_settings.static_dir)
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Serve frontend — use a catch-all route instead of mount("/") so that
# API routes always take priority over the SPA fallback.
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="frontend-assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_frontend(request: Request, path: str):
        """Serve frontend static files, falling back to index.html for SPA routing."""
        file = _frontend_dist / path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )
