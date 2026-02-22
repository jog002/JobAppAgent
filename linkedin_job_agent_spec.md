# LinkedIn Job Search Agent - Project Specification

## Project Overview

An AI-powered job search automation system that leverages the LinkedIn MCP server to discover jobs, scores them against user preferences using Claude AI, and generates personalized recommendations. The system will run on-demand initially (MVP) with plans to add daily automation and application submission features.

---

## User Profile: Oscar Giller

### Current Situation
- **Current Role**: Software Engineer at JP Morgan Chase
- **Current Salary**: $130,000 base
- **Location**: New York, NY 10002
- **LinkedIn**: linkedin.com/in/joscargiller

### Technical Background
- **Primary Skills**: Python, TypeScript, React, Azure OpenAI, KQL, Terraform
- **Experience**: Full-stack development, AI/ML applications, cloud platforms (Azure, AWS)
- **Notable Projects**: 
  - Built internal AI-powered dashboard for monitoring 1,000+ applications
  - Azure OpenAI deployment management and quota optimization
  - Grafana dashboard development with KQL queries

### Job Search Requirements

#### Must-Have Criteria
- **Minimum Salary**: $140,000 (to justify switch)
- **Target Salary**: $150,000+ (good match), $165,000+ (excellent match)
- **Location**: Remote (preferred) or NYC-based (hybrid acceptable)
- **Title**: Software Engineer 2 level or equivalent
- **Work Arrangement Preference**: Remote > Hybrid > In-Office

#### Preferred Criteria
- **Company Type**: Big Tech (FAANG+) strongly preferred
- **Industry**: AI/ML related roles are a bonus
- **Finance**: Only highly reputable firms unless compensation is exceptional
- **Avoid**: Small trading firms unless pay is significantly higher

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Trigger (Manual/Cron)                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Job Search Agent (Python)                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 1. Fetch Jobs (LinkedIn MCP Server)                   │  │
│  │    - search_jobs (keywords, location)                 │  │
│  │    - get_recommended_jobs (personalized)              │  │
│  │    - get_job_details (detailed info)                  │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                   │
│  ┌───────────────────────▼───────────────────────────────┐  │
│  │ 2. Score Jobs (Claude API)                            │  │
│  │    - Parse job description                            │  │
│  │    - Compare against resume & preferences             │  │
│  │    - Generate score (0-100) with reasoning            │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                   │
│  ┌───────────────────────▼───────────────────────────────┐  │
│  │ 3. Store Results (SQLite Database)                    │  │
│  │    - Job details                                      │  │
│  │    - Scores and reasoning                             │  │
│  │    - Deduplication                                    │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                   │
│  ┌───────────────────────▼───────────────────────────────┐  │
│  │ 4. Generate Report                                    │  │
│  │    - Top recommendations                              │  │
│  │    - Score breakdown                                  │  │
│  │    - Action items                                     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Output (Console/Email/File)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Core Dependencies
- **Python**: 3.12+
- **LinkedIn MCP Server**: `stickerdaniel/linkedin-mcp-server` (Docker)
- **LLM API**: Anthropic Claude API (claude-sonnet-4-20250514)
- **Database**: SQLite3
- **Environment**: python-dotenv for configuration

### Additional Libraries
- **anthropic**: Official Anthropic Python SDK
- **sqlite3**: Built-in Python database
- **docker**: For LinkedIn MCP server (via subprocess/CLI)
- **json**: Job data parsing
- **datetime**: Timestamp management
- **logging**: System logging

---

## Database Schema

### Table: `jobs`
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    linkedin_job_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    location TEXT,
    remote_type TEXT,  -- 'Remote', 'Hybrid', 'On-site', 'Unknown'
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT DEFAULT 'USD',
    posted_date TEXT,
    found_date TEXT NOT NULL,
    score INTEGER,  -- 0-100
    score_reasoning TEXT,
    status TEXT DEFAULT 'new',  -- 'new', 'reviewed', 'applied', 'rejected', 'archived'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jobs_score ON jobs(score DESC);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_linkedin_id ON jobs(linkedin_job_id);
```

### Table: `search_runs`
```sql
CREATE TABLE search_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    jobs_found INTEGER DEFAULT 0,
    jobs_new INTEGER DEFAULT 0,
    jobs_updated INTEGER DEFAULT 0,
    search_queries TEXT,  -- JSON array of queries used
    status TEXT DEFAULT 'running',  -- 'running', 'completed', 'failed'
    error_message TEXT,
    duration_seconds REAL
);
```

---

## Scoring Algorithm

### Scoring Criteria (Total: 100 points)

#### 1. Remote Work Flexibility (30 points)
- **Remote**: 30 points
- **Hybrid (NYC)**: 20 points
- **On-site (NYC)**: 10 points
- **On-site (Other)**: 0 points

#### 2. Salary Range (35 points)
- **$165k+**: 35 points
- **$150k-$164k**: 28 points
- **$140k-$149k**: 20 points
- **$130k-$139k**: 10 points
- **<$130k**: 0 points
- **Unknown**: 15 points (benefit of doubt, but lower priority)

#### 3. Company Type (20 points)
- **FAANG (Meta, Apple, Amazon, Netflix, Google)**: 20 points
- **Big Tech (Microsoft, Uber, Airbnb, etc.)**: 18 points
- **Well-known Tech Unicorns**: 15 points
- **Top-tier Finance (Goldman, JPM, Citadel)**: 14 points
- **Other reputable companies**: 10 points
- **Unknown/Small firms**: 5 points

#### 4. AI/ML Relevance (10 points)
- **Primary focus on AI/ML**: 10 points
- **Significant AI/ML component**: 7 points
- **Some AI/ML work**: 4 points
- **No AI/ML**: 0 points

#### 5. Title/Level Match (5 points)
- **Software Engineer II / Engineer 2**: 5 points
- **Software Engineer / Mid-level**: 4 points
- **Senior Software Engineer**: 3 points (only if exceptional pay)
- **SWE I / Junior**: 0 points

### Score Interpretation
- **90-100**: Excellent match - Auto-apply candidate (future feature)
- **75-89**: Strong match - Definitely review and apply
- **60-74**: Good match - Review carefully
- **45-59**: Moderate match - Consider if other factors align
- **<45**: Poor match - Archive unless exceptional circumstances

---

## MVP Implementation Plan

### Phase 1: Environment Setup (Day 1)

#### Tasks
1. **Install LinkedIn MCP Server**
   ```bash
   # Using Docker (recommended)
   docker pull stickerdaniel/linkedin-mcp-server:latest
   
   # Test the server
   docker run -it --rm \
     -e LINKEDIN_COOKIE="your_cookie_here" \
     stickerdaniel/linkedin-mcp-server:latest \
     --help
   ```

2. **Obtain LinkedIn Cookie**
   - Method 1: Chrome DevTools
     - Open linkedin.com and log in
     - F12 → Application → Cookies → https://www.linkedin.com
     - Copy `li_at` cookie value
   - Method 2: Using the MCP server
     ```bash
     docker run -it --rm \
       stickerdaniel/linkedin-mcp-server:latest \
       --get-cookie
     ```

3. **Project Structure**
   ```
   linkedin-job-agent/
   ├── .env                    # Environment variables
   ├── .gitignore              # Git ignore file
   ├── requirements.txt        # Python dependencies
   ├── README.md               # Project documentation
   ├── config.py               # Configuration management
   ├── database.py             # Database operations
   ├── linkedin_client.py      # LinkedIn MCP server interface
   ├── scoring_engine.py       # Job scoring logic
   ├── main.py                 # Main entry point
   ├── data/
   │   └── jobs.db            # SQLite database
   ├── logs/
   │   └── agent.log          # Application logs
   └── resume/
       └── oscar_resume.txt   # Resume for scoring reference
   ```

4. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install --upgrade pip
   ```

