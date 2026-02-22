"""LinkedIn job source implementation."""
from pathlib import Path
from typing import List, Dict
import logging

from ..base_source import BaseJobSource
from . import linkedin_client

logger = logging.getLogger(__name__)


class LinkedInSource(BaseJobSource):
    """LinkedIn job source using MCP server."""

    @property
    def source_name(self) -> str:
        return 'linkedin'

    def search_jobs(self, keywords: str, location: str = None, **kwargs) -> List[Dict]:
        """Search LinkedIn via MCP server."""
        try:
            jobs = linkedin_client.search_jobs(keywords, location)
            return [self.normalize_job(job) for job in jobs]
        except Exception as e:
            logger.error(f"LinkedIn search failed: {e}")
            return []

    def is_available(self) -> bool:
        """Check if LinkedIn MCP is configured."""
        try:
            from config import LINKEDIN_COOKIE, LINKEDIN_SESSION_PATH
            return bool(LINKEDIN_COOKIE or (LINKEDIN_SESSION_PATH and Path(LINKEDIN_SESSION_PATH).exists()))
        except ImportError:
            logger.warning("Could not import LinkedIn config")
            return False

    def normalize_job(self, job: Dict) -> Dict:
        """Normalize LinkedIn job data."""
        return {
            'source': 'linkedin',
            'job_id': job.get('id') or job.get('linkedin_job_id') or '',
            'title': job.get('title', 'Unknown Title'),
            'company': job.get('company', 'Unknown Company'),
            'url': job.get('url', ''),
            'description': job.get('description', ''),
            'location': job.get('location', ''),
            'remote_type': job.get('remote_type', 'Unknown'),
            'salary_min': job.get('salary_min'),
            'salary_max': job.get('salary_max'),
            'posted_date': job.get('posted_date')
        }


# Register this source
from .. import register_source
register_source('linkedin')(LinkedInSource)
