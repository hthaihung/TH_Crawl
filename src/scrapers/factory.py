"""
Scraper factory for instantiating platform-specific scrapers.

This module implements the Factory Pattern to provide a clean interface
for creating scraper instances without tight coupling to specific implementations.
"""

import logging
from typing import Optional

from .base import BaseScraper, ScraperError


logger = logging.getLogger(__name__)


class UnsupportedPlatformError(ScraperError):
    """Raised when attempting to create a scraper for an unsupported platform."""
    pass


class ScraperFactory:
    """
    Factory class for creating platform-specific scraper instances.
    
    This factory uses a registry pattern to map platform names to their
    corresponding scraper classes. New platforms can be added by registering
    them with the `register()` method.
    
    The factory ensures that:
    - Only one scraper instance exists per platform (singleton per platform)
    - Platform names are case-insensitive
    - Clear error messages for unsupported platforms
    - Easy extension for new platforms
    
    Example:
        >>> factory = ScraperFactory()
        >>> tiktok_scraper = factory.get_scraper("tiktok")
        >>> videos = await tiktok_scraper.fetch_latest_videos("coolcreator")
    """
    
    # Class-level registry mapping platform names to scraper classes
    _registry: dict[str, type[BaseScraper]] = {}
    
    # Singleton instances cache
    _instances: dict[str, BaseScraper] = {}
    
    @classmethod
    def register(cls, platform: str, scraper_class: type[BaseScraper]) -> None:
        """
        Register a new scraper class for a platform.
        
        This method allows dynamic registration of new scrapers at runtime,
        making it easy to extend the system with new platforms without
        modifying the factory code.
        
        Args:
            platform: Platform identifier (e.g., 'tiktok', 'instagram').
            scraper_class: The scraper class to register (must inherit from BaseScraper).
        
        Raises:
            TypeError: If scraper_class doesn't inherit from BaseScraper.
        
        Example:
            >>> ScraperFactory.register("tiktok", TikTokScraper)
            >>> ScraperFactory.register("instagram", InstagramScraper)
        """
        if not issubclass(scraper_class, BaseScraper):
            raise TypeError(
                f"Scraper class must inherit from BaseScraper, "
                f"got {scraper_class.__name__}"
            )
        
        platform_key = platform.lower()
        cls._registry[platform_key] = scraper_class
        logger.info(f"Registered scraper for platform: {platform}")
    
    @classmethod
    def get_scraper(cls, platform: str) -> BaseScraper:
        """
        Get a scraper instance for the specified platform.
        
        This method returns a singleton instance of the scraper for the
        given platform. If the scraper hasn't been instantiated yet, it
        creates a new instance and caches it for future use.
        
        Args:
            platform: Platform identifier (case-insensitive).
        
        Returns:
            An instance of the platform-specific scraper.
        
        Raises:
            UnsupportedPlatformError: If no scraper is registered for the platform.
        
        Example:
            >>> scraper = ScraperFactory.get_scraper("tiktok")
            >>> videos = await scraper.fetch_latest_videos("coolcreator")
        """
        platform_key = platform.lower()
        
        # Check if scraper is already instantiated
        if platform_key in cls._instances:
            return cls._instances[platform_key]
        
        # Check if scraper class is registered
        if platform_key not in cls._registry:
            available_platforms = list(cls._registry.keys())
            raise UnsupportedPlatformError(
                f"No scraper registered for platform: '{platform}'. "
                f"Available platforms: {available_platforms}"
            )
        
        # Instantiate and cache the scraper
        scraper_class = cls._registry[platform_key]
        scraper_instance = scraper_class()
        cls._instances[platform_key] = scraper_instance
        
        logger.debug(f"Created new scraper instance for platform: {platform}")
        return scraper_instance
    
    @classmethod
    def is_supported(cls, platform: str) -> bool:
        """
        Check if a platform is supported.
        
        Args:
            platform: Platform identifier to check.
        
        Returns:
            True if the platform has a registered scraper, False otherwise.
        
        Example:
            >>> ScraperFactory.is_supported("tiktok")
            True
            >>> ScraperFactory.is_supported("myspace")
            False
        """
        return platform.lower() in cls._registry
    
    @classmethod
    def get_supported_platforms(cls) -> list[str]:
        """
        Get a list of all supported platform names.
        
        Returns:
            List of platform identifiers that have registered scrapers.
        
        Example:
            >>> ScraperFactory.get_supported_platforms()
            ['tiktok', 'instagram', 'facebook']
        """
        return list(cls._registry.keys())
    
    @classmethod
    def clear_instances(cls) -> None:
        """
        Clear all cached scraper instances.
        
        This is primarily useful for testing purposes to force
        re-instantiation of scrapers with fresh state.
        
        Warning:
            This should not be used in production code.
        """
        cls._instances.clear()
        logger.debug("Cleared all scraper instances")