5. **Install Dependencies**
   ```bash
   pip install anthropic python-dotenv
   ```

#### Deliverables
- ✅ LinkedIn MCP server running in Docker
- ✅ LinkedIn cookie obtained and tested
- ✅ Project structure created
- ✅ Virtual environment configured
- ✅ Dependencies installed

---

### Phase 2: Core Components (Day 2-3)

#### 2.1 Configuration Management (`config.py`)

**Purpose**: Centralized configuration and environment variable management

**Required Environment Variables** (`.env`):
```env
# LinkedIn MCP Server
LINKEDIN_COOKIE=your_li_at_cookie_value_here

# Anthropic API
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database
DATABASE_PATH=./data/jobs.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/agent.log

# Search Parameters
SEARCH_KEYWORDS=software engineer,ai engineer,machine learning engineer
SEARCH_LOCATIONS=Remote,New York
MAX_RESULTS_PER_SEARCH=50
```

**Implementation Requirements**:
- Load environment variables using `python-dotenv`
- Provide defaults for optional configurations
- Validate required variables on startup
- Expose configuration as a singleton or module-level variables

---

#### 2.2 Database Layer (`database.py`)

**Purpose**: Handle all database operations with proper error handling

**Required Functions**:

```python
def init_database(db_path: str) -> None:
    """Initialize database with schema if it doesn't exist"""
    pass

def insert_job(job_data: dict) -> int:
    """Insert a new job or update if exists. Returns job_id"""
    pass

def update_job_score(linkedin_job_id: str, score: int, reasoning: str) -> None:
    """Update the score and reasoning for a job"""
    pass

def get_job_by_linkedin_id(linkedin_job_id: str) -> dict | None:
    """Retrieve a job by its LinkedIn ID"""
    pass

def get_top_jobs(limit: int = 20, min_score: int = 60) -> list[dict]:
    """Get top-scoring jobs above minimum threshold"""
    pass

def get_jobs_by_status(status: str, limit: int = 100) -> list[dict]:
    """Get jobs filtered by status"""
    pass

def create_search_run() -> int:
    """Create a new search run record. Returns run_id"""
    pass

def complete_search_run(run_id: int, stats: dict) -> None:
    """Mark search run as complete with statistics"""
    pass

def get_recent_jobs(days: int = 7) -> list[dict]:
    """Get jobs found in the last N days"""
    pass
```

**Error Handling**:
- Wrap all database operations in try-except blocks
- Log all database errors
- Handle duplicate key violations gracefully
- Ensure proper connection cleanup

---

#### 2.3 LinkedIn Client (`linkedin_client.py`)

**Purpose**: Interface with the LinkedIn MCP server via Docker

**Required Functions**:

```python
def call_linkedin_mcp(tool_name: str, arguments: dict) -> dict:
    """
    Call a LinkedIn MCP server tool via Docker
    
    Args:
        tool_name: Name of the MCP tool (e.g., 'search_jobs', 'get_job_details')
        arguments: Dictionary of arguments for the tool
    
    Returns:
        Parsed JSON response from the MCP server
    """
    pass

def search_jobs(keywords: str, location: str = "", limit: int = 50) -> list[dict]:
    """
    Search for jobs using the MCP server
    
    Returns list of job dictionaries with basic info
    """
    pass

def get_recommended_jobs(limit: int = 50) -> list[dict]:
    """
    Get personalized job recommendations from LinkedIn
    
    Returns list of recommended job dictionaries
    """
    pass

def get_job_details(job_id: str) -> dict:
    """
    Get detailed information for a specific job
    
    Args:
        job_id: LinkedIn job ID
    
    Returns:
        Detailed job information dictionary
    """
    pass
```

**Implementation Notes**:
- Use `subprocess` to run Docker commands
- Parse JSON output from MCP server
- Handle MCP server errors and timeouts
- Implement retry logic for transient failures
- Log all MCP interactions for debugging

**Example Docker Command**:
```python
import subprocess
import json

cmd = [
    "docker", "run", "--rm", "-i",
    "-e", f"LINKEDIN_COOKIE={os.getenv('LINKEDIN_COOKIE')}",
    "stickerdaniel/linkedin-mcp-server:latest",
    "--tool", "search_jobs",
    "--args", json.dumps({"keywords": "software engineer", "location": "Remote"})
]

result = subprocess.run(cmd, capture_output=True, text=True)
data = json.loads(result.stdout)
```

---

#### 2.4 Scoring Engine (`scoring_engine.py`)

**Purpose**: Use Claude API to score jobs against user profile

**Required Functions**:

```python
def score_job(job: dict, resume_text: str) -> dict:
    """
    Score a job using Claude API
    
    Args:
        job: Job dictionary with title, company, description, location, etc.
        resume_text: Oscar's resume content
    
    Returns:
        {
            "score": int (0-100),
            "reasoning": str,
            "salary_estimate": str,
            "remote_type": str,
            "auto_apply_recommended": bool
        }
    """
    pass

def batch_score_jobs(jobs: list[dict], resume_text: str) -> list[dict]:
    """
    Score multiple jobs efficiently
    
    Returns list of jobs with scores added
    """
    pass
```

**Scoring Prompt Template**:

```python
SCORING_PROMPT = """You are an expert job search advisor helping Oscar Giller find his next role.

# Oscar's Profile
Current Role: Software Engineer at JP Morgan Chase
Current Salary: $130,000
Location: New York, NY
Target: Software Engineer 2 level positions

# Oscar's Resume
{resume_text}

# Job Requirements
- Minimum Salary: $140,000 (to justify switch)
- Preferred Salary: $150,000+ (good), $165,000+ (excellent)
- Location: Remote (best) > Hybrid NYC > On-site NYC
- Company: Big Tech / FAANG strongly preferred
- AI/ML focus is a significant bonus

# Job to Score
Title: {job_title}
Company: {company}
Location: {location}
Description:
{description}

# Scoring Criteria (Total 100 points)
1. Remote Work (30 pts): Remote=30, Hybrid NYC=20, On-site NYC=10, Other=0
2. Salary (35 pts): $165k+=35, $150-164k=28, $140-149k=20, $130-139k=10, <$130k=0, Unknown=15
3. Company (20 pts): FAANG=20, Big Tech=18, Tech Unicorn=15, Top Finance=14, Other=10, Unknown=5
4. AI/ML (10 pts): Primary=10, Significant=7, Some=4, None=0
5. Level Match (5 pts): SWE2=5, Mid-level=4, Senior=3, Junior=0

# Task
Analyze this job and provide:
1. A score (0-100) based on the criteria above
2. Brief reasoning for the score (2-3 sentences)
3. Salary estimate if not explicitly stated
4. Whether this would be a good match for Oscar

Return ONLY a JSON object with this exact structure:
{
    "score": <number 0-100>,
    "reasoning": "<string>",
    "salary_estimate": "<string or 'Not specified'>",
    "remote_type": "<Remote|Hybrid|On-site|Unknown>",
    "auto_apply_recommended": <boolean>
}
"""
```

