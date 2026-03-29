"""Database operations for LinkedIn Job Agent."""

import sqlite3
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from contextlib import contextmanager

from config import DATABASE_PATH, DATABASE_MODE, TURSO_DATABASE_URL, TURSO_AUTH_TOKEN

# Initialize connection type based on DATABASE_MODE config
_use_turso = DATABASE_MODE == "turso"
_libsql = None

if _use_turso:
    try:
        import libsql_experimental as libsql
        _libsql = libsql
    except ImportError:
        logging.warning("libsql_experimental not installed, falling back to local SQLite")
        _use_turso = False

logger = logging.getLogger(__name__)

# Hard filters - jobs not matching these criteria are rejected and not stored
ALLOWED_LOCATIONS = [
    # NYC and surrounding
    "new york",
    "nyc",
    "ny, ny",
    "manhattan",
    "brooklyn",
    "queens",
    "bronx",
    "staten island",
    "jersey city",
    # Ohio
    "columbus, oh",
    "columbus, ohio",
    "columbus oh",
    # Montana
    "bozeman",
    "montana",
    # Remote
    "remote",
]

# Experience levels that are too senior
SENIOR_LEVEL_KEYWORDS = [
    "senior",
    "sr.",
    "sr ",
    "staff",
    "principal",
    "lead engineer",
    "lead software",
    "architect",
    "distinguished",
    "director",
    "manager",
    "head of",
    "vp ",
    "vice president",
]


def is_allowed_location(location: str) -> bool:
    """
    Check if a job location is in the allowed list.

    Args:
        location: Job location string

    Returns:
        True if location is allowed or unknown, False otherwise
    """
    # Allow jobs with unknown/empty locations through
    # (can't determine location, so give them benefit of doubt)
    if not location or location.lower() == 'unknown':
        return True

    location_lower = location.lower()

    for allowed in ALLOWED_LOCATIONS:
        if allowed in location_lower:
            return True

    return False


def is_senior_level(title: str) -> bool:
    """
    Check if a job title indicates senior+ level experience requirement.

    Args:
        title: Job title string

    Returns:
        True if job requires senior+ level, False otherwise
    """
    if not title:
        return False

    title_lower = title.lower()

    for keyword in SENIOR_LEVEL_KEYWORDS:
        if keyword in title_lower:
            return True

    return False


def passes_hard_filters(job_data: dict) -> tuple[bool, str]:
    """
    Check if a job passes all hard filters.

    Args:
        job_data: Dictionary containing job information

    Returns:
        Tuple of (passes, reason) - passes is True if job should be stored,
        reason explains why it was rejected if passes is False
    """
    location = job_data.get('location', '')
    title = job_data.get('title', '')

    # Check location filter
    if not is_allowed_location(location):
        return False, f"Location '{location}' not in allowed list"

    # Check experience level filter
    if is_senior_level(title):
        return False, f"Title '{title}' indicates senior+ level"

    return True, ""


def cleanup_old_jobs(days: int = 30) -> int:
    """
    Delete jobs older than the specified number of days.

    Args:
        days: Number of days after which jobs are considered old (default 30)

    Returns:
        Number of jobs deleted
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff_date.isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Count jobs to be deleted
        cursor.execute(
            "SELECT COUNT(*) FROM jobs WHERE created_at < ?",
            (cutoff_str,)
        )
        count = cursor.fetchone()[0]

        if count > 0:
            cursor.execute(
                "DELETE FROM jobs WHERE created_at < ?",
                (cutoff_str,)
            )
            logger.info(f"Deleted {count} jobs older than {days} days")
        else:
            logger.info(f"No jobs older than {days} days to delete")

        return count

# SQL Schema
SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    linkedin_job_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    location TEXT,
    remote_type TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT DEFAULT 'USD',
    posted_date TEXT,
    found_date TEXT NOT NULL,
    score INTEGER,
    score_reasoning TEXT,
    status TEXT DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_linkedin_id ON jobs(linkedin_job_id);

CREATE TABLE IF NOT EXISTS search_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    jobs_found INTEGER DEFAULT 0,
    jobs_new INTEGER DEFAULT 0,
    jobs_updated INTEGER DEFAULT 0,
    search_queries TEXT,
    status TEXT DEFAULT 'running',
    error_message TEXT,
    duration_seconds REAL
);

CREATE TABLE IF NOT EXISTS greenhouse_tokens (
    token TEXT PRIMARY KEY,
    company_name TEXT,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_polled TIMESTAMP,
    job_count INTEGER DEFAULT 0,
    source TEXT DEFAULT 'curated'
);

CREATE INDEX IF NOT EXISTS idx_greenhouse_tokens_source ON greenhouse_tokens(source);
"""

