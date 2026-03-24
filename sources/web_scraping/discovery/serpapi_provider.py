"""SerpAPI (Google Search) discovery provider for ATS job boards.

This provider uses SerpAPI to access Google Search results for discovering
job postings on ATS platforms like Greenhouse.

Key features:
- Single consolidated query per run (minimizes API credits)
- 250 free queries/month
- Full Google search syntax support (site:, OR, -, "phrases")
- Reliable API with no rate limiting concerns
- Returns URLs only (scraping needed for full details)

Get your API key at: https://serpapi.com/
"""

import logging
import random
import re
import time
from typing import List, Optional

import requests

from .base_provider import BaseDiscoveryProvider, DiscoveredJob

logger = logging.getLogger(__name__)


class SerpAPIProvider(BaseDiscoveryProvider):
    """Discovery provider using SerpAPI for Google Search on ATS job boards.

    This provider constructs a single consolidated Google Search query with
    site: and OR operators to find job postings on Greenhouse.

    Uses a single API call per run to minimize API usage (250 free/month).

    Query format:
        site:greenhouse.io ("Software Engineer II" OR "Software Engineer 2" OR
        "Associate Software Engineer") ("NY" OR "New York" OR "Remote")
        -Senior -Staff -Principal -Lead

    Attributes:
        api_key: SerpAPI API key
        search_mode: Query construction mode
        level_terms: Level II terms to search for
        exclude_terms: Seniority terms to exclude
        location_terms: Location terms to include in query
        target_site: Site to restrict search to (default: greenhouse.io)

    Example:
        provider = SerpAPIProvider(
            api_key='your_api_key',
            search_mode='combined',
            location_terms=['NY', 'New York', 'Remote']
        )
        jobs = provider.discover(keywords='software engineer', max_results=20)
    """

    # SerpAPI endpoint
    API_ENDPOINT = "https://serpapi.com/search"

    # Default level II terms to target mid-level roles
    DEFAULT_LEVEL_TERMS = [
        'Software Engineer II',
        'Software Engineer 2',
        'SWE II',
        'SWE 2',
        'Associate Software Engineer',
    ]

    # Default seniority terms to exclude
    DEFAULT_EXCLUDE_TERMS = [
        'Senior',
        'Staff',
        'Principal',
        'Lead',
    ]

    # Default location terms
    DEFAULT_LOCATION_TERMS = [
        'NY',
        'New York',
        'Remote',
    ]

    # URL patterns to validate Greenhouse job URLs
    GREENHOUSE_URL_PATTERNS = [
        r'boards\.greenhouse\.io/.+/jobs/',
        r'job-boards\.greenhouse\.io/.+/jobs/',
        r'greenhouse\.io/embed/job_app',
    ]

    # Valid recency filter values (maps to Google's tbs=qdr:X parameter)
    RECENCY_OPTIONS = {
        'hour': 'qdr:h',
        'day': 'qdr:d',
        'week': 'qdr:w',
        'month': 'qdr:m',
        'year': 'qdr:y',
        None: None,  # No filter
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        search_mode: str = 'combined',
        level_terms: Optional[List[str]] = None,
        exclude_terms: Optional[List[str]] = None,
        location_terms: Optional[List[str]] = None,
        target_site: str = 'greenhouse.io',
        max_results: int = 50,
        recency: Optional[str] = None,
        max_pages: int = 3,
        start_page: int = 0,
        max_retries: int = 3,
        base_delay: float = 1.0,
        # Legacy parameters (ignored, kept for backward compatibility)
        platforms: Optional[List[str]] = None,
        delay_between_searches: float = 1.5,
    ):
        """Initialize SerpAPI provider.

        Args:
            api_key: SerpAPI API key. Get yours at: https://serpapi.com/
            search_mode: Query construction mode.
                Options: 'default', 'mid_level', 'exclude_senior', 'combined'
                - 'default': Standard keyword search
                - 'mid_level': Add OR group for level II terms
                - 'exclude_senior': Add exclusions (-Senior -Staff etc.)
                - 'combined': Both targeting and exclusion (recommended)
            level_terms: Custom level II terms to search for.
                Defaults to DEFAULT_LEVEL_TERMS.
            exclude_terms: Custom seniority terms to exclude.
                Defaults to DEFAULT_EXCLUDE_TERMS.
            location_terms: Location terms to include in OR group.
                Defaults to DEFAULT_LOCATION_TERMS.
            target_site: Site to restrict search to.
                Defaults to 'greenhouse.io'.
            max_results: Maximum results to request per search (max 100).
                Defaults to 50.
            recency: Time filter for results.
                Options: 'hour', 'day', 'week', 'month', 'year', None (no filter)
            max_pages: Maximum number of pagination requests (each returns 10 results).
                Defaults to 3 (30 results). Max 10 (100 results).
                Each page uses 1 API credit.
            start_page: Starting page number for pagination (0-indexed).
                Defaults to 0. Set higher for deeper searches on subsequent runs.
            max_retries: Maximum retry attempts for transient failures.
            base_delay: Base delay in seconds for exponential backoff.
            platforms: LEGACY - ignored (always searches target_site)
            delay_between_searches: LEGACY - ignored (single query now)
        """
        self.api_key = api_key
        self.search_mode = search_mode
        self.level_terms = level_terms or self.DEFAULT_LEVEL_TERMS
        self.exclude_terms = exclude_terms or self.DEFAULT_EXCLUDE_TERMS
        self.location_terms = location_terms or self.DEFAULT_LOCATION_TERMS
        self.target_site = target_site
        self.max_results = min(max_results, 100)  # SerpAPI max is 100
        self.max_pages = min(max(max_pages, 1), 10)  # 1-10 pages
        self.start_page = max(start_page, 0)  # Ensure non-negative
        self.recency = self.RECENCY_OPTIONS.get(recency, None)
        self.max_retries = max_retries
        self.base_delay = base_delay

    @property
    def provider_name(self) -> str:
        return 'serpapi'

    @property
    def consolidates_locations(self) -> bool:
        """SerpAPI builds a single query with all locations as OR groups."""
        return True

    def discover(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_results: int = None,
        **kwargs
    ) -> List[DiscoveredJob]:
        """Discover job URLs using a single SerpAPI call.

        Makes ONE API call with a consolidated query:
            site:greenhouse.io ("Software Engineer II" OR "SWE 2" ...)
            ("NY" OR "New York" OR "Remote") -Senior -Staff -Principal -Lead

        Args:
            keywords: Search keywords (used in 'default' mode only)
            location: Location filter (appended to location_terms if provided)
            max_results: Maximum results to return (max 100 per SerpAPI).
                Defaults to instance max_results if not specified.
            **kwargs: Additional options:
                - location_terms: Override instance location_terms
                - level_terms: Override instance level_terms
                - recency: Override instance recency filter

        Returns:
            List of DiscoveredJob objects with URLs (needs scraping for details).
        """
        if not self.is_available():
            logger.warning("SerpAPI provider not available: API key not set")
            return []

        # Use the larger of passed value or instance max_results
        # This ensures SERPAPI_MAX_RESULTS config is respected even when
        # DiscoveryManager passes its own calculated value
        if max_results is None:
            max_results = self.max_results
        else:
            max_results = max(max_results, self.max_results)

        # Allow per-call overrides
        level_terms = kwargs.get('level_terms', self.level_terms)
        location_terms = list(kwargs.get('location_terms', self.location_terms))
        recency = kwargs.get('recency', self.recency)
        if recency and recency in self.RECENCY_OPTIONS:
            recency = self.RECENCY_OPTIONS[recency]

        # If location provided and not in location_terms, add it
        if location and location not in location_terms:
            location_terms = location_terms + [location]

        # Build the consolidated query
        query = self._build_query(keywords, level_terms, location_terms)

        logger.info(
            f"SerpAPI: query='{query}', "
            f"max_results={max_results}, "
            f"recency={recency or 'none'}"
        )

        try:
            # Single API call
            urls = self._search_serpapi(query, num_results=max_results, recency=recency)

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

            logger.info(
                f"SerpAPI: {len(discovered)} valid Greenhouse job URLs "
                f"from {len(urls)} results"
            )
            return discovered

        except Exception as e:
            logger.error(f"SerpAPI error: {e}")
            return []

    def _build_query(
        self,
        keywords: str = None,
        level_terms: List[str] = None,
        location_terms: List[str] = None
    ) -> str:
        """Build consolidated Google Search query for SerpAPI.

        Constructs a single query based on search_mode:
        - 'default': site:greenhouse.io "keywords" ("location1" OR "location2")
        - 'mid_level': site:greenhouse.io ("SWE II" OR "SWE 2" ...) ("NY" OR ...)
        - 'exclude_senior': site:greenhouse.io "keywords" ("NY" OR ...) -Senior -Staff
        - 'combined': site:greenhouse.io ("SWE II" OR ...) ("NY" OR ...) -Senior -Staff

        Example output (combined mode):
            site:greenhouse.io ("Software Engineer II" OR "Software Engineer 2"
            OR "SWE II" OR "SWE 2" OR "Associate Software Engineer")
            ("NY" OR "New York" OR "Remote") -Senior -Staff -Principal -Lead

        Args:
            keywords: Job keywords (used in default/exclude_senior modes only)
            level_terms: Level II terms for the OR group
            location_terms: Location terms for the OR group

        Returns:
            Formatted search query string with boolean operators.
        """
        level_terms = level_terms or self.level_terms
        location_terms = location_terms or self.location_terms

        parts = [f'site:{self.target_site}']

        # Build level/keyword terms based on mode
        if self.search_mode in ('mid_level', 'combined'):
            # Build OR group for level II terms
            if level_terms:
                level_group = ' OR '.join(f'"{term}"' for term in level_terms)
                parts.append(f'({level_group})')
            elif keywords:
                # Fallback to keywords if no level terms
                parts.append(f'"{keywords}"')
        else:
            # Default/exclude_senior: use keywords directly
            if keywords:
                parts.append(f'"{keywords}"')

        # Build location OR group
        if location_terms:
            location_group = ' OR '.join(f'"{loc}"' for loc in location_terms)
            parts.append(f'({location_group})')

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

    def _search_serpapi(
        self,
        query: str,
        num_results: int = 50,
        recency: Optional[str] = None
    ) -> List[str]:
        """Execute SerpAPI requests with pagination.

        Google now limits all search engines to 10 results per request.
        This method paginates using the 'start' parameter to fetch more results.

        Each page uses 1 API credit (250 free/month).

        Args:
            query: Search query with boolean operators
            num_results: Desired number of results (will fetch ceil(n/10) pages)
            recency: Time filter (qdr:d, qdr:w, qdr:m, qdr:y, or None)

        Returns:
            List of URLs from search results.
        """
        all_urls = []
        # Calculate pages needed, but cap at max_pages
        pages_needed = min((num_results + 9) // 10, self.max_pages)

        end_page = self.start_page + pages_needed
        logger.debug(
            f"SerpAPI: Fetching pages {self.start_page}-{end_page - 1} "
            f"({pages_needed} pages, up to {pages_needed * 10} results)"
        )

        for page in range(self.start_page, end_page):
            start_index = page * 10

            urls = self._fetch_page(query, start_index, recency)

            if urls is None:
                # Fatal error occurred, stop pagination
                break

            all_urls.extend(urls)

            # If we got fewer than 10 results, no more pages available
            if len(urls) < 10:
                logger.debug(
                    f"SerpAPI: Page {page} returned {len(urls)} results, "
                    f"stopping pagination"
                )
                break

            # Small delay between pages to be nice to the API
            if page < end_page - 1:
                time.sleep(0.5)

        logger.debug(f"SerpAPI: Collected {len(all_urls)} total URLs")
        return all_urls

    def _fetch_page(
        self,
        query: str,
        start: int = 0,
        recency: Optional[str] = None
    ) -> Optional[List[str]]:
        """Fetch a single page of results from SerpAPI.

        Implements exponential backoff for transient failures including:
        - Network/DNS errors
        - Connection timeouts
        - Rate limiting (429)
        - Server errors (5xx)

        Args:
            query: Search query with boolean operators
            start: Starting index for pagination (0, 10, 20, ...)
            recency: Time filter (qdr:d, qdr:w, qdr:m, qdr:y, or None)

        Returns:
            List of URLs from this page, or None on fatal error.
        """
        params = {
            "engine": "google_light",
            "q": query,
            "api_key": self.api_key,
            "start": start,
        }

        # Add recency filter if specified
        if recency:
            params["tbs"] = recency

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    self.API_ENDPOINT,
                    params=params,
                    timeout=30
                )

                # Non-retryable: Invalid API key
                if response.status_code == 401:
                    logger.error("SerpAPI: Invalid or missing API key")
                    return None

                # Non-retryable: Bad request
                if response.status_code == 400:
                    logger.error(f"SerpAPI: Bad request - {response.text[:200]}")
                    return None

                # Retryable: Rate limit exceeded
                if response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        logger.warning(
                            f"SerpAPI: Rate limited, retrying in {delay:.1f}s "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error("SerpAPI: Rate limit exceeded after all retries")
                        return None

                # Retryable: Server errors
                if response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        logger.warning(
                            f"SerpAPI: Server error {response.status_code}, "
                            f"retrying in {delay:.1f}s "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"SerpAPI: Server error {response.status_code} "
                            f"after all retries"
                        )
                        return None

                response.raise_for_status()

                data = response.json()

                # Check for API-level errors
                if "error" in data:
                    logger.error(f"SerpAPI error: {data['error']}")
                    return None

                # Extract URLs from organic results
                urls = []
                organic_results = data.get("organic_results", [])

                for result in organic_results:
                    url = result.get("link")
                    if url:
                        urls.append(url)

                # Log search metadata if available
                search_metadata = data.get("search_metadata", {})
                total_time = search_metadata.get("total_time_taken")
                if total_time:
                    logger.debug(
                        f"SerpAPI page (start={start}) took {total_time}s, "
                        f"returned {len(urls)} results"
                    )

                return urls

            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        f"SerpAPI: Network error, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"SerpAPI: Network error after {self.max_retries} "
                        f"attempts: {e}"
                    )
                    return None

            except requests.exceptions.RequestException as e:
                logger.error(f"SerpAPI error: {e}")
                return None

            except (KeyError, ValueError) as e:
                logger.error(f"SerpAPI: Error parsing response: {e}")
                return None

        return None

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
        """Check if SerpAPI is configured with an API key."""
        if not self.api_key:
            logger.debug(
                "SerpAPI provider not available: "
                "SERPAPI_API_KEY not set"
            )
            return False
        return True