**Implementation Requirements**:
- Use Anthropic SDK with `claude-sonnet-4-20250514` model
- Parse JSON response from Claude
- Handle API errors and rate limits
- Implement caching for already-scored jobs
- Log all scoring decisions

---

#### 2.5 Main Application (`main.py`)

**Purpose**: Orchestrate the job search and scoring workflow

**Required Functions**:

```python
def load_resume() -> str:
    """Load Oscar's resume from file"""
    pass

def run_job_search() -> dict:
    """
    Main workflow:
    1. Create search run record
    2. Fetch jobs from LinkedIn MCP
    3. Store jobs in database
    4. Score jobs with Claude
    5. Update database with scores
    6. Generate report
    
    Returns:
        {
            "total_jobs_found": int,
            "new_jobs": int,
            "top_jobs": list[dict],
            "summary": str
        }
    """
    pass

def generate_report(run_results: dict) -> str:
    """Generate human-readable report of findings"""
    pass

def main():
    """Entry point for the application"""
    pass
```

**Workflow Logic**:

```python
def run_job_search():
    # 1. Initialize
    run_id = db.create_search_run()
    resume = load_resume()
    
    # 2. Search LinkedIn
    search_queries = [
        ("software engineer", "Remote"),
        ("ai engineer", "Remote"),
        ("machine learning engineer", "New York"),
    ]
    
    all_jobs = []
    for keywords, location in search_queries:
        jobs = linkedin_client.search_jobs(keywords, location)
        all_jobs.extend(jobs)
    
    # Also get recommended jobs
    recommended = linkedin_client.get_recommended_jobs()
    all_jobs.extend(recommended)
    
    # 3. Deduplicate and store
    new_jobs = []
    for job in all_jobs:
        existing = db.get_job_by_linkedin_id(job['id'])
        if not existing:
            db.insert_job(job)
            new_jobs.append(job)
    
    # 4. Score new jobs
    scored_jobs = scoring_engine.batch_score_jobs(new_jobs, resume)
    
    # 5. Update database with scores
    for job in scored_jobs:
        db.update_job_score(
            job['linkedin_job_id'],
            job['score'],
            job['reasoning']
        )
    
    # 6. Get top results
    top_jobs = db.get_top_jobs(limit=20, min_score=60)
    
    # 7. Complete search run
    stats = {
        'jobs_found': len(all_jobs),
        'jobs_new': len(new_jobs),
        'jobs_updated': 0
    }
    db.complete_search_run(run_id, stats)
    
    return {
        'total_jobs_found': len(all_jobs),
        'new_jobs': len(new_jobs),
        'top_jobs': top_jobs,
        'summary': generate_report({'top_jobs': top_jobs, 'stats': stats})
    }
```

---

#### Deliverables
- ✅ `config.py` with environment management
- ✅ `database.py` with complete CRUD operations
- ✅ `linkedin_client.py` with MCP server integration
- ✅ `scoring_engine.py` with Claude API scoring
- ✅ `main.py` with complete workflow orchestration

---

### Phase 3: Testing & Refinement (Day 4)

#### Tasks

1. **Unit Testing**
   - Test database operations with sample data
   - Test LinkedIn MCP client with mock responses
   - Test scoring engine with sample job descriptions

2. **Integration Testing**
   - Run end-to-end workflow with real LinkedIn data
   - Verify database persistence
   - Validate score calculations

3. **Output Validation**
   - Review top 20 recommendations manually
   - Verify scores make sense given criteria
   - Check for missing salary/location data

4. **Error Handling**
   - Test with invalid LinkedIn cookies
   - Test with network failures
   - Test with Claude API rate limits

5. **Performance Optimization**
   - Measure time for full search cycle
   - Optimize database queries
   - Implement caching where appropriate

#### Deliverables
- ✅ All components tested and working
- ✅ Error handling verified
- ✅ Performance acceptable (<5 min for full run)
- ✅ Documentation updated with findings

---

### Phase 4: Reporting & Output (Day 5)

#### 4.1 Console Report Format

```
================================================================================
                   LINKEDIN JOB SEARCH REPORT
                   Run Date: 2025-01-19 08:00:00
================================================================================

SEARCH SUMMARY
--------------
• Total Jobs Found: 127
• New Jobs: 43
• Jobs Scored: 43
• Duration: 4m 32s

TOP RECOMMENDATIONS (Score ≥ 75)
================================

1. ⭐ SCORE: 96 - Senior AI Engineer @ Google
   💰 Salary: $180,000 - $250,000
   📍 Location: Remote (US)
   🔗 URL: https://linkedin.com/jobs/view/123456789
   💡 Reasoning: Excellent match - Remote role at FAANG with strong AI focus,
      salary well above target, and perfect level match for SWE2.

2. ⭐ SCORE: 94 - ML Platform Engineer @ Stripe
   💰 Salary: $175,000 - $220,000
   📍 Location: Remote
   🔗 URL: https://linkedin.com/jobs/view/987654321
   💡 Reasoning: Outstanding opportunity - Remote at top fintech, strong AI/ML
      component, excellent compensation.

[... continue for top 20 jobs ...]

GOOD MATCHES (Score 60-74)
===========================
• Software Engineer II @ Microsoft - Score: 72 (Hybrid, $155k)
• Backend Engineer @ Airbnb - Score: 68 (Remote, $150k)
[... etc ...]

STATISTICS
----------
Score Distribution:
  90-100: 3 jobs   ████████
  75-89:  8 jobs   ████████████████████
  60-74:  12 jobs  ██████████████████████████
  45-59:  15 jobs  ██████████████████████████████
  <45:    5 jobs   ████████

================================================================================
```

#### 4.2 JSON Export Option

```python
def export_results_json(results: dict, filepath: str) -> None:
    """Export results to JSON file for programmatic access"""
    pass
```

#### 4.3 Email Report (Future Enhancement)

Prepare structure for email integration:
- HTML email template
- SendGrid integration placeholder
- Scheduled sending logic

#### Deliverables
- ✅ Console report with rich formatting
- ✅ JSON export functionality
- ✅ Clear action items for user
- ✅ Statistics and insights

---

## File-by-File Implementation Guide

### 1. `.env` (Environment Configuration)

```env
# LinkedIn MCP Server Configuration
LINKEDIN_COOKIE=your_li_at_cookie_value_here

# Anthropic API Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database Configuration
DATABASE_PATH=./data/jobs.db

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=./logs/agent.log

# Search Configuration
SEARCH_KEYWORDS=software engineer,ai engineer,machine learning engineer
SEARCH_LOCATIONS=Remote,New York
MAX_RESULTS_PER_SEARCH=50

# Scoring Configuration
MIN_DISPLAY_SCORE=60
TOP_JOBS_LIMIT=20
```

---

### 2. `requirements.txt` (Python Dependencies)

```txt
anthropic>=0.40.0
python-dotenv>=1.0.0
```

---

### 3. `config.py` (Configuration Management)

