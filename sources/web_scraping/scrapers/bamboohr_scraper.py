"""Scraper for BambooHR ATS platform."""
import re
import logging
from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseATSScraper

logger = logging.getLogger(__name__)


class BambooHRScraper(BaseATSScraper):
    """Scraper for *.bamboohr.com/careers job postings."""

    @property
    def platform_name(self) -> str:
        return 'bamboohr'

    def can_scrape(self, url: str) -> bool:
        """Check if URL is a BambooHR job posting."""
        return 'bamboohr.com' in url

    def extract_job_id(self, url: str) -> Optional[str]:
        """Extract job ID from BambooHR URL."""
        # BambooHR URLs vary: https://company.bamboohr.com/careers/123
        match = re.search(r'/careers/(\d+)', url)
        if match:
            return match.group(1)

        # Try other numeric ID patterns
        match = re.search(r'/(\d+)/?$', url)
        if match:
            return match.group(1)

        # Fallback: use path components but limit length
        match = re.search(r'bamboohr\.com/(.+?)/?$', url)
        if match:
            path = match.group(1).replace('/', '_')
            # Limit to reasonable length
            if len(path) < 50:
                return path

        return None

    def scrape_job(self, url: str) -> Optional[Dict]:
        """Scrape job details from BambooHR posting."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract company name from subdomain
            company = self._extract_company_from_url(url)

            # Extract job title - BambooHR uses various selectors
            title = None
            title_selectors = ['h1', '.job-title', '.position-title', 'h2']
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title and len(title) > 5:  # Validate it's not just a label
                        break
            title = title or 'Unknown'

            # Extract location
            location = 'Unknown'
            location_selectors = ['.location', '.job-location', 'div[class*="location"]']
            for selector in location_selectors:
                location_elem = soup.select_one(selector)
                if location_elem:
                    location = location_elem.get_text(strip=True)
                    break

            # Extract description - look for main content area
            description = ''
            content_selectors = ['.job-description', '.description', 'div[class*="description"]', 'main']
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
                'id': f"bamboohr_{job_id}",
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
            logger.error(f"Timeout scraping BambooHR job {url}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Rate limited on BambooHR {url}, backing off")
            else:
                logger.error(f"HTTP error scraping BambooHR {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to scrape BambooHR job {url}: {e}")
            return None

    def _extract_company_from_url(self, url: str) -> str:
        """Extract company name from BambooHR subdomain."""
        # URL format: https://company.bamboohr.com/careers/123
        match = re.search(r'https?://([^.]+)\.bamboohr\.com', url)
        if match:
            return self._normalize_company_name(match.group(1))
        return 'Unknown'
