"""FastAPI backend for Job Agent UI."""

import os
import sys
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent.parent
FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"

# Add project root and backend to path for importing
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

# Change to project root so relative paths work correctly
os.chdir(PROJECT_ROOT)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from routes import jobs_router, runs_router, logs_router

# Initialize database on startup
import database as db

app = FastAPI(
    title="Job Agent API",
    description="API for the Job Search Agent UI",
    version="1.0.0"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(jobs_router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(runs_router, prefix="/api/runs", tags=["Runs"])
app.include_router(logs_router, prefix="/api/logs", tags=["Logs"])


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    db.init_database()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def serve_root():
    """Serve the React app's index.html."""
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse(
        status_code=503,
        content={"detail": "Frontend not built. Run 'npm run build' in ui/frontend/"}
    )


# Mount static assets if they exist
if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")


# Catch-all for SPA routing (must be last)
@app.get("/{path:path}")
async def serve_spa(path: str):
    """Serve index.html for SPA routing."""
    # Don't catch API routes
    if path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    # Check if it's a static file
    static_path = FRONTEND_DIST / path
    if static_path.exists() and static_path.is_file():
        return FileResponse(static_path)

    # Fall back to index.html for SPA routing
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    return JSONResponse(
        status_code=503,
        content={"detail": "Frontend not built. Run 'npm run build' in ui/frontend/"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