```python
"""Configuration management for LinkedIn Job Agent."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
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

# LinkedIn MCP Configuration
LINKEDIN_COOKIE = os.getenv("LINKEDIN_COOKIE")
if not LINKEDIN_COOKIE:
    raise ValueError("LINKEDIN_COOKIE environment variable is required")

# Anthropic API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is required")

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "jobs.db"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "agent.log"))

# Search Configuration
SEARCH_KEYWORDS = os.getenv("SEARCH_KEYWORDS", "software engineer,ai engineer,machine learning engineer").split(",")
SEARCH_LOCATIONS = os.getenv("SEARCH_LOCATIONS", "Remote,New York").split(",")
MAX_RESULTS_PER_SEARCH = int(os.getenv("MAX_RESULTS_PER_SEARCH", "50"))

# Scoring Configuration
MIN_DISPLAY_SCORE = int(os.getenv("MIN_DISPLAY_SCORE", "60"))
TOP_JOBS_LIMIT = int(os.getenv("TOP_JOBS_LIMIT", "20"))

# Resume file path
RESUME_FILE = RESUME_DIR / "oscar_resume.txt"
```

**Requirements**:
- Load all environment variables using `python-dotenv`
- Validate required variables
- Provide sensible defaults for optional configs
- Create necessary directories
- Export all configs as module-level variables

---

### 4. `database.py` (Database Operations)

```python
"""Database operations for LinkedIn Job Agent."""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from config import DATABASE_PATH

logger = logging.getLogger(__name__)

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
"""

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
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
    logger.info(f"Initializing database at {DATABASE_PATH}")
    with get_db_connection() as conn:
        conn.executescript(SCHEMA)
    logger.info("Database initialized successfully")


def insert_job(job_data: dict) -> int:
    """
    Insert a new job or update if exists.
    
    Args:
        job_data: Dictionary containing job information
        
    Returns:
        Job ID (primary key)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if job already exists
        cursor.execute(
            "SELECT id FROM jobs WHERE linkedin_job_id = ?",
            (job_data.get('linkedin_job_id'),)
        )
        existing = cursor.fetchone()
        
        if existing:
            logger.info(f"Job {job_data.get('linkedin_job_id')} already exists")
            return existing[0]
        
        # Insert new job
        cursor.execute("""
            INSERT INTO jobs (
                linkedin_job_id, title, company, url, description,
                location, remote_type, salary_min, salary_max,
                posted_date, found_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_data.get('linkedin_job_id'),
            job_data.get('title'),
            job_data.get('company'),
            job_data.get('url'),
            job_data.get('description'),
            job_data.get('location'),
            job_data.get('remote_type', 'Unknown'),
            job_data.get('salary_min'),
            job_data.get('salary_max'),
            job_data.get('posted_date'),
            datetime.now().isoformat()
        ))
        
        job_id = cursor.lastrowid
        logger.info(f"Inserted new job: {job_data.get('title')} at {job_data.get('company')}")
        return job_id


def update_job_score(linkedin_job_id: str, score: int, reasoning: str) -> None:
    """Update the score and reasoning for a job."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs 
            SET score = ?, score_reasoning = ?, updated_at = ?
            WHERE linkedin_job_id = ?
        """, (score, reasoning, datetime.now().isoformat(), linkedin_job_id))
        logger.info(f"Updated score for job {linkedin_job_id}: {score}")


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
    """Create a new search run record."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO search_runs (search_queries)
            VALUES (?)
        """, (json.dumps(search_queries),))
        run_id = cursor.lastrowid
        logger.info(f"Created search run {run_id}")
        return run_id


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
```

**Requirements**:
- Use context managers for database connections
- Implement proper error handling and rollback
- Log all database operations
- Handle duplicate job insertions gracefully
- Use parameterized queries to prevent SQL injection

---

### 5. `linkedin_client.py` (LinkedIn MCP Interface)

```python
"""LinkedIn MCP Server client interface."""

import subprocess
import json
import logging
import os
from typing import Optional

from config import LINKEDIN_COOKIE, MAX_RESULTS_PER_SEARCH

logger = logging.getLogger(__name__)

MCP_DOCKER_IMAGE = "stickerdaniel/linkedin-mcp-server:latest"


def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """
    Call a LinkedIn MCP server tool via Docker.
    
    This function interfaces with the MCP server by running it in a Docker
    container with stdio transport mode.
    
    Args:
        tool_name: Name of the MCP tool to call
        arguments: Dictionary of arguments for the tool
        
    Returns:
        Parsed JSON response from the MCP server
        
    Raises:
        RuntimeError: If the MCP server call fails
    """
    logger.debug(f"Calling MCP tool: {tool_name} with args: {arguments}")
    
    try:
        # Prepare the MCP request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        # Build Docker command
        cmd = [
            "docker", "run", "--rm", "-i",
            "-e", f"LINKEDIN_COOKIE={LINKEDIN_COOKIE}",
            MCP_DOCKER_IMAGE
        ]
        
        # Run the Docker command with the request as stdin
        result = subprocess.run(
            cmd,
            input=json.dumps(mcp_request),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            logger.error(f"MCP tool call failed: {result.stderr}")
            raise RuntimeError(f"MCP tool '{tool_name}' failed: {result.stderr}")
        
        # Parse the response
        response = json.loads(result.stdout)
        logger.debug(f"MCP response: {response}")
        
        # Check for errors in the response
        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")
        
        return response.get("result", {})
        
    except subprocess.TimeoutExpired:
        logger.error(f"MCP tool call timed out: {tool_name}")
        raise RuntimeError(f"MCP tool '{tool_name}' timed out")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse MCP response: {e}")
        raise RuntimeError(f"Invalid JSON response from MCP: {e}")
    except Exception as e:
        logger.error(f"Unexpected error calling MCP tool: {e}")
        raise


def search_jobs(keywords: str, location: str = "", limit: int = None) -> list[dict]:
    """
    Search for jobs using LinkedIn MCP server.
    
    Args:
        keywords: Search keywords (e.g., "software engineer")
        location: Location filter (e.g., "Remote", "New York")
        limit: Maximum number of results (default from config)
        
    Returns:
        List of job dictionaries
    """
    if limit is None:
        limit = MAX_RESULTS_PER_SEARCH
    
    logger.info(f"Searching jobs: keywords='{keywords}', location='{location}', limit={limit}")
    
    arguments = {
        "keywords": keywords,
        "location": location,
        "limit": limit
    }
    
    try:
        result = call_mcp_tool("search_jobs", arguments)
        jobs = result.get("jobs", [])
        logger.info(f"Found {len(jobs)} jobs for query: {keywords}")
        return jobs
    except Exception as e:
        logger.error(f"Failed to search jobs: {e}")
        return []


def get_recommended_jobs(limit: int = None) -> list[dict]:
    """
    Get personalized job recommendations from LinkedIn.
    
    Args:
        limit: Maximum number of results
        
    Returns:
        List of recommended job dictionaries
    """
    if limit is None:
        limit = MAX_RESULTS_PER_SEARCH
    
    logger.info(f"Fetching recommended jobs (limit={limit})")
    
    try:
        result = call_mcp_tool("get_recommended_jobs", {"limit": limit})
        jobs = result.get("jobs", [])
        logger.info(f"Found {len(jobs)} recommended jobs")
        return jobs
    except Exception as e:
        logger.error(f"Failed to get recommended jobs: {e}")
        return []


def get_job_details(job_id: str) -> Optional[dict]:
    """
    Get detailed information for a specific job.
    
    Args:
        job_id: LinkedIn job ID
        
    Returns:
        Detailed job information dictionary or None if failed
    """
    logger.info(f"Fetching job details for job_id={job_id}")
    
    try:
        result = call_mcp_tool("get_job_details", {"job_id": job_id})
        return result.get("job", {})
    except Exception as e:
        logger.error(f"Failed to get job details for {job_id}: {e}")
        return None


def enrich_job_data(job: dict) -> dict:
    """
    Enrich basic job data with detailed information.
    
    Args:
        job: Basic job dictionary from search results
        
    Returns:
        Enriched job dictionary with more details
    """
    job_id = job.get('id') or job.get('linkedin_job_id')
    if not job_id:
        logger.warning("Job missing ID, cannot enrich")
        return job
    
    details = get_job_details(job_id)
    if details:
        job.update(details)
    
    return job
```