class TursoRowWrapper:
    """Wrapper to make libsql rows behave like sqlite3.Row."""

    def __init__(self, row, description):
        self._row = row
        self._keys = [col[0] for col in description] if description else []

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._row[key]
        if isinstance(key, str):
            try:
                idx = self._keys.index(key)
                return self._row[idx]
            except ValueError:
                raise KeyError(key)
        raise TypeError(f"Invalid key type: {type(key)}")

    def keys(self):
        return self._keys


class TursoCursorWrapper:
    """Wrapper to make libsql cursor return dict-compatible rows."""

    def __init__(self, cursor):
        self._cursor = cursor
        self._description = None

    def execute(self, sql, params=None):
        if params:
            result = self._cursor.execute(sql, params)
        else:
            result = self._cursor.execute(sql)
        self._description = self._cursor.description
        return result

    def executescript(self, sql):
        return self._cursor.executescript(sql)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return TursoRowWrapper(row, self._description)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [TursoRowWrapper(row, self._description) for row in rows]

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description


class TursoConnectionWrapper:
    """Wrapper to make libsql connection compatible with sqlite3 API."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return TursoCursorWrapper(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def executescript(self, sql):
        return self._conn.executescript(sql)


@contextmanager
def get_db_connection():
    """Context manager for database connections.

    Uses Turso (libsql) if DATABASE_MODE=turso, otherwise local SQLite.
    Returns a connection with consistent API regardless of backend.
    """
    if _use_turso and _libsql:
        raw_conn = _libsql.connect(TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
        conn = TursoConnectionWrapper(raw_conn)
        logger.debug("Connected to Turso cloud database")
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        logger.debug(f"Connected to local SQLite: {DATABASE_PATH}")

    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database with schema."""
    if _use_turso:
        logger.info("Initializing Turso cloud database")
    else:
        logger.info(f"Initializing database at {DATABASE_PATH}")
    with get_db_connection() as conn:
        conn.executescript(SCHEMA)
    logger.info("Database initialized successfully")
    # Run migration to add multi-source support
    migrate_database()


