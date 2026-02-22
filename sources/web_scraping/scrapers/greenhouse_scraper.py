"""Scraper for Greenhouse ATS platform."""
import re
import logging
from typing import Dict, Optional
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseATSScraper

logger = logging.getLogger(__name__)

# Common headers to avoid being blocked
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# Greenhouse public API endpoint
GREENHOUSE_API_BASE = 'https://boards-api.greenhouse.io/v1/boards'


class GreenhouseScraper(BaseATSScraper):
    """Scraper for boards.greenhouse.io job postings."""

    @property
    def platform_name(self) -> str:
        return 'greenhouse'

    def can_scrape(self, url: str) -> bool:
        """Check if URL is a Greenhouse job posting."""
        return 'boards.greenhouse.io' in url or 'greenhouse.io' in url

    def extract_job_id(self, url: str) -> Optional[str]:
        """Extract job ID from Greenhouse URL."""
        # Greenhouse URLs: https://boards.greenhouse.io/company/jobs/123456
        # Also handles: https://careers.company.com/jobs/123456?gh_jid=123456
        match = re.search(r'/jobs/(\d+)', url)
        if match:
            return match.group(1)
        # Try gh_jid parameter
        match = re.search(r'gh_jid=(\d+)', url)
        return match.group(1) if match else None

    def _extract_company_from_url(self, url: str) -> str:
        """Extract company name from Greenhouse URL."""
        # URL format: https://boards.greenhouse.io/company/jobs/123
        match = re.search(r'boards\.greenhouse\.io/([^/]+)', url)
        if match:
            return self._normalize_company_name(match.group(1))
        # Try pattern for custom domains that still use Greenhouse
        match = re.search(r'greenhouse\.io/([^/]+)', url)
        if match:
            return self._normalize_company_name(match.group(1))
        return 'Unknown'

    def _scrape_via_api(self, company: str, job_id: str, url: str) -> Optional[Dict]:
        """
        Scrape job using Greenhouse's public JSON API.

        API endpoint: https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}
        """
        api_url = f"{GREENHOUSE_API_BASE}/{company}/jobs/{job_id}"

        try:
            response = requests.get(api_url, timeout=15, headers=DEFAULT_HEADERS)

            if response.status_code == 404:
                logger.info(f"Job not found via API (404): {api_url}")
                return None

            response.raise_for_status()
            data = response.json()

            # Extract fields from API response
            title = data.get('title', 'Unknown')

            # Location can be a nested object or string
            location_data = data.get('location', {})
            if isinstance(location_data, dict):
                location = location_data.get('name', 'Unknown')
            else:
                location = str(location_data) if location_data else 'Unknown'

            # Content is HTML, convert to plain text
            content_html = data.get('content', '')
            description = ''
            if content_html:
                soup = BeautifulSoup(content_html, 'html.parser')
                description = soup.get_text(separator='\n', strip=True)

            # Use absolute_url if available, otherwise use original
            job_url = data.get('absolute_url', url)

            # Determine remote type from location and description
            remote_type = self._determine_remote_type(location, description)

            # Normalize company name
            company_name = self._normalize_company_name(company)

            return {
                'id': f"greenhouse_{job_id}",
                'job_id': job_id,
                'title': title,
                'company': company_name,
                'url': job_url,
                'description': description,
                'location': location,
                'remote_type': remote_type,
                'salary_min': None,
                'salary_max': None,
                'posted_date': data.get('updated_at')
            }

        except requests.exceptions.RequestException as e:
            logger.warning(f"API request failed for {api_url}: {e}")
            return None
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse API response for {api_url}: {e}")
            return None

    def scrape_job(self, url: str, max_retries: int = 2) -> Optional[Dict]:
        """
        Scrape job details from Greenhouse posting.

        Uses Greenhouse's public JSON API for reliable data extraction.
        Falls back to HTML scraping if API fails.

        Returns job dict with: id, title, company, description, location, etc.
        Returns None if job is unavailable or scraping fails.

        Args:
            url: Greenhouse job URL to scrape
            max_retries: Number of retry attempts on timeout (default 2)
        """
        import time

        # Extract company and job_id from URL
        company = self._extract_company_from_url(url)
        job_id = self.extract_job_id(url)

        if not job_id:
            logger.warning(f"Could not extract job ID from URL: {url}")
            return None

        # For API, we need the company slug from URL
        match = re.search(r'boards\.greenhouse\.io/([^/]+)', url)
        company_slug = match.group(1) if match else None

        # Try API first (most reliable)
        if company_slug:
            result = self._scrape_via_api(company_slug, job_id, url)
            if result:
                return result
            logger.info(f"API scrape failed for {url}, trying HTML fallback")

        # Fallback to HTML scraping for custom domains or API failures
        for attempt in range(max_retries + 1):
            try:
                response = requests.get(url, timeout=15, headers=DEFAULT_HEADERS)

                # Check for redirect to error page (job removed)
                if 'error=true' in response.url or 'error' in response.url.split('?')[-1]:
                    logger.info(f"Job no longer available (redirected to error): {url}")
                    return None

                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # Check for "job closed" indicators in page content
                page_text = soup.get_text().lower()
                closed_indicators = [
                    'no longer available',
                    'no longer accepting',
                    'position has been filled',
                    'job has been closed',
                    'this job is no longer',
                ]

                for indicator in closed_indicators:
                    if indicator in page_text:
                        logger.info(f"Job closed ('{indicator}'): {url}")
                        return None

                # Extract job title - try multiple selectors for different Greenhouse layouts
                title = 'Unknown'
                # New layout: section-header class
                title_elem = soup.find('h1', class_='section-header')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    # Legacy layout: app-title class
                    title_elem = soup.find('h1', class_='app-title')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                    else:
                        # Fallback: parse from <title> tag "Job Application for TITLE at COMPANY"
                        title_tag = soup.find('title')
                        if title_tag:
                            title_text = title_tag.get_text(strip=True)
                            match = re.search(r'Job Application for (.+?) at', title_text)
                            if match:
                                title = match.group(1).strip()

                # Extract location - try multiple selectors
                location = 'Unknown'
                # New layout: job__location class
                location_elem = soup.find('div', class_='job__location')
                if location_elem:
                    location = location_elem.get_text(strip=True)
                else:
                    # Legacy layout: location class
                    location_elem = soup.find('div', class_='location')
                    if location_elem:
                        location = location_elem.get_text(strip=True)

                # Extract description - try multiple selectors
                description = ''
                # New layout: job__description with body class
                content_elem = soup.find('div', class_='job__description')
                if content_elem:
                    description = content_elem.get_text(separator='\n', strip=True)
                else:
                    # Alternative: just body class within job section
                    content_elem = soup.find('div', class_='body')
                    if content_elem:
                        description = content_elem.get_text(separator='\n', strip=True)
                    else:
                        # Legacy layout: content id
                        content_elem = soup.find('div', id='content')
                        if content_elem:
                            description = content_elem.get_text(separator='\n', strip=True)

                # Determine if remote
                remote_type = self._determine_remote_type(location, description)

                # Use extracted job_id or generate fallback
                if not job_id:
                    logger.warning(f"Failed to extract job_id from {url}, using hash fallback")
                    job_id = self._generate_fallback_job_id(url)

                return {
                    'id': f"greenhouse_{job_id}",
                    'job_id': job_id,
                    'title': title,
                    'company': company,
                    'url': url,
                    'description': description,
                    'location': location,
                    'remote_type': remote_type,
                    'salary_min': None,  # Greenhouse doesn't always show salary
                    'salary_max': None,
                    'posted_date': None
                }

            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s
                    logger.warning(f"Timeout scraping {url}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Timeout scraping Greenhouse job {url} after {max_retries + 1} attempts")
                    return None
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    logger.info(f"Job not found (404): {url}")
                    return None
                elif e.response.status_code == 429:
                    if attempt < max_retries:
                        wait_time = 5 * (attempt + 1)  # Rate limit: wait longer
                        logger.warning(f"Rate limited on {url}, waiting {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Rate limited on Greenhouse {url}, giving up")
                        return None
                elif e.response.status_code >= 500:
                    # Server error - might be temporary
                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Server error {e.response.status_code} for {url}, retrying in {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Server error scraping Greenhouse {url}: {e}")
                        return None
                else:
                    logger.error(f"HTTP error scraping Greenhouse {url}: {e}")
                    return None
            except Exception as e:
                logger.error(f"Failed to scrape Greenhouse job {url}: {e}")
                return None

        return None  # Should not reach here