**Requirements**:
- Use subprocess to call Docker commands
- Handle MCP protocol communication (JSON-RPC)
- Parse and validate MCP responses
- Implement retry logic for transient failures
- Log all interactions for debugging
- Handle timeout scenarios gracefully

**Note**: The exact MCP protocol may vary. Consult the LinkedIn MCP server documentation for the precise request/response format. You may need to adjust the `call_mcp_tool` function based on how the server expects to receive commands.

---

### 6. `scoring_engine.py` (Job Scoring Logic)

```python
"""Job scoring engine using Claude API."""

import logging
import json
from typing import Optional
from anthropic import Anthropic

from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# Initialize Anthropic client
client = Anthropic(api_key=ANTHROPIC_API_KEY)

SCORING_PROMPT_TEMPLATE = """You are an expert job search advisor helping Oscar Giller find his next software engineering role.

# Oscar's Current Situation
- **Current Role**: Software Engineer at JP Morgan Chase
- **Current Salary**: $130,000 base
- **Location**: New York, NY
- **Target Level**: Software Engineer 2 / Mid-level Engineer
- **Years of Experience**: ~3 years (since 2022)

# Oscar's Resume & Skills
{resume_text}

# Job Search Requirements

## Critical Requirements (Deal-breakers)
- **Minimum Salary**: $140,000 (to justify switching)
- **Location**: Must be Remote or NYC-based (hybrid/on-site)

## Strong Preferences
- **Target Salary**: $150,000+ (good match), $165,000+ (excellent match)
- **Work Arrangement**: Remote > Hybrid NYC > On-site NYC
- **Company Type**: Big Tech (FAANG+) strongly preferred
- **Industry Focus**: AI/ML related roles are a significant bonus
- **Finance**: Only top-tier firms (Goldman, JPM, Citadel) unless exceptional pay

# Scoring Criteria (Total: 100 points)

## 1. Remote Work Flexibility (30 points)
- **Remote**: 30 points
- **Hybrid (NYC)**: 20 points  
- **On-site (NYC)**: 10 points
- **On-site (Other location)**: 0 points

## 2. Salary Range (35 points)
- **$165,000+**: 35 points (excellent)
- **$150,000-$164,999**: 28 points (good)
- **$140,000-$149,999**: 20 points (acceptable)
- **$130,000-$139,999**: 10 points (marginal)
- **Below $130,000**: 0 points (below current)
- **Unknown/Not specified**: 15 points (benefit of doubt, but flag it)

## 3. Company Type & Reputation (20 points)
- **FAANG** (Meta, Apple, Amazon, Netflix, Google): 20 points
- **Big Tech** (Microsoft, Uber, Lyft, Airbnb, Stripe, etc.): 18 points
- **Well-known Tech Unicorns** (OpenAI, Anthropic, Scale AI, etc.): 15 points
- **Top-tier Finance** (Goldman Sachs, JP Morgan, Citadel): 14 points
- **Reputable mid-size companies**: 10 points
- **Small/unknown firms**: 5 points

## 4. AI/ML Relevance (10 points)
- **Primary focus on AI/ML**: 10 points
- **Significant AI/ML component**: 7 points
- **Some AI/ML work**: 4 points
- **No AI/ML**: 0 points

## 5. Title/Level Match (5 points)
- **Software Engineer II / Engineer 2 / Mid-level Engineer**: 5 points
- **Software Engineer / equivalent**: 4 points
- **Senior Software Engineer**: 3 points (only if compensation is exceptional)
- **Junior / SWE I**: 0 points (below current level)

# Job to Score

**Title**: {job_title}
**Company**: {company}
**Location**: {location}
**Posted**: {posted_date}
**Job URL**: {job_url}

**Description**:
{description}

# Your Task

Carefully analyze this job posting against Oscar's profile and requirements. Consider:
1. How well does Oscar's experience match the requirements?
2. What is the likely salary range (if not explicitly stated)?
3. Is this role truly remote, hybrid, or on-site?
4. What is the company's reputation in tech?
5. Is there meaningful AI/ML work involved?
6. Is this the right level for a Software Engineer 2?

Calculate a score from 0-100 based strictly on the criteria above. Show your work by explaining which points were awarded in each category.

**Return ONLY valid JSON** with this exact structure (no markdown, no code blocks):

{{
    "score": <integer 0-100>,
    "reasoning": "<2-3 sentence explanation of the score>",
    "breakdown": {{
        "remote_work_score": <integer>,
        "salary_score": <integer>,
        "company_score": <integer>,
        "ai_ml_score": <integer>,
        "level_match_score": <integer>
    }},
    "salary_estimate": "<string like '$150,000-$170,000' or 'Not specified'>",
    "remote_type": "<Remote|Hybrid|On-site|Unknown>",
    "auto_apply_recommended": <boolean true if score >= 90>
}}
"""


def score_job(job: dict, resume_text: str) -> dict:
    """
    Score a single job using Claude API.
    
    Args:
        job: Job dictionary with title, company, description, etc.
        resume_text: Oscar's resume content
        
    Returns:
        Dictionary with score, reasoning, and other metadata
    """
    logger.info(f"Scoring job: {job.get('title')} at {job.get('company')}")
    
    # Prepare the prompt
    prompt = SCORING_PROMPT_TEMPLATE.format(
        resume_text=resume_text,
        job_title=job.get('title', 'Unknown'),
        company=job.get('company', 'Unknown'),
        location=job.get('location', 'Unknown'),
        posted_date=job.get('posted_date', 'Unknown'),
        job_url=job.get('url', ''),
        description=job.get('description', 'No description available')
    )
    
    try:
        # Call Claude API
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract the text response
        response_text = response.content[0].text
        
        # Parse JSON response
        # Remove any markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        result = json.loads(response_text.strip())
        
        logger.info(f"Scored {job.get('title')} at {job.get('company')}: {result['score']}/100")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        logger.error(f"Response text: {response_text}")
        return {
            "score": 0,
            "reasoning": "Error: Failed to parse scoring response",
            "salary_estimate": "Unknown",
            "remote_type": "Unknown",
            "auto_apply_recommended": False
        }
    except Exception as e:
        logger.error(f"Error scoring job: {e}")
        return {
            "score": 0,
            "reasoning": f"Error during scoring: {str(e)}",
            "salary_estimate": "Unknown",
            "remote_type": "Unknown",
            "auto_apply_recommended": False
        }


def batch_score_jobs(jobs: list[dict], resume_text: str) -> list[dict]:
    """
    Score multiple jobs efficiently.
    
    Args:
        jobs: List of job dictionaries
        resume_text: Oscar's resume content
        
    Returns:
        List of jobs with scores added
    """
    logger.info(f"Batch scoring {len(jobs)} jobs")
    
    scored_jobs = []
    for i, job in enumerate(jobs, 1):
        logger.info(f"Scoring job {i}/{len(jobs)}")
        
        score_result = score_job(job, resume_text)
        
        # Add scoring results to job dict
        job['score'] = score_result['score']
        job['score_reasoning'] = score_result['reasoning']
        job['salary_estimate'] = score_result.get('salary_estimate')
        job['remote_type'] = score_result.get('remote_type')
        job['auto_apply_recommended'] = score_result.get('auto_apply_recommended', False)
        
        scored_jobs.append(job)
    
    logger.info(f"Completed scoring {len(scored_jobs)} jobs")
    return scored_jobs
```

