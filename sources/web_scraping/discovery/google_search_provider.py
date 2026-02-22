"""Google Search discovery provider for ATS job boards.

This provider uses Google Search to discover job postings on ATS platforms
like Greenhouse, Lever, Ashby, and BambooHR. It's inspired by the approach
used in ghiarishi/job-scraper.

Key features:
- CAN discover obfuscated URLs (job-boards.greenhouse.io/RANDOM)
- Works via Google's public search index
- Returns URLs only (scraping needed for full details)
- May hit Google rate limits on heavy use

This provider searches for job URLs but doesn't extract full job details.
The returned DiscoveredJob objects will have URLs but need scraping.
"""

import logging
import time
import random
from typing import List, Optional
import re

from .base_provider import BaseDiscoveryProvider, DiscoveredJob

logger = logging.getLogger(__name__)


class GoogleSearchProvider(BaseDiscoveryProvider):
    """Discovery provider using Google Search for ATS job boards.

    This provider constructs Google search queries with site: operators
    to find job postings on specific ATS platforms.

    Supports multiple search modes for level-targeted job discovery:
    - 'default': Standard keyword search
    - 'mid_level': Targets SWE II / mid-level roles with OR groups
    - 'exclude_senior': Excludes senior/staff titles with minus operators
    - 'combined': Both targeting and exclusion (recommended)

    Attributes:
        platforms: List of ATS platforms to search
        delay_between_searches: Seconds to wait between searches (rate limiting)
        search_mode: Query construction mode ('default', 'mid_level', 'exclude_senior', 'combined')
        level_terms: Custom level II terms to search for
        exclude_terms: Custom seniority terms to exclude

    Example:
        provider = GoogleSearchProvider(
            platforms=['greenhouse', 'lever'],
            search_mode='combined'
        )
        jobs = provider.discover(
            keywords='software engineer',
            location='Remote',
            max_results=50
        )
    """

    # Platform-specific search patterns
    PLATFORM_QUERIES = {
        'greenhouse': '(site:boards.greenhouse.io OR site:job-boards.greenhouse.io) /jobs/',
        'lever': 'site:jobs.lever.co',
        'ashby': 'site:jobs.ashbyhq.com',
        'bamboohr': 'site:*.bamboohr.com/careers',
    }

    # Default level II terms to target mid-level roles
    DEFAULT_LEVEL_TERMS = [
        'Software Engineer II',
        'Software Engineer 2',
        'Engineer II',
        'SWE II',
        'SWE 2',
        'Mid-Level',
    ]

    # Default seniority terms to exclude
    DEFAULT_EXCLUDE_TERMS = [
        'Senior',
        'Staff',
        'Principal',
        'Lead',
        'Distinguished',
        'Director',
    ]

    # URL patterns to validate results
    PLATFORM_URL_PATTERNS = {
        'greenhouse': [
            r'boards\.greenhouse\.io/.+/jobs/',
            r'job-boards\.greenhouse\.io/.+/jobs/',
            r'greenhouse\.io/embed/job_app',
        ],
        'lever': [
            r'jobs\.lever\.co/.+',
        ],
        'ashby': [
            r'jobs\.ashbyhq\.com/.+',
        ],
        'bamboohr': [
            r'.*\.bamboohr\.com/careers/',
            r'.*\.bamboohr\.com/jobs/',
        ],
    }

    def __init__(
        self,
        platforms: Optional[List[str]] = None,
        delay_between_searches: float = 5.0,  # Increased from 2.0
        search_mode: str = 'combined',
        level_terms: Optional[List[str]] = None,
        exclude_terms: Optional[List[str]] = None,
        max_retries: int = 3,
        base_delay: float = 10.0  # Base delay for exponential backoff
    ):
        """Initialize Google Search provider.

        Args:
            platforms: ATS platforms to search.
                Options: 'greenhouse', 'lever', 'ashby', 'bamboohr'
            delay_between_searches: Seconds to wait between platform searches
                to avoid rate limiting.
            search_mode: Query construction mode.
                Options: 'default', 'mid_level', 'exclude_senior', 'combined'
                - 'default': Standard keyword search (backward compatible)
                - 'mid_level': Add OR group for level II terms
                - 'exclude_senior': Add exclusions (-Senior -Staff etc.)
                - 'combined': Both targeting and exclusion (recommended)
            level_terms: Custom level II terms to search for.
                Defaults to DEFAULT_LEVEL_TERMS.
            exclude_terms: Custom seniority terms to exclude.
                Defaults to DEFAULT_EXCLUDE_TERMS.
            max_retries: Maximum number of retries on rate limit errors
            base_delay: Base delay in seconds for exponential backoff
        """
        self.platforms = platforms or ['greenhouse', 'lever']
        self.delay_between_searches = delay_between_searches
        self.search_mode = search_mode
        self.level_terms = level_terms or self.DEFAULT_LEVEL_TERMS
        self.exclude_terms = exclude_terms or self.DEFAULT_EXCLUDE_TERMS
        self.max_retries = max_retries
        self.base_delay = base_delay

    @property
    def provider_name(self) -> str:
        return 'google_search'

    def discover(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_results: int = 50,
        platforms: Optional[List[str]] = None,
        **kwargs
    ) -> List[DiscoveredJob]:
        """Discover job URLs using Google Search.

        Args:
            keywords: Search keywords (e.g., "software engineer")
            location: Location filter (e.g., "Remote", "New York")
            max_results: Maximum total results to return
            platforms: Override default platforms for this search
            **kwargs: Additional options (not used currently)

        Returns:
            List of DiscoveredJob objects with URLs (needs scraping for details).
        """
        try:
            from googlesearch import search
        except ImportError:
            logger.error(
                "googlesearch-python not installed. "
                "Install with: pip install googlesearch-python"
            )
            return []

        platforms = platforms or self.platforms
        discovered = []
        seen_urls = set()

        # Calculate results per platform
        results_per_platform = max(max_results // len(platforms), 5)

        logger.info(
            f"Google Search: keywords='{keywords}', location='{location}', "
            f"platforms={platforms}, per_platform={results_per_platform}, "
            f"mode='{self.search_mode}'"
        )

        for platform in platforms:
            if platform not in self.PLATFORM_QUERIES:
                logger.warning(f"Unknown platform: {platform}")
                continue

            try:
                # Build search query
                query = self._build_query(platform, keywords, location)
                logger.debug(f"Google query: {query}")

                # Execute search
                urls = self._search_google(
                    query,
                    num_results=results_per_platform,
                    search_func=search
                )

                # Filter and add results
                for url in urls:
                    # Validate URL matches platform pattern
                    if not self._is_valid_job_url(url, platform):
                        logger.debug(f"Skipping non-job URL: {url}")
                        continue

                    # Deduplicate
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    discovered.append(DiscoveredJob(
                        url=url,
                        source_platform=platform
                    ))

                logger.info(f"Found {len(urls)} URLs for platform '{platform}'")

                # Rate limiting between platforms
                if platform != platforms[-1]:
                    time.sleep(self.delay_between_searches)

            except Exception as e:
                logger.error(f"Error searching {platform}: {e}")
                continue

        logger.info(f"Google Search total: {len(discovered)} unique job URLs")
        return discovered

    def _build_query(
        self,
        platform: str,
        keywords: str,
        location: Optional[str]
    ) -> str:
        """Build Google search query for a platform with boolean operators.

        Constructs queries based on search_mode:
        - 'default': site:platform "keywords" "location"
        - 'mid_level': site:platform ("SWE II" OR "Engineer II" ...) "location"
        - 'exclude_senior': site:platform "keywords" -Senior -Staff "location"
        - 'combined': site:platform ("SWE II" OR ...) -Senior -Staff "location"

        Args:
            platform: ATS platform name
            keywords: Job keywords (used in default/exclude_senior modes)
            location: Location filter

        Returns:
            Formatted search query string with boolean operators.
        """
        parts = [self.PLATFORM_QUERIES[platform]]

        # Determine what to search for based on mode
        if self.search_mode in ('mid_level', 'combined'):
            # Build OR group for level II terms
            if self.level_terms:
                level_group = ' OR '.join(f'"{term}"' for term in self.level_terms)
                parts.append(f'({level_group})')
            elif keywords:
                # Fallback to keywords if no level terms
                parts.append(f'"{keywords}"')
        else:
            # Default/exclude_senior: use keywords directly
            if keywords:
                parts.append(f'"{keywords}"')

        # Add exclusions for exclude_senior and combined modes
        if self.search_mode in ('exclude_senior', 'combined'):
            for term in self.exclude_terms:
                parts.append(f'-{term}')

        # Add location if provided
        if location:
            parts.append(f'"{location}"')

        return ' '.join(parts)

    def _search_google(
        self,
        query: str,
        num_results: int,
        search_func
    ) -> List[str]:
        """Execute Google search with retry logic for rate limiting.

        Args:
            query: Search query
            num_results: Number of results to request
            search_func: The googlesearch.search function

        Returns:
            List of URLs from search results.
        """
        for attempt in range(self.max_retries):
            try:
                # Add longer sleep interval to avoid rate limiting
                sleep_interval = 2 + random.uniform(0, 1)

                results = list(search_func(
                    query,
                    num_results=num_results,
                    lang='en',
                    sleep_interval=sleep_interval
                ))
                return results

            except Exception as e:
                error_str = str(e).lower()

                # Check for rate limiting
                is_rate_limit = (
                    '429' in error_str or
                    'rate limit' in error_str or
                    'too many requests' in error_str or
                    'blocked' in error_str or
                    'unusual traffic' in error_str or
                    'captcha' in error_str
                )

                if is_rate_limit and attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    delay = (self.base_delay * (2 ** attempt)) + random.uniform(0, 10)
                    logger.warning(
                        f"Google rate limited. Waiting {delay:.1f}s before retry "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Google search error: {e}")
                    return []

        return []

    def _is_valid_job_url(self, url: str, platform: str) -> bool:
        """Check if URL is a valid job posting for the platform.

        Args:
            url: URL to validate
            platform: Platform to check against

        Returns:
            True if URL matches expected job posting pattern.
        """
        if platform not in self.PLATFORM_URL_PATTERNS:
            return True  # No patterns defined, accept all

        patterns = self.PLATFORM_URL_PATTERNS[platform]

        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True

        return False

    def is_available(self) -> bool:
        """Check if googlesearch-python is installed."""
        try:
            from googlesearch import search
            return True
        except ImportError:
            logger.debug(
                "Google Search provider not available: "
                "googlesearch-python not installed"
            )
            return False
