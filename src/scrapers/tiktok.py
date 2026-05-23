"""
TikTok scraper implementation.

This module provides a scraper for fetching videos from TikTok user profiles
using a third-party API service. It implements the BaseScraper interface
and handles TikTok-specific data extraction and error handling.
"""

import os
import logging
from typing import Optional
import httpx
import asyncio

from .base import (
    BaseScraper,
    ScrapedVideo,
    ScraperAPIError,
    ScraperRateLimitError,
    ScraperNotFoundError,
    ScraperTimeoutError,
)


logger = logging.getLogger(__name__)


class TikTokScraper(BaseScraper):
    """
    TikTok video scraper using Tikwm API.
    
    This scraper fetches videos from TikTok user profiles using the Tikwm
    API (https://www.tikwm.com/api), which provides a free tier for fetching
    TikTok video data without authentication.
    
    Features:
    - Async HTTP requests using httpx
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Comprehensive error handling
    - Standardized output format
    
    Environment Variables:
        TIKTOK_API_BASE_URL: Base URL for TikTok API (default: https://www.tikwm.com/api)
        TIKTOK_API_TIMEOUT: Request timeout in seconds (default: 30)
        TIKTOK_MAX_RETRIES: Maximum retry attempts (default: 3)
    
    Example:
        >>> scraper = TikTokScraper()
        >>> videos = await scraper.fetch_latest_videos("charlidamelio", limit=5)
        >>> print(f"Fetched {len(videos)} videos from TikTok")
    """
    
    def __init__(self):
        """Initialize the TikTok scraper with configuration."""
        self.api_base_url = os.getenv(
            "TIKTOK_API_BASE_URL",
            "https://www.tikwm.com/api"
        )
        self.timeout = int(os.getenv("TIKTOK_API_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("TIKTOK_MAX_RETRIES", "3"))
        
        # Create async HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
        )
    
    def platform_name(self) -> str:
        """
        Return the platform identifier.
        
        Returns:
            'tiktok'
        """
        return "tiktok"
    
    async def fetch_latest_videos(
        self,
        username: str,
        limit: int = 10
    ) -> list[ScrapedVideo]:
        """
        Fetch the latest videos from a TikTok user profile.
        
        Args:
            username: TikTok username (without @ symbol).
            limit: Maximum number of videos to fetch (default: 10).
        
        Returns:
            List of ScrapedVideo objects, ordered by creation date (newest first).
        
        Raises:
            ScraperAPIError: If the API returns an error response.
            ScraperRateLimitError: If rate limit is exceeded.
            ScraperNotFoundError: If the user profile is not found.
            ScraperTimeoutError: If the request times out.
        """
        # Remove @ symbol if present
        username = username.lstrip("@")
        
        logger.info(f"Fetching latest {limit} videos for TikTok user: @{username}")
        
        try:
            # Fetch user feed with retry logic
            videos_data = await self._fetch_user_feed_with_retry(username, limit)
            
            # Parse and standardize video data
            scraped_videos = []
            for video_data in videos_data[:limit]:
                try:
                    scraped_video = self._parse_video_data(video_data, username)
                    scraped_videos.append(scraped_video)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse video data for @{username}: {e}",
                        exc_info=True
                    )
                    continue
            
            logger.info(
                f"Successfully fetched {len(scraped_videos)} videos "
                f"for TikTok user: @{username}"
            )
            return scraped_videos
            
        except (ScraperAPIError, ScraperRateLimitError, ScraperNotFoundError, ScraperTimeoutError):
            # Re-raise known scraper errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching TikTok videos for @{username}: {e}")
            raise ScraperAPIError(f"Failed to fetch TikTok videos: {str(e)}") from e
    
    async def _fetch_user_feed_with_retry(
        self,
        username: str,
        limit: int
    ) -> list[dict]:
        """
        Fetch user feed with exponential backoff retry logic.
        
        Args:
            username: TikTok username.
            limit: Number of videos to fetch.
        
        Returns:
            List of video data dictionaries from the API.
        
        Raises:
            ScraperAPIError: If all retries fail.
            ScraperRateLimitError: If rate limited.
            ScraperNotFoundError: If user not found.
            ScraperTimeoutError: If request times out.
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await self._fetch_user_feed(username, limit)
            except ScraperTimeoutError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Timeout fetching TikTok feed for @{username}, "
                        f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                continue
            except (ScraperRateLimitError, ScraperNotFoundError, ScraperAPIError):
                # Don't retry these errors
                raise
        
        # All retries exhausted
        raise last_exception or ScraperAPIError("Failed to fetch user feed after retries")
    
    async def _fetch_user_feed(self, username: str, limit: int) -> list[dict]:
        """
        Fetch user feed from the TikTok API.
        
        Args:
            username: TikTok username.
            limit: Number of videos to fetch.
        
        Returns:
            List of video data dictionaries.
        
        Raises:
            ScraperAPIError: If API returns an error.
            ScraperRateLimitError: If rate limited.
            ScraperNotFoundError: If user not found.
            ScraperTimeoutError: If request times out.
        """
        url = f"{self.api_base_url}/user/posts"
        params = {
            "unique_id": username,
            "count": min(limit, 35),  # API typically limits to 35 per request
        }
        
        try:
            response = await self.client.get(url, params=params)
            
            # Handle rate limiting
            if response.status_code == 429:
                raise ScraperRateLimitError(
                    f"Rate limit exceeded for TikTok API. "
                    f"Please try again later."
                )
            
            # Handle not found
            if response.status_code == 404:
                raise ScraperNotFoundError(
                    f"TikTok user not found: @{username}"
                )
            
            # Handle other HTTP errors
            if response.status_code != 200:
                raise ScraperAPIError(
                    f"TikTok API returned status {response.status_code}: "
                    f"{response.text[:200]}"
                )
            
            # Parse JSON response
            data = response.json()
            
            # Check API response status
            if data.get("code") != 0:
                error_msg = data.get("msg", "Unknown error")
                if "not found" in error_msg.lower():
                    raise ScraperNotFoundError(f"TikTok user not found: @{username}")
                raise ScraperAPIError(f"TikTok API error: {error_msg}")
            
            # Extract video list
            videos = data.get("data", {}).get("videos", [])
            
            if not videos:
                logger.warning(f"No videos found for TikTok user: @{username}")
                return []
            
            return videos
            
        except httpx.TimeoutException as e:
            raise ScraperTimeoutError(
                f"Request timed out after {self.timeout}s"
            ) from e
        except httpx.HTTPError as e:
            raise ScraperAPIError(
                f"HTTP error fetching TikTok feed: {str(e)}"
            ) from e
    
    def _parse_video_data(self, video_data: dict, username: str) -> ScrapedVideo:
        """
        Parse raw API video data into a ScrapedVideo object.
        
        Args:
            video_data: Raw video data from the API.
            username: TikTok username.
        
        Returns:
            ScrapedVideo object with standardized fields.
        """
        video_id = str(video_data.get("video_id", ""))
        
        # Extract video URL (prefer play URL, fallback to download URL)
        video_url = (
            video_data.get("play", "") or
            video_data.get("wmplay", "") or
            video_data.get("download_addr", "")
        )
        
        # Extract thumbnail URL
        thumbnail_url = (
            video_data.get("cover", "") or
            video_data.get("origin_cover", "") or
            video_data.get("dynamic_cover", "")
        )
        
        # Extract caption/title
        caption = video_data.get("title", "") or video_data.get("desc", "")
        
        # Extract author info
        author = video_data.get("author", {}).get("unique_id", username)
        author_url = f"https://www.tiktok.com/@{author}"
        
        # Extract timestamps
        created_at = str(video_data.get("create_time", ""))
        
        # Extract metrics
        duration_seconds = video_data.get("duration")
        view_count = video_data.get("play_count")
        like_count = video_data.get("digg_count")
        
        # Build original post URL
        original_post_url = f"https://www.tiktok.com/@{author}/video/{video_id}"
        
        # Extract metadata
        metadata = {
            "share_count": video_data.get("share_count"),
            "comment_count": video_data.get("comment_count"),
            "music": video_data.get("music"),
            "hashtags": [tag.get("name") for tag in video_data.get("text_extra", [])
                        if tag.get("type") == 1],  # Type 1 = hashtag
        }
        
        return ScrapedVideo(
            video_id=video_id,
            platform="tiktok",
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            caption=caption,
            author=author,
            author_url=author_url,
            created_at=created_at,
            duration_seconds=duration_seconds,
            view_count=view_count,
            like_count=like_count,
            original_post_url=original_post_url,
            metadata=metadata,
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup HTTP client."""
        await self.client.aclose()
