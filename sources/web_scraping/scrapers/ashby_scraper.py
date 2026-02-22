"""Scraper for Ashby ATS platform."""
import re
import logging
from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseATSScraper

logger = logging.getLogger(__name__)


class AshbyScraper(BaseATSScraper):
    """Scraper for *.ashbyhq.com job postings."""

    @property
    def platform_name(self) -> str:
        return 'ashby'

    def can_scrape(self, url: str) -> bool:
        """Check if URL is an Ashby job posting."""
        return 'ashbyhq.com' in url

    def extract_job_id(self, url: str) -> Optional[str]:
        """Extract job ID from Ashby URL."""
        # Ashby URLs: https://jobs.ashbyhq.com/company/job-id or similar
        # Try UUID-style job ID (common for Ashby)
        match = re.search(r'/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/?$', url)
        if match:
            return match.group(1)

        # Try alphanumeric with hyphens (job slug)
        match = re.search(r'ashbyhq\.com/[^/]+/([a-z0-9\-]+)/?$', url)
        if match:
            job_id = match.group(1)
            # Limit fallback ID length to avoid overly long IDs
            if len(job_id) < 100:
                return job_id

        # Last resort: hash the URL
        return None

    def scrape_job(self, url: str) -> Optional[Dict]:
        """Scrape job details from Ashby posting."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract company name
            company = self._extract_company_from_url(url)

            # Extract job title - Ashby typically uses h1 or specific classes
            title = None
            title_selectors = ['h1', 'h2', '.job-title', 'div[class*="title"]']
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title and len(title) > 5:
                        break
            title = title or 'Unknown'

            # Extract location
            location = 'Unknown'
            location_selectors = ['.location', 'div[class*="location"]', 'span[class*="location"]']
            for selector in location_selectors:
                location_elem = soup.select_one(selector)
                if location_elem:
                    location = location_elem.get_text(strip=True)
                    if location and len(location) > 2:
                        break

            # Extract description
            description = ''
            content_selectors = ['div[class*="description"]', 'div[class*="content"]', 'main', 'article']
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    description = content_elem.get_text(separator='\n', strip=True)
                    if description and len(description) > 100:
                        break

            # Determine if remote
            remote_type = self._determine_remote_type(location, description)

            # Extract job_id with fallback
            job_id = self.extract_job_id(url)
            if not job_id:
                logger.warning(f"Failed to extract job_id from {url}, using hash fallback")
                job_id = self._generate_fallback_job_id(url)

            return {
                'id': f"ashby_{job_id}",
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
            logger.error(f"Timeout scraping Ashby job {url}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Rate limited on Ashby {url}, backing off")
            else:
                logger.error(f"HTTP error scraping Ashby {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to scrape Ashby job {url}: {e}")
            return None

    def _extract_company_from_url(self, url: str) -> str:
        """Extract company name from Ashby URL or subdomain."""
        # Check for subdomain pattern
        match = re.search(r'https?://jobs\.([^.]+)\.ashbyhq\.com', url)
        if match:
            return self._normalize_company_name(match.group(1))

        # Check for path pattern: https://jobs.ashbyhq.com/company/...
        match = re.search(r'ashbyhq\.com/([^/]+)', url)
        if match:
            return self._normalize_company_name(match.group(1))

        return 'Unknown'
