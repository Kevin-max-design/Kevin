"""Scrapers module for Job Application Agent."""

from .base_scraper import BaseScraper
from .indeed import IndeedScraper
from .linkedin import LinkedInScraper
from .naukri import NaukriScraper
from .glassdoor import GlassdoorScraper
from .angellist import AngelListScraper

# Registry of all available scrapers
SCRAPERS = {
    "indeed": IndeedScraper,
    "linkedin": LinkedInScraper,
    "naukri": NaukriScraper,
    "glassdoor": GlassdoorScraper,
    "angellist": AngelListScraper,
    "wellfound": AngelListScraper,  # Alias
}


def get_scraper(platform: str, config: dict) -> BaseScraper:
    """Get a scraper instance for the specified platform.
    
    Args:
        platform: Platform name (e.g., 'linkedin', 'indeed')
        config: Configuration dictionary
        
    Returns:
        Scraper instance
        
    Raises:
        ValueError: If platform is not supported
    """
    platform = platform.lower()
    if platform not in SCRAPERS:
        raise ValueError(f"Unsupported platform: {platform}. Available: {list(SCRAPERS.keys())}")
    
    return SCRAPERS[platform](config)


def get_all_scrapers(config: dict) -> list:
    """Get instances of all available scrapers.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of scraper instances
    """
    # Exclude duplicates (wellfound is an alias for angellist)
    unique_platforms = ["indeed", "linkedin", "naukri", "glassdoor", "angellist"]
    return [SCRAPERS[p](config) for p in unique_platforms]


__all__ = [
    "BaseScraper",
    "IndeedScraper",
    "LinkedInScraper",
    "NaukriScraper",
    "GlassdoorScraper",
    "AngelListScraper",
    "SCRAPERS",
    "get_scraper",
    "get_all_scrapers",
]
