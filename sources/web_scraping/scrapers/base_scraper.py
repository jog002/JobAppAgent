"""Base class for ATS-specific scrapers."""
from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging
import hashlib

logger = logging.getLogger(__name__)


class BaseATSScraper(ABC):
    """Abstract base class for ATS platform scrapers."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Name of the ATS platform (e.g., 'greenhouse', 'lever')."""
        pass

    @abstractmethod
    def can_scrape(self, url: str) -> bool:
        """Check if this scraper can handle the given URL."""
        pass

    @abstractmethod
    def scrape_job(self, url: str) -> Optional[Dict]:
        """
        Scrape job details from a URL.

        Returns:
            Dictionary with job fields, or None if scraping failed
        """
        pass

    def extract_job_id(self, url: str) -> Optional[str]:
        """Extract job ID from URL (platform-specific)."""
        return None  # Override in subclass

    def _generate_fallback_job_id(self, url: str) -> str:
        """
        Generate a fallback job ID from URL hash if extraction fails.

        Uses SHA256 hash of URL, truncated to first 16 characters.
        This ensures every unique URL gets a unique, consistent ID.
        """
        url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
        return f"hash_{url_hash[:16]}"

    def _determine_remote_type(self, location: str, description: str) -> str:
        """Determine if job is remote, hybrid, or on-site."""
        location_lower = location.lower()
        # Check full description for better accuracy
        description_lower = description.lower()

        remote_keywords = ['remote', 'work from home', 'wfh', 'work-from-home']
        hybrid_keywords = ['hybrid']

        if any(keyword in location_lower for keyword in remote_keywords):
            return 'Remote'
        elif any(keyword in description_lower for keyword in remote_keywords):
            return 'Remote'
        elif any(keyword in location_lower for keyword in hybrid_keywords):
            return 'Hybrid'
        elif any(keyword in description_lower for keyword in hybrid_keywords):
            return 'Hybrid'
        else:
            return 'On-site'

    def _normalize_company_name(self, company_slug: str) -> str:
        """
        Normalize company name from URL slug.

        Handles common patterns like:
        - 'acme-corp' -> 'Acme Corp'
        - 'h-r-systems' -> 'HR Systems' (keeps common acronyms uppercase)
        - 'ai-ml-research' -> 'AI ML Research'
        """
        if not company_slug:
            return 'Unknown'

        # Replace separators with spaces
        name = company_slug.replace('-', ' ').replace('_', ' ')

        # Common acronyms that should stay uppercase
        acronyms = {'ai', 'ml', 'hr', 'it', 'io', 'ui', 'ux', 'api', 'sdk', 'aws', 'gcp'}

        # Title case each word, but preserve acronyms
        words = []
        for word in name.split():
            word_lower = word.lower()
            if word_lower in acronyms:
                words.append(word.upper())
            else:
                words.append(word.title())

        return ' '.join(words)
