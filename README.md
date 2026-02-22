# LinkedIn Job Search Agent

An AI-powered job search automation system that leverages the LinkedIn MCP server to discover jobs, scores them against user preferences using Claude AI, and generates personalized recommendations.

## Overview

This agent automatically:
1. Searches LinkedIn for relevant job postings
2. Scores each job against your specific requirements using Claude AI
3. Stores results in a local database with deduplication
4. Generates detailed reports with top recommendations

## Quick Start

### 1. Prerequisites

- Python 3.12+
- Docker installed and running
- LinkedIn account (for cookie)
- OpenAI API key

### 2. Installation

```bash
# Clone or create the project directory
cd JobApp_Agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Pull LinkedIn MCP Docker image
docker pull stickerdaniel/linkedin-mcp-server:latest
```

### 3. Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
# Get your LinkedIn cookie (li_at value):
# 1. Log into LinkedIn in your browser
# 2. Open DevTools (F12) → Application → Cookies → https://www.linkedin.com
# 3. Copy the value of the 'li_at' cookie
LINKEDIN_COOKIE=your_li_at_cookie_value_here

# Get your OpenAI API key from https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=1000
```

### 4. Customize Your Resume

Edit `resume/oscar_resume.txt` with your own resume content. This is used by Claude to match jobs to your experience.

### 5. Run the Agent

```bash
python main.py
```

## How It Works

### Job Scoring System (0-100 points)

Jobs are scored based on 5 criteria:

1. **Remote Work Flexibility (30 points)**
   - Remote: 30 points
   - Hybrid (NYC): 20 points
   - On-site (NYC): 10 points
   - On-site (Other): 0 points

2. **Salary Range (35 points)**
   - $165k+: 35 points (excellent)
   - $150k-164k: 28 points (good)
   - $140k-149k: 20 points (acceptable)
   - $130k-139k: 10 points (marginal)
   - Below $130k: 0 points

3. **Company Type (20 points)**
   - FAANG: 20 points
   - Big Tech: 18 points
   - Tech Unicorns: 15 points
   - Top Finance: 14 points
   - Other: 5-10 points

4. **AI/ML Relevance (10 points)**
   - Primary focus: 10 points
   - Significant component: 7 points
   - Some work: 4 points
   - None: 0 points

5. **Title/Level Match (5 points)**
   - SWE II: 5 points
   - Mid-level: 4 points
   - Senior: 3 points
   - Junior: 0 points

### Score Interpretation

- **90-100**: Excellent match - Top priority
- **75-89**: Strong match - Definitely review and apply
- **60-74**: Good match - Review carefully
- **45-59**: Moderate match - Consider if aligned
- **<45**: Poor match - Archive

## Project Structure

```
JobApp_Agent/
├── config.py              # Configuration management
├── database.py            # SQLite database operations
├── linkedin_client.py     # LinkedIn MCP server interface
├── scoring_engine.py      # Claude AI job scoring
├── main.py                # Main application entry point
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── .env.example           # Environment template
├── .gitignore             # Git ignore rules
├── data/
│   └── jobs.db           # SQLite database (auto-created)
├── logs/
│   └── agent.log         # Application logs (auto-created)
└── resume/
    └── oscar_resume.txt  # Your resume for job matching
```

## Configuration Options

All configuration is done via the `.env` file:

```env
# OpenAI Configuration
OPENAI_MODEL=gpt-4o              # Model to use (gpt-4o, gpt-4o-mini, gpt-4-turbo, etc.)
OPENAI_TEMPERATURE=0.3           # Lower = more deterministic (0.0-2.0)
OPENAI_MAX_TOKENS=1000           # Max tokens for response

# Search Configuration
SEARCH_KEYWORDS=software engineer,ai engineer,machine learning engineer
SEARCH_LOCATIONS=Remote,New York
MAX_RESULTS_PER_SEARCH=50

# Scoring Configuration
MIN_DISPLAY_SCORE=60
TOP_JOBS_LIMIT=20

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/agent.log
```

### Available OpenAI Models

- **gpt-4o** (default) - Latest GPT-4 Omni, best quality, ~$2.50/M input tokens
- **gpt-4o-mini** - Faster and cheaper, ~$0.15/M input tokens, good quality
- **gpt-4-turbo** - Previous generation, ~$10/M input tokens
- **gpt-3.5-turbo** - Cheapest option, ~$0.50/M input tokens, lower quality

**Recommendation**: Use `gpt-4o-mini` for cost savings with minimal quality loss.

## Troubleshooting

### LinkedIn Cookie Issues

**Problem**: "Cookie invalid" error
- **Solution**: LinkedIn cookies expire every ~30 days. Get a fresh cookie:
  1. Log into LinkedIn in your browser
  2. F12 → Application → Cookies → https://www.linkedin.com
  3. Copy the `li_at` cookie value
  4. Update your `.env` file

### Docker Issues

**Problem**: "Docker not found" or timeout errors
- **Solution**: Ensure Docker is running
  ```bash
  docker ps  # Should list running containers
  ```

### No Jobs Found

**Problem**: Zero jobs returned from search
- **Solution**: Check:
  1. LinkedIn cookie is valid
  2. Search keywords are appropriate
  3. LinkedIn account is in good standing
  4. Check logs for detailed errors

### Claude API Errors

**Problem**: Rate limits or API errors
- **Solution**:
  1. Check your Anthropic API key is valid
  2. Ensure you have available credits
  3. Add delays between API calls if needed

## Future Enhancements

- Email notifications for new high-scoring jobs
- Automated application submission for "Easy Apply" jobs
- Daily automated runs via cron/scheduled tasks
- Web dashboard for viewing results
- Application tracking and follow-up management

## Database Schema

The agent uses SQLite to store jobs and track search runs. Two main tables:

### jobs
- Stores all discovered jobs with scores and metadata
- Deduplicates based on `linkedin_job_id`
- Tracks status: new, reviewed, applied, rejected, archived

### search_runs
- Logs each execution of the agent
- Tracks statistics and performance metrics
- Useful for debugging and optimization

## Security Notes

- Never commit `.env` file to version control
- Keep your LinkedIn cookie secure
- Keep your Anthropic API key secure
- Rotate credentials regularly

## License

Private project for personal use.

## Support

For issues with:
- LinkedIn MCP Server: [GitHub Issues](https://github.com/stickerdaniel/linkedin-mcp-server/issues)
- Anthropic API: [Documentation](https://docs.anthropic.com)