def migrate_database():
    """
    Migrate existing database to support multi-source jobs.
    Safe to run multiple times (idempotent).
    """
    logger.info("Checking database migration status")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if source column exists
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'source' not in columns:
            logger.info("Adding source column")
            cursor.execute("ALTER TABLE jobs ADD COLUMN source TEXT DEFAULT 'linkedin'")

        if 'job_id' not in columns:
            logger.info("Adding job_id column")
            cursor.execute("ALTER TABLE jobs ADD COLUMN job_id TEXT")
            # Copy data from linkedin_job_id to job_id
            cursor.execute("UPDATE jobs SET job_id = linkedin_job_id WHERE job_id IS NULL")

        # Add first_seen_run_id column for tracking which run first discovered each job
        if 'first_seen_run_id' not in columns:
            logger.info("Adding first_seen_run_id column")
            cursor.execute("ALTER TABLE jobs ADD COLUMN first_seen_run_id INTEGER")

        # Update indices
        cursor.execute("DROP INDEX IF EXISTS idx_jobs_source_id")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_source_id ON jobs(source, job_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_first_seen_run ON jobs(first_seen_run_id)")

        # Add source column to search_runs if it doesn't exist
        cursor.execute("PRAGMA table_info(search_runs)")
        search_run_columns = [row[1] for row in cursor.fetchall()]

        if 'source' not in search_run_columns:
            logger.info("Adding source column to search_runs")
            cursor.execute("ALTER TABLE search_runs ADD COLUMN source TEXT DEFAULT 'all'")

        # Add run_number column to search_runs for sequential numbering
        if 'run_number' not in search_run_columns:
            logger.info("Adding run_number column to search_runs")
            cursor.execute("ALTER TABLE search_runs ADD COLUMN run_number INTEGER")
            # Backfill run_numbers based on existing IDs
            cursor.execute("""
                UPDATE search_runs
                SET run_number = (
                    SELECT COUNT(*)
                    FROM search_runs s2
                    WHERE s2.id <= search_runs.id
                )
            """)

    logger.info("Database migration completed")


def insert_job(job_data: dict, run_id: int = None) -> Optional[int]:
    """
    Insert a new job or update if exists.

    Jobs are filtered before insertion - jobs with disallowed locations
    or senior+ level requirements are rejected and not stored.

    Args:
        job_data: Dictionary containing job information
        run_id: The search run ID that discovered this job (for tracking first_seen_run_id)

    Returns:
        Job ID (primary key) if inserted, None if filtered out
    """
    # Apply hard filters before inserting
    passes, reason = passes_hard_filters(job_data)
    if not passes:
        logger.info(f"Filtered out job: {job_data.get('title')} at {job_data.get('company')} - {reason}")
        return None

    with get_db_connection() as conn:
        cursor = conn.cursor()

        source = job_data.get('source', 'linkedin')
        job_id = job_data.get('job_id') or job_data.get('linkedin_job_id')

        # Check if job already exists (by source + job_id)
        cursor.execute(
            "SELECT id FROM jobs WHERE source = ? AND job_id = ?",
            (source, job_id)
        )
        existing = cursor.fetchone()

        if existing:
            logger.info(f"Job {source}/{job_id} already exists")
            return existing[0]

        # Insert new job
        cursor.execute("""
            INSERT INTO jobs (
                source, job_id, linkedin_job_id, title, company, url, description,
                location, remote_type, salary_min, salary_max,
                posted_date, found_date, first_seen_run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source,
            job_id,
            job_data.get('linkedin_job_id') or job_id,  # Keep for backward compatibility
            job_data.get('title'),
            job_data.get('company'),
            job_data.get('url'),
            job_data.get('description'),
            job_data.get('location'),
            job_data.get('remote_type', 'Unknown'),
            job_data.get('salary_min'),
            job_data.get('salary_max'),
            job_data.get('posted_date'),
            datetime.now().isoformat(),
            run_id
        ))

        db_job_id = cursor.lastrowid
        logger.info(f"Inserted new job: {job_data.get('title')} at {job_data.get('company')} (source: {source}, run={run_id})")
        return db_job_id


def update_job_score(source: str, job_id: str, score: int, reasoning: str) -> None:
    """Update the score and reasoning for a job."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs
            SET score = ?, score_reasoning = ?, updated_at = ?
            WHERE source = ? AND job_id = ?
        """, (score, reasoning, datetime.now().isoformat(), source, job_id))
        logger.info(f"Updated score for job {source}/{job_id}: {score}")


def update_job_score_legacy(linkedin_job_id: str, score: int, reasoning: str) -> None:
    """Legacy function for backward compatibility."""
    update_job_score('linkedin', linkedin_job_id, score, reasoning)


def get_job_by_linkedin_id(linkedin_job_id: str) -> Optional[dict]:
    """Retrieve a job by its LinkedIn ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE linkedin_job_id = ?", (linkedin_job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_top_jobs(limit: int = 20, min_score: int = 60) -> list[dict]:
    """Get top-scoring jobs above minimum threshold."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs
            WHERE score >= ?
            ORDER BY score DESC, created_at DESC
            LIMIT ?
        """, (min_score, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_jobs_by_status(status: str, limit: int = 100) -> list[dict]:
    """Get jobs filtered by status."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs
            WHERE status = ?
            ORDER BY score DESC, created_at DESC
            LIMIT ?
        """, (status, limit))
        return [dict(row) for row in cursor.fetchall()]


def create_search_run(search_queries: list) -> int:
    """Create a new search run record with sequential run number."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get the next run number
        cursor.execute("SELECT COALESCE(MAX(run_number), 0) + 1 FROM search_runs")
        next_run_number = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO search_runs (search_queries, run_number)
            VALUES (?, ?)
        """, (json.dumps(search_queries), next_run_number))
        run_id = cursor.lastrowid
        logger.info(f"Created search run #{next_run_number} (id={run_id})")
        return run_id


def get_current_run_number() -> int:
    """Get the current (most recent) run number."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(run_number), 0) FROM search_runs")
        return cursor.fetchone()[0]


def get_run_info(run_id: int) -> Optional[dict]:
    """Get information about a specific search run."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM search_runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def complete_search_run(run_id: int, stats: dict, error: Optional[str] = None) -> None:
    """Mark search run as complete with statistics."""
    status = 'failed' if error else 'completed'
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE search_runs
            SET status = ?,
                jobs_found = ?,
                jobs_new = ?,
                jobs_updated = ?,
                error_message = ?,
                duration_seconds = ?
            WHERE id = ?
        """, (
            status,
            stats.get('jobs_found', 0),
            stats.get('jobs_new', 0),
            stats.get('jobs_updated', 0),
            error,
            stats.get('duration_seconds', 0),
            run_id
        ))
        logger.info(f"Completed search run {run_id}: {status}")


def get_score_distribution() -> dict:
    """Get distribution of job scores for reporting."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(CASE WHEN score >= 90 THEN 1 END) as excellent,
                COUNT(CASE WHEN score >= 75 AND score < 90 THEN 1 END) as strong,
                COUNT(CASE WHEN score >= 60 AND score < 75 THEN 1 END) as good,
                COUNT(CASE WHEN score >= 45 AND score < 60 THEN 1 END) as moderate,
                COUNT(CASE WHEN score < 45 THEN 1 END) as poor
            FROM jobs
            WHERE score IS NOT NULL
        """)
        row = cursor.fetchone()
        return dict(row) if row else {}


def get_job_by_source_and_id(source: str, job_id: str) -> Optional[dict]:
    """Retrieve a job by its source and job_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM jobs WHERE source = ? AND job_id = ?",
            (source, job_id)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_jobs_by_source(source: str, limit: int = 100) -> list[dict]:
    """Get jobs from a specific source."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs
            WHERE source = ?
            ORDER BY score DESC, created_at DESC
            LIMIT ?
        """, (source, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_source_statistics() -> dict:
    """Get statistics by source."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                source,
                COUNT(*) as total,
                COUNT(CASE WHEN score >= 75 THEN 1 END) as strong_matches,
                AVG(score) as avg_score
            FROM jobs
            WHERE score IS NOT NULL
            GROUP BY source
        """)
        return {row['source']: dict(row) for row in cursor.fetchall()}


def get_jobs_for_reranking(min_score: int = 0, limit: int = 100) -> list[dict]:
    """
    Get jobs for reranking/rescoring.

    Args:
        min_score: Only return jobs with score >= this value (0 = all)
        limit: Maximum number of jobs to return

    Returns:
        List of job dictionaries
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if min_score > 0:
            cursor.execute("""
                SELECT * FROM jobs
                WHERE score IS NOT NULL AND score >= ?
                ORDER BY score DESC, created_at DESC
                LIMIT ?
            """, (min_score, limit))
        else:
            cursor.execute("""
                SELECT * FROM jobs
                ORDER BY score DESC NULLS LAST, created_at DESC
                LIMIT ?
            """, (limit,))

        return [dict(row) for row in cursor.fetchall()]


def get_all_jobs_with_descriptions(limit: int = 500) -> list[dict]:
    """
    Get all jobs that have descriptions for rescoring.

    Args:
        limit: Maximum number of jobs to return

    Returns:
        List of job dictionaries
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs
            WHERE description IS NOT NULL AND description != ''
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_jobs_by_run(run_id: int = None, run_number: int = None) -> list[dict]:
    """
    Get jobs discovered in a specific search run.

    Args:
        run_id: The database ID of the search run
        run_number: The sequential run number (alternative to run_id)

    Returns:
        List of job dictionaries
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if run_number is not None:
            # Get run_id from run_number
            cursor.execute(
                "SELECT id FROM search_runs WHERE run_number = ?",
                (run_number,)
            )
            row = cursor.fetchone()
            if not row:
                return []
            run_id = row[0]

        cursor.execute("""
            SELECT j.*, sr.run_number
            FROM jobs j
            LEFT JOIN search_runs sr ON j.first_seen_run_id = sr.id
            WHERE j.first_seen_run_id = ?
            ORDER BY j.score DESC NULLS LAST, j.created_at DESC
        """, (run_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_jobs_from_run(run_id: int, limit: int = 10) -> list[dict]:
    """
    Get jobs discovered in a specific run, sorted by score (for email reports).

    Args:
        run_id: The database ID of the search run
        limit: Maximum number of jobs to return (default 10)

    Returns:
        List of job dictionaries sorted by score descending
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs
            WHERE first_seen_run_id = ? AND score IS NOT NULL
            ORDER BY score DESC
            LIMIT ?
        """, (run_id, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_run_statistics() -> list[dict]:
    """
    Get statistics for all search runs.

    Returns:
        List of run statistics dictionaries
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                sr.id,
                sr.run_number,
                sr.run_date,
                sr.jobs_found,
                sr.jobs_new,
                sr.status,
                sr.duration_seconds,
                COUNT(j.id) as jobs_in_db,
                AVG(j.score) as avg_score,
                COUNT(CASE WHEN j.score >= 75 THEN 1 END) as strong_matches
            FROM search_runs sr
            LEFT JOIN jobs j ON j.first_seen_run_id = sr.id
            GROUP BY sr.id
            ORDER BY sr.run_number DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


# Valid job status values
JOB_STATUSES = ['new', 'reviewed', 'applied', 'not_interested', 'deleted']


def update_job_status(job_id: int, status: str) -> bool:
    """
    Update the status of a job by its database ID.

    Args:
        job_id: The database primary key ID of the job
        status: New status value (new, reviewed, applied, not_interested, deleted)

    Returns:
        True if job was updated, False if job not found
    """
    if status not in JOB_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {JOB_STATUSES}")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs
            SET status = ?, updated_at = ?
            WHERE id = ?
        """, (status, datetime.now().isoformat(), job_id))
        updated = cursor.rowcount > 0
        if updated:
            logger.info(f"Updated job {job_id} status to '{status}'")
        return updated


def get_job_by_id(job_id: int) -> Optional[dict]:
    """
    Get a single job by its database ID.

    Args:
        job_id: The database primary key ID

    Returns:
        Job dictionary or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_jobs(
    exclude_deleted: bool = True,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    status: Optional[list[str]] = None,
    source: Optional[list[str]] = None,
    location: Optional[list[str]] = None,
    remote_type: Optional[list[str]] = None,
    sort_by: Optional[str] = None,
    sort_desc: bool = True,
    limit: int = 500,
    offset: int = 0
) -> list[dict]:
    """
    Get all jobs with optional filters.

    Args:
        exclude_deleted: If True, exclude jobs with status='deleted'
        min_score: Only include jobs with score >= this value
        max_score: Only include jobs with score <= this value
        status: Filter by status(es) - list for multi-select
        source: Filter by source(s) - list for multi-select
        location: Filter by location(s) - list for multi-select
        remote_type: Filter by remote type(s) - list for multi-select
        sort_by: Column to sort by (whitelist validated)
        sort_desc: Sort descending if True, ascending if False
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip (for pagination)

    Returns:
        List of job dictionaries
    """
    # Whitelist of allowed sort columns
    allowed_sort_columns = {'score', 'title', 'company', 'found_date', 'created_at', 'status', 'location', 'source', 'remote_type'}

    with get_db_connection() as conn:
        cursor = conn.cursor()

        conditions = []
        params = []

        if exclude_deleted:
            conditions.append("(status != 'deleted' OR status IS NULL)")

        if min_score is not None:
            conditions.append("score >= ?")
            params.append(min_score)

        if max_score is not None:
            conditions.append("score <= ?")
            params.append(max_score)

        if status:
            placeholders = ",".join("?" * len(status))
            conditions.append(f"status IN ({placeholders})")
            params.extend(status)

        if source:
            placeholders = ",".join("?" * len(source))
            conditions.append(f"source IN ({placeholders})")
            params.extend(source)

        if location:
            placeholders = ",".join("?" * len(location))
            conditions.append(f"location IN ({placeholders})")
            params.extend(location)

        if remote_type:
            placeholders = ",".join("?" * len(remote_type))
            conditions.append(f"remote_type IN ({placeholders})")
            params.extend(remote_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Build ORDER BY clause with whitelist validation
        if sort_by and sort_by in allowed_sort_columns:
            direction = "DESC" if sort_desc else "ASC"
            order_clause = f"ORDER BY {sort_by} {direction} NULLS LAST"
        else:
            order_clause = "ORDER BY score DESC NULLS LAST, created_at DESC"

        query = f"""
            SELECT * FROM jobs
            WHERE {where_clause}
            {order_clause}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_jobs_count(
    exclude_deleted: bool = True,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    status: Optional[list[str]] = None,
    source: Optional[list[str]] = None,
    location: Optional[list[str]] = None,
    remote_type: Optional[list[str]] = None
) -> int:
    """
    Get total count of jobs matching filters (for pagination).

    Args:
        exclude_deleted: If True, exclude jobs with status='deleted'
        min_score: Only count jobs with score >= this value
        max_score: Only count jobs with score <= this value
        status: Filter by status(es) - list for multi-select
        source: Filter by source(s) - list for multi-select
        location: Filter by location(s) - list for multi-select
        remote_type: Filter by remote type(s) - list for multi-select

    Returns:
        Total count of matching jobs
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        conditions = []
        params = []

        if exclude_deleted:
            conditions.append("(status != 'deleted' OR status IS NULL)")

        if min_score is not None:
            conditions.append("score >= ?")
            params.append(min_score)

        if max_score is not None:
            conditions.append("score <= ?")
            params.append(max_score)

        if status:
            placeholders = ",".join("?" * len(status))
            conditions.append(f"status IN ({placeholders})")
            params.extend(status)

        if source:
            placeholders = ",".join("?" * len(source))
            conditions.append(f"source IN ({placeholders})")
            params.extend(source)

        if location:
            placeholders = ",".join("?" * len(location))
            conditions.append(f"location IN ({placeholders})")
            params.extend(location)

        if remote_type:
            placeholders = ",".join("?" * len(remote_type))
            conditions.append(f"remote_type IN ({placeholders})")
            params.extend(remote_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        cursor.execute(f"SELECT COUNT(*) FROM jobs WHERE {where_clause}", params)
        return cursor.fetchone()[0]


def get_suggested_jobs(min_score: int = 80, run_id: Optional[int] = None) -> dict:
    """
    Get suggested jobs for the UI dashboard.

    Returns two lists:
    1. High-rated jobs from the latest run (or specified run)
    2. Top 20 jobs with status='new'

    Args:
        min_score: Minimum score for "high rated" jobs
        run_id: Specific run ID, or None for latest run

    Returns:
        Dictionary with 'high_rated' and 'top_new' lists
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get latest run_id if not specified
        if run_id is None:
            cursor.execute("SELECT id FROM search_runs ORDER BY run_number DESC LIMIT 1")
            row = cursor.fetchone()
            run_id = row[0] if row else None

        # High-rated jobs from latest run
        high_rated = []
        if run_id:
            cursor.execute("""
                SELECT * FROM jobs
                WHERE first_seen_run_id = ?
                  AND score >= ?
                  AND (status != 'deleted' OR status IS NULL)
                ORDER BY score DESC
            """, (run_id, min_score))
            high_rated = [dict(row) for row in cursor.fetchall()]

        # Top 20 new jobs (status = 'new')
        cursor.execute("""
            SELECT * FROM jobs
            WHERE status = 'new'
              AND score IS NOT NULL
            ORDER BY score DESC
            LIMIT 20
        """)
        top_new = [dict(row) for row in cursor.fetchall()]

        return {
            'high_rated': high_rated,
            'top_new': top_new,
            'run_id': run_id
        }


def get_latest_run() -> Optional[dict]:
    """
    Get the most recent search run info.

    Returns:
        Run dictionary or None if no runs exist
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM search_runs
            ORDER BY run_number DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None


# Greenhouse token management functions

def get_greenhouse_tokens(source: Optional[str] = None) -> list[dict]:
    """
    Get all stored Greenhouse company tokens.

    Args:
        source: Filter by source ('curated' or 'discovered'), or None for all

    Returns:
        List of token dictionaries
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if source:
            cursor.execute(
                "SELECT * FROM greenhouse_tokens WHERE source = ? ORDER BY token",
                (source,)
            )
        else:
            cursor.execute("SELECT * FROM greenhouse_tokens ORDER BY token")
        return [dict(row) for row in cursor.fetchall()]


def add_greenhouse_token(
    token: str,
    company_name: Optional[str] = None,
    source: str = "discovered"
) -> bool:
    """
    Add a new Greenhouse company token.

    Args:
        token: The company board token (e.g., 'anthropic')
        company_name: Human-readable company name
        source: How it was found ('curated' or 'discovered')

    Returns:
        True if token was added, False if already exists
    """
    token = token.lower().strip()
    if not token:
        return False

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO greenhouse_tokens (token, company_name, source)
                VALUES (?, ?, ?)
            """, (token, company_name, source))
            logger.info(f"Added Greenhouse token: {token} (source: {source})")
            return True
        except Exception:
            # Token already exists
            return False


def update_greenhouse_token_stats(token: str, job_count: int) -> None:
    """
    Update statistics for a Greenhouse token after polling.

    Args:
        token: The company board token
        job_count: Number of jobs found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE greenhouse_tokens
            SET last_polled = ?, job_count = ?
            WHERE token = ?
        """, (datetime.now().isoformat(), job_count, token.lower()))


def get_greenhouse_token_stats() -> dict:
    """
    Get statistics about stored Greenhouse tokens.

    Returns:
        Dictionary with token statistics
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total_tokens,
                COUNT(CASE WHEN source = 'curated' THEN 1 END) as curated,
                COUNT(CASE WHEN source = 'discovered' THEN 1 END) as discovered,
                SUM(job_count) as total_jobs,
                COUNT(CASE WHEN last_polled IS NOT NULL THEN 1 END) as polled_tokens
            FROM greenhouse_tokens
        """)
        row = cursor.fetchone()
        return dict(row) if row else {}
