"""Configuration management for Multi-Source Job Agent."""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv


def load_env_file(env_file: str = ".env"):
    """
    Load environment variables from a specific .env file.

    Call this BEFORE importing config if you need to use a different env file.
    For batch jobs, call this at the start of the batch function before any
    other imports that depend on config values.

    Args:
        env_file: Path to the environment file to load (default: ".env")
    """
    load_dotenv(env_file, override=True)


# Load environment variables (default .env for backwards compatibility)
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
RESUME_DIR = PROJECT_ROOT / "resume"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
RESUME_DIR.mkdir(exist_ok=True)

# LinkedIn MCP Configuration (Optional - only if using LinkedIn source)
# Two authentication methods are supported:
# 1. Cookie-based: Set LINKEDIN_COOKIE (li_at cookie value)
# 2. Session file: Set LINKEDIN_SESSION_PATH (path to session.json from --get-session)
LINKEDIN_COOKIE = os.getenv("LINKEDIN_COOKIE")
LINKEDIN_SESSION_PATH = os.getenv("LINKEDIN_SESSION_PATH", str(Path.home() / ".linkedin-mcp" / "session.json"))

# Job Sources Configuration
ENABLED_SOURCES = [s.strip() for s in os.getenv("ENABLED_SOURCES", "web_scraping").split(",")]

# Web Scraping Configuration
WEB_SCRAPING_PLATFORMS = [p.strip() for p in os.getenv("WEB_SCRAPING_PLATFORMS", "greenhouse,lever,bamboohr,ashby").split(",")]

try:
    SCRAPING_DELAY_SECONDS = float(os.getenv("SCRAPING_DELAY_SECONDS", "2.0"))
    if SCRAPING_DELAY_SECONDS < 0:
        raise ValueError("SCRAPING_DELAY_SECONDS must be non-negative")
except ValueError as e:
    raise ValueError(f"Invalid SCRAPING_DELAY_SECONDS: {e}")

# Discovery Provider Configuration
# Available providers: greenhouse_api, lever_api, ashby_api, serpapi, jobspy, brave_search
# Direct API providers (greenhouse_api, lever_api, ashby_api) are free and most reliable
# serpapi uses 3 pages/day = ~90 credits/month (within 250 free limit)
ENABLED_DISCOVERY_PROVIDERS = [
    p.strip() for p in os.getenv(
        "ENABLED_DISCOVERY_PROVIDERS",
        "greenhouse_api,lever_api,ashby_api,serpapi,jobspy"
    ).split(",") if p.strip()
]

# Brave Search API Configuration
# Get your API key at: https://brave.com/search/api/
# Free tier: 2,000 queries/month
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

# SerpAPI Configuration (Google Search)
# Get your API key at: https://serpapi.com/
# Free tier: 250 searches/month
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# SerpAPI pages (pagination)
# Each page = 10 results = 1 API credit
# 3 pages = 30 results = 3 API credits per search (~90/month for daily runs)
try:
    SERPAPI_PAGES = int(os.getenv("SERPAPI_PAGES", "3"))
    if SERPAPI_PAGES < 1:
        raise ValueError("SERPAPI_PAGES must be positive")
    SERPAPI_PAGES = min(SERPAPI_PAGES, 10)  # Cap at 10 pages (100 results)
except ValueError as e:
    raise ValueError(f"Invalid SERPAPI_PAGES: {e}")

# SerpAPI recency filter
# Options: hour, day, week, month, year, or empty for all results
SERPAPI_RECENCY = os.getenv("SERPAPI_RECENCY", "") or None

# SerpAPI start page (for deeper searches on subsequent runs)
# Page 0 = results 1-10, Page 1 = results 11-20, etc.
SERPAPI_START_PAGE = int(os.getenv("SERPAPI_START_PAGE", "0"))

# SerpAPI target site (default: greenhouse.io)
SERPAPI_TARGET_SITE = os.getenv("SERPAPI_TARGET_SITE", "greenhouse.io")

# JobSpy Configuration
# Sites: indeed, google, linkedin, glassdoor, zip_recruiter
# Note: linkedin has aggressive rate limiting, indeed works best
JOBSPY_SITES = [
    s.strip() for s in os.getenv(
        "JOBSPY_SITES",
        "indeed,google"
    ).split(",") if s.strip()
]

try:
    JOBSPY_HOURS_OLD = int(os.getenv("JOBSPY_HOURS_OLD", "72"))
    if JOBSPY_HOURS_OLD < 1:
        raise ValueError("JOBSPY_HOURS_OLD must be positive")
except ValueError as e:
    raise ValueError(f"Invalid JOBSPY_HOURS_OLD: {e}")

