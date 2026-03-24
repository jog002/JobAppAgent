"""Main application entry point for Multi-Source Job Agent."""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Handle batch mode env file loading BEFORE importing config
# This ensures batch.env is loaded before config evaluates its values
if '--batch' in sys.argv or (len(sys.argv) > 1 and sys.argv[1] == 'batch'):
    from dotenv import load_dotenv
    batch_env_path = Path(__file__).parent / "batch.env"
    if batch_env_path.exists():
        load_dotenv(batch_env_path, override=True)
        print(f"[Batch Mode] Loaded config from {batch_env_path}")
    else:
        print(f"[Batch Mode] Warning: {batch_env_path} not found, using default .env")
        load_dotenv(override=True)

import config
from config import (
    LLM_PROVIDER,
    CLAUDE_INPUT_COST_PER_M, CLAUDE_OUTPUT_COST_PER_M,
    OPENAI_INPUT_COST_PER_M, OPENAI_OUTPUT_COST_PER_M
)
import database as db
import scoring_engine
from email_reporter import create_email_reporter_from_config

# Import sources
from sources import get_enabled_sources

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


def fetch_jobs_from_all_sources() -> list[dict]:
    """
    Fetch jobs from all enabled sources.

    Returns:
        List of unique jobs from all sources
    """
    logger.info("Starting multi-source job search")
    all_jobs = []
    job_signatures_seen = set()  # (source, job_id) tuples

    try:
        enabled_sources = get_enabled_sources(config)
        logger.info(f"Enabled sources: {[s.source_name for s in enabled_sources]}")
    except Exception as e:
        logger.error(f"Failed to get enabled sources: {e}")
        return []

    for source in enabled_sources:
        source_name = source.source_name

        if not source.is_available():
            logger.warning(f"Source {source_name} not available, skipping")
            continue

        logger.info(f"Searching {source_name}...")

        try:
            # Search with each keyword/location combination
            for keywords in config.SEARCH_KEYWORDS:
                # Check if source consolidates all locations into a single query
                if source.consolidates_locations:
                    # Provider handles all locations in one query (e.g., SerpAPI with OR groups)
                    logger.info(f"  {source_name}: '{keywords}' (all locations consolidated)")
                    jobs = source.search_jobs(keywords.strip(), None)

                    # Deduplicate across sources using (source, job_id) tuple
                    for job in jobs:
                        job_source = job.get('source', source_name)
                        job_id = job.get('job_id')

                        if not job_id:
                            logger.warning(f"Job missing job_id, skipping: {job.get('title')} at {job.get('url')}")
                            continue

                        signature = (job_source, job_id)
                        if signature not in job_signatures_seen:
                            job_signatures_seen.add(signature)
                            all_jobs.append(job)

                    time.sleep(config.SCRAPING_DELAY_SECONDS)  # Rate limiting
                else:
                    # Traditional per-location search
                    for location in config.SEARCH_LOCATIONS:
                        logger.info(f"  {source_name}: '{keywords}' in '{location}'")
                        jobs = source.search_jobs(keywords.strip(), location.strip())

                        # Deduplicate across sources using (source, job_id) tuple
                        for job in jobs:
                            job_source = job.get('source', source_name)
                            job_id = job.get('job_id')

                            # All scrapers now generate fallback IDs, so job_id should never be None
                            # But keep the check for safety in case of scraping errors
                            if not job_id:
                                logger.warning(f"Job missing job_id, skipping: {job.get('title')} at {job.get('url')}")
                                continue

                            signature = (job_source, job_id)
                            if signature not in job_signatures_seen:
                                job_signatures_seen.add(signature)
                                all_jobs.append(job)

                        time.sleep(config.SCRAPING_DELAY_SECONDS)  # Rate limiting

        except Exception as e:
            logger.error(f"Error searching {source_name}: {e}", exc_info=True)

    logger.info(f"Fetched {len(all_jobs)} unique jobs from {len(enabled_sources)} sources")
    return all_jobs


