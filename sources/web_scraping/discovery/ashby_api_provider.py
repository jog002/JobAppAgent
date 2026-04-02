"""Ashby API provider for direct job board polling.

This provider fetches jobs directly from Ashby's public job board pages.
Ashby uses a JavaScript-rendered frontend, so we fetch the embedded JSON data.

Job board URL: https://jobs.ashbyhq.com/{company}
"""

import logging
import re
import json
import requests
from typing import List, Optional, Set

from .base_provider import BaseDiscoveryProvider, DiscoveredJob

logger = logging.getLogger(__name__)

# Curated list of tech companies using Ashby
# Note: Ashby is popular with modern startups
DEFAULT_COMPANY_TOKENS = [
    # Verified Active
    "linear",

    # AI/ML & Data Companies
    "ramp",
    "posthog",
    "langchain",
    "pinecone",
    "weaviate",
    "anyscale",
    "modal",
    "replicate",
    "humanloop",
    "deepgram",

    # Developer Tools
    "vercel",
    "supabase",
    "neon",
    "turso",
    "convex",
    "upstash",
    "railway",
    "render",
    "fly",

    # Growth Startups
    "deel",
    "remote",
    "oyster",
    "lattice",
    "mercury",
    "brex",
    "ramp",
    "gusto",
    "rippling",

    # Security & Infrastructure
    "snyk",
    "lacework",
    "wiz",
    "orca-security",
    "vanta",

    # Collaboration Tools
    "loom",
    "miro",
    "pitch",
    "coda",
    "notion",
    "airtable",

    # Other Notable
    "watershed",
    "persona",
    "census",
    "hightouch",
    "segment",
]


