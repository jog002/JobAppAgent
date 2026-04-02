"""Configuration API endpoints for database settings."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

router = APIRouter()


class ConfigResponse(BaseModel):
    database_mode: str
    turso_url: Optional[str] = None
    turso_token: Optional[str] = None  # Will be masked


class ConfigUpdate(BaseModel):
    database_mode: str
    turso_url: Optional[str] = None
    turso_token: Optional[str] = None


class ConnectionTestRequest(BaseModel):
    mode: str
    turso_url: Optional[str] = None
    turso_token: Optional[str] = None


class ConnectionTestResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    job_count: Optional[int] = None


def get_env_file_path() -> Path:
    """Get the path to the .env file."""
    project_root = Path(__file__).parent.parent.parent.parent
    return project_root / ".env"


def read_env_value(key: str) -> Optional[str]:
    """Read a value from the .env file."""
    env_file = get_env_file_path()
    if not env_file.exists():
        return None

    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key}="):
                value = line[len(key) + 1:]
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                return value
    return None


def update_env_file(updates: dict):
    """Update values in the .env file."""
    env_file = get_env_file_path()
    lines = []

    # Read existing content
    if env_file.exists():
        with open(env_file, "r") as f:
            lines = f.readlines()

    # Track which keys have been updated
    updated_keys = set()

    # Update existing lines
    new_lines = []
    for line in lines:
        stripped = line.strip()
        updated = False
        for key, value in updates.items():
            if stripped.startswith(f"{key}=") or stripped.startswith(f"# {key}="):
                if value is not None:
                    new_lines.append(f"{key}={value}\n")
                    updated_keys.add(key)
                updated = True
                break
        if not updated:
            new_lines.append(line)

    # Add new keys that weren't found
    for key, value in updates.items():
        if key not in updated_keys and value is not None:
            new_lines.append(f"{key}={value}\n")

    # Write back
    with open(env_file, "w") as f:
        f.writelines(new_lines)


@router.get("")
async def get_config() -> ConfigResponse:
    """Get current database configuration."""
    database_mode = read_env_value("DATABASE_MODE") or os.getenv("DATABASE_MODE", "local")
    turso_url = read_env_value("TURSO_DATABASE_URL") or os.getenv("TURSO_DATABASE_URL")
    turso_token = read_env_value("TURSO_AUTH_TOKEN") or os.getenv("TURSO_AUTH_TOKEN")

    return ConfigResponse(
        database_mode=database_mode,
        turso_url=turso_url,
        turso_token="********" if turso_token else None,
    )


@router.post("")
async def update_config(config: ConfigUpdate) -> ConfigResponse:
    """Update database configuration."""
    if config.database_mode not in ("local", "turso"):
        raise HTTPException(status_code=400, detail="Invalid database mode")

    if config.database_mode == "turso":
        if not config.turso_url:
            raise HTTPException(status_code=400, detail="Turso URL is required")
        # Only require token if it's not already set or being updated
        existing_token = read_env_value("TURSO_AUTH_TOKEN") or os.getenv("TURSO_AUTH_TOKEN")
        if not config.turso_token and not existing_token:
            raise HTTPException(status_code=400, detail="Turso auth token is required")

    # Prepare updates
    updates = {
        "DATABASE_MODE": config.database_mode,
    }

    if config.database_mode == "turso":
        updates["TURSO_DATABASE_URL"] = config.turso_url
        if config.turso_token:
            updates["TURSO_AUTH_TOKEN"] = config.turso_token

    # Update the .env file
    update_env_file(updates)

    # Update runtime environment variables
    os.environ["DATABASE_MODE"] = config.database_mode
    if config.turso_url:
        os.environ["TURSO_DATABASE_URL"] = config.turso_url
    if config.turso_token:
        os.environ["TURSO_AUTH_TOKEN"] = config.turso_token

    # Re-initialize database with new config
    try:
        import database as db
        import importlib
        import config as cfg

        # Reload config module to pick up new env vars
        importlib.reload(cfg)

        # Reinitialize database
        db.init_database()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reinitialize database: {str(e)}")

    return ConfigResponse(
        database_mode=config.database_mode,
        turso_url=config.turso_url,
        turso_token="********" if config.turso_token or read_env_value("TURSO_AUTH_TOKEN") else None,
    )


@router.post("/test")
async def test_connection(request: ConnectionTestRequest) -> ConnectionTestResponse:
    """Test database connection with provided credentials."""
    if request.mode == "local":
        # Test local SQLite connection
        try:
            import sqlite3
            from pathlib import Path

            project_root = Path(__file__).parent.parent.parent.parent
            db_path = project_root / "data" / "jobs.db"

            if not db_path.exists():
                return ConnectionTestResponse(success=True, job_count=0)

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM jobs")
            count = cursor.fetchone()[0]
            conn.close()

            return ConnectionTestResponse(success=True, job_count=count)
        except Exception as e:
            return ConnectionTestResponse(success=False, error=str(e))

    elif request.mode == "turso":
        # Test Turso connection
        if not request.turso_url:
            return ConnectionTestResponse(success=False, error="Turso URL is required")

        # Use existing token if not provided
        turso_token = request.turso_token
        if not turso_token:
            turso_token = read_env_value("TURSO_AUTH_TOKEN") or os.getenv("TURSO_AUTH_TOKEN")

        if not turso_token:
            return ConnectionTestResponse(success=False, error="Turso auth token is required")

        try:
            import libsql_experimental as libsql

            conn = libsql.connect(
                database=request.turso_url,
                auth_token=turso_token
            )
            cursor = conn.cursor()

            # Try to get job count, or 0 if table doesn't exist
            try:
                cursor.execute("SELECT COUNT(*) FROM jobs")
                count = cursor.fetchone()[0]
            except Exception:
                count = 0

            conn.close()

            return ConnectionTestResponse(success=True, job_count=count)
        except Exception as e:
            return ConnectionTestResponse(success=False, error=str(e))

    return ConnectionTestResponse(success=False, error="Invalid mode")
