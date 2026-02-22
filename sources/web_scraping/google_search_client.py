"""Google Custom Search API client for finding job postings."""
import logging
import requests
from typing import List, Dict, Optional
from urllib.parse import urlparse
from datetime import datetime, date

logger = logging.getLogger(__name__)


class RateLimiter:
    """Track and enforce Google API rate limits."""

    def __init__(self, daily_limit: int = 100):
        self.daily_limit = daily_limit
        self.requests_today = 0
        self.last_reset = date.today()

    def can_make_request(self) -> bool:
        """Check if we can make another request."""
        self._check_reset()
        return self.requests_today < self.daily_limit

    def record_request(self):
        """Record that a request was made."""
        self._check_reset()
        self.requests_today += 1

    def _check_reset(self):
        """Reset counter if it's a new day."""
        today = date.today()
        if today > self.last_reset:
            logger.info(f"Rate limiter reset. Used {self.requests_today} requests yesterday.")
            self.requests_today = 0
            self.last_reset = today

    def remaining_requests(self) -> int:
        """Get remaining requests for today."""
        self._check_reset()
        return max(0, self.daily_limit - self.requests_today)


class GoogleSearchClient:
    """Client for Google Custom Search API."""

    def __init__(self, api_key: str, search_engine_id: str, daily_limit: int = 100):
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.rate_limiter = RateLimiter(daily_limit)

    def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Search using Google Custom Search API.

        Args:
            query: Search query (e.g., 'site:boards.greenhouse.io "software engineer" "remote"')
            num_results: Number of results (max 10 per request)

        Returns:
            List of search result dictionaries with 'url', 'title', 'snippet'
        """
        if not self.rate_limiter.can_make_request():
            logger.warning(f"Rate limit reached. {self.rate_limiter.remaining_requests()} requests remaining today.")
            return []

        try:
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': query,
                'num': min(num_results, 10)  # API limit
            }

            response = requests.get(self.base_url, params=params, timeout=10)

            # Record request immediately after receiving response (before status check)
            # If we got a response (even an error like 429), we consumed quota
            self.rate_limiter.record_request()

            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get('items', []):
                results.append({
                    'url': item.get('link'),
                    'title': item.get('title'),
                    'snippet': item.get('snippet'),
                    'displayed_link': item.get('displayLink')
                })

            logger.info(f"Google Search found {len(results)} results for query: {query[:100]}...")
            return results

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("Rate limit exceeded (429). Check your API quota.")
            else:
                logger.error(f"Google Search API HTTP error: {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Search API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in Google Search: {e}")
            return []

    def identify_ats_platform(self, url: str) -> Optional[str]:
        """
        Identify which ATS platform a URL belongs to.

        Returns: 'greenhouse', 'lever', 'bamboohr', 'ashby', or None
        """
        domain = urlparse(url).netloc.lower()

        if 'greenhouse.io' in domain:
            return 'greenhouse'
        elif 'lever.co' in domain:
            return 'lever'
        elif 'bamboohr.com' in domain:
            return 'bamboohr'
        elif 'ashbyhq.com' in domain:
            return 'ashby'
        else:
            return None

    def build_search_query(self, platform: str, keywords: str, location: str = None) -> str:
        """
        Build optimized Google search query for ATS platform.

        Note: If your Programmable Search Engine is configured with site restrictions,
        the site: operator is redundant. This method supports both configurations:
        - USE_SITE_OPERATOR=true (default): Adds site: to query (for "Search entire web")
        - USE_SITE_OPERATOR=false: Omits site: (for site-restricted search engines)

        Examples with site operator:
            - site:boards.greenhouse.io "software engineer" "remote"
            - site:jobs.lever.co "machine learning" "new york"

        Examples without site operator:
            - "software engineer" "remote"
            - "machine learning" "new york"
        """
        import os
        use_site_operator = os.getenv('USE_SITE_OPERATOR', 'true').lower() == 'true'

        query_parts = []

        # Only add site: filter if USE_SITE_OPERATOR is true
        if use_site_operator:
            query_templates = {
                'greenhouse': 'site:boards.greenhouse.io',
                'lever': 'site:jobs.lever.co',
                'bamboohr': 'site:*.bamboohr.com/careers',
                'ashby': 'site:*.ashbyhq.com'
            }

            site_filter = query_templates.get(platform, '')
            if not site_filter:
                logger.warning(f"Unknown platform: {platform}")
                return ''

            query_parts.append(site_filter)

        # Add keywords (quoted for exact match)
        if keywords:
            query_parts.append(f'"{keywords}"')

        # Add location if provided
        if location:
            query_parts.append(f'"{location}"')

        return ' '.join(query_parts)