# Location Terms Configuration (UNIFIED)
# These location terms are used across all search providers:
# - SerpAPI: builds OR group in query ("NY" OR "New York" OR "Remote")
# - JobSpy: passed as the location parameter for each search
# - Post-discovery filtering: filters out jobs not matching these locations
# Format: comma-separated list of location terms/aliases
_location_terms_raw = os.getenv("LOCATION_TERMS", "")
LOCATION_TERMS = [
    loc.strip() for loc in _location_terms_raw.split(",") if loc.strip()
] or None  # None means use defaults (NY, New York, Remote)

# Google Search Mode Configuration
# Options: 'default', 'mid_level', 'exclude_senior', 'combined'
# - 'default': Standard keyword search
# - 'mid_level': Targets SWE II / mid-level roles with OR groups
# - 'exclude_senior': Excludes senior/staff titles with minus operators
# - 'combined': Both targeting and exclusion (recommended)
SEARCH_MODE = os.getenv("SEARCH_MODE", "combined")
if SEARCH_MODE not in ('default', 'mid_level', 'exclude_senior', 'combined'):
    _logger = logging.getLogger(__name__)
    _logger.warning(f"Invalid SEARCH_MODE '{SEARCH_MODE}', defaulting to 'combined'")
    SEARCH_MODE = 'combined'

# Level-specific terms to search for (comma-separated)
# Used in 'mid_level' and 'combined' search modes
_level_terms_raw = os.getenv("LEVEL_TERMS", "")
LEVEL_TERMS = [
    t.strip() for t in _level_terms_raw.split(",") if t.strip()
] or None  # None means use defaults

# Seniority levels to exclude from search (comma-separated)
# Used in 'exclude_senior' and 'combined' search modes
_exclude_levels_raw = os.getenv("EXCLUDE_LEVELS", "")
EXCLUDE_LEVELS = [
    t.strip() for t in _exclude_levels_raw.split(",") if t.strip()
] or None  # None means use defaults

# Title Keywords Filter (comma-separated)
# Jobs must have at least one of these keywords in the title to pass filtering
# Used to filter out non-software roles when polling API providers
# Empty string disables the filter (all jobs pass through)
_title_keywords_raw = os.getenv("TITLE_KEYWORDS", "engineer,developer,software,swe,sde,programmer,backend,frontend,fullstack,full-stack,devops,platform,infrastructure,systems")
TITLE_KEYWORDS = [
    kw.strip() for kw in _title_keywords_raw.split(",") if kw.strip()
] or None  # None disables the filter

# LLM API Provider Selection
# Options: "claude" or "openai"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "claude").lower()
if LLM_PROVIDER not in ("claude", "openai"):
    raise ValueError("LLM_PROVIDER must be 'claude' or 'openai'")

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

try:
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    if not 0 <= OPENAI_TEMPERATURE <= 2:
        raise ValueError("OPENAI_TEMPERATURE must be between 0 and 2")
except ValueError as e:
    raise ValueError(f"Invalid OPENAI_TEMPERATURE: {e}")

try:
    OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
    if OPENAI_MAX_TOKENS < 1:
        raise ValueError("OPENAI_MAX_TOKENS must be positive")
except ValueError as e:
    raise ValueError(f"Invalid OPENAI_MAX_TOKENS: {e}")

# OpenAI cost per million tokens (for reporting)
try:
    OPENAI_INPUT_COST_PER_M = float(os.getenv("OPENAI_INPUT_COST_PER_M", "2.0"))
except ValueError as e:
    raise ValueError(f"Invalid OPENAI_INPUT_COST_PER_M: {e}")

try:
    OPENAI_OUTPUT_COST_PER_M = float(os.getenv("OPENAI_OUTPUT_COST_PER_M", "8.0"))
except ValueError as e:
    raise ValueError(f"Invalid OPENAI_OUTPUT_COST_PER_M: {e}")

# Claude API Configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

try:
    CLAUDE_TEMPERATURE = float(os.getenv("CLAUDE_TEMPERATURE", "0.3"))
    if not 0 <= CLAUDE_TEMPERATURE <= 1:
        raise ValueError("CLAUDE_TEMPERATURE must be between 0 and 1")
except ValueError as e:
    raise ValueError(f"Invalid CLAUDE_TEMPERATURE: {e}")

try:
    CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "1000"))
    if CLAUDE_MAX_TOKENS < 1:
        raise ValueError("CLAUDE_MAX_TOKENS must be positive")
except ValueError as e:
    raise ValueError(f"Invalid CLAUDE_MAX_TOKENS: {e}")

# Claude cost per million tokens (for reporting)
try:
    CLAUDE_INPUT_COST_PER_M = float(os.getenv("CLAUDE_INPUT_COST_PER_M", "3.0"))
except ValueError as e:
    raise ValueError(f"Invalid CLAUDE_INPUT_COST_PER_M: {e}")

