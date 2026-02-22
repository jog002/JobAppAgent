"""Scraper for Lever ATS platform."""
import re
import logging
from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseATSScraper

logger = logging.getLogger(__name__)


class LeverScraper(BaseATSScraper):
    """Scraper for jobs.lever.co job postings."""

    @property
    def platform_name(self) -> str:
        return 'lever'

    def can_scrape(self, url: str) -> bool:
        """Check if URL is a Lever job posting."""
        return 'jobs.lever.co' in url or 'lever.co' in url

    def extract_job_id(self, url: str) -> Optional[str]:
        """Extract job ID from Lever URL."""
        # Lever URLs: https://jobs.lever.co/company/job-id-slug
        # Extract the last path component if it's after company name
        match = re.search(r'lever\.co/[^/]+/([^/]+)/?$', url)
        if match:
            return match.group(1)
        # Fallback: use last path segment if URL structure is different
        match = re.search(r'/([^/]+)/?$', url)
        job_id = match.group(1) if match else None
        # Avoid extracting domain parts as job_id
        if job_id and job_id not in ['co', 'lever', 'jobs']:
            return job_id
        return None

    def scrape_job(self, url: str) -> Optional[Dict]:
        """Scrape job details from Lever posting."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract company name
            company_elem = soup.find('a', class_='main-footer-logo')
            if company_elem and company_elem.has_attr('alt'):
                company = company_elem['alt']
            else:
                company = self._extract_company_from_url(url)

            # Extract job title
            title_elem = soup.find('h2', class_='posting-headline')
            title = title_elem.get_text(strip=True) if title_elem else 'Unknown'

            # Extract location
            location_elem = soup.find('div', class_='sort-by-location')
            if not location_elem:
                location_elem = soup.find('div', class_='location')
            location = location_elem.get_text(strip=True) if location_elem else 'Unknown'

            # Extract description
            content_elem = soup.find('div', class_='content')
            if not content_elem:
                content_elem = soup.find('div', class_='section-wrapper')
            description = content_elem.get_text(separator='\n', strip=True) if content_elem else ''

            # Determine if remote
            remote_type = self._determine_remote_type(location, description)

            # Extract job_id with fallback
            job_id = self.extract_job_id(url)
            if not job_id:
                logger.warning(f"Failed to extract job_id from {url}, using hash fallback")
                job_id = self._generate_fallback_job_id(url)

            return {
                'id': f"lever_{job_id}",
                'job_id': job_id,
                'title': title,
                'company': company,
                'url': url,
                'description': description,
                'location': location,
                'remote_type': remote_type,
                'salary_min': None,
                'salary_max': None,
                'posted_date': None
            }

        except requests.exceptions.Timeout:
            logger.error(f"Timeout scraping Lever job {url}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Rate limited on Lever {url}, backing off")
            else:
                logger.error(f"HTTP error scraping Lever {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to scrape Lever job {url}: {e}")
            return None

    def _extract_company_from_url(self, url: str) -> str:
        """Extract company name from Lever URL."""
        # URL format: https://jobs.lever.co/company/job-slug
        match = re.search(r'lever\.co/([^/]+)', url)
        if match:
            return self._normalize_company_name(match.group(1))
        return 'Unknown'
