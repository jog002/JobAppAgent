"""JobSpy discovery provider for aggregated job search.

JobSpy is an open-source library that scrapes job postings from multiple
job aggregators including Indeed, Google Jobs, LinkedIn, Glassdoor, and ZipRecruiter.

Key features:
- Returns FULL job data (title, company, description, salary, etc.)
- Jobs from JobSpy don't need additional scraping
- ~1,000 jobs per search limit
- Indeed works best (no rate limiting)
- LinkedIn has aggressive rate limiting (proxies recommended)

GitHub: https://github.com/speedyapply/JobSpy
"""

import logging
import time
import random
from typing import List, Optional

from .base_provider import BaseDiscoveryProvider, DiscoveredJob

logger = logging.getLogger(__name__)


class JobSpyProvider(BaseDiscoveryProvider):
    """Discovery provider using the JobSpy library.

    JobSpy aggregates job postings from multiple platforms:
    - indeed: Works best, no rate limiting
    - google: Google Jobs aggregator
    - linkedin: Aggressive rate limiting, use proxies
    - glassdoor: Works but may require proxies
    - zip_recruiter: Works well

    Attributes:
        default_sites: Default sites to search if none specified
        default_country: Default country for Indeed searches
        default_hours_old: Default age filter for job postings

    Example:
        provider = JobSpyProvider()
        jobs = provider.discover(
            keywords='software engineer',
            location='Remote',
            max_results=50,
            sites=['indeed', 'google']
        )
    """

    # Sites that work well without proxies
    DEFAULT_SITES = ['indeed', 'google']

    def __init__(
        self,
        default_sites: Optional[List[str]] = None,
        default_country: str = 'USA',
        default_hours_old: int = 72,
        max_retries: int = 3,
        base_delay: float = 5.0
    ):
        """Initialize JobSpy provider.

        Args:
            default_sites: Sites to search by default.
                Options: 'indeed', 'google', 'linkedin', 'glassdoor', 'zip_recruiter'
            default_country: Country for Indeed searches (default: 'USA')
            default_hours_old: Only return jobs posted within this many hours
            max_retries: Maximum number of retries on rate limit errors
            base_delay: Base delay in seconds for exponential backoff
        """
        self.default_sites = default_sites or self.DEFAULT_SITES
        self.default_country = default_country
        self.default_hours_old = default_hours_old
        self.max_retries = max_retries
        self.base_delay = base_delay

    @property
    def provider_name(self) -> str:
        return 'jobspy'

    def discover(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_results: int = 50,
        sites: Optional[List[str]] = None,
        hours_old: Optional[int] = None,
        **kwargs
    ) -> List[DiscoveredJob]:
        """Discover jobs using JobSpy.

        Args:
            keywords: Search keywords (e.g., "software engineer")
            location: Location filter (e.g., "Remote", "New York")
            max_results: Maximum results to return (capped at ~1000 per search)
            sites: List of sites to search (overrides default_sites)
                Options: 'indeed', 'google', 'linkedin', 'glassdoor', 'zip_recruiter'
            hours_old: Only return jobs posted within this many hours
            **kwargs: Additional options passed to jobspy.scrape_jobs()

        Returns:
            List of DiscoveredJob objects with full job data.
        """
        try:
            from jobspy import scrape_jobs
        except ImportError:
            logger.error(
                "JobSpy not installed. Install with: pip install python-jobspy"
            )
            return []

        sites = sites or self.default_sites
        hours_old = hours_old or self.default_hours_old

        logger.info(
            f"JobSpy searching: keywords='{keywords}', location='{location}', "
            f"sites={sites}, max_results={max_results}"
        )

        # Try each site individually with retry logic to handle rate limiting
        all_jobs = []
        seen_urls = set()

        for site in sites:
            jobs_from_site = self._search_with_retry(
                site=site,
                keywords=keywords,
                location=location,
                max_results=max_results,
                hours_old=hours_old,
                scrape_jobs_func=scrape_jobs,
                **kwargs
            )

            for job in jobs_from_site:
                if job.url not in seen_urls:
                    seen_urls.add(job.url)
                    all_jobs.append(job)

            # Add delay between sites to avoid rate limiting
            if site != sites[-1]:
                delay = self.base_delay + random.uniform(0, 2)
                logger.debug(f"Waiting {delay:.1f}s before next site")
                time.sleep(delay)

        logger.info(f"JobSpy total: {len(all_jobs)} unique jobs from {len(sites)} sites")
        return all_jobs

    def _search_with_retry(
        self,
        site: str,
        keywords: str,
        location: Optional[str],
        max_results: int,
        hours_old: int,
        scrape_jobs_func,
        **kwargs
    ) -> List[DiscoveredJob]:
        """Search a single site with retry logic for rate limiting.

        Args:
            site: Site to search (indeed, google, etc.)
            keywords: Search keywords
            location: Location filter
            max_results: Maximum results
            hours_old: Hours old filter
            scrape_jobs_func: The jobspy scrape_jobs function
            **kwargs: Additional options

        Returns:
            List of DiscoveredJob objects
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"JobSpy searching {site} (attempt {attempt + 1}/{self.max_retries})")

                jobs_df = scrape_jobs_func(
                    site_name=[site],
                    search_term=keywords,
                    location=location or self.default_country,
                    results_wanted=min(max_results, 100),
                    hours_old=hours_old,
                    country_indeed=self.default_country,
                    **kwargs
                )

                if jobs_df is None or jobs_df.empty:
                    logger.info(f"JobSpy {site}: no results")
                    return []

                logger.info(f"JobSpy {site}: {len(jobs_df)} jobs found")

                discovered = []
                for _, row in jobs_df.iterrows():
                    job = self._row_to_discovered_job(row)
                    if job and job.url:
                        discovered.append(job)

                return discovered

            except Exception as e:
                error_str = str(e).lower()

                # Check for rate limiting (429 or similar)
                is_rate_limit = (
                    '429' in error_str or
                    'rate limit' in error_str or
                    'too many requests' in error_str or
                    'blocked' in error_str
                )

                if is_rate_limit and attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    delay = (self.base_delay * (2 ** attempt)) + random.uniform(0, 5)
                    logger.warning(
                        f"Rate limited by {site}. Waiting {delay:.1f}s before retry "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"JobSpy {site} error: {e}")
                    return []

        return []

    def _row_to_discovered_job(self, row) -> Optional[DiscoveredJob]:
        """Convert a JobSpy DataFrame row to DiscoveredJob.

        Args:
            row: A pandas Series from JobSpy results.

        Returns:
            DiscoveredJob with data extracted from row.
        """
        try:
            # Get URL - required field
            url = self._get_field(row, 'job_url')
            if not url:
                url = self._get_field(row, 'link')
            if not url:
                return None

            # Extract salary if available
            salary_min = None
            salary_max = None

            min_amount = self._get_field(row, 'min_amount')
            max_amount = self._get_field(row, 'max_amount')

            if min_amount is not None:
                try:
                    salary_min = float(min_amount)
                except (ValueError, TypeError):
                    pass

            if max_amount is not None:
                try:
                    salary_max = float(max_amount)
                except (ValueError, TypeError):
                    pass

            # Get source platform
            site = self._get_field(row, 'site')

            return DiscoveredJob(
                url=url,
                title=self._get_field(row, 'title'),
                company=self._get_field(row, 'company'),
                location=self._get_field(row, 'location'),
                description=self._get_field(row, 'description'),
                source_platform=site,
                salary_min=salary_min,
                salary_max=salary_max,
                posted_date=self._get_field(row, 'date_posted'),
                metadata={
                    'job_type': self._get_field(row, 'job_type'),
                    'is_remote': self._get_field(row, 'is_remote'),
                    'company_url': self._get_field(row, 'company_url'),
                    'company_industry': self._get_field(row, 'company_industry'),
                }
            )

        except Exception as e:
            logger.debug(f"Error converting JobSpy row: {e}")
            return None

    def _get_field(self, row, field_name: str) -> Optional[str]:
        """Safely get a field from a DataFrame row.

        Args:
            row: pandas Series
            field_name: Name of field to get

        Returns:
            Field value as string, or None if missing/NaN
        """
        try:
            if field_name not in row.index:
                return None

            value = row[field_name]

            # Handle pandas NaN/None
            import pandas as pd
            if pd.isna(value):
                return None

            # Convert to string and strip whitespace
            return str(value).strip() if value else None

        except Exception:
            return None

    def is_available(self) -> bool:
        """Check if JobSpy is installed and available."""
        try:
            import jobspy
            return True
        except ImportError:
            logger.debug("JobSpy not available: python-jobspy not installed")
            return False