**Requirements**:
- Use Anthropic SDK with `claude-sonnet-4-20250514` model
- Implement robust JSON parsing with fallbacks
- Handle API errors and rate limits gracefully
- Log all scoring decisions for debugging
- Validate that scores are between 0-100
- Extract salary estimates and remote type from descriptions

---

### 7. `main.py` (Application Entry Point)

```python
"""Main application entry point for LinkedIn Job Agent."""

import logging
import time
from datetime import datetime
from pathlib import Path

import config
import database as db
import linkedin_client
import scoring_engine

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_resume() -> str:
    """Load Oscar's resume from file."""
    resume_path = config.RESUME_FILE
    
    if not resume_path.exists():
        logger.error(f"Resume file not found: {resume_path}")
        raise FileNotFoundError(f"Please create resume file at {resume_path}")
    
    with open(resume_path, 'r', encoding='utf-8') as f:
        resume_text = f.read()
    
    logger.info(f"Loaded resume from {resume_path} ({len(resume_text)} characters)")
    return resume_text


def fetch_jobs_from_linkedin() -> list[dict]:
    """
    Fetch jobs from LinkedIn using multiple search strategies.
    
    Returns:
        List of unique jobs
    """
    logger.info("Starting LinkedIn job search")
    all_jobs = []
    job_ids_seen = set()
    
    # Strategy 1: Keyword searches
    for keywords in config.SEARCH_KEYWORDS:
        for location in config.SEARCH_LOCATIONS:
            logger.info(f"Searching: '{keywords}' in '{location}'")
            jobs = linkedin_client.search_jobs(keywords.strip(), location.strip())
            
            # Deduplicate
            for job in jobs:
                job_id = job.get('id') or job.get('linkedin_job_id')
                if job_id and job_id not in job_ids_seen:
                    job_ids_seen.add(job_id)
                    all_jobs.append(job)
            
            time.sleep(2)  # Rate limiting
    
    # Strategy 2: Get recommended jobs
    logger.info("Fetching recommended jobs")
    recommended_jobs = linkedin_client.get_recommended_jobs()
    
    for job in recommended_jobs:
        job_id = job.get('id') or job.get('linkedin_job_id')
        if job_id and job_id not in job_ids_seen:
            job_ids_seen.add(job_id)
            all_jobs.append(job)
    
    logger.info(f"Fetched {len(all_jobs)} unique jobs from LinkedIn")
    return all_jobs


def normalize_job_data(job: dict) -> dict:
    """
    Normalize job data structure for database storage.
    
    Different LinkedIn endpoints may return slightly different structures.
    This function ensures consistency.
    """
    return {
        'linkedin_job_id': job.get('id') or job.get('linkedin_job_id') or job.get('job_id'),
        'title': job.get('title') or job.get('job_title'),
        'company': job.get('company') or job.get('company_name'),
        'url': job.get('url') or job.get('job_url') or job.get('link'),
        'description': job.get('description') or job.get('job_description') or '',
        'location': job.get('location') or job.get('job_location'),
        'remote_type': job.get('remote_type') or job.get('work_type') or 'Unknown',
        'salary_min': job.get('salary_min'),
        'salary_max': job.get('salary_max'),
        'posted_date': job.get('posted_date') or job.get('listed_at')
    }


def run_job_search() -> dict:
    """
    Execute the complete job search and scoring workflow.
    
    Returns:
        Dictionary with run statistics and results
    """
    start_time = time.time()
    
    logger.info("=" * 80)
    logger.info("Starting LinkedIn Job Search Agent")
    logger.info("=" * 80)
    
    try:
        # Initialize database
        db.init_database()
        
        # Create search run record
        search_queries = [
            f"{kw} in {loc}" 
            for kw in config.SEARCH_KEYWORDS 
            for loc in config.SEARCH_LOCATIONS
        ]
        run_id = db.create_search_run(search_queries)
        
        # Load resume
        resume_text = load_resume()
        
        # Fetch jobs from LinkedIn
        linkedin_jobs = fetch_jobs_from_linkedin()
        
        # Process and store jobs
        new_jobs = []
        updated_jobs = []
        
        for job in linkedin_jobs:
            # Normalize job data structure
            normalized_job = normalize_job_data(job)
            
            # Check if job already exists
            linkedin_job_id = normalized_job['linkedin_job_id']
            existing_job = db.get_job_by_linkedin_id(linkedin_job_id)
            
            if existing_job:
                logger.debug(f"Job already exists: {linkedin_job_id}")
                updated_jobs.append(existing_job)
            else:
                # Insert new job
                job_id = db.insert_job(normalized_job)
                normalized_job['id'] = job_id
                new_jobs.append(normalized_job)
        
        logger.info(f"Found {len(new_jobs)} new jobs, {len(updated_jobs)} existing jobs")
        
        # Score new jobs
        if new_jobs:
            logger.info("Starting job scoring phase")
            scored_jobs = scoring_engine.batch_score_jobs(new_jobs, resume_text)
            
            # Update database with scores
            for job in scored_jobs:
                db.update_job_score(
                    job['linkedin_job_id'],
                    job['score'],
                    job['score_reasoning']
                )
        else:
            logger.info("No new jobs to score")
        
        # Get top jobs for report
        top_jobs = db.get_top_jobs(
            limit=config.TOP_JOBS_LIMIT,
            min_score=config.MIN_DISPLAY_SCORE
        )
        
        # Calculate statistics
        duration_seconds = time.time() - start_time
        stats = {
            'jobs_found': len(linkedin_jobs),
            'jobs_new': len(new_jobs),
            'jobs_updated': len(updated_jobs),
            'duration_seconds': duration_seconds
        }
        
        # Complete search run
        db.complete_search_run(run_id, stats)
        
        logger.info("=" * 80)
        logger.info("Job Search Complete")
        logger.info("=" * 80)
        
        return {
            'success': True,
            'run_id': run_id,
            'stats': stats,
            'top_jobs': top_jobs
        }
        
    except Exception as e:
        logger.error(f"Job search failed: {e}", exc_info=True)
        
        # Record failure
        duration_seconds = time.time() - start_time
        if 'run_id' in locals():
            db.complete_search_run(
                run_id,
                {'duration_seconds': duration_seconds},
                error=str(e)
            )
        
        return {
            'success': False,
            'error': str(e),
            'stats': {'duration_seconds': duration_seconds}
        }


def format_score_bar(score: int, max_width: int = 30) -> str:
    """Create a visual score bar."""
    filled = int((score / 100) * max_width)
    bar = "█" * filled + "░" * (max_width - filled)
    return f"{bar} {score}/100"


def generate_console_report(results: dict) -> None:
    """Generate and print a formatted console report."""
    print("\n")
    print("=" * 80)
    print("                   LINKEDIN JOB SEARCH REPORT")
    print(f"                   Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    if not results['success']:
        print("❌ ERROR: Job search failed")
        print(f"   {results.get('error', 'Unknown error')}")
        return
    
    stats = results['stats']
    top_jobs = results['top_jobs']
    
    # Summary section
    print("SEARCH SUMMARY")
    print("-" * 80)
    print(f"• Total Jobs Found: {stats['jobs_found']}")
    print(f"• New Jobs: {stats['jobs_new']}")
    print(f"• Previously Seen: {stats['jobs_updated']}")
    print(f"• Duration: {stats['duration_seconds']:.1f} seconds")
    print()
    
    # Top recommendations
    if top_jobs:
        print("TOP RECOMMENDATIONS")
        print("=" * 80)
        print()
        
        for i, job in enumerate(top_jobs, 1):
            # Determine emoji based on score
            if job['score'] >= 90:
                emoji = "🔥"
            elif job['score'] >= 75:
                emoji = "⭐"
            else:
                emoji = "👍"
            
            print(f"{i}. {emoji} SCORE: {job['score']} - {job['title']} @ {job['company']}")
            print(f"   {format_score_bar(job['score'])}")
            
            # Salary info
            if job.get('salary_min') and job.get('salary_max'):
                print(f"   💰 Salary: ${job['salary_min']:,} - ${job['salary_max']:,}")
            elif job.get('salary_estimate'):
                print(f"   💰 Salary: {job['salary_estimate']}")
            else:
                print(f"   💰 Salary: Not specified")
            
            # Location info
            print(f"   📍 Location: {job.get('location', 'Unknown')} ({job.get('remote_type', 'Unknown')})")
            
            # URL
            print(f"   🔗 URL: {job['url']}")
            
            # Reasoning
            if job.get('score_reasoning'):
                print(f"   💡 {job['score_reasoning']}")
            
            print()
    else:
        print("No jobs found matching your criteria (score >= 60)")
        print()
    
    # Score distribution
    print("SCORE DISTRIBUTION")
    print("-" * 80)
    distribution = db.get_score_distribution()
    
    if distribution:
        print(f"90-100 (Excellent): {distribution.get('excellent', 0):3d} jobs  {'█' * (distribution.get('excellent', 0) // 2)}")
        print(f"75-89  (Strong):    {distribution.get('strong', 0):3d} jobs  {'█' * (distribution.get('strong', 0) // 2)}")
        print(f"60-74  (Good):      {distribution.get('good', 0):3d} jobs  {'█' * (distribution.get('good', 0) // 2)}")
        print(f"45-59  (Moderate):  {distribution.get('moderate', 0):3d} jobs  {'█' * (distribution.get('moderate', 0) // 2)}")
        print(f"<45    (Poor):      {distribution.get('poor', 0):3d} jobs  {'█' * (distribution.get('poor', 0) // 2)}")
    
    print()
    print("=" * 80)
    print()


def main():
    """Application entry point."""
    logger.info("LinkedIn Job Agent starting")
    
    try:
        # Run the job search
        results = run_job_search()
        
        # Generate console report
        generate_console_report(results)
        
        # Exit with appropriate code
        exit(0 if results['success'] else 1)
        
    except KeyboardInterrupt:
        logger.info("Job search interrupted by user")
        print("\n\n⚠️  Job search interrupted by user")
        exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n\n❌ Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
```