class AshbyAPIProvider(BaseDiscoveryProvider):
    """Direct Ashby job board polling for known companies.

    This provider fetches job listings from Ashby job boards.
    Ashby embeds job data as JSON in the page, which we extract.

    Attributes:
        tokens: Set of company board tokens to poll
        timeout: Request timeout in seconds
    """

    JOB_BOARD_URL = "https://jobs.ashbyhq.com/{token}"
    API_URL = "https://jobs.ashbyhq.com/api/non-user-graphql"

    def __init__(
        self,
        tokens: Optional[List[str]] = None,
        use_curated: bool = True,
        timeout: int = 30
    ):
        """Initialize the Ashby API provider.

        Args:
            tokens: List of company board tokens to poll (e.g., ['notion', 'linear'])
            use_curated: If True, include the curated list of known tech companies
            timeout: Request timeout in seconds
        """
        self.tokens: Set[str] = set()
        self.timeout = timeout

        if use_curated:
            self.tokens.update(DEFAULT_COMPANY_TOKENS)

        if tokens:
            self.tokens.update(tokens)

        logger.info(f"Initialized Ashby API provider with {len(self.tokens)} company tokens")

    @property
    def provider_name(self) -> str:
        return "ashby_api"

    @property
    def consolidates_locations(self) -> bool:
        return True

    def is_available(self) -> bool:
        return len(self.tokens) > 0

    def add_token(self, token: str, source: str = "discovered") -> None:
        """Add a new company token.

        Args:
            token: The company board token (e.g., 'notion')
            source: How the token was found ('curated' or 'discovered')
        """
        token = token.lower().strip()
        if token and token not in self.tokens:
            self.tokens.add(token)
            logger.info(f"Added Ashby token: {token} (source: {source})")

    def discover(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_results: int = 100,
        **kwargs
    ) -> List[DiscoveredJob]:
        """Fetch jobs from all known Ashby company boards.

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

        logger.info(f"Polling {len(self.tokens)} Ashby boards...")

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

        logger.info(f"Total jobs from Ashby API: {len(all_jobs)}")
        return all_jobs[:max_results]

    def _fetch_company_jobs(self, token: str) -> List[DiscoveredJob]:
        """Fetch all jobs for a single company using GraphQL API.

        Args:
            token: Company board token (e.g., 'notion')

        Returns:
            List of DiscoveredJob objects
        """
        # First, try the GraphQL API
        jobs = self._fetch_via_graphql(token)
        if jobs is not None:
            return jobs

        # Fallback to HTML scraping
        return self._fetch_via_html(token)

    def _fetch_via_graphql(self, token: str) -> Optional[List[DiscoveredJob]]:
        """Fetch jobs via Ashby's GraphQL API.

        Args:
            token: Company board token

        Returns:
            List of DiscoveredJob objects, or None if GraphQL fails
        """
        query = """
        query JobBoardWithOrganizationId($organizationHostedJobsPageName: String!) {
          jobBoard: jobBoardWithOrganizationId(
            organizationHostedJobsPageName: $organizationHostedJobsPageName
          ) {
            jobPostings {
              id
              title
              locationName
              employmentType
              publishedDate
              descriptionPlain
              descriptionHtml
            }
            organization {
              name
            }
          }
        }
        """

        payload = {
            "operationName": "JobBoardWithOrganizationId",
            "variables": {"organizationHostedJobsPageName": token},
            "query": query
        }

        try:
            response = requests.post(
                self.API_URL,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.debug(f"GraphQL API returned {response.status_code} for {token}")
                return None

            data = response.json()

            if "errors" in data:
                logger.debug(f"GraphQL errors for {token}: {data['errors']}")
                return None

            job_board = data.get("data", {}).get("jobBoard")
            if not job_board:
                logger.debug(f"No job board found for {token}")
                return []

            company_name = job_board.get("organization", {}).get("name", token.title())
            postings = job_board.get("jobPostings", [])

            jobs = []
            for posting in postings:
                job = self._parse_graphql_job(posting, token, company_name)
                if job:
                    jobs.append(job)

            return jobs

        except Exception as e:
            logger.debug(f"GraphQL fetch failed for {token}: {e}")
            return None

    def _parse_graphql_job(
        self,
        posting: dict,
        token: str,
        company_name: str
    ) -> Optional[DiscoveredJob]:
        """Parse a job from GraphQL response.

        Args:
            posting: Job posting data from GraphQL
            token: Company board token
            company_name: Company display name

        Returns:
            DiscoveredJob or None
        """
        job_id = posting.get("id")
        if not job_id:
            return None

        job_url = f"https://jobs.ashbyhq.com/{token}/{job_id}"

        # Get description
        description = posting.get("descriptionPlain", "")
        if not description:
            description = posting.get("descriptionHtml", "")

        return DiscoveredJob(
            url=job_url,
            title=posting.get("title"),
            company=company_name,
            location=posting.get("locationName"),
            description=description,
            source_platform="ashby",
            posted_date=posting.get("publishedDate"),
            metadata={
                "ashby_id": job_id,
                "ashby_token": token,
                "employment_type": posting.get("employmentType"),
            }
        )

    def _fetch_via_html(self, token: str) -> List[DiscoveredJob]:
        """Fallback: Fetch jobs by scraping HTML page.

        Ashby embeds job data as JSON in the page.

        Args:
            token: Company board token

        Returns:
            List of DiscoveredJob objects
        """
        url = self.JOB_BOARD_URL.format(token=token)

        response = requests.get(url, timeout=self.timeout)

        if response.status_code == 404:
            logger.debug(f"Board not found for token: {token}")
            return []

        response.raise_for_status()

        # Try to extract jobPostings array directly from page
        # Ashby embeds this as JSON in the page source
        # We need to properly extract the full JSON array by matching brackets
        start_match = re.search(r'"jobPostings":\s*\[', response.text)
        if start_match:
            try:
                json_str = self._extract_json_array(response.text, start_match.end() - 1)
                if json_str:
                    postings = json.loads(json_str)
                    logger.debug(f"Found {len(postings)} job postings for {token}")

                    # Get company name from the page if possible
                    company_match = re.search(r'"organizationName":\s*"([^"]+)"', response.text)
                    company_name = company_match.group(1) if company_match else token.title()

                    jobs = []
                    for posting in postings:
                        job = self._parse_html_job(posting, token, company_name)
                        if job:
                            jobs.append(job)
                    return jobs
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse jobPostings JSON for {token}: {e}")

        # Try __NEXT_DATA__ pattern as fallback
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', response.text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                return self._parse_next_data(data, token)
            except json.JSONDecodeError:
                pass

        logger.debug(f"Could not extract job data from HTML for {token}")
        return []

    def _extract_json_array(self, text: str, start: int) -> Optional[str]:
        """Extract a complete JSON array from text starting at a given position.

        Uses bracket counting to find the matching closing bracket.

        Args:
            text: The full text to extract from
            start: Starting position of the '[' character

        Returns:
            The JSON array string, or None if extraction fails
        """
        depth = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == '[':
                depth += 1
            elif char == ']':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

        return None

    def _parse_html_job(
        self,
        posting: dict,
        token: str,
        company_name: str
    ) -> Optional[DiscoveredJob]:
        """Parse a job from HTML-embedded JSON.

        Args:
            posting: Job posting data from embedded JSON
            token: Company board token
            company_name: Company display name

        Returns:
            DiscoveredJob or None
        """
        job_id = posting.get("id")
        if not job_id:
            return None

        job_url = f"https://jobs.ashbyhq.com/{token}/{job_id}"

        # Get location
        location = posting.get("location") or posting.get("locationName")

        # Get description
        description = posting.get("descriptionPlain", "")

        # Get posted date
        posted_date = None
        updated_at = posting.get("updatedAt")
        if updated_at:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                posted_date = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        return DiscoveredJob(
            url=job_url,
            title=posting.get("title"),
            company=company_name,
            location=location,
            description=description,
            source_platform="ashby",
            posted_date=posted_date,
            metadata={
                "ashby_id": job_id,
                "ashby_token": token,
                "department": posting.get("department"),
            }
        )

    def _parse_next_data(self, data: dict, token: str) -> List[DiscoveredJob]:
        """Parse jobs from Next.js __NEXT_DATA__ JSON.

        Args:
            data: Parsed JSON from __NEXT_DATA__
            token: Company board token

        Returns:
            List of DiscoveredJob objects
        """
        jobs = []

        # Navigate to job postings in Next.js data structure
        try:
            props = data.get("props", {})
            page_props = props.get("pageProps", {})
            job_board = page_props.get("jobBoard", {})
            postings = job_board.get("jobPostings", [])
            company_name = job_board.get("organization", {}).get("name", token.title())

            for posting in postings:
                job = self._parse_graphql_job(posting, token, company_name)
                if job:
                    jobs.append(job)

        except (KeyError, TypeError) as e:
            logger.debug(f"Error parsing Next.js data for {token}: {e}")

        return jobs


def extract_ashby_token(url: str) -> Optional[str]:
    """Extract company token from an Ashby URL.

    Args:
        url: An Ashby job board URL

    Returns:
        The company token, or None if not found

    Examples:
        >>> extract_ashby_token("https://jobs.ashbyhq.com/notion/abc123")
        'notion'
        >>> extract_ashby_token("https://example.com/job")
        None
    """
    patterns = [
        r"jobs\.ashbyhq\.com/([^/]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1).lower()

    return None
