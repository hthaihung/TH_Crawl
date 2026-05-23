"""
Base scraper abstract class and data models.

This module defines the abstract base class that all platform-specific
scrapers must inherit from, ensuring a consistent interface across all
social media platforms.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class ScrapedVideo:
    """
    Standardized video data structure returned by all scrapers.
    
    This dataclass ensures consistent output format across all platform
    scrapers, making it easy to process videos uniformly regardless of
    their source platform.
    
    Attributes:
        video_id: Unique identifier from the platform (e.g., TikTok video ID).
        platform: Platform identifier ('tiktok', 'instagram', 'facebook').
        video_url: Direct link to the video file (.mp4 or streaming URL).
        thumbnail_url: URL to the video thumbnail/cover image.
        caption: Video description, title, or caption text.
        author: Username or display name of the content creator.
        author_url: URL to the author's profile page.
        created_at: Original posting timestamp (ISO 8601 format or Unix timestamp).
        duration_seconds: Video duration in seconds.
        view_count: Number of views (if available).
        like_count: Number of likes/hearts (if available).
        original_post_url: Full URL to the original post on the platform.
        metadata: Platform-specific additional data (hashtags, music, etc.).
    
    Example:
        >>> video = ScrapedVideo(
        ...     video_id="7123456789012345678",
        ...     platform="tiktok",
        ...     video_url="https://v16-webapp.tiktok.com/...",
        ...     thumbnail_url="https://p16-sign.tiktokcdn.com/...",
        ...     caption="Check out this amazing video! #fyp",
        ...     author="coolcreator",
        ...     author_url="https://www.tiktok.com/@coolcreator",
        ...     created_at="2026-05-23T10:30:00Z",
        ...     duration_seconds=15,
        ...     view_count=1000000,
        ...     like_count=50000,
        ...     original_post_url="https://www.tiktok.com/@coolcreator/video/7123456789012345678",
        ...     metadata={"hashtags": ["fyp", "viral"], "music": "Original Sound"}
        ... )
    """
    
    video_id: str
    platform: str
    video_url: str
    thumbnail_url: Optional[str]
    caption: str
    author: str
    author_url: str
    created_at: str
    duration_seconds: Optional[int]
    view_count: Optional[int]
    like_count: Optional[int]
    original_post_url: str
    metadata: dict


class ScraperError(Exception):
    """Base exception for all scraper-related errors."""
    pass


class ScraperAPIError(ScraperError):
    """Raised when the external API returns an error."""
    pass


class ScraperRateLimitError(ScraperError):
    """Raised when rate limit is exceeded."""
    pass


class ScraperNotFoundError(ScraperError):
    """Raised when the target profile/video is not found."""
    pass


class ScraperTimeoutError(ScraperError):
    """Raised when the API request times out."""
    pass


class BaseScraper(ABC):
    """
    Abstract base class for all social media platform scrapers.
    
    All platform-specific scrapers (TikTok, Instagram, Facebook, etc.)
    must inherit from this class and implement the required abstract methods.
    This ensures a consistent interface for the ScraperFactory and scheduler.
    
    The scraper follows these principles:
    - Async-first: All I/O operations use asyncio
    - Error handling: Specific exceptions for different failure modes
    - Rate limiting: Built-in retry logic with exponential backoff
    - Standardized output: All scrapers return ScrapedVideo objects
    """
    
    @abstractmethod
    async def fetch_latest_videos(
        self,
        username: str,
        limit: int = 10
    ) -> list[ScrapedVideo]:
        """
        Fetch the latest videos from a user's profile.
        
        This method must be implemented by all platform-specific scrapers.
        It should fetch the most recent videos from the specified user's
        profile and return them as a list of ScrapedVideo objects.
        
        Args:
            username: The username or profile identifier (without @ symbol).
            limit: Maximum number of videos to fetch (default: 10).
        
        Returns:
            List of ScrapedVideo objects, ordered by creation date (newest first).
        
        Raises:
            ScraperAPIError: If the API returns an error response.
            ScraperRateLimitError: If rate limit is exceeded.
            ScraperNotFoundError: If the user profile is not found.
            ScraperTimeoutError: If the request times out.
        
        Example:
            >>> scraper = TikTokScraper()
            >>> videos = await scraper.fetch_latest_videos("coolcreator", limit=5)
            >>> print(f"Fetched {len(videos)} videos")
            Fetched 5 videos
        """
        ...
    
    @abstractmethod
    def platform_name(self) -> str:
        """
        Return the platform identifier for this scraper.
        
        Returns:
            Platform identifier string ('tiktok', 'instagram', 'facebook', etc.).
        
        Example:
            >>> scraper = TikTokScraper()
            >>> scraper.platform_name()
            'tiktok'
        """
        ...
    
    async def validate_username(self, username: str) -> bool:
        """
        Validate that a username exists and is accessible.
        
        This is a helper method that can be overridden by platform-specific
        scrapers if they have a more efficient validation endpoint.
        
        Args:
            username: The username to validate.
        
        Returns:
            True if the username exists and is accessible, False otherwise.
        
        Example:
            >>> scraper = TikTokScraper()
            >>> is_valid = await scraper.validate_username("coolcreator")
            >>> print(is_valid)
            True
        """
        try:
            videos = await self.fetch_latest_videos(username, limit=1)
            return len(videos) > 0
        except ScraperNotFoundError:
            return False
        except Exception:
            # If we can't validate due to other errors, assume it might be valid
            return True
