"""ATS job board crawler for extracting job listing URLs.

This crawler parses ATS job board listing pages to extract individual job URLs.
It supports Greenhouse, Lever, BambooHR, and Ashby platforms.
"""

import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class ATSCrawler:
    """Crawler for extracting job URLs from ATS listing pages."""

    def __init__(self, timeout=10):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def crawl_company(
        self,
        company: Dict[str, str],
        keywords: Optional[List[str]] = None,
        location: Optional[str] = None
    ) -> List[str]:
        """
        Crawl a company's ATS job board and extract matching job URLs.

        Args:
            company: Dict with 'name', 'ats', and 'url' fields
            keywords: Optional list of keywords to filter jobs (e.g., ['engineer', 'software'])
            location: Optional location to filter jobs (e.g., 'Remote', 'New York')

        Returns:
            List of job posting URLs
        """
        ats_platform = company.get('ats')
        url = company.get('url')
        company_name = company.get('name')

        if not ats_platform or not url:
            logger.warning(f"Invalid company entry: {company}")
            return []

        logger.info(f"Crawling {company_name} ({ats_platform}): {url}")

        try:
            if ats_platform == 'greenhouse':
                return self._crawl_greenhouse(url, keywords, location)
            elif ats_platform == 'lever':
                return self._crawl_lever(url, keywords, location)
            elif ats_platform == 'bamboohr':
                return self._crawl_bamboohr(url, keywords, location)
            elif ats_platform == 'ashby':
                return self._crawl_ashby(url, keywords, location)
            else:
                logger.warning(f"Unsupported ATS platform: {ats_platform}")
                return []

        except requests.exceptions.Timeout:
            logger.error(f"Timeout crawling {company_name}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error crawling {company_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error crawling {company_name}: {e}")
            return []

    def _crawl_greenhouse(
        self,
        base_url: str,
        keywords: Optional[List[str]],
        location: Optional[str]
    ) -> List[str]:
        """Crawl Greenhouse job board listing page."""
        response = requests.get(base_url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        job_urls = []

        # Greenhouse uses <div class="opening"> for each job listing
        for opening in soup.find_all('div', class_='opening'):
            # Extract job URL
            link = opening.find('a')
            if not link or not link.get('href'):
                continue

            job_url = urljoin(base_url, link['href'])

            # Extract job title and location for filtering
            title_elem = opening.find('a')
            title = title_elem.get_text(strip=True) if title_elem else ''

            location_elem = opening.find('span', class_='location')
            job_location = location_elem.get_text(strip=True) if location_elem else ''

            # Apply filters
            if keywords and not self._matches_keywords(title, keywords):
                continue

            if location and not self._matches_location(job_location, location):
                continue

            job_urls.append(job_url)

        logger.info(f"Found {len(job_urls)} matching jobs on Greenhouse")
        return job_urls

    def _crawl_lever(
        self,
        base_url: str,
        keywords: Optional[List[str]],
        location: Optional[str]
    ) -> List[str]:
        """Crawl Lever job board listing page."""
        response = requests.get(base_url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        job_urls = []

        # Lever uses <a class="posting-title"> for job links
        for posting in soup.find_all('a', class_='posting-title'):
            job_url = posting.get('href')
            if not job_url:
                continue

            # Make absolute URL
            job_url = urljoin(base_url, job_url)

            # Extract title for filtering
            title = posting.get_text(strip=True)

            # Extract location (usually in a sibling element)
            parent = posting.find_parent()
            location_elem = parent.find(class_='sort-by-location') if parent else None
            job_location = location_elem.get_text(strip=True) if location_elem else ''

            # Apply filters
            if keywords and not self._matches_keywords(title, keywords):
                continue

            if location and not self._matches_location(job_location, location):
                continue

            job_urls.append(job_url)

        logger.info(f"Found {len(job_urls)} matching jobs on Lever")
        return job_urls

    def _crawl_bamboohr(
        self,
        base_url: str,
        keywords: Optional[List[str]],
        location: Optional[str]
    ) -> List[str]:
        """Crawl BambooHR careers page."""
        response = requests.get(base_url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        job_urls = []

        # BambooHR varies by company, but typically has job links in the careers page
        # Look for links containing '/careers/' or '/jobs/'
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/careers/' not in href and '/jobs/' not in href:
                continue

            job_url = urljoin(base_url, href)

            # Extract title for filtering
            title = link.get_text(strip=True)

            # Try to find location nearby
            parent = link.find_parent()
            location_text = parent.get_text(strip=True) if parent else ''

            # Apply filters
            if keywords and not self._matches_keywords(title, keywords):
                continue

            if location and not self._matches_location(location_text, location):
                continue

            job_urls.append(job_url)

        logger.info(f"Found {len(job_urls)} matching jobs on BambooHR")
        return job_urls

    def _crawl_ashby(
        self,
        base_url: str,
        keywords: Optional[List[str]],
        location: Optional[str]
    ) -> List[str]:
        """Crawl Ashby job board listing page."""
        response = requests.get(base_url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        job_urls = []

        # Ashby typically uses links with job IDs in the path
        # Look for links that appear to be job postings
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Ashby job URLs typically contain the job ID or slug
            if 'ashbyhq.com' not in href and not href.startswith('/'):
                continue

            job_url = urljoin(base_url, href)

            # Skip if it looks like a navigation link
            if any(skip in href for skip in ['/jobs', '/careers', '/apply', '#']):
                if href.count('/') < 2:  # Skip listing pages, keep individual job pages
                    continue

            # Extract title for filtering
            title = link.get_text(strip=True)

            # Try to find location nearby
            parent = link.find_parent()
            location_text = parent.get_text(strip=True) if parent else ''

            # Apply filters
            if keywords and not self._matches_keywords(title, keywords):
                continue

            if location and not self._matches_location(location_text, location):
                continue

            job_urls.append(job_url)

        logger.info(f"Found {len(job_urls)} matching jobs on Ashby")
        return job_urls

    def _matches_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the keywords (case-insensitive)."""
        if not keywords:
            return True

        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)

    def _matches_location(self, job_location: str, target_location: str) -> bool:
        """Check if job location matches target location (case-insensitive)."""
        if not target_location:
            return True

        job_location_lower = job_location.lower()
        target_lower = target_location.lower()

        # Exact match or contains
        return target_lower in job_location_lower
