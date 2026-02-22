"""ATS scrapers module."""
from typing import Optional
from .base_scraper import BaseATSScraper
from .greenhouse_scraper import GreenhouseScraper
from .lever_scraper import LeverScraper
from .bamboohr_scraper import BambooHRScraper
from .ashby_scraper import AshbyScraper

# Registry of scrapers
_SCRAPERS = [
    GreenhouseScraper(),
    LeverScraper(),
    BambooHRScraper(),
    AshbyScraper()
]


def get_scraper(url: str) -> Optional[BaseATSScraper]:
    """Get the appropriate scraper for a given URL."""
    for scraper in _SCRAPERS:
        if scraper.can_scrape(url):
            return scraper
    return None


def get_all_scrapers():
    """Get all available scrapers."""
    return _SCRAPERS


__all__ = [
    'BaseATSScraper',
    'GreenhouseScraper',
    'LeverScraper',
    'BambooHRScraper',
    'AshbyScraper',
    'get_scraper',
    'get_all_scrapers'
]
