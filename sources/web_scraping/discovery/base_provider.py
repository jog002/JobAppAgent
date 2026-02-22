"""Base class for job discovery providers.

This module defines the abstract interface that all discovery providers must implement.
Discovery providers are responsible for finding job postings (URLs or full data)
from various sources like JobSpy, Google Search, Apify, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredJob:
    """A job discovered by a provider.

    May contain full data (from aggregators like JobSpy) or just a URL
    (from search providers like Google Search) that needs scraping.

    Attributes:
        url: The job posting URL (required)
        title: Job title (optional - may need scraping)
        company: Company name (optional - may need scraping)
        location: Job location (optional - may need scraping)
        description: Full job description (optional - may need scraping)
        source_platform: Origin platform ('greenhouse', 'lever', 'indeed', etc.)
        salary_min: Minimum salary (optional)
        salary_max: Maximum salary (optional)
        posted_date: When the job was posted (optional)
        metadata: Additional provider-specific data
    """
    url: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    source_platform: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    posted_date: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_full_data(self) -> bool:
        """Check if this job has enough data to skip scraping."""
        return bool(self.title and self.description)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format compatible with job normalization."""
        return {
            'url': self.url,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'description': self.description,
            'source': self.source_platform,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'posted_date': self.posted_date,
            **self.metadata
        }


class BaseDiscoveryProvider(ABC):
    """Abstract base class for job discovery providers.

    Discovery providers find job postings from various sources. They may return:
    - Full job data (title, company, description, etc.) from aggregators
    - Just URLs that need to be scraped for full details

    Implement this class to add new discovery sources like:
    - JobSpy (Indeed, Google Jobs, LinkedIn, etc.)
    - Google Search (for ATS job boards)
    - Apify scrapers
    - TheirStack API
    - Custom scrapers

    Example:
        class MyProvider(BaseDiscoveryProvider):
            @property
            def provider_name(self) -> str:
                return 'my_provider'

            def discover(self, keywords, location, max_results, **kwargs):
                # Implement discovery logic
                return [DiscoveredJob(url='...', title='...')]

            def is_available(self) -> bool:
                return True
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider.

        Used for logging, configuration, and distinguishing between providers.
        Should be lowercase with underscores (e.g., 'jobspy', 'google_search').
        """
        pass

    @abstractmethod
    def discover(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[DiscoveredJob]:
        """Discover job postings matching the given criteria.

        Args:
            keywords: Search keywords (e.g., "software engineer", "data scientist")
            location: Location filter (e.g., "Remote", "New York", "San Francisco")
            max_results: Maximum number of results to return
            **kwargs: Provider-specific options (e.g., 'sites' for JobSpy)

        Returns:
            List of DiscoveredJob objects. These may have:
            - Full data (title, company, description) - ready for scoring
            - Just URL and source_platform - needs scraping for details

        Raises:
            Exception: Provider-specific errors should be caught and logged,
                      returning an empty list rather than raising.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is properly configured and available.

        Returns:
            True if the provider can be used, False otherwise.

        Should check:
            - Required dependencies are installed
            - Required API keys/credentials are configured
            - External services are reachable (optional)
        """
        pass

    @property
    def consolidates_locations(self) -> bool:
        """Whether this provider handles all locations in a single query.

        If True, the provider builds a query that includes all location terms
        (e.g., via OR groups) and should only be called once, not per-location.

        Default: False (call once per location)
        """
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider_name='{self.provider_name}')"
