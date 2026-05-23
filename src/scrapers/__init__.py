"""
Social media scraper module for CrawlStory.

This module contains the Factory Pattern implementation for platform scrapers.
Scrapers are implemented following the BaseScraper abstract class pattern.

Available scrapers:
- TikTok: Fetches videos from TikTok user profiles

Usage:
    >>> from scrapers import ScraperFactory
    >>> scraper = ScraperFactory.get_scraper("tiktok")
    >>> videos = await scraper.fetch_latest_videos("coolcreator", limit=10)
"""

from .base import (
    BaseScraper,
    ScrapedVideo,
    ScraperError,
    ScraperAPIError,
    ScraperRateLimitError,
    ScraperNotFoundError,
    ScraperTimeoutError,
)
from .factory import ScraperFactory, UnsupportedPlatformError
from .tiktok import TikTokScraper


# Auto-register available scrapers
ScraperFactory.register("tiktok", TikTokScraper)


__all__ = [
    # Base classes and data models
    "BaseScraper",
    "ScrapedVideo",
    
    # Factory
    "ScraperFactory",
    
    # Exceptions
    "ScraperError",
    "ScraperAPIError",
    "ScraperRateLimitError",
    "ScraperNotFoundError",
    "ScraperTimeoutError",
    "UnsupportedPlatformError",
    
    # Platform scrapers
    "TikTokScraper",
]
