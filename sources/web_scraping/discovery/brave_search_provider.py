"""Brave Search API discovery provider for ATS job boards.

This provider uses the Brave Search API to discover job postings on ATS platforms,
currently focused on Greenhouse.

Key features:
- Single consolidated query per run (minimizes API calls)
- Proper REST API with documented rate limits (vs scraping Google)
- 2,000 free queries/month
- Supports boolean operators: site:, inpage:, -, OR, "quoted phrases"
- Optional freshness filter for time-based results
- Returns URLs only (scraping needed for full details)

Get your API key at: https://brave.com/search/api/
"""

import logging
import random
import re
import time
from typing import List, Optional

import requests

from .base_provider import BaseDiscoveryProvider, DiscoveredJob

logger = logging.getLogger(__name__)


class BraveSearchProvider(BaseDiscoveryProvider):
    """Discovery provider using Brave Search API for ATS job boards.

    This provider constructs a single consolidated Brave Search query with
    site: and inpage: operators to find job postings on Greenhouse.

    Uses a single API call per run to minimize API usage (2,000 free/month).

    Query format:
        site:greenhouse.io (inpage:"Software Engineer II" OR inpage:"SWE 2" ...)
        -Senior -Staff -Principal -Lead

    Attributes:
        api_key: Brave Search API subscription token
        search_mode: Query construction mode
        level_terms: Custom level II terms to search for (used with inpage:)
        exclude_terms: Custom seniority terms to exclude
        freshness: Time filter (pd=day, pw=week, pm=month, py=year, None=all)

    Example:
        provider = BraveSearchProvider(
            api_key='your_api_key',
            search_mode='combined'
        )
        jobs = provider.discover(
            keywords='software engineer',
            max_results=20
        )
    """

    # Brave Search API endpoint
    API_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

    # Default level II terms to target mid-level roles (used with inpage:)
    DEFAULT_LEVEL_TERMS = [
        'Software Engineer II',
        'Software Engineer 2',
        'SWE II',
        'SWE 2',
    ]

    # Default seniority terms to exclude
    DEFAULT_EXCLUDE_TERMS = [
        'Senior',
        'Staff',
        'Principal',
        'Lead',
    ]

    # URL patterns to validate Greenhouse job URLs
    GREENHOUSE_URL_PATTERNS = [
        r'boards\.greenhouse\.io/.+/jobs/',
        r'job-boards\.greenhouse\.io/.+/jobs/',
        r'greenhouse\.io/embed/job_app',
    ]

    # Valid freshness values
    FRESHNESS_OPTIONS = {
        'day': 'pd',
        'week': 'pw',
        'month': 'pm',
        'year': 'py',
        None: None,  # No filter
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        search_mode: str = 'combined',
        level_terms: Optional[List[str]] = None,
        exclude_terms: Optional[List[str]] = None,
        freshness: Optional[str] = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        # Legacy parameters (ignored, kept for backward compatibility)
        platforms: Optional[List[str]] = None,
        delay_between_searches: float = 1.5,
    ):
        """Initialize Brave Search provider.

        Args:
            api_key: Brave Search API subscription token.
                Get yours at: https://brave.com/search/api/
            search_mode: Query construction mode.
                Options: 'default', 'mid_level', 'exclude_senior', 'combined'
                - 'default': Standard keyword search
                - 'mid_level': Add OR group for level II terms with inpage:
                - 'exclude_senior': Add exclusions (-Senior -Staff etc.)
                - 'combined': Both targeting and exclusion (recommended)
            level_terms: Custom level II terms to search for with inpage:.
                Defaults to DEFAULT_LEVEL_TERMS.
            exclude_terms: Custom seniority terms to exclude.
                Defaults to DEFAULT_EXCLUDE_TERMS.
            freshness: Time filter for results.
                Options: 'day', 'week', 'month', 'year', None (no filter)
                Note: May reduce results as Brave's index timing varies.
            max_retries: Maximum retry attempts for transient failures.
            base_delay: Base delay in seconds for exponential backoff.
            platforms: LEGACY - ignored (always searches Greenhouse only)
            delay_between_searches: LEGACY - ignored (single query now)
        """
        self.api_key = api_key
        self.search_mode = search_mode
        self.level_terms = level_terms or self.DEFAULT_LEVEL_TERMS
        self.exclude_terms = exclude_terms or self.DEFAULT_EXCLUDE_TERMS
        self.freshness = self.FRESHNESS_OPTIONS.get(freshness, None)
        self.max_retries = max_retries
        self.base_delay = base_delay

    @property
    def provider_name(self) -> str:
        return 'brave_search'

    def discover(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_results: int = 20,
        **kwargs
    ) -> List[DiscoveredJob]:
        """Discover job URLs using a single Brave Search API call.

        Makes ONE API call with a consolidated query:
            site:greenhouse.io (inpage:"Software Engineer II" OR inpage:"SWE 2" ...)
            -Senior -Staff -Principal -Lead

        Args:
            keywords: Search keywords (used in 'default' mode only)
            location: Location filter (not currently used - Greenhouse is location-agnostic)
            max_results: Maximum results to return (max 20 per Brave API)
            **kwargs: Additional options:
                - freshness: Override instance freshness setting

        Returns:
            List of DiscoveredJob objects with URLs (needs scraping for details).
        """
        if not self.is_available():
            logger.warning("Brave Search provider not available: API key not set")
            return []

        # Build the consolidated query
        query = self._build_query(keywords)

        # Allow freshness override per-call
        freshness = kwargs.get('freshness', self.freshness)
        if freshness and freshness in self.FRESHNESS_OPTIONS:
            freshness = self.FRESHNESS_OPTIONS[freshness]

        logger.info(
            f"Brave Search: query='{query}', "
            f"max_results={max_results}, "
            f"freshness={freshness or 'none'}"
        )

        try:
            # Single API call
            urls = self._search_brave(query, num_results=max_results, freshness=freshness)

            # Filter and collect valid job URLs
            discovered = []
            seen_urls = set()

            for url in urls:
                # Validate URL is a Greenhouse job posting
                if not self._is_valid_job_url(url):
                    logger.debug(f"Skipping non-job URL: {url}")
                    continue

                # Deduplicate
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                discovered.append(DiscoveredJob(
                    url=url,
                    source_platform='greenhouse'
                ))

            logger.info(f"Brave Search: {len(discovered)} valid Greenhouse job URLs from {len(urls)} results")
            return discovered

        except Exception as e:
            logger.error(f"Brave Search error: {e}")
            return []

    def _build_query(self, keywords: str = None) -> str:
        """Build consolidated Brave Search query for Greenhouse.

        Constructs a single query based on search_mode:
        - 'default': site:greenhouse.io inpage:"keywords"
        - 'mid_level': site:greenhouse.io AND inpage:"SWE II" OR inpage:"SWE 2" ...
        - 'exclude_senior': site:greenhouse.io inpage:"keywords" -Senior -Staff
        - 'combined': site:greenhouse.io AND inpage:"SWE II" OR ... -Senior -Staff

        Note: Brave API breaks with parentheses, so we use AND before first term instead.

        Example output (combined mode):
            site:greenhouse.io AND inpage:"Software Engineer II" OR inpage:"Software Engineer 2"
            OR inpage:"SWE II" OR inpage:"SWE 2" -Senior -Staff -Principal -Lead

        Args:
            keywords: Job keywords (used in default/exclude_senior modes only)

        Returns:
            Formatted search query string with boolean operators.
        """
        parts = ['site:greenhouse.io']

        # Build search terms based on mode
        if self.search_mode in ('mid_level', 'combined'):
            # Build OR group for level II terms with inpage:
            # Note: Brave API breaks with parentheses, use AND before first term instead
            if self.level_terms:
                level_group = ' OR '.join(f'inpage:"{term}"' for term in self.level_terms)
                parts.append(f'AND {level_group}')
            elif keywords:
                # Fallback to keywords if no level terms
                parts.append(f'inpage:"{keywords}"')
        else:
            # Default/exclude_senior: use keywords directly
            if keywords:
                parts.append(f'inpage:"{keywords}"')

        # Add exclusions for exclude_senior and combined modes
        if self.search_mode in ('exclude_senior', 'combined'):
            for term in self.exclude_terms:
                parts.append(f'-{term}')

        return ' '.join(parts)

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter.

        Args:
            attempt: Current attempt number (0-indexed).

        Returns:
            Delay in seconds with exponential backoff and random jitter.
        """
        return (self.base_delay * (2 ** attempt)) + random.uniform(0, 1)

    def _search_brave(
        self,
        query: str,
        num_results: int = 20,
        freshness: Optional[str] = None
    ) -> List[str]:
        """Execute Brave Search API request with retry logic.

        Implements exponential backoff for transient failures including:
        - Network/DNS errors
        - Connection timeouts
        - Rate limiting (429)
        - Server errors (5xx)

        Args:
            query: Search query with boolean operators
            num_results: Number of results to request (max 20 per request)
            freshness: Time filter (pd=day, pw=week, pm=month, py=year)
                Note: May reduce results as Brave's index timing varies.

        Returns:
            List of URLs from search results.
        """
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }

        params = {
            "q": query,
            "count": min(num_results, 20),  # Brave API max is 20 per request
        }

        # Add freshness filter if specified
        if freshness:
            params["freshness"] = freshness

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    self.API_ENDPOINT,
                    headers=headers,
                    params=params,
                    timeout=30
                )

                # Non-retryable: Invalid API key
                if response.status_code == 401:
                    logger.error("Brave Search API: Invalid or missing API key")
                    return []

                # Non-retryable: Bad request
                if response.status_code == 400:
                    logger.error(f"Brave Search API: Bad request - {response.text[:200]}")
                    return []

                # Retryable: Rate limit exceeded
                if response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        logger.warning(
                            f"Brave Search API: Rate limited, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error("Brave Search API: Rate limit exceeded after all retries")
                        return []

                # Retryable: Server errors
                if response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        logger.warning(
                            f"Brave Search API: Server error {response.status_code}, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"Brave Search API: Server error {response.status_code} after all retries"
                        )
                        return []

                response.raise_for_status()

                data = response.json()

                # Extract URLs from web results
                urls = []
                web_results = data.get("web", {}).get("results", [])

                for result in web_results:
                    url = result.get("url")
                    if url:
                        urls.append(url)

                # Log remaining quota if available
                rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
                if rate_limit_remaining:
                    logger.info(f"Brave API rate limit remaining: {rate_limit_remaining}")

                return urls

            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Brave Search API: Network error, "
                        f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Brave Search API: Network error after {self.max_retries} attempts: {e}"
                    )
                    return []

            except requests.exceptions.RequestException as e:
                logger.error(f"Brave Search API error: {e}")
                return []

            except (KeyError, ValueError) as e:
                logger.error(f"Brave Search API: Error parsing response: {e}")
                return []

        return []

    def _is_valid_job_url(self, url: str) -> bool:
        """Check if URL is a valid Greenhouse job posting.

        Args:
            url: URL to validate

        Returns:
            True if URL matches expected Greenhouse job posting pattern.
        """
        for pattern in self.GREENHOUSE_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def is_available(self) -> bool:
        """Check if Brave Search API is configured with an API key."""
        if not self.api_key:
            logger.debug(
                "Brave Search provider not available: "
                "BRAVE_API_KEY not set"
            )
            return False
        return True