try:
    CLAUDE_OUTPUT_COST_PER_M = float(os.getenv("CLAUDE_OUTPUT_COST_PER_M", "15.0"))
except ValueError as e:
    raise ValueError(f"Invalid CLAUDE_OUTPUT_COST_PER_M: {e}")

# Validate that the selected provider has an API key
if LLM_PROVIDER == "claude" and not CLAUDE_API_KEY:
    raise ValueError("CLAUDE_API_KEY is required when LLM_PROVIDER=claude")
if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

# Database Configuration
# DATABASE_MODE: "local" (SQLite file) or "turso" (cloud database)
DATABASE_MODE = os.getenv("DATABASE_MODE", "local").lower()
if DATABASE_MODE not in ("local", "turso"):
    raise ValueError("DATABASE_MODE must be 'local' or 'turso'")

# Local SQLite database path (used when DATABASE_MODE=local)
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "jobs.db"))

# Turso Cloud Database Configuration (used when DATABASE_MODE=turso)
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Validate Turso config if mode is turso
if DATABASE_MODE == "turso":
    if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
        raise ValueError(
            "DATABASE_MODE=turso requires TURSO_DATABASE_URL and TURSO_AUTH_TOKEN to be set"
        )

# Direct API Polling Configuration
# These providers fetch jobs directly from ATS APIs (free, no rate limits)

# Greenhouse API Configuration
GREENHOUSE_API_ENABLED = os.getenv("GREENHOUSE_API_ENABLED", "true").lower() == "true"
GREENHOUSE_POLL_CURATED = os.getenv("GREENHOUSE_POLL_CURATED", "true").lower() == "true"

# Lever API Configuration
LEVER_API_ENABLED = os.getenv("LEVER_API_ENABLED", "true").lower() == "true"
LEVER_POLL_CURATED = os.getenv("LEVER_POLL_CURATED", "true").lower() == "true"

# Ashby API Configuration
ASHBY_API_ENABLED = os.getenv("ASHBY_API_ENABLED", "true").lower() == "true"
ASHBY_POLL_CURATED = os.getenv("ASHBY_POLL_CURATED", "true").lower() == "true"

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "agent.log"))

# Search Configuration
SEARCH_KEYWORDS = [k.strip() for k in os.getenv("SEARCH_KEYWORDS", "software engineer,ai engineer,machine learning engineer").split(",")]
SEARCH_LOCATIONS = [l.strip() for l in os.getenv("SEARCH_LOCATIONS", "Remote,New York").split(",")]

try:
    MAX_RESULTS_PER_SEARCH = int(os.getenv("MAX_RESULTS_PER_SEARCH", "50"))
    if MAX_RESULTS_PER_SEARCH < 1:
        raise ValueError("MAX_RESULTS_PER_SEARCH must be positive")
except ValueError as e:
    raise ValueError(f"Invalid MAX_RESULTS_PER_SEARCH: {e}")

# Scoring Configuration
try:
    MIN_DISPLAY_SCORE = int(os.getenv("MIN_DISPLAY_SCORE", "60"))
    if not 0 <= MIN_DISPLAY_SCORE <= 100:
        raise ValueError("MIN_DISPLAY_SCORE must be between 0 and 100")
except ValueError as e:
    raise ValueError(f"Invalid MIN_DISPLAY_SCORE: {e}")

try:
    TOP_JOBS_LIMIT = int(os.getenv("TOP_JOBS_LIMIT", "20"))
    if TOP_JOBS_LIMIT < 1:
        raise ValueError("TOP_JOBS_LIMIT must be positive")
except ValueError as e:
    raise ValueError(f"Invalid TOP_JOBS_LIMIT: {e}")

# Resume file path
RESUME_FILE = RESUME_DIR / "oscar_resume.txt"

# Validation
_logger = logging.getLogger(__name__)

# Validate source configurations
if "linkedin" in ENABLED_SOURCES:
    if not LINKEDIN_COOKIE and not Path(LINKEDIN_SESSION_PATH).exists():
        _logger.warning(
            "LinkedIn source enabled but not configured. Either:\n"
            "  1. Set LINKEDIN_COOKIE environment variable (li_at cookie value), OR\n"
            "  2. Set LINKEDIN_SESSION_PATH to a valid session.json file"
        )

if "web_scraping" in ENABLED_SOURCES:
    # Log discovery provider configuration
    _logger.info(
        f"Web scraping enabled with discovery providers: {ENABLED_DISCOVERY_PROVIDERS}\n"
        f"  JobSpy sites: {JOBSPY_SITES}\n"
        f"  JobSpy hours_old: {JOBSPY_HOURS_OLD}\n"
        f"  ATS platforms: {WEB_SCRAPING_PLATFORMS}\n"
        f"  Location filter: {LOCATION_TERMS or 'None (all locations)'}"
    )
