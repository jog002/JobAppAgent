"""Post-discovery filters for job results.

These filters are applied after jobs are discovered but before scraping,
allowing you to reduce the number of jobs that need detailed processing.

Filters are functions that take a DiscoveredJob and return True to keep it,
or False to filter it out.
"""

from typing import Callable, List
import logging

from .base_provider import DiscoveredJob

logger = logging.getLogger(__name__)


# Type alias for filter functions
FilterFunc = Callable[[DiscoveredJob], bool]


def create_location_filter(allowed_locations: List[str]) -> FilterFunc:
    """Create a filter that keeps jobs matching allowed locations.

    Args:
        allowed_locations: List of location strings to allow.
            Uses case-insensitive partial matching.
            Example: ['Remote', 'New York', 'San Francisco']

    Returns:
        A filter function that returns True for jobs in allowed locations.

    Note:
        Jobs without a location field are kept (they may get location
        after scraping and can be filtered later).

    Example:
        filter_fn = create_location_filter(['Remote', 'NYC'])
        filtered_jobs = [j for j in jobs if filter_fn(j)]
    """
    allowed_lower = [loc.lower() for loc in allowed_locations]

    def filter_func(job: DiscoveredJob) -> bool:
        if not job.location:
            # Keep jobs without location - they may get it after scraping
            return True

        job_loc_lower = job.location.lower()
        return any(loc in job_loc_lower for loc in allowed_lower)

    return filter_func


def create_remote_only_filter() -> FilterFunc:
    """Create a filter that keeps only remote jobs.

    Returns:
        A filter function that returns True only for remote jobs.

    Note:
        Jobs without a location field are kept (they may be remote
        but just not labeled as such in the initial discovery).
    """
    def filter_func(job: DiscoveredJob) -> bool:
        if not job.location:
            return True
        return 'remote' in job.location.lower()

    return filter_func


def create_exclude_locations_filter(excluded_locations: List[str]) -> FilterFunc:
    """Create a filter that excludes jobs in certain locations.

    Args:
        excluded_locations: List of location strings to exclude.
            Uses case-insensitive partial matching.
            Example: ['India', 'Philippines', 'Overseas']

    Returns:
        A filter function that returns False for jobs in excluded locations.
    """
    excluded_lower = [loc.lower() for loc in excluded_locations]

    def filter_func(job: DiscoveredJob) -> bool:
        if not job.location:
            return True

        job_loc_lower = job.location.lower()
        return not any(loc in job_loc_lower for loc in excluded_lower)

    return filter_func


def create_title_keywords_filter(required_keywords: List[str]) -> FilterFunc:
    """Create a filter that requires certain keywords in job title.

    Args:
        required_keywords: List of keywords (any match keeps the job).
            Uses case-insensitive partial matching.
            Example: ['engineer', 'developer', 'programmer']

    Returns:
        A filter function that returns True if title contains any keyword.

    Note:
        Jobs without a title are kept (title comes from scraping).
    """
    required_lower = [kw.lower() for kw in required_keywords]

    def filter_func(job: DiscoveredJob) -> bool:
        if not job.title:
            return True

        title_lower = job.title.lower()
        return any(kw in title_lower for kw in required_lower)

    return filter_func


def create_exclude_title_keywords_filter(excluded_keywords: List[str]) -> FilterFunc:
    """Create a filter that excludes jobs with certain title keywords.

    Args:
        excluded_keywords: List of keywords to exclude.
            Uses case-insensitive partial matching.
            Example: ['senior', 'lead', 'manager', 'director']

    Returns:
        A filter function that returns False if title contains any keyword.

    Example:
        # Exclude senior/lead roles
        filter_fn = create_exclude_title_keywords_filter(['senior', 'lead', 'principal'])
    """
    excluded_lower = [kw.lower() for kw in excluded_keywords]

    def filter_func(job: DiscoveredJob) -> bool:
        if not job.title:
            return True

        title_lower = job.title.lower()
        return not any(kw in title_lower for kw in excluded_lower)

    return filter_func


def create_company_filter(allowed_companies: List[str]) -> FilterFunc:
    """Create a filter that keeps only jobs from specific companies.

    Args:
        allowed_companies: List of company names to allow.
            Uses case-insensitive partial matching.
            Example: ['Google', 'Meta', 'Amazon']

    Returns:
        A filter function that returns True for jobs at allowed companies.
    """
    allowed_lower = [co.lower() for co in allowed_companies]

    def filter_func(job: DiscoveredJob) -> bool:
        if not job.company:
            return True

        company_lower = job.company.lower()
        return any(co in company_lower for co in allowed_lower)

    return filter_func


def create_exclude_companies_filter(excluded_companies: List[str]) -> FilterFunc:
    """Create a filter that excludes jobs from specific companies.

    Args:
        excluded_companies: List of company names to exclude.
            Uses case-insensitive partial matching.
            Example: ['Recruiting Agency', 'Staffing Solutions']

    Returns:
        A filter function that returns False for jobs at excluded companies.
    """
    excluded_lower = [co.lower() for co in excluded_companies]

    def filter_func(job: DiscoveredJob) -> bool:
        if not job.company:
            return True

        company_lower = job.company.lower()
        return not any(co in company_lower for co in excluded_lower)

    return filter_func


def create_platform_filter(allowed_platforms: List[str]) -> FilterFunc:
    """Create a filter that keeps only jobs from specific platforms.

    Args:
        allowed_platforms: List of platform names to allow.
            Example: ['greenhouse', 'lever', 'indeed']

    Returns:
        A filter function that returns True for jobs from allowed platforms.
    """
    allowed_lower = [p.lower() for p in allowed_platforms]

    def filter_func(job: DiscoveredJob) -> bool:
        if not job.source_platform:
            return True

        return job.source_platform.lower() in allowed_lower

    return filter_func


def combine_filters(*filters: FilterFunc) -> FilterFunc:
    """Combine multiple filters with AND logic.

    All filters must return True for the job to be kept.

    Args:
        *filters: Filter functions to combine.

    Returns:
        A combined filter function.

    Example:
        combined = combine_filters(
            create_remote_only_filter(),
            create_exclude_title_keywords_filter(['senior', 'lead'])
        )
    """
    def combined_filter(job: DiscoveredJob) -> bool:
        return all(f(job) for f in filters)

    return combined_filter


def create_or_filters(*filters: FilterFunc) -> FilterFunc:
    """Combine multiple filters with OR logic.

    Any filter returning True will keep the job.

    Args:
        *filters: Filter functions to combine.

    Returns:
        A combined filter function.
    """
    def combined_filter(job: DiscoveredJob) -> bool:
        return any(f(job) for f in filters)

    return combined_filter
