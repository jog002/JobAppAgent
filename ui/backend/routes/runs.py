"""Search run related API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import database as db

router = APIRouter()


@router.get("")
async def list_runs():
    """Get all search runs with statistics."""
    runs = db.get_run_statistics()
    return {"runs": runs}


@router.get("/latest")
async def get_latest_run():
    """Get the most recent search run."""
    run = db.get_latest_run()
    if not run:
        raise HTTPException(status_code=404, detail="No runs found")
    return run


@router.get("/{run_id}")
async def get_run(run_id: int):
    """Get a specific run by ID."""
    run = db.get_run_info(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/jobs")
async def get_run_jobs(
    run_id: int,
    limit: int = Query(100, le=500, description="Max jobs to return")
):
    """Get jobs discovered in a specific run."""
    jobs = db.get_jobs_by_run(run_id=run_id)
    return {
        "run_id": run_id,
        "jobs": jobs[:limit],
        "total": len(jobs)
    }
