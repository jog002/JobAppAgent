"""Abstract base class for job sources."""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseJobSource(ABC):
    """Base class for all job sources."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this source (e.g., 'linkedin', 'greenhouse')."""
        pass

    @abstractmethod
    def search_jobs(self, keywords: str, location: str = None, **kwargs) -> List[Dict]:
        """
        Search for jobs using source-specific logic.

        Args:
            keywords: Search keywords
            location: Location filter (optional)
            **kwargs: Source-specific parameters

        Returns:
            List of job dictionaries with standardized fields
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this source is properly configured and available."""
        pass

    @property
    def consolidates_locations(self) -> bool:
        """Whether this source handles all locations in a single search.

        If True, the source builds queries that include all location terms
        (e.g., via OR groups) and should only be called once, not per-location.

        Default: False (search once per location)
        """
        return False

    def normalize_job(self, job: Dict) -> Dict:
        """
        Normalize job data to standard format.

        Standard fields:
            - source: str (e.g., 'linkedin', 'greenhouse')
            - job_id: str (unique within source)
            - title: str
            - company: str
            - url: str
            - description: str (optional)
            - location: str (optional)
            - remote_type: str (optional)
            - salary_min: int (optional)
            - salary_max: int (optional)
            - posted_date: str (optional)
        """
        return {
            'source': self.source_name,
            'job_id': job.get('job_id') or job.get('id') or f"unknown_{hash(job.get('url', ''))}",
            'title': job.get('title') or 'Untitled Position',
            'company': job.get('company') or 'Unknown Company',
            'url': job.get('url') or '',
            'description': job.get('description', ''),
            'location': job.get('location', ''),
            'remote_type': job.get('remote_type', 'Unknown'),
            'salary_min': job.get('salary_min'),
            'salary_max': job.get('salary_max'),
            'posted_date': job.get('posted_date')
        }
