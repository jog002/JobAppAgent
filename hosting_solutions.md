# Hosting Solutions for Scheduled Batch Job

This document contains research and implementation details for running the job search agent on a schedule. Created February 2026.

---

## The Problem

Your scheduled job ran when you opened your laptop instead of at 3 AM because:

1. **FileVault is enabled** on your Mac
2. When the lid closes for extended periods, macOS goes into a deeper sleep/hibernation state
3. FileVault requires user authentication to decrypt the disk before macOS fully boots
4. LaunchAgents cannot run until AFTER you log in because the disk isn't decrypted yet
5. Once you logged in, launchd saw the missed scheduled task and ran it immediately

**This is a fundamental limitation** - FileVault encryption means no scheduled tasks can run without you entering your password first.

---

## Solution Comparison

### Option A: Amphetamine + Login Fallback (Local)

**How it works:**
- Install free [Amphetamine](https://apps.apple.com/app/amphetamine/id937984704) from Mac App Store
- Schedule it to keep Mac awake from 2:55-3:30 AM
- Existing launchd job runs at 3:01 AM
- Add `RunAtLoad` to also run on login as a fallback
- Add lockfile logic so job only runs once per day

| Pros | Cons |
|------|------|
| No ongoing cost ($0/month) | Requires laptop to be plugged in overnight |
| All data stays local | May not work reliably with lid closed |
| No cloud setup required | Extra app to install and configure |
| Works offline | If laptop dies/restarts, misses job |

**Estimated cost:** $0/month

---

### Option B: Login-Only Fallback (Local, Simplest)

**How it works:**
- Remove scheduled time entirely
- Job runs immediately when you log in each morning
- Lockfile ensures it only runs once per 24 hours

| Pros | Cons |
|------|------|
| Simplest setup | Job runs when YOU wake up, not at 3 AM |
| No external dependencies | Results not ready until after login |
| 100% reliable | Less "fresh" data (depends on when you login) |
| No extra apps needed | - |

**Estimated cost:** $0/month

---

### Option C: GitHub Actions (Cloud) - RECOMMENDED

**How it works:**
- Create a GitHub repo (can be private)
- Add workflow file that runs `python main.py batch` on schedule
- Store secrets (API keys) in GitHub Secrets
- Results emailed to you

| Pros | Cons |
|------|------|
| Runs reliably at exact time | Need to upload code to GitHub |
| No laptop required | API keys stored in GitHub (encrypted) |
| 2,000 free minutes/month (private repos) | Some setup complexity |
| Generous free tier | Need network access for job |

**Pricing (2026):**
- **Free tier:** 2,000 minutes/month for private repos ([source](https://docs.github.com/en/actions/concepts/billing-and-usage))
- **Your job:** ~5-10 minutes/run × 30 days = **150-300 min/month** → **$0/month**
- **If exceeded:** ~$0.008/minute for Linux runners
- **Note:** [GitHub reduced hosted runner prices by 39%](https://resources.github.com/actions/2026-pricing-changes-for-github-actions/) as of Jan 1, 2026

---

### Option D: AWS Lambda (Cloud)

**How it works:**
- Deploy Python script as Lambda function
- Use EventBridge (CloudWatch Events) to trigger on schedule
- Lambda runs your job, sends email

| Pros | Cons |
|------|------|
| Extremely generous free tier | More complex setup (IAM, roles, etc.) |
| Runs reliably | Need AWS account |
| Scales infinitely | Learning curve if new to AWS |
| Very cheap beyond free tier | May need to refactor code slightly |

**Pricing (2026):**
- **Free tier (never expires):** 1 million requests + 400,000 GB-seconds/month ([source](https://aws.amazon.com/lambda/pricing/))
- **Your job:** 1 run/day × 30 = 30 requests, ~5 min × 512MB = ~75 GB-sec/month → **$0/month**
- **If exceeded:** $0.20/million requests + $0.0000166667/GB-second
- **Additional:** CloudWatch Logs (5GB free), potential egress charges

---

### Option E: Google Cloud Functions (Cloud)

**How it works:**
- Deploy as Cloud Run function
- Use Cloud Scheduler for timing (3 free jobs/account)
- Similar to Lambda

| Pros | Cons |
|------|------|
| Good free tier | Requires billing account (even for free tier) |
| Cloud Scheduler has 3 free jobs | Slightly less generous than AWS |
| Good Python support | Similar complexity to AWS |

**Pricing (2026):**
- **Free tier:** 2 million invocations + 400,000 GB-seconds/month ([source](https://cloud.google.com/functions/pricing-1stgen))
- **Cloud Scheduler:** 3 jobs free/month ([source](https://cloud.google.com/scheduler/pricing))
- **Your job:** → **$0/month** (easily within free tier)
- **If exceeded:** $0.40/million invocations + compute charges

---

### Option F: Railway.app (Cloud)

**How it works:**
- Deploy app to Railway
- Configure cron schedule in dashboard
- Railway runs your job on schedule

| Pros | Cons |
|------|------|
| Very easy setup | **No permanent free tier** |
| Nice dashboard | $5/month minimum after 30-day trial |
| Built-in cron support | Includes $5 credit (covers light usage) |

**Pricing (2026):**
- **Trial:** $5 credit for 30 days ([source](https://railway.com/pricing))
- **After trial:** **$5/month minimum** (Hobby plan)
- **Usage:** Pay for CPU, memory, egress used
- Your job would likely use <$1 of the $5 credit

---

### Option G: Render.com (Cloud)

**How it works:**
- Deploy as cron job service
- Render runs on your schedule

| Pros | Cons |
|------|------|
| Simple setup | **Cron jobs are not free** |
| Good documentation | Billed by active running time |
| Built-in cron support | Free tier only covers web services |

**Pricing (2026):**
- **Cron jobs:** Billed per second of active running time ([source](https://render.com/docs/cronjobs))
- **Estimate:** ~$3-7/month for daily 5-10 min job
- Free tier only covers static sites and web services (with spin-down)

---

## Recommendation Summary

| Option | Monthly Cost | Reliability | Setup Effort | Best For |
|--------|--------------|-------------|--------------|----------|
| **B: Login fallback** | $0 | Medium | Low | Just want it to work |
| **A: Amphetamine** | $0 | Medium-High | Medium | Want specific time, have power |
| **C: GitHub Actions** | $0 | High | Medium | Already use GitHub |
| **D: AWS Lambda** | $0 | Very High | High | Want bulletproof reliability |
| **E: Google Cloud** | $0 | Very High | High | Prefer Google ecosystem |
| F: Railway | $5/mo | High | Low | Want simplest cloud option |
| G: Render | ~$5/mo | High | Low | Already use Render |

---

## Implementation: GitHub Actions

### GitHub Actions Workflow

**File:** `.github/workflows/batch-job.yml`

```yaml
name: Daily Job Search

on:
  schedule:
    # Run at 3:00 AM EST (8:00 AM UTC)
    # Note: GitHub Actions uses UTC timezone
    - cron: '0 8 * * *'
  workflow_dispatch:  # Allow manual trigger

jobs:
  batch-search:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Create .batch_env from secrets
        run: |
          cat << 'EOF' > .batch_env
          OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}
          OPENAI_MODEL=gpt-4.1
          OPENAI_TEMPERATURE=0.3
          OPENAI_MAX_TOKENS=2000
          DATABASE_PATH=./data/jobs.db
          LOG_LEVEL=INFO
          LOG_FILE=./logs/batch_agent.log
          SEARCH_KEYWORDS=software engineer
          SEARCH_LOCATIONS=Remote,New York
          MAX_RESULTS_PER_SEARCH=50
          MIN_DISPLAY_SCORE=60
          TOP_JOBS_LIMIT=20
          ENABLED_SOURCES=web_scraping
          WEB_SCRAPING_PLATFORMS=greenhouse,lever,bamboohr,ashby
          SCRAPING_DELAY_SECONDS=2.0
          ENABLED_DISCOVERY_PROVIDERS=jobspy,brave_search,serpapi
          BRAVE_API_KEY=${{ secrets.BRAVE_API_KEY }}
          BRAVE_SEARCH_FRESHNESS=day
          JOBSPY_SITES=glassdoor,indeed
          JOBSPY_HOURS_OLD=24
          LOCATION_TERMS=NY,New York,Remote,NYC,Jersey City
          SEARCH_MODE=combined
          LEVEL_TERMS=Software Engineer II,Software Engineer 2,SWE II,SWE 2,Software Developer II,Software Developer 2,Associate Software Engineer
          SERPAPI_API_KEY=${{ secrets.SERPAPI_API_KEY }}
          SERPAPI_PAGES=1
          SERPAPI_RECENCY=day
          SERPAPI_TARGET_SITE=greenhouse.io
          EMAIL_ENABLED=true
          EMAIL_RECIPIENT=${{ secrets.EMAIL_RECIPIENT }}
          SMTP_SERVER=smtp.gmail.com
          SMTP_PORT=587
          SMTP_SENDER_EMAIL=${{ secrets.SMTP_SENDER_EMAIL }}
          SMTP_SENDER_PASSWORD=${{ secrets.SMTP_SENDER_PASSWORD }}
          SMTP_USE_TLS=true
          EOF

      - name: Create required directories
        run: |
          mkdir -p data logs resume

      - name: Copy resume file
        run: |
          echo "${{ secrets.RESUME_CONTENT }}" > resume/oscar_resume.txt

      - name: Run batch job
        run: python main.py batch

      - name: Upload logs as artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: batch-logs-${{ github.run_number }}
          path: logs/
          retention-days: 7
```

### Required GitHub Secrets

Go to your GitHub repo → Settings → Secrets and variables → Actions → New repository secret

| Secret Name | Value |
|-------------|-------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `BRAVE_API_KEY` | Your Brave Search API key |
| `SERPAPI_API_KEY` | Your SerpAPI key |
| `EMAIL_RECIPIENT` | your-email@gmail.com |
| `SMTP_SENDER_EMAIL` | your-email@gmail.com |
| `SMTP_SENDER_PASSWORD` | Your Gmail app password |
| `RESUME_CONTENT` | Contents of your resume file |

### Setup Steps

```bash
# If not already a git repo with remote
git remote add origin https://github.com/YOUR_USERNAME/JobApp_Agent.git

# Create the workflow directory
mkdir -p .github/workflows

# Add and push
git add .github/workflows/batch-job.yml
git commit -m "Add GitHub Actions workflow for daily batch job"
git push origin master
```

### Verification

1. Go to your repo on GitHub
2. Click "Actions" tab
3. You should see "Daily Job Search" workflow
4. Click "Run workflow" → "Run workflow" to test manually
5. Watch the job run and verify email is received

### Important Notes

**Timezone:**
- GitHub Actions cron uses **UTC timezone**
- 3:00 AM EST = 8:00 AM UTC (standard time)
- 3:00 AM EDT = 7:00 AM UTC (daylight saving)
- You may need to adjust the cron expression seasonally

**Database:**
- Each run starts fresh with no existing database
- Same jobs may appear multiple days until filled
- See Database Persistence Options below for alternatives

---

## Database Persistence Options (For Future Reference)

### Option 1: Turso (SQLite Cloud) - Recommended

**Why Turso:**
- SQLite-compatible (minimal code changes to your existing `database.py`)
- Most generous free tier: 5GB storage, 500M reads/month, 10M writes/month
- $4.99/month if you exceed free tier

**Implementation Steps:**

1. **Create Turso Account:**
   - Go to https://turso.tech/
   - Sign up (no credit card required)
   - Create a database: `turso db create jobagent`
   - Get connection URL: `turso db show jobagent --url`
   - Get auth token: `turso db tokens create jobagent`

2. **Install libsql-client:**
   Add to `requirements.txt`:
   ```
   libsql-client
   ```

3. **Modify `database.py`:**
   ```python
   import os
   import libsql_client

   def get_connection():
       turso_url = os.getenv("TURSO_DATABASE_URL")
       turso_token = os.getenv("TURSO_AUTH_TOKEN")

       if turso_url and turso_token:
           # Use Turso cloud database
           return libsql_client.create_client(
               url=turso_url,
               auth_token=turso_token
           )
       else:
           # Fallback to local SQLite
           import sqlite3
           return sqlite3.connect(os.getenv("DATABASE_PATH", "./data/jobs.db"))
   ```

4. **Add GitHub Secrets:**
   - `TURSO_DATABASE_URL`: libsql://jobagent-yourusername.turso.io
   - `TURSO_AUTH_TOKEN`: your-auth-token

5. **Update workflow to include Turso env vars:**
   ```yaml
   TURSO_DATABASE_URL=${{ secrets.TURSO_DATABASE_URL }}
   TURSO_AUTH_TOKEN=${{ secrets.TURSO_AUTH_TOKEN }}
   ```

**Estimated cost:** $0/month (free tier is very generous for this use case)

---

### Option 2: Supabase (PostgreSQL)

**Why Supabase:**
- Full PostgreSQL with web dashboard
- 500MB storage on free tier
- Good ecosystem and documentation

**Downsides:**
- Projects pause after 1 week of inactivity (need to wake manually)
- Requires migrating from SQLite to PostgreSQL
- More complex setup

**Implementation Steps:**

1. **Create Supabase Project:**
   - Go to https://supabase.com/
   - Create new project
   - Get connection string from Settings → Database

2. **Install psycopg2:**
   Add to `requirements.txt`:
   ```
   psycopg2-binary
   ```

3. **Migrate database.py to PostgreSQL:**
   - Replace sqlite3 with psycopg2
   - Update SQL syntax (some SQLite-specific syntax won't work)
   - Create tables in Supabase dashboard or via migration

4. **Add GitHub Secrets:**
   - `DATABASE_URL`: postgresql://postgres:password@host:5432/postgres

**Estimated cost:** $0/month (but requires occasional manual wake-up)

---

### Option 3: GitHub Actions Artifacts (No External DB)

**How it works:**
- Store SQLite database as a GitHub Actions artifact
- Download artifact at start of each run
- Upload updated artifact at end of run
- Artifacts retained for 90 days by default

**Implementation:**

```yaml
- name: Download previous database
  uses: dawidd6/action-download-artifact@v3
  with:
    name: jobs-database
    path: data/
    if_no_artifact_found: ignore

- name: Run batch job
  run: python main.py batch

- name: Upload database for next run
  uses: actions/upload-artifact@v4
  with:
    name: jobs-database
    path: data/jobs.db
    retention-days: 90
```

**Pros:**
- No external service needed
- Free (within GitHub Actions limits)

**Cons:**
- 90-day retention (data lost if no runs for 90 days)
- Artifacts count toward storage limits (500MB free)
- More complex workflow

---

### Database Pricing Summary

| Provider | Free Tier Storage | Free Tier Limits | Paid Price | SQLite Compatible |
|----------|-------------------|------------------|------------|-------------------|
| **Turso** | 5 GB | 500M reads, 10M writes | $4.99/mo | Yes |
| **Supabase** | 500 MB | Pauses after 1 week | $25/mo | No (Postgres) |
| **Neon** | 512 MB | Compute hours limited | $19/mo | No (Postgres) |
| **PlanetScale** | None | N/A | $39/mo | No (MySQL) |
| **GH Artifacts** | 500 MB | 90-day retention | Free | Yes |

---

## Implementation: Local Fallback (Option B)

If you prefer to keep everything local and just run on login:

### Changes to `run_batch.sh`

```bash
#!/bin/bash
# Batch Job Runner with daily deduplication

set -e
cd /Users/oscargiller/Projects/JobApp_Agent

# Only run once per day
LOCKFILE="/tmp/jobagent_batch_$(date +%Y%m%d).lock"
if [ -f "$LOCKFILE" ]; then
    echo "[$(date)] Already ran today, skipping"
    exit 0
fi

echo "=========================================="
echo "Batch job started at: $(date)"
echo "=========================================="

# Create lockfile
touch "$LOCKFILE"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the batch job
caffeinate -is python main.py batch

echo "=========================================="
echo "Batch job completed at: $(date)"
echo "=========================================="

exit 0
```

### Changes to LaunchAgent plist

Add `RunAtLoad` so it runs at login:

```xml
<key>RunAtLoad</key>
<true/>
```

---

## Sources

- [Apple Support - launchd](https://support.apple.com/guide/terminal/script-management-with-launchd-apdc6c1077b-5d5d-4d35-9c19-60f2397b2369/mac)
- [Creating LaunchDaemons and Agents - Apple Developer](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)
- [launchd.info Tutorial](https://www.launchd.info/)
- [Jamf Community - FileVault and Auto Login](https://community.jamf.com/general-discussions-2/auto-login-with-filevault-enabled-29417)
- [GitHub Actions Billing](https://docs.github.com/en/actions/concepts/billing-and-usage)
- [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
- [Google Cloud Functions Pricing](https://cloud.google.com/functions/pricing-1stgen)
- [Turso Pricing](https://turso.tech/pricing)
- [Supabase Pricing](https://supabase.com/pricing)
