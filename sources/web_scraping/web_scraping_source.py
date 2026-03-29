"""Web scraping job source using pluggable discovery providers.

This module provides job discovery through multiple providers:
- JobSpy: Aggregates from Indeed, Google Jobs, LinkedIn, etc.
- Google Search: Finds jobs on Greenhouse, Lever, Ashby via search
- Brave Search: Uses Brave Search API for ATS job boards (recommended)

Jobs discovered with full data (from JobSpy) skip scraping.
Jobs discovered as URLs only are scraped using platform-specific scrapers.
"""

import logging
import os
import time
import hashlib
from typing import List, Dict, Optional

from ..base_source import BaseJobSource
from .scrapers import get_scraper

logger = logging.getLogger(__name__)


class WebScrapingSource(BaseJobSource):
    """Job source using pluggable discovery providers + scraping.

    This source uses a DiscoveryManager to find jobs from multiple providers,
    then uses platform-specific scrapers to extract full job details when needed.

    Discovery Providers:
        - JobSpy: Returns full job data (no scraping needed)
        - Google Search: Returns URLs (scraping needed) - may get rate limited
        - Brave Search: Returns URLs via Brave API (recommended)

    Scrapers (for URL-only discoveries):
        - GreenhouseScraper
        - LeverScraper
        - BambooHRScraper
        - AshbyScraper
    """

    def __init__(
        self,
        enabled_platforms: List[str] = None,
        enabled_discovery_providers: List[str] = None,
        scraping_delay: float = 2.0,
        location_filter: List[str] = None,
        jobspy_sites: List[str] = None,
        jobspy_hours_old: int = 72,
        # Google Search mode configuration
        search_mode: str = 'combined',
        level_terms: List[str] = None,
        exclude_terms: List[str] = None,
        # Legacy parameters (backward compatibility)
        vertex_ai_project_id: Optional[str] = None,
        vertex_ai_search_engine_id: Optional[str] = None,
        company_registry_path: Optional[str] = None
    ):
        """Initialize WebScrapingSource with discovery providers.

        Args:
            enabled_platforms: ATS platforms to search via Google Search
                (greenhouse, lever, bamboohr, ashby)
            enabled_discovery_providers: Discovery providers to use
                (jobspy, google_search)
            scraping_delay: Delay between scraping requests (seconds)
            location_filter: List of locations to filter results
                (e.g., ['Remote', 'New York'])
            jobspy_sites: Sites for JobSpy to search
                (indeed, google, linkedin, glassdoor, zip_recruiter)
            jobspy_hours_old: Only return jobs from last N hours (JobSpy)
            search_mode: Google Search query mode
                (default, mid_level, exclude_senior, combined)
            level_terms: Level II terms to search for in mid_level/combined modes
            exclude_terms: Seniority terms to exclude in exclude_senior/combined modes
            vertex_ai_project_id: LEGACY - no longer used
            vertex_ai_search_engine_id: LEGACY - no longer used
            company_registry_path: LEGACY - no longer used
        """
        self.enabled_platforms = enabled_platforms or [
            'greenhouse', 'lever', 'bamboohr', 'ashby'
        ]
        self.scraping_delay = scraping_delay
        self.jobspy_sites = jobspy_sites or ['indeed', 'google']
        self.jobspy_hours_old = jobspy_hours_old
        self.search_mode = search_mode
        self.level_terms = level_terms
        self.exclude_terms = exclude_terms

        # Initialize discovery manager
        self.discovery_manager = self._create_discovery_manager(
            enabled_providers=enabled_discovery_providers or ['jobspy', 'google_search'],
            location_filter=location_filter
        )

    def _create_discovery_manager(
        self,
        enabled_providers: List[str],
        location_filter: Optional[List[str]]
    ):
        """Create and configure the discovery manager.

        Args:
            enabled_providers: List of provider names to enable
            location_filter: Optional location filter

        Returns:
            Configured DiscoveryManager instance
        """
        from .discovery import DiscoveryManager

        manager = DiscoveryManager()

        # Add JobSpy provider
        if 'jobspy' in enabled_providers:
            try:
                from .discovery.jobspy_provider import JobSpyProvider
                manager.add_provider(JobSpyProvider(
                    default_sites=self.jobspy_sites,
                    default_hours_old=self.jobspy_hours_old
                ))
                logger.info(
                    f"Added JobSpy provider (sites={self.jobspy_sites}, "
                    f"hours_old={self.jobspy_hours_old})"
                )
            except ImportError:
                logger.warning(
                    "JobSpy provider not available: python-jobspy not installed"
                )

        # Add Google Search provider
        if 'google_search' in enabled_providers:
            try:
                from .discovery.google_search_provider import GoogleSearchProvider
                manager.add_provider(GoogleSearchProvider(
                    platforms=self.enabled_platforms,
                    search_mode=self.search_mode,
                    level_terms=self.level_terms,
                    exclude_terms=self.exclude_terms
                ))
                logger.info(
                    f"Added Google Search provider (platforms={self.enabled_platforms}, "
                    f"mode='{self.search_mode}')"
                )
            except ImportError:
                logger.warning(
                    "Google Search provider not available: "
                    "googlesearch-python not installed"
                )

        # Add Brave Search provider
        if 'brave_search' in enabled_providers:
            try:
                from .discovery.brave_search_provider import BraveSearchProvider
                api_key = os.getenv('BRAVE_API_KEY')
                if api_key:
                    # Get freshness filter (defaults to 'week' to reduce stale URLs)
                    freshness = os.getenv('BRAVE_SEARCH_FRESHNESS', 'week')
                    # Empty string means no filter
                    freshness = freshness if freshness else None

                    manager.add_provider(BraveSearchProvider(
                        api_key=api_key,
                        platforms=self.enabled_platforms,
                        search_mode=self.search_mode,
                        level_terms=self.level_terms,
                        exclude_terms=self.exclude_terms,
                        freshness=freshness
                    ))
                    logger.info(
                        f"Added Brave Search provider (platforms={self.enabled_platforms}, "
                        f"mode='{self.search_mode}', freshness='{freshness or 'none'}')"
                    )
                else:
                    logger.warning(
                        "Brave Search provider enabled but BRAVE_API_KEY not set"
                    )
            except ImportError as e:
                logger.warning(
                    f"Brave Search provider not available: {e}"
                )

        # Add SerpAPI provider
        if 'serpapi' in enabled_providers:
            try:
                from .discovery.serpapi_provider import SerpAPIProvider
                api_key = os.getenv('SERPAPI_API_KEY')
                if api_key:
                    # Get unified location terms (falls back to provider defaults)
                    location_terms_raw = os.getenv('LOCATION_TERMS', '')
                    location_terms = [
                        loc.strip() for loc in location_terms_raw.split(',')
                        if loc.strip()
                    ] or None

                    # Get target site
                    target_site = os.getenv('SERPAPI_TARGET_SITE', 'greenhouse.io')

                    # Get max pages (each page = 10 results = 1 API credit)
                    try:
                        max_pages = int(os.getenv('SERPAPI_PAGES', '5'))
                        max_pages = min(max(max_pages, 1), 10)
                    except ValueError:
                        max_pages = 5

                    # Get recency filter
                    recency = os.getenv('SERPAPI_RECENCY', '') or None

                    manager.add_provider(SerpAPIProvider(
                        api_key=api_key,
                        search_mode=self.search_mode,
                        level_terms=self.level_terms,
                        exclude_terms=self.exclude_terms,
                        location_terms=location_terms,
                        target_site=target_site,
                        max_pages=max_pages,
                        recency=recency
                    ))
                    logger.info(
                        f"Added SerpAPI provider (site={target_site}, "
                        f"mode='{self.search_mode}', "
                        f"max_pages={max_pages} ({max_pages * 10} results), "
                        f"recency={recency or 'none'}, "
                        f"locations={location_terms or 'defaults'})"
                    )
                else:
                    logger.warning(
                        "SerpAPI provider enabled but SERPAPI_API_KEY not set"
                    )
            except ImportError as e:
                logger.warning(
                    f"SerpAPI provider not available: {e}"
                )

        # Add Greenhouse API provider (direct API polling)
        if 'greenhouse_api' in enabled_providers:
            try:
                from .discovery.greenhouse_api_provider import GreenhouseAPIProvider
                greenhouse_enabled = os.getenv('GREENHOUSE_API_ENABLED', 'true').lower() == 'true'
                use_curated = os.getenv('GREENHOUSE_POLL_CURATED', 'true').lower() == 'true'

                if greenhouse_enabled:
                    manager.add_provider(GreenhouseAPIProvider(
                        use_curated=use_curated
                    ))
                    logger.info(
                        f"Added Greenhouse API provider (curated={use_curated})"
                    )
                else:
                    logger.info("Greenhouse API provider disabled via GREENHOUSE_API_ENABLED")
            except ImportError as e:
                logger.warning(
                    f"Greenhouse API provider not available: {e}"
                )

        # Add location filter if specified
        if location_filter:
            from .discovery.filters import create_location_filter
            manager.add_filter(create_location_filter(location_filter))
            logger.info(f"Added location filter: {location_filter}")

        return manager

    @property
    def source_name(self) -> str:
        return 'web_scraping'

    @property
    def consolidates_locations(self) -> bool:
        """Check if any discovery provider consolidates locations."""
        for provider in self.discovery_manager.providers:
            if getattr(provider, 'consolidates_locations', False):
                return True
        return False

    def search_jobs(self, keywords: str, location: str = None, **kwargs) -> List[Dict]:
        """Search for jobs using discovery providers + scraping.

        Process:
        1. Run all discovery providers to find jobs
        2. For jobs with full data (JobSpy): use directly
        3. For jobs with URLs only: scrape for details
        4. Normalize and return all results

        Args:
            keywords: Job keywords (e.g., "software engineer")
            location: Location filter (e.g., "Remote", "New York")
            **kwargs: Additional options
                - max_results: Maximum total results
                - jobspy_sites: Override JobSpy sites
                - hours_old: Override JobSpy hours_old

        Returns:
            List of normalized job dictionaries
        """
        all_jobs = []
        urls_seen = set()

        max_results = kwargs.get('max_results', 100)

        logger.info(
            f"Searching jobs: keywords='{keywords}', location='{location}', "
            f"max_results={max_results}"
        )

        # Step 1: Discover jobs using all providers
        try:
            discovered = self.discovery_manager.discover_all(
                keywords=keywords,
                location=location,
                max_results=max_results,
                sites=kwargs.get('jobspy_sites', self.jobspy_sites),
                hours_old=kwargs.get('hours_old', self.jobspy_hours_old)
            )
        except Exception as e:
            logger.error(f"Discovery error: {e}", exc_info=True)
            return []

        if not discovered:
            logger.warning("No jobs discovered from any provider")
            return []

        logger.info(f"Discovered {len(discovered)} jobs from all providers")

        # Step 2: Process each discovered job
        jobs_with_full_data = 0
        jobs_scraped = 0
        jobs_failed = 0

        for job in discovered:
            # Skip if we've already seen this URL
            if job.url in urls_seen:
                continue
            urls_seen.add(job.url)

            try:
                if job.has_full_data:
                    # Job already has full data (from JobSpy) - use directly
                    normalized = self._process_full_job(job)
                    if normalized:
                        all_jobs.append(normalized)
                        jobs_with_full_data += 1
                else:
                    # Job has URL only - need to scrape for details
                    normalized = self._scrape_and_process(job)
                    if normalized:
                        all_jobs.append(normalized)
                        jobs_scraped += 1
                    else:
                        jobs_failed += 1

            except Exception as e:
                logger.error(f"Error processing job {job.url}: {e}")
                jobs_failed += 1
                continue

        logger.info(
            f"Processed {len(all_jobs)} jobs: "
            f"{jobs_with_full_data} with full data, "
            f"{jobs_scraped} scraped, "
            f"{jobs_failed} failed"
        )

        return all_jobs

    def _process_full_job(self, job) -> Optional[Dict]:
        """Process a job that already has full data.

        Args:
            job: DiscoveredJob with full data

        Returns:
            Normalized job dictionary
        """
        job_data = {
            'job_id': self._extract_job_id(job.url),
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'description': job.description,
            'url': job.url,
            'salary_min': job.salary_min,
            'salary_max': job.salary_max,
            'posted_date': job.posted_date,
        }

        normalized = self.normalize_job(job_data)
        normalized['source'] = job.source_platform or 'jobspy'

        logger.debug(
            f"Processed full job: {job.title} at {job.company} ({job.source_platform})"
        )

        return normalized

    def _scrape_and_process(self, job) -> Optional[Dict]:
        """Scrape a job URL and process the result.

        Args:
            job: DiscoveredJob with URL only

        Returns:
            Normalized job dictionary, or None if scraping failed
        """
        # Get appropriate scraper for this URL
        scraper = get_scraper(job.url)

        if not scraper:
            logger.debug(f"No scraper found for URL: {job.url}")
            return None

        logger.debug(f"Scraping {scraper.platform_name} job: {job.url}")

        try:
            job_data = scraper.scrape_job(job.url)

            if not job_data:
                logger.debug(f"Scraper returned no data for {job.url}")
                return None

            normalized = self.normalize_job(job_data)
            normalized['source'] = scraper.platform_name

            logger.debug(
                f"Scraped: {job_data.get('title')} at {job_data.get('company')}"
            )

            # Polite delay between scrapes
            time.sleep(self.scraping_delay)

            return normalized

        except Exception as e:
            logger.error(f"Scraping error for {job.url}: {e}")
            return None

    def _extract_job_id(self, url: str) -> str:
        """Extract or generate a job ID from URL.

        Args:
            url: Job posting URL

        Returns:
            Job ID string
        """
        # Try to get scraper and use its ID extraction
        scraper = get_scraper(url)
        if scraper:
            try:
                job_id = scraper.extract_job_id(url)
                if job_id:
                    return job_id
            except Exception:
                pass

        # Fallback: hash the URL
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def is_available(self) -> bool:
        """Check if at least one discovery provider is available."""
        available_providers = self.discovery_manager.get_available_providers()

        if not available_providers:
            logger.warning(
                "Web scraping source not available: no discovery providers configured. "
                "Install python-jobspy and/or googlesearch-python"
            )
            return False

        provider_names = [p.provider_name for p in available_providers]
        logger.debug(f"Web scraping source available with providers: {provider_names}")
        return True


# Register this source
from .. import register_source
register_source('web_scraping')(WebScrapingSource)
