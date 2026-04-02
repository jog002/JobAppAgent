# Job Search Agent

An AI-powered job search automation system that discovers jobs from multiple sources, scores them against your resume using Claude/OpenAI, and generates personalized recommendations.

## What It Does

1. **Discovers jobs** from ATS platforms (Greenhouse, Lever, Ashby) and job aggregators (Indeed, Google Jobs)
2. **Scores each job** against your resume using AI (0-100 score)
3. **Stores results** in a database with deduplication
4. **Generates reports** with top recommendations

## Quick Start

```bash
# 1. Clone and setup
cd JobApp_Agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your Claude API key

# 3. Add your resume
# Edit resume/oscar_resume.txt with your resume

# 4. Run
python main.py
```

## Configuration

All configuration is in `.env`. See `.env.example` for all options with inline documentation.

### Required Settings

```env
LLM_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-your-key-here
```

### Key Options

| Setting | Default | Description |
|---------|---------|-------------|
| `SEARCH_KEYWORDS` | software engineer | Comma-separated job titles to search |
| `SEARCH_LOCATIONS` | Remote,New York | Comma-separated locations |
| `MIN_DISPLAY_SCORE` | 60 | Minimum AI score to show (0-100) |
| `DATABASE_MODE` | local | `local` (SQLite) or `turso` (cloud) |

## Discovery Providers

The agent uses multiple providers to find jobs. All are free.

### Direct API Polling (Recommended)

These poll company job boards directly. No rate limits, complete job data.

| Provider | Companies | Enable/Disable |
|----------|-----------|----------------|
| Greenhouse API | 250+ tech companies | `GREENHOUSE_API_ENABLED=true` |
| Lever API | 80+ tech companies | `LEVER_API_ENABLED=true` |
| Ashby API | 50+ tech companies | `ASHBY_API_ENABLED=true` |

### Job Aggregators

| Provider | Description | Config |
|----------|-------------|--------|
| JobSpy | Aggregates Indeed, Google Jobs | `JOBSPY_SITES=indeed,google` |
| SerpAPI | Google Search for job URLs | `SERPAPI_API_KEY` (250 free/month) |
| Brave Search | Backup URL discovery | `BRAVE_API_KEY` (2000 free/month) |

### Default Configuration

```env
ENABLED_DISCOVERY_PROVIDERS=greenhouse_api,lever_api,ashby_api,serpapi,jobspy
```

## Job Scoring (0-100 points)

Jobs are scored based on 5 criteria:

| Criteria | Points | Description |
|----------|--------|-------------|
| Remote Work | 30 | Remote=30, Hybrid=20, On-site=10 |
| Salary | 35 | Based on your target range |
| Company Type | 20 | FAANG/Big Tech/Unicorn tiers |
| AI/ML Relevance | 10 | Based on job description |
| Title Match | 5 | SWE II/Mid-level targeting |

### Score Interpretation

- **90-100**: Top priority - apply immediately
- **75-89**: Strong match - definitely apply
- **60-74**: Good match - review carefully
- **<60**: Lower match - filtered out by default

## Database Options

### Local SQLite (default)

```env
DATABASE_MODE=local
DATABASE_PATH=./data/jobs.db
```

### Turso Cloud Database

For persistence across environments or CI/CD:

```env
DATABASE_MODE=turso
TURSO_DATABASE_URL=libsql://your-db.turso.io
TURSO_AUTH_TOKEN=your-token
```

Setup:
```bash
# Install Turso CLI
curl -sSfL https://get.tur.so/install.sh | bash

# Create database
turso db create jobagent
turso db show jobagent --url
turso db tokens create jobagent
```

## Running Modes

```bash
# Interactive mode - run once
python main.py

# Batch mode - for automation/cron
python main.py batch
```

## Project Structure

```
JobApp_Agent/
├── main.py                 # Entry point
├── config.py               # Configuration
├── database.py             # Database operations
├── scoring_engine.py       # AI job scoring
├── sources/
│   ├── web_scraping/       # Main job source
│   │   ├── discovery/      # Job discovery providers
│   │   └── scrapers/       # ATS-specific scrapers
│   └── linkedin/           # Legacy LinkedIn source
├── resume/
│   └── oscar_resume.txt    # Your resume
├── data/
│   └── jobs.db             # SQLite database
└── logs/
    └── agent.log           # Application logs
```

## Troubleshooting

### No Jobs Found

1. Check logs: `tail -f logs/agent.log`
2. Verify API keys are set correctly
3. Try running with `LOG_LEVEL=DEBUG`

### API Errors

- **Claude/OpenAI**: Verify API key and credits
- **SerpAPI**: Check monthly quota (250 free)
- **Brave Search**: Check monthly quota (2000 free)

---

## Legacy Features

These features are deprecated but still functional if needed.

### LinkedIn MCP Server

The LinkedIn source requires Docker and a LinkedIn cookie. It has rate limiting issues and is not recommended.

```env
# Enable LinkedIn source
ENABLED_SOURCES=web_scraping,linkedin

# Method 1: Cookie-based
LINKEDIN_COOKIE=your-li_at-cookie

# Method 2: Session file
LINKEDIN_SESSION_PATH=/path/to/session.json
```

Setup:
```bash
docker pull stickerdaniel/linkedin-mcp-server:latest
```

### Google Search Provider

Removed due to CAPTCHA and rate limiting issues. Use SerpAPI or Brave Search instead.

### Scheduled Batch Jobs (macOS)

If you previously set up scheduled runs, uninstall with:

```bash
# Unload the launchd agent
launchctl unload ~/Library/LaunchAgents/com.oscar.jobagent.batch.plist
rm ~/Library/LaunchAgents/com.oscar.jobagent.batch.plist

# Cancel the wake schedule
sudo pmset repeat cancel

# Verify removal
pmset -g sched
launchctl list | grep jobagent
```
