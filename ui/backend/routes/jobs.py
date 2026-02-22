"""Job-related API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import database as db

router = APIRouter()


class StatusUpdate(BaseModel):
    status: str


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    url: str
    description: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    score: Optional[int] = None
    score_reasoning: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    posted_date: Optional[str] = None
    found_date: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("")
async def list_jobs(
    exclude_deleted: bool = Query(True, description="Exclude deleted jobs"),
    min_score: Optional[int] = Query(None, description="Minimum score filter"),
    max_score: Optional[int] = Query(None, description="Maximum score filter"),
    status: Optional[str] = Query(None, description="Filter by status"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(100, le=500, description="Max jobs to return"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """Get all jobs with optional filters."""
    jobs = db.get_all_jobs(
        exclude_deleted=exclude_deleted,
        min_score=min_score,
        max_score=max_score,
        status=status,
        source=source,
        limit=limit,
        offset=offset
    )
    total = db.get_jobs_count(
        exclude_deleted=exclude_deleted,
        min_score=min_score,
        status=status,
        source=source
    )
    return {
        "jobs": jobs,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/suggested")
async def get_suggested_jobs(
    min_score: int = Query(80, description="Minimum score for high-rated jobs"),
    run_id: Optional[int] = Query(None, description="Specific run ID (defaults to latest)")
):
    """Get suggested jobs for the dashboard."""
    result = db.get_suggested_jobs(min_score=min_score, run_id=run_id)
    return result


@router.get("/stats")
async def get_job_stats():
    """Get job statistics."""
    score_dist = db.get_score_distribution()
    source_stats = db.get_source_statistics()
    total = db.get_jobs_count(exclude_deleted=True)
    new_count = db.get_jobs_count(exclude_deleted=True, status='new')

    return {
        "total_jobs": total,
        "new_jobs": new_count,
        "score_distribution": score_dist,
        "source_statistics": source_stats
    }


@router.get("/{job_id}")
async def get_job(job_id: int):
    """Get a single job by ID."""
    job = db.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}/status")
async def update_job_status(job_id: int, update: StatusUpdate):
    """Update a job's status."""
    try:
        success = db.update_job_status(job_id, update.status)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"success": True, "job_id": job_id, "status": update.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
