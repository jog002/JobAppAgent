"""Log viewing API endpoints."""

from fastapi import APIRouter, Query
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config import LOGS_DIR, LOG_FILE

router = APIRouter()


@router.get("/latest")
async def get_latest_logs(
    lines: int = Query(500, le=5000, description="Number of lines to return"),
    level: str = Query(None, description="Filter by log level (INFO, WARNING, ERROR)")
):
    """Get the latest log entries from the log file."""
    log_path = Path(LOG_FILE) if LOG_FILE else LOGS_DIR / "job_agent.log"

    if not log_path.exists():
        return {
            "logs": [],
            "total_lines": 0,
            "file": str(log_path),
            "error": "Log file not found"
        }

    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()

        # Filter by level if specified
        if level:
            level_upper = level.upper()
            filtered_lines = [
                line for line in all_lines
                if f" - {level_upper} - " in line
            ]
        else:
            filtered_lines = all_lines

        # Get last N lines
        recent_lines = filtered_lines[-lines:] if len(filtered_lines) > lines else filtered_lines

        # Parse each line into structured format
        parsed_logs = []
        for line in recent_lines:
            line = line.strip()
            if not line:
                continue

            # Try to parse: "2024-02-17 10:23:45,123 - module - LEVEL - message"
            parts = line.split(' - ', 3)
            if len(parts) >= 4:
                parsed_logs.append({
                    "timestamp": parts[0],
                    "module": parts[1],
                    "level": parts[2],
                    "message": parts[3],
                    "raw": line
                })
            else:
                parsed_logs.append({
                    "timestamp": "",
                    "module": "",
                    "level": "INFO",
                    "message": line,
                    "raw": line
                })

        return {
            "logs": parsed_logs,
            "total_lines": len(all_lines),
            "returned_lines": len(parsed_logs),
            "file": str(log_path)
        }

    except Exception as e:
        return {
            "logs": [],
            "total_lines": 0,
            "file": str(log_path),
            "error": str(e)
        }


@router.get("/files")
async def list_log_files():
    """List available log files."""
    log_files = []

    if LOGS_DIR.exists():
        for f in LOGS_DIR.glob("*.log"):
            stat = f.stat()
            log_files.append({
                "name": f.name,
                "path": str(f),
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime
            })

    # Sort by modification time, newest first
    log_files.sort(key=lambda x: x['modified'], reverse=True)

    return {"files": log_files}
