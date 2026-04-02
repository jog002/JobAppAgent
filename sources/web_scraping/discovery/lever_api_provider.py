"""Lever API provider for direct job board polling.

This provider fetches jobs directly from Lever's public API,
bypassing search engines entirely. It's fast, free, and provides full job data.

API endpoint: https://api.lever.co/v0/postings/{company}?mode=json
"""

import logging
import requests
from typing import List, Optional, Set

from .base_provider import BaseDiscoveryProvider, DiscoveredJob

logger = logging.getLogger(__name__)

# Curated list of tech companies using Lever
# Note: Many tech companies have migrated to other ATS platforms
# These are verified active Lever boards as of 2024
DEFAULT_COMPANY_TOKENS = [
    # Verified Active
    "attentive",
    "brightwheel",
    "clubhouse",
    "outreach",
    "zeta",

    # Tech Companies (to verify)
    "appcues",
    "aptible",
    "astronomer",
    "baseten",
    "betterup",
    "braze",
    "census",
    "clari",
    "clearco",
    "clockwise",
    "cribl",
    "crossbeam",
    "customerio",
    "dataminr",
    "dooly",
    "dragos",
    "drift",
    "envoy",
    "everlaw",
    "exabeam",
    "fetchrewards",
    "flatfile",
    "forter",
    "gladly",
    "go1",
    "harness",
    "honeycomb",
    "huntress",
    "hyperscience",
    "immuta",
    "instabase",
    "intercom",
    "iterable",
    "komodor",
    "launchnotes",
    "lilt",
    "mattermost",
    "melio",
    "metronome",
    "mixmax",
    "mode",
    "moveworks",
    "mutiny",
    "newfront",
    "observe",
    "olo",
    "onepeloton",
    "orca",
    "oyster",
    "paddle",
    "pave",
    "peerspace",
    "persona",
    "pilot",
    "pocus",
    "productboard",
    "recurly",
    "remote",
    "rigetti",
    "rokt",
    "runway",
    "scale",
    "scribe",
    "segment",
    "sentry",
    "snyk",
    "sourcegraph",
    "stytch",
    "tremendous",
    "vanta",
    "watershed",
]


class LeverAPIProvider(BaseDiscoveryProvider):
    """Direct Lever API polling for known companies.

    This provider polls Lever job boards directly via their public API.
    It's more reliable than search engines and provides complete job data.

    Attributes:
        tokens: Set of company board tokens to poll
        timeout: Request timeout in seconds
    """

    API_URL = "https://api.lever.co/v0/postings/{token}"

    def __init__(
        self,
        tokens: Optional[List[str]] = None,
        use_curated: bool = True,
        timeout: int = 30
    ):
        """Initialize the Lever API provider.

        Args:
            tokens: List of company board tokens to poll (e.g., ['netflix', 'shopify'])
            use_curated: If True, include the curated list of known tech companies
            timeout: Request timeout in seconds
        """
        self.tokens: Set[str] = set()
        self.timeout = timeout

        if use_curated:
            self.tokens.update(DEFAULT_COMPANY_TOKENS)

        if tokens:
            self.tokens.update(tokens)

        logger.info(f"Initialized Lever API provider with {len(self.tokens)} company tokens")

    @property
    def provider_name(self) -> str:
        return "lever_api"

    @property
    def consolidates_locations(self) -> bool:
        return True

    def is_available(self) -> bool:
        return len(self.tokens) > 0

    def add_token(self, token: str, source: str = "discovered") -> None:
        """Add a new company token.

        Args:
            token: The company board token (e.g., 'netflix')
            source: How the token was found ('curated' or 'discovered')
        """
        token = token.lower().strip()
        if token and token not in self.tokens:
            self.tokens.add(token)
            logger.info(f"Added Lever token: {token} (source: {source})")

    def discover(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_results: int = 100,
        **kwargs
    ) -> List[DiscoveredJob]:
        """Fetch jobs from all known Lever company boards.

        Note: keywords and location are used for post-filtering only.
        The API returns all jobs from each company board.

        Args:
            keywords: Search keywords (used for filtering, not API query)
            location: Location filter (used for filtering, not API query)
            max_results: Maximum total results to return
            **kwargs: Additional options (ignored)

        Returns:
            List of DiscoveredJob objects with full job data
        """
        all_jobs: List[DiscoveredJob] = []

        logger.info(f"Polling {len(self.tokens)} Lever boards...")

        for token in self.tokens:
            if len(all_jobs) >= max_results:
                break

            try:
                jobs = self._fetch_company_jobs(token)
                all_jobs.extend(jobs)
                logger.debug(f"Fetched {len(jobs)} jobs from {token}")
            except Exception as e:
                logger.warning(f"Failed to fetch jobs from {token}: {e}")
                continue

        logger.info(f"Total jobs from Lever API: {len(all_jobs)}")
        return all_jobs[:max_results]

    def _fetch_company_jobs(self, token: str) -> List[DiscoveredJob]:
        """Fetch all jobs for a single company.

        Args:
            token: Company board token (e.g., 'netflix')

        Returns:
            List of DiscoveredJob objects
        """
        url = self.API_URL.format(token=token)
        params = {"mode": "json"}

        response = requests.get(url, params=params, timeout=self.timeout)

        if response.status_code == 404:
            logger.debug(f"Board not found for token: {token}")
            return []

        response.raise_for_status()
        data = response.json()

        jobs = []
        for job_data in data:
            try:
                job = self._parse_job(job_data, token)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to parse job from {token}: {e}")
                continue

        return jobs

    def _parse_job(self, job_data: dict, token: str) -> Optional[DiscoveredJob]:
        """Parse a job from Lever API response.

        Args:
            job_data: Raw job data from API
            token: Company board token

        Returns:
            DiscoveredJob or None if parsing fails
        """
        job_url = job_data.get("hostedUrl")
        if not job_url:
            return None

        # Extract location from categories
        location = None
        categories = job_data.get("categories", {})
        if categories:
            location = categories.get("location")

        # Get posted timestamp
        posted_date = None
        created_at = job_data.get("createdAt")
        if created_at:
            try:
                from datetime import datetime
                # Lever uses milliseconds
                dt = datetime.fromtimestamp(created_at / 1000)
                posted_date = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError, OSError):
                pass

        # Get description text
        description = job_data.get("descriptionPlain", "")
        if not description:
            # Fall back to HTML description
            description = job_data.get("description", "")

        # Build company name from token
        company_name = token.replace("-", " ").title()

        return DiscoveredJob(
            url=job_url,
            title=job_data.get("text"),
            company=company_name,
            location=location,
            description=description,
            source_platform="lever",
            posted_date=posted_date,
            metadata={
                "lever_id": job_data.get("id"),
                "lever_token": token,
                "team": categories.get("team"),
                "department": categories.get("department"),
                "commitment": categories.get("commitment"),
            }
        )


def extract_lever_token(url: str) -> Optional[str]:
    """Extract company token from a Lever URL.

    Args:
        url: A Lever job board URL

    Returns:
        The company token, or None if not found

    Examples:
        >>> extract_lever_token("https://jobs.lever.co/netflix/abc123")
        'netflix'
        >>> extract_lever_token("https://example.com/job")
        None
    """
    import re

    patterns = [
        r"jobs\.lever\.co/([^/]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1).lower()

    return None
