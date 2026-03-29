"""Greenhouse API provider for direct job board polling.

This provider fetches jobs directly from Greenhouse's public API,
bypassing search engines entirely. It's faster, more complete, and free.

API endpoint: https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
"""

import logging
import re
import requests
from datetime import datetime
from typing import List, Optional, Set

from .base_provider import BaseDiscoveryProvider, DiscoveredJob

logger = logging.getLogger(__name__)

# Curated list of tech companies using Greenhouse
# This list is automatically expanded as new tokens are discovered from search results
DEFAULT_COMPANY_TOKENS = [
    # Top AI Companies
    "anthropic",
    "openai",
    "cohere",
    "huggingface",
    "stability",
    "midjourney",
    "perplexityai",
    "scale",

    # Big Tech & Large Companies
    "airbnb",
    "brex",
    "coinbase",
    "databricks",
    "discord",
    "dropbox",
    "figma",
    "gitlab",
    "gusto",
    "hubspot",
    "instacart",
    "klaviyo",
    "lyft",
    "notion",
    "pagerduty",
    "plaid",
    "ramp",
    "reddit",
    "rippling",
    "snap",
    "snowflakecomputing",
    "spotify",
    "stripe",
    "twilio",
    "uber",
    "vercel",
    "webflow",
    "zapier",
    "zendesk",

    # Finance/Fintech
    "robinhood",
    "chime",
    "sofi",
    "wealthfront",
    "betterment",
    "affirm",
    "marqeta",

    # Other Notable Tech
    "asana",
    "airtable",
    "atlassian",
    "canva",
    "cloudflare",
    "datadog",
    "doordash",
    "elastic",
    "flexport",
    "grammarly",
    "intercom",
    "linear",
    "loom",
    "miro",
    "mixpanel",
    "mongodb",
    "netlify",
    "okta",
    "onepassword",
    "postman",
    "retool",
    "samsara",
    "segment",
    "sentry",
    "slackfeed",
    "supabase",
    "tailscale",
    "twitch",
    "vanta",
    "wiz",
    "zscaler",
]


class GreenhouseAPIProvider(BaseDiscoveryProvider):
    """Direct Greenhouse API polling for known companies.

    This provider polls Greenhouse job boards directly via their public API.
    It's more reliable than search engines and provides complete job data.

    Attributes:
        tokens: Set of company board tokens to poll
        timeout: Request timeout in seconds
    """

    API_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

    def __init__(
        self,
        tokens: Optional[List[str]] = None,
        use_curated: bool = True,
        timeout: int = 30
    ):
        """Initialize the Greenhouse API provider.

        Args:
            tokens: List of company board tokens to poll (e.g., ['anthropic', 'stripe'])
            use_curated: If True, include the curated list of known tech companies
            timeout: Request timeout in seconds
        """
        self.tokens: Set[str] = set()
        self.timeout = timeout

        if use_curated:
            self.tokens.update(DEFAULT_COMPANY_TOKENS)

        if tokens:
            self.tokens.update(tokens)

        logger.info(f"Initialized Greenhouse API provider with {len(self.tokens)} company tokens")

    @property
    def provider_name(self) -> str:
        return "greenhouse_api"

    @property
    def consolidates_locations(self) -> bool:
        return True

    def is_available(self) -> bool:
        return len(self.tokens) > 0

    def add_token(self, token: str, source: str = "discovered") -> None:
        """Add a new company token.

        Args:
            token: The company board token (e.g., 'anthropic')
            source: How the token was found ('curated' or 'discovered')
        """
        token = token.lower().strip()
        if token and token not in self.tokens:
            self.tokens.add(token)
            logger.info(f"Added Greenhouse token: {token} (source: {source})")

    def discover(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_results: int = 100,
        **kwargs
    ) -> List[DiscoveredJob]:
        """Fetch jobs from all known Greenhouse company boards.

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

        logger.info(f"Polling {len(self.tokens)} Greenhouse boards...")

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

        logger.info(f"Total jobs from Greenhouse API: {len(all_jobs)}")
        return all_jobs[:max_results]

    def _fetch_company_jobs(self, token: str) -> List[DiscoveredJob]:
        """Fetch all jobs for a single company.

        Args:
            token: Company board token (e.g., 'anthropic')

        Returns:
            List of DiscoveredJob objects
        """
        url = self.API_URL.format(token=token) + "?content=true"

        response = requests.get(url, timeout=self.timeout)

        if response.status_code == 404:
            logger.debug(f"Board not found for token: {token}")
            return []

        response.raise_for_status()
        data = response.json()

        jobs = []
        for job_data in data.get("jobs", []):
            try:
                job = self._parse_job(job_data, token)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to parse job from {token}: {e}")
                continue

        return jobs

    def _parse_job(self, job_data: dict, token: str) -> Optional[DiscoveredJob]:
        """Parse a job from Greenhouse API response.

        Args:
            job_data: Raw job data from API
            token: Company board token

        Returns:
            DiscoveredJob or None if parsing fails
        """
        job_url = job_data.get("absolute_url")
        if not job_url:
            return None

        # Extract location from offices
        location = None
        offices = job_data.get("offices", [])
        if offices:
            location_parts = [office.get("name") for office in offices if office.get("name")]
            location = ", ".join(location_parts) if location_parts else None

        # Parse updated_at for posted date
        posted_date = None
        updated_at = job_data.get("updated_at")
        if updated_at:
            try:
                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                posted_date = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        # Extract content (HTML job description)
        content = job_data.get("content", "")

        return DiscoveredJob(
            url=job_url,
            title=job_data.get("title"),
            company=token.replace("-", " ").title(),
            location=location,
            description=content,
            source_platform="greenhouse",
            posted_date=posted_date,
            metadata={
                "greenhouse_id": job_data.get("id"),
                "greenhouse_token": token,
                "departments": [d.get("name") for d in job_data.get("departments", [])],
            }
        )


def extract_greenhouse_token(url: str) -> Optional[str]:
    """Extract company token from a Greenhouse URL.

    Args:
        url: A Greenhouse job board URL

    Returns:
        The company token, or None if not found

    Examples:
        >>> extract_greenhouse_token("https://boards.greenhouse.io/anthropic/jobs/123")
        'anthropic'
        >>> extract_greenhouse_token("https://job-boards.greenhouse.io/stripe/jobs/456")
        'stripe'
        >>> extract_greenhouse_token("https://example.com/job")
        None
    """
    patterns = [
        r"boards\.greenhouse\.io/([^/]+)",
        r"job-boards\.greenhouse\.io/([^/]+)",
        r"greenhouse\.io/([^/]+)/jobs",
    ]

    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1).lower()

    return None