**Requirements**:
- Implement complete workflow orchestration
- Handle all errors gracefully
- Provide detailed logging
- Generate human-readable console output
- Track execution statistics
- Support keyboard interruption

---

## Resume File Setup

Create `resume/oscar_resume.txt` with Oscar's resume content:

```txt
# Oscar Giller - Software Engineer Resume

## Contact Information
- Email: gilleroscar@gmail.com
- Location: New York, NY 10002
- LinkedIn: linkedin.com/in/joscargiller

## Professional Experience

### JP MORGAN CHASE - Software Engineer (June 2023 - Present)
- Developed full-stack internal application for real-time data retrieval, monitoring, and visualization of 1,000+ internal applications using Azure OpenAI
- Created executive dashboard with React, TypeScript, Python, and DynamoDB for Product, Engineering, and Operations teams
- Wrote KQL queries from Azure LAW logs for Grafana dashboards to visualize cloud data and monitor Microsoft OpenAI service instability
- Monitored errors, quota consumption, latency, token consumption, and generated proactive alerts for production issues
- Supported active OpenAI deployments in Azure, managing quota, capacity, and custom content filters via Terraform and Jenkins
- Automated collection of OpenAI onboarding data from ServiceNow tickets to reduce manual team workload
- Consolidated user usage data from multiple sources into unified database

### JP MORGAN CHASE - Software Engineering Intern (June 2022 - September 2022)
- Created business analytics monitoring (BAM) application using Java Spring Boot
- Monitored internal data pipelines to increase response time to security failures
- Designed relational databases in H2 using data design best practices
- Collaborated with team on iterative design and stakeholder expectation management

### STATUS SOLUTIONS - Software Development Intern (June 2021 - September 2021)
- Modernized front-end legacy code to fix web design bugs
- Increased customer satisfaction and reduced technical debt
- Learned PHP and SQL on the fly to drive immediate impact
- Presented business results summary to stakeholders

### FACILITIES MANAGEMENT EXPRESS - Software Development Intern (June 2020 - September 2020)
- Developed automated QA testing suite for UI/UX interaction using Selenium IDE
- Created robust and maintainable test suite architecture with Jest
- Saved QA engineer ~30% of time during product update cycles

## Technical Skills

### Languages
Python, Java, TypeScript, JavaScript, HTML, SQL, KQL, Groovy, PHP, Bash, C, C#, C++, Terraform

### Frameworks & Libraries
OpenAI API, Azure OpenAI, React, Spring Boot, Pandas, PyTorch, Jenkins

### Tools & Platforms
Azure, AWS, DynamoDB, H2, ServiceNow, Grafana, Jules, Docker

### Concepts
Distributed Systems, Image Processing, Databases, Statistics, Machine Learning, Cloud Computing

## Education
Bucknell University - B.S. Computer Science (Graduated)
Location: Lewisburg, PA

## Key Strengths
- Strong experience with Azure OpenAI and AI/ML applications in production
- Full-stack development with modern frameworks (React, TypeScript, Python)
- Cloud platform expertise (Azure, AWS)
- Data engineering and monitoring (KQL, Grafana, DynamoDB)
- Infrastructure as Code (Terraform, Jenkins)
- Proven ability to learn new technologies quickly
- Experience working with enterprise-scale applications (1,000+ apps monitored)
```

