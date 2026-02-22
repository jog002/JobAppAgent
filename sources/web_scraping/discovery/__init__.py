"""Discovery module for finding job postings from multiple sources.

This module provides a pluggable architecture for job discovery:
- BaseDiscoveryProvider: Abstract interface for providers
- DiscoveryManager: Aggregates results from multiple providers
- Filters: Post-discovery filtering functions

Providers:
- JobSpyProvider: Uses JobSpy to search Indeed, Google Jobs, LinkedIn, etc.
- GoogleSearchProvider: Uses Google Search to find ATS job board URLs

Example:
    from sources.web_scraping.discovery import (
        DiscoveryManager,
        JobSpyProvider,
        GoogleSearchProvider
    )
    from sources.web_scraping.discovery.filters import create_location_filter

    # Create manager with providers
    manager = DiscoveryManager()
    manager.add_provider(JobSpyProvider())
    manager.add_provider(GoogleSearchProvider(platforms=['greenhouse', 'lever']))

    # Add filters
    manager.add_filter(create_location_filter(['Remote', 'New York']))

    # Discover jobs
    jobs = manager.discover_all(
        keywords='software engineer',
        location='Remote',
        max_results=100
    )
"""

import logging
from typing import List, Optional, Callable, Dict, Any

from .base_provider import BaseDiscoveryProvider, DiscoveredJob
from .filters import FilterFunc

logger = logging.getLogger(__name__)


class DiscoveryManager:
    """Manages multiple discovery providers and aggregates results.

    The DiscoveryManager:
    1. Runs all enabled providers in sequence
    2. Aggregates and deduplicates results by URL
    3. Applies post-discovery filters
    4. Returns a combined list of DiscoveredJob objects

    Attributes:
        providers: List of registered discovery providers
        filters: List of filter functions to apply

    Example:
        manager = DiscoveryManager()
        manager.add_provider(JobSpyProvider())
        manager.add_provider(GoogleSearchProvider())
        manager.add_filter(create_remote_only_filter())

        jobs = manager.discover_all(
            keywords='python developer',
            location='Remote'
        )
    """

    def __init__(self):
        """Initialize an empty DiscoveryManager."""
        self.providers: List[BaseDiscoveryProvider] = []
        self.filters: List[FilterFunc] = []

    def add_provider(self, provider: BaseDiscoveryProvider) -> None:
        """Add a discovery provider.

        Args:
            provider: A discovery provider instance.
        """
        self.providers.append(provider)
        logger.debug(f"Added discovery provider: {provider.provider_name}")

    def remove_provider(self, provider_name: str) -> bool:
        """Remove a provider by name.

        Args:
            provider_name: Name of the provider to remove.

        Returns:
            True if provider was found and removed, False otherwise.
        """
        for i, provider in enumerate(self.providers):
            if provider.provider_name == provider_name:
                self.providers.pop(i)
                logger.debug(f"Removed discovery provider: {provider_name}")
                return True
        return False

    def add_filter(self, filter_func: FilterFunc) -> None:
        """Add a post-discovery filter.

        Filters are applied after all providers have returned results,
        but before results are returned from discover_all().

        Args:
            filter_func: A function that takes DiscoveredJob and returns bool.
        """
        self.filters.append(filter_func)
        logger.debug("Added discovery filter")

    def clear_filters(self) -> None:
        """Remove all filters."""
        self.filters.clear()
        logger.debug("Cleared all discovery filters")

    def get_available_providers(self) -> List[BaseDiscoveryProvider]:
        """Get list of providers that are currently available.

        Returns:
            List of providers where is_available() returns True.
        """
        return [p for p in self.providers if p.is_available()]

    def discover_all(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_results: int = 100,
        **kwargs
    ) -> List[DiscoveredJob]:
        """Run all providers and aggregate results.

        Args:
            keywords: Search keywords (e.g., "software engineer")
            location: Location filter (e.g., "Remote", "New York")
            max_results: Total maximum results to return
            **kwargs: Provider-specific options passed to each provider

        Returns:
            Deduplicated, filtered list of DiscoveredJob objects.

        Note:
            Results are deduplicated by URL. The first occurrence of a URL
            is kept if multiple providers return the same job.
        """
        all_jobs: List[DiscoveredJob] = []
        seen_urls: set = set()

        available_providers = self.get_available_providers()

        if not available_providers:
            logger.warning("No discovery providers available")
            return []

        logger.info(
            f"Running {len(available_providers)} discovery providers "
            f"for keywords='{keywords}', location='{location}'"
        )

        # Calculate per-provider result limit
        results_per_provider = max(max_results // len(available_providers), 10)

        for provider in available_providers:
            try:
                logger.debug(
                    f"Running provider '{provider.provider_name}' "
                    f"(max_results={results_per_provider})"
                )

                jobs = provider.discover(
                    keywords=keywords,
                    location=location,
                    max_results=results_per_provider,
                    **kwargs
                )

                logger.info(
                    f"Provider '{provider.provider_name}' returned {len(jobs)} jobs"
                )

                # Deduplicate by URL
                for job in jobs:
                    if not job.url:
                        logger.debug("Skipping job without URL")
                        continue

                    # Normalize URL for deduplication
                    normalized_url = self._normalize_url(job.url)

                    if normalized_url not in seen_urls:
                        seen_urls.add(normalized_url)
                        all_jobs.append(job)
                    else:
                        logger.debug(f"Skipping duplicate URL: {job.url}")

            except Exception as e:
                logger.error(
                    f"Provider '{provider.provider_name}' failed: {e}",
                    exc_info=True
                )
                # Continue with other providers
                continue

        logger.info(f"Total unique jobs before filtering: {len(all_jobs)}")

        # Apply filters
        if self.filters:
            original_count = len(all_jobs)
            for filter_func in self.filters:
                all_jobs = [job for job in all_jobs if filter_func(job)]
            filtered_count = original_count - len(all_jobs)
            logger.info(f"Filtered out {filtered_count} jobs, {len(all_jobs)} remaining")

        return all_jobs

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication.

        Removes trailing slashes and fragments, but preserves query parameters
        since many job sites (like Indeed) use query params for job IDs.

        Args:
            url: The URL to normalize.

        Returns:
            Normalized URL string.
        """
        # Remove trailing slash
        url = url.rstrip('/')

        # Remove fragments only (keep query parameters for job ID)
        if '#' in url:
            url = url.split('#')[0]

        return url.lower()

    def __repr__(self) -> str:
        provider_names = [p.provider_name for p in self.providers]
        return (
            f"DiscoveryManager("
            f"providers={provider_names}, "
            f"filters={len(self.filters)})"
        )


# Import providers for convenience
# These are imported here to allow:
#   from sources.web_scraping.discovery import JobSpyProvider
try:
    from .jobspy_provider import JobSpyProvider
except ImportError:
    JobSpyProvider = None  # JobSpy not installed

try:
    from .google_search_provider import GoogleSearchProvider
except ImportError:
    GoogleSearchProvider = None  # googlesearch-python not installed

try:
    from .brave_search_provider import BraveSearchProvider
except ImportError:
    BraveSearchProvider = None  # requests not installed (unlikely)

try:
    from .serpapi_provider import SerpAPIProvider
except ImportError:
    SerpAPIProvider = None  # requests not installed (unlikely)


__all__ = [
    'BaseDiscoveryProvider',
    'DiscoveredJob',
    'DiscoveryManager',
    'JobSpyProvider',
    'GoogleSearchProvider',
    'BraveSearchProvider',
    'SerpAPIProvider',
    'FilterFunc',
]