def normalize_job_data(job: dict) -> dict:
    """
    Normalize job data structure for database storage.

    Jobs from different sources may have slightly different structures.
    This function ensures consistency while preserving source information.
    """
    return {
        'source': job.get('source', 'unknown'),
        'job_id': job.get('job_id') or job.get('id') or job.get('linkedin_job_id'),
        'linkedin_job_id': job.get('linkedin_job_id') or job.get('id') or job.get('job_id'),  # Backward compatibility
        'title': job.get('title') or job.get('job_title'),
        'company': job.get('company') or job.get('company_name'),
        'url': job.get('url') or job.get('job_url') or job.get('link'),
        'description': job.get('description') or job.get('job_description') or '',
        'location': job.get('location') or job.get('job_location') or '',
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
    logger.info("Starting Multi-Source Job Search Agent")
    logger.info("=" * 80)

    try:
        # Initialize database (includes migration)
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

        # Fetch jobs from all enabled sources
        all_jobs = fetch_jobs_from_all_sources()

        # Process and store jobs
        new_jobs = []
        updated_jobs = []

        for job in all_jobs:
            # Normalize job data structure
            normalized_job = normalize_job_data(job)

            # Check if job already exists (by source + job_id)
            source = normalized_job.get('source')
            job_id = normalized_job.get('job_id')
            existing_job = db.get_job_by_source_and_id(source, job_id)

            if existing_job:
                logger.debug(f"Job already exists: {source}/{job_id}")
                updated_jobs.append(existing_job)
            else:
                # Insert new job with run_id for tracking
                # insert_job returns None if job is filtered out (location, seniority, etc.)
                db_job_id = db.insert_job(normalized_job, run_id=run_id)
                if db_job_id is not None:
                    normalized_job['id'] = db_job_id
                    new_jobs.append(normalized_job)
                # Filtered jobs are not added to new_jobs and won't be scored

        logger.info(f"Found {len(new_jobs)} new jobs, {len(updated_jobs)} existing jobs")

        # Score new jobs
        if new_jobs:
            logger.info("Starting job scoring phase")
            scored_jobs = scoring_engine.batch_score_jobs(new_jobs, resume_text)

            # Update database with scores
            for job in scored_jobs:
                db.update_job_score(
                    job.get('source', 'unknown'),
                    job.get('job_id'),
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
        token_stats = scoring_engine.get_token_usage()
        stats = {
            'jobs_found': len(all_jobs),
            'jobs_new': len(new_jobs),
            'jobs_updated': len(updated_jobs),
            'duration_seconds': duration_seconds,
            'tokens_used': token_stats.total_tokens,
            'prompt_tokens': token_stats.prompt_tokens,
            'completion_tokens': token_stats.completion_tokens,
            'api_calls': token_stats.api_calls
        }

        # Complete search run
        db.complete_search_run(run_id, stats)

        logger.info("=" * 80)
        logger.info("Job Search Complete")
        logger.info("=" * 80)

        # Get run number for display
        run_info = db.get_run_info(run_id)
        run_number = run_info.get('run_number', run_id) if run_info else run_id

        return {
            'success': True,
            'run_id': run_id,
            'run_number': run_number,
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
    run_number = results.get('run_number', '?')
    print("=" * 80)
    print("                   MULTI-SOURCE JOB SEARCH REPORT")
    print(f"                   Run #{run_number} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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

    # Token usage section
    if stats.get('tokens_used'):
        print()
        print("OPENAI API USAGE")
        print("-" * 80)
        print(f"• Total Tokens: {stats['tokens_used']:,}")
        print(f"• Prompt Tokens: {stats['prompt_tokens']:,}")
        print(f"• Completion Tokens: {stats['completion_tokens']:,}")
        print(f"• API Calls: {stats['api_calls']}")
        if LLM_PROVIDER == "claude":
            est_cost = (stats['prompt_tokens'] * CLAUDE_INPUT_COST_PER_M + stats['completion_tokens'] * CLAUDE_OUTPUT_COST_PER_M) / 1000000
        else:
            est_cost = (stats['prompt_tokens'] * OPENAI_INPUT_COST_PER_M + stats['completion_tokens'] * OPENAI_OUTPUT_COST_PER_M) / 1000000
        print(f"• Estimated Cost: ${est_cost:.4f}")
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


def rerank_jobs(min_score: int = 0, limit: int = 100) -> dict:
    """
    Rescore existing jobs in the database using the current scoring criteria.

    Args:
        min_score: Only rescore jobs with current score >= this value (0 = all)
        limit: Maximum number of jobs to rescore

    Returns:
        Dictionary with reranking statistics
    """
    start_time = time.time()

    logger.info("=" * 80)
    logger.info("Starting Job Reranking")
    logger.info("=" * 80)

    try:
        # Initialize database
        db.init_database()

        # Reset token usage for this run
        scoring_engine.reset_token_usage()

        # Load resume
        resume_text = load_resume()

        # Get jobs to rescore
        jobs = db.get_jobs_for_reranking(min_score=min_score, limit=limit)

        if not jobs:
            logger.info("No jobs found to rescore")
            return {
                'success': True,
                'jobs_rescored': 0,
                'stats': {'duration_seconds': 0}
            }

        logger.info(f"Rescoring {len(jobs)} jobs")

        # Track score changes
        score_changes = []

        for i, job in enumerate(jobs, 1):
            logger.info(f"Rescoring job {i}/{len(jobs)}: {job['title']} at {job['company']}")

            old_score = job.get('score', 0)

            # Score the job
            score_result = scoring_engine.score_job(job, resume_text)
            new_score = score_result['score']

            # Update database
            db.update_job_score(
                job.get('source', 'unknown'),
                job.get('job_id'),
                new_score,
                score_result['reasoning']
            )

            score_changes.append({
                'title': job['title'],
                'company': job['company'],
                'old_score': old_score,
                'new_score': new_score,
                'change': new_score - old_score
            })

        # Calculate statistics
        duration_seconds = time.time() - start_time
        token_stats = scoring_engine.get_token_usage()

        stats = {
            'jobs_rescored': len(jobs),
            'duration_seconds': duration_seconds,
            'tokens_used': token_stats.total_tokens,
            'prompt_tokens': token_stats.prompt_tokens,
            'completion_tokens': token_stats.completion_tokens,
            'api_calls': token_stats.api_calls
        }

        logger.info("=" * 80)
        logger.info("Reranking Complete")
        logger.info("=" * 80)

        return {
            'success': True,
            'stats': stats,
            'score_changes': score_changes
        }

    except Exception as e:
        logger.error(f"Reranking failed: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'stats': {'duration_seconds': time.time() - start_time}
        }


def generate_rerank_report(results: dict) -> None:
    """Generate and print a formatted reranking report."""
    print("\n")
    print("=" * 80)
    print("                   JOB RERANKING REPORT")
    print(f"                   Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    if not results['success']:
        print("❌ ERROR: Reranking failed")
        print(f"   {results.get('error', 'Unknown error')}")
        return

    stats = results['stats']
    score_changes = results.get('score_changes', [])

    # Summary section
    print("RERANKING SUMMARY")
    print("-" * 80)
    print(f"• Jobs Rescored: {stats['jobs_rescored']}")
    print(f"• Duration: {stats['duration_seconds']:.1f} seconds")
    print()

    # Token usage
    if stats.get('tokens_used'):
        print("OPENAI API USAGE")
        print("-" * 80)
        print(f"• Total Tokens: {stats['tokens_used']:,}")
        print(f"• Prompt Tokens: {stats['prompt_tokens']:,}")
        print(f"• Completion Tokens: {stats['completion_tokens']:,}")
        print(f"• API Calls: {stats['api_calls']}")
        if LLM_PROVIDER == "claude":
            est_cost = (stats['prompt_tokens'] * CLAUDE_INPUT_COST_PER_M + stats['completion_tokens'] * CLAUDE_OUTPUT_COST_PER_M) / 1000000
        else:
            est_cost = (stats['prompt_tokens'] * OPENAI_INPUT_COST_PER_M + stats['completion_tokens'] * OPENAI_OUTPUT_COST_PER_M) / 1000000
        print(f"• Estimated Cost: ${est_cost:.4f}")
        print()

    # Score changes
    if score_changes:
        print("SCORE CHANGES")
        print("-" * 80)

        # Sort by change magnitude
        score_changes.sort(key=lambda x: abs(x['change']), reverse=True)

        increased = [c for c in score_changes if c['change'] > 0]
        decreased = [c for c in score_changes if c['change'] < 0]
        unchanged = [c for c in score_changes if c['change'] == 0]

        print(f"• Increased: {len(increased)} jobs")
        print(f"• Decreased: {len(decreased)} jobs")
        print(f"• Unchanged: {len(unchanged)} jobs")
        print()

        # Show top changes
        if len(score_changes) > 0:
            print("TOP CHANGES:")
            for change in score_changes[:10]:
                if change['change'] > 0:
                    symbol = "📈"
                elif change['change'] < 0:
                    symbol = "📉"
                else:
                    symbol = "➡️"

                print(f"  {symbol} {change['old_score']} → {change['new_score']} "
                      f"({change['change']:+d}) - {change['title']} @ {change['company']}")

    print()
    print("=" * 80)
    print()


def run_batch_job() -> dict:
    """
    Run a batch job using batch.env configuration.

    This is designed to be called by automated schedulers (launchd, cron).
    It runs the standard job search but:
    - Uses batch.env for configuration (loaded at startup)
    - Logs to batch-specific log files
    - Returns appropriate exit codes for automation

    Returns:
        Dictionary with run results (same as run_job_search)
    """
    logger.info("=" * 80)
    logger.info("Starting BATCH Job Search")
    logger.info(f"Using config from batch.env")
    logger.info("=" * 80)

    # Run the standard job search
    results = run_job_search()

    # Generate console report (will be captured in batch logs)
    generate_console_report(results)

    # Send email report if configured
    email_reporter = create_email_reporter_from_config()
    if email_reporter:
        new_jobs_this_run = db.get_jobs_from_run(results.get('run_id'), limit=10)
        top_jobs_overall = results.get('top_jobs', [])[:10]

        email_sent = email_reporter.send_report(
            run_number=results.get('run_number', 0),
            new_jobs=new_jobs_this_run,
            top_jobs_overall=top_jobs_overall,
            stats=results.get('stats', {}),
            success=results.get('success', False),
            error=results.get('error')
        )
        if email_sent:
            logger.info("Batch email report sent successfully")
        else:
            logger.warning("Failed to send batch email report")

    return results


def main():
    """Application entry point."""
    parser = argparse.ArgumentParser(
        description='Multi-Source Job Search Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  (default)   Run job search and score new jobs
  rerank      Rescore existing jobs with current scoring criteria
  batch       Run job search using batch.env config (for scheduled automation)

Examples:
  python main.py              # Run normal job search
  python main.py rerank       # Rescore all jobs in database
  python main.py rerank --min-score 60 --limit 50  # Rescore top 50 jobs with score >= 60
  python main.py batch        # Run batch job with batch.env config
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        default='search',
        choices=['search', 'rerank', 'batch'],
        help='Command to run (default: search)'
    )

    parser.add_argument(
        '--min-score',
        type=int,
        default=0,
        help='For rerank: only rescore jobs with score >= this value (default: 0 = all)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='For rerank: maximum number of jobs to rescore (default: 100)'
    )

    args = parser.parse_args()

    logger.info("Multi-Source Job Agent starting")

    try:
        if args.command == 'rerank':
            # Reset token usage at start of run
            scoring_engine.reset_token_usage()

            # Run reranking
            results = rerank_jobs(min_score=args.min_score, limit=args.limit)
            generate_rerank_report(results)

        elif args.command == 'batch':
            # Reset token usage at start of run
            scoring_engine.reset_token_usage()

            # Run batch job (uses batch.env loaded at startup)
            results = run_batch_job()

        else:
            # Reset token usage at start of run
            scoring_engine.reset_token_usage()

            # Run the job search
            results = run_job_search()
            generate_console_report(results)

            # Send email report if configured
            email_reporter = create_email_reporter_from_config()
            if email_reporter:
                new_jobs_this_run = db.get_jobs_from_run(results.get('run_id'), limit=10)
                top_jobs_overall = results.get('top_jobs', [])[:10]

                email_sent = email_reporter.send_report(
                    run_number=results.get('run_number', 0),
                    new_jobs=new_jobs_this_run,
                    top_jobs_overall=top_jobs_overall,
                    stats=results.get('stats', {}),
                    success=results.get('success', False),
                    error=results.get('error')
                )
                if email_sent:
                    print("📧 Email report sent successfully!")
                else:
                    print("⚠️  Failed to send email report (check logs)")

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