---

## Testing & Validation Checklist

### Before First Run
- [ ] LinkedIn cookie obtained and added to `.env`
- [ ] Anthropic API key added to `.env`
- [ ] Resume file created at `resume/oscar_resume.txt`
- [ ] All Python dependencies installed
- [ ] Docker installed and running
- [ ] LinkedIn MCP server Docker image pulled

### First Test Run
- [ ] Database initializes without errors
- [ ] LinkedIn MCP connection successful
- [ ] At least 10 jobs retrieved from LinkedIn
- [ ] All jobs successfully stored in database
- [ ] Claude API scoring works for at least one job
- [ ] Console report generates and displays

### Validation Checks
- [ ] Top-scoring jobs make intuitive sense
- [ ] Score breakdown aligns with criteria
- [ ] Remote/hybrid/on-site classification accurate
- [ ] Salary estimates reasonable
- [ ] Company reputation scores logical
- [ ] No duplicate jobs in database
- [ ] All database fields populated correctly

### Error Handling Tests
- [ ] Handles invalid LinkedIn cookie gracefully
- [ ] Handles Claude API rate limits
- [ ] Handles missing job descriptions
- [ ] Handles database connection failures
- [ ] Handles MCP server timeouts

---

## Usage Instructions

### Initial Setup
```bash
# 1. Create project directory
mkdir linkedin-job-agent
cd linkedin-job-agent

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install anthropic python-dotenv

# 4. Pull LinkedIn MCP Docker image
docker pull stickerdaniel/linkedin-mcp-server:latest

# 5. Create directory structure
mkdir -p data logs resume

# 6. Create configuration files
touch .env
# Add your credentials to .env (see .env section above)

# 7. Add your resume
# Create resume/oscar_resume.txt with your resume content
```

### Running the Agent
```bash
# Activate virtual environment
source venv/bin/activate

# Run the agent
python main.py
```

### Expected Output
```
2025-01-19 08:00:00 - __main__ - INFO - LinkedIn Job Agent starting
2025-01-19 08:00:01 - database - INFO - Initializing database at ./data/jobs.db
2025-01-19 08:00:01 - database - INFO - Database initialized successfully
2025-01-19 08:00:02 - linkedin_client - INFO - Searching jobs: keywords='software engineer', location='Remote', limit=50
2025-01-19 08:00:10 - linkedin_client - INFO - Found 47 jobs for query: software engineer
...

================================================================================
                   LINKEDIN JOB SEARCH REPORT
                   Run Date: 2025-01-19 08:05:32
================================================================================

SEARCH SUMMARY
--------------------------------------------------------------------------------
• Total Jobs Found: 127
• New Jobs: 43
• Previously Seen: 84
• Duration: 332.4 seconds

TOP RECOMMENDATIONS
================================================================================

1. 🔥 SCORE: 96 - Senior AI Engineer @ Google
   ██████████████████████████████ 96/100
   💰 Salary: $180,000 - $250,000
   📍 Location: Remote (US) (Remote)
   🔗 URL: https://linkedin.com/jobs/view/123456789
   💡 Excellent match - Remote role at FAANG with strong AI focus,
      salary well above target, and perfect level match for SWE2.

...
```

---

## Future Enhancements (Post-MVP)

### Phase 2: Email Notifications
- Integrate SendGrid or AWS SES
- HTML email template
- Daily digest emails at 6 AM
- Include top jobs with scores and links

### Phase 3: Application Automation
- Playwright browser automation
- "Easy Apply" detection and submission
- Custom question answering with Claude
- Safety limits (max applications per day)
- Application tracking in database

### Phase 4: Scheduling
- Cron job setup for daily runs
- GitHub Actions workflow
- Cloud hosting (AWS EC2, DigitalOcean)

### Phase 5: MCP Server Wrapper
- Wrap entire system as MCP server
- Enable Claude.ai / ChatGPT interaction
- Commands like "apply to top 3 jobs"
- Real-time job search queries

### Phase 6: Learning & Optimization
- Track which jobs lead to interviews
- Adjust scoring weights based on outcomes
- A/B test different application materials
- Salary negotiation guidance

---

## Troubleshooting Guide

### LinkedIn MCP Server Issues

**Problem**: "Cookie invalid" error
- **Solution**: Get a fresh LinkedIn cookie and update `.env`
- **Note**: LinkedIn cookies expire ~30 days

**Problem**: MCP server timeout
- **Solution**: Check Docker is running, increase timeout, try again

**Problem**: "Rate limited" errors
- **Solution**: Add delays between searches, reduce search frequency

### Database Issues

**Problem**: "Database locked" error
- **Solution**: Ensure no other process is accessing the database

**Problem**: Duplicate jobs appearing
- **Solution**: Check `linkedin_job_id` normalization logic

### Scoring Issues

**Problem**: All scores are very low
- **Solution**: Review scoring criteria, check if resume loaded correctly

**Problem**: Claude API rate limits
- **Solution**: Add delays between API calls, reduce batch size

**Problem**: JSON parse errors from Claude
- **Solution**: Check prompt template, add more robust JSON extraction

### General Issues

**Problem**: No jobs found
- **Solution**: Check search keywords, verify LinkedIn cookie, check MCP server logs

**Problem**: Missing salary information
- **Solution**: This is expected for many jobs; scoring handles this with default points

---

## Success Metrics

After running the MVP successfully, you should see:

- **20-50 new jobs** found per run
- **5-10 jobs scoring 75+** (strong matches)
- **1-3 jobs scoring 90+** (excellent matches)
- **Complete run time** under 10 minutes
- **No crashes or fatal errors**

---

## Notes for Claude Coding Agent

### Code Style Guidelines
- Use type hints for all function parameters and returns
- Include docstrings for all functions
- Use descriptive variable names
- Add comments for complex logic
- Follow PEP 8 style guide

### Error Handling
- Wrap all external API calls in try-except
- Log all errors with context
- Provide graceful degradation
- Never crash the entire program for single job failures

### Performance Considerations
- Batch operations where possible
- Add rate limiting between API calls
- Cache results when appropriate
- Use database indices for common queries

### Security
- Never commit `.env` file
- Never log sensitive data (cookies, API keys)
- Use environment variables for all credentials

### Testing
- Test each module independently first
- Test with small batches before full runs
- Validate all database operations
- Check edge cases (missing data, API errors, etc.)

---

## Project Completion Definition

The MVP is considered complete when:

1. ✅ All Python modules implemented and tested
2. ✅ Database schema created and operational
3. ✅ LinkedIn MCP server integration working
4. ✅ Claude API scoring functional
5. ✅ Console report generates correctly
6. ✅ At least one successful end-to-end run
7. ✅ Top 20 jobs displayed with accurate scores
8. ✅ All error handling in place
9. ✅ Documentation complete
10. ✅ Ready for daily automated runs

---

## Contact & Support

For issues or questions:
- GitHub Issues: [linkedin-mcp-server issues](https://github.com/stickerdaniel/linkedin-mcp-server/issues)
- Anthropic API Docs: [docs.anthropic.com](https://docs.anthropic.com)

Good luck building your job search agent! 🚀
