"""
Media orchestrator and automated delivery scheduler.

This module implements the core orchestration loop that connects the
Supabase database, scraper factory, and Discord bot to automatically
fetch, process, and deliver social media videos to Discord channels.
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from datetime import datetime

import discord
import httpx
from discord.ext import tasks

from scrapers import ScraperFactory, ScrapedVideo, ScraperError
from database.supabase_client import get_supabase_client

if TYPE_CHECKING:
    from .core import CrawlStoryBot


logger = logging.getLogger(__name__)


# Configuration constants
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "20"))
VIDEO_DOWNLOAD_TIMEOUT = int(os.getenv("VIDEO_DOWNLOAD_TIMEOUT", "60"))


class MediaOrchestrator:
    """
    Orchestrates automated video scraping and delivery to Discord.
    
    This class manages the background loop that:
    1. Fetches approved mappings from Supabase
    2. Scrapes videos from social media platforms
    3. Downloads and validates video files
    4. Delivers videos to Discord channels
    5. Tracks processed videos to prevent duplicates
    
    Attributes:
        bot: The Discord bot instance.
        supabase: Supabase client for database operations.
        http_client: Async HTTP client for downloading videos.
    """
    
    def __init__(self, bot: "CrawlStoryBot"):
        """
        Initialize the media orchestrator.
        
        Args:
            bot: The Discord bot instance to use for delivery.
        """
        self.bot = bot
        self.supabase = get_supabase_client()
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(VIDEO_DOWNLOAD_TIMEOUT),
            follow_redirects=True,
        )
        
        # Statistics tracking
        self.stats = {
            "total_runs": 0,
            "total_videos_processed": 0,
            "total_videos_delivered": 0,
            "total_errors": 0,
        }
    
    def start(self) -> None:
        """Start the orchestration background loop."""
        self.orchestration_loop.start()
        logger.info(
            f"Media orchestrator started with {SCRAPE_INTERVAL_MINUTES} minute interval"
        )
    
    def stop(self) -> None:
        """Stop the orchestration background loop."""
        self.orchestration_loop.cancel()
        logger.info("Media orchestrator stopped")
    
    @tasks.loop(minutes=SCRAPE_INTERVAL_MINUTES)
    async def orchestration_loop(self) -> None:
        """
        Main orchestration loop that runs periodically.
        
        Fetches approved mappings, scrapes videos, and delivers them to Discord.
        """
        logger.info("=" * 60)
        logger.info("Starting orchestration cycle")
        logger.info("=" * 60)
        
        session_stats = {
            "videos_processed": 0,
            "videos_delivered": 0,
            "videos_skipped": 0,
            "errors": 0,
        }
        
        try:
            # Fetch approved mappings
            mappings = await self._fetch_approved_mappings()
            logger.info(f"Found {len(mappings)} approved mappings")
            
            # Process each mapping
            for mapping in mappings:
                try:
                    result = await self._process_mapping(mapping)
                    session_stats["videos_processed"] += result["processed"]
                    session_stats["videos_delivered"] += result["delivered"]
                    session_stats["videos_skipped"] += result["skipped"]
                except Exception as e:
                    session_stats["errors"] += 1
                    logger.error(
                        f"Error processing mapping {mapping.get('id')}: {e}",
                        exc_info=True
                    )
            
            # Update global statistics
            self.stats["total_runs"] += 1
            self.stats["total_videos_processed"] += session_stats["videos_processed"]
            self.stats["total_videos_delivered"] += session_stats["videos_delivered"]
            self.stats["total_errors"] += session_stats["errors"]
            
        except Exception as e:
            logger.error(f"Fatal error in orchestration loop: {e}", exc_info=True)
            session_stats["errors"] += 1
        
        # Log session summary
        logger.info("=" * 60)
        logger.info(
            f"Scrape session completed: "
            f"{session_stats['videos_processed']} videos processed, "
            f"{session_stats['videos_delivered']} uploaded, "
            f"{session_stats['videos_skipped']} skipped, "
            f"{session_stats['errors']} errors"
        )
        logger.info("=" * 60)
    
    @orchestration_loop.before_loop
    async def before_orchestration_loop(self) -> None:
        """Wait for the bot to be ready before starting the loop."""
        await self.bot.wait_until_ready()
        logger.info("Bot is ready, orchestration loop will start")
    
    async def _fetch_approved_mappings(self) -> list[dict]:
        """
        Fetch approved mappings with joined data from Supabase.
        
        Returns:
            List of mapping dictionaries with social_targets and discord_channels data.
        """
        try:
            response = self.supabase.table("ai_mappings").select(
                "id, "
                "social_targets(id, platform, target_url, display_name, is_active), "
                "discord_channels(id, channel_id, channel_name, is_active)"
            ).eq("status", "approved").execute()
            
            # Filter out mappings with inactive targets or channels
            active_mappings = [
                m for m in response.data
                if m.get("social_targets", {}).get("is_active")
                and m.get("discord_channels", {}).get("is_active")
            ]
            
            return active_mappings
            
        except Exception as e:
            logger.error(f"Failed to fetch approved mappings: {e}")
            return []
    
    async def _process_mapping(self, mapping: dict) -> dict:
        """
        Process a single mapping: scrape videos and deliver to Discord.
        
        Args:
            mapping: Mapping dictionary with social_targets and discord_channels.
        
        Returns:
            Dictionary with processing statistics.
        """
        stats = {"processed": 0, "delivered": 0, "skipped": 0}
        
        target = mapping.get("social_targets", {})
        channel_data = mapping.get("discord_channels", {})
        
        platform = target.get("platform")
        username = self._extract_username(target.get("target_url", ""))
        channel_id = int(channel_data.get("channel_id"))
        
        logger.info(
            f"Processing: {platform}/@{username} → #{channel_data.get('channel_name')}"
        )
        
        # Get scraper and fetch videos
        try:
            scraper = ScraperFactory.get_scraper(platform)
            videos = await scraper.fetch_latest_videos(username, limit=10)
            logger.info(f"Fetched {len(videos)} videos from {platform}/@{username}")
        except ScraperError as e:
            logger.error(f"Scraper error for {platform}/@{username}: {e}")
            return stats
        
        # Process each video
        for video in videos:
            stats["processed"] += 1
            
            # Check if already processed
            if await self._is_video_processed(video.video_id):
                logger.debug(f"Video {video.video_id} already processed, skipping")
                stats["skipped"] += 1
                continue
            
            # Download and deliver video
            delivered = await self._download_and_deliver(
                video, channel_id, target.get("id"), channel_data.get("id")
            )
            
            if delivered:
                stats["delivered"] += 1
            else:
                stats["skipped"] += 1
        
        return stats
    
    async def _is_video_processed(self, video_id: str) -> bool:
        """
        Check if a video has already been processed.
        
        Args:
            video_id: The video ID to check.
        
        Returns:
            True if the video exists in processed_videos table.
        """
        try:
            response = self.supabase.table("processed_videos").select(
                "id"
            ).eq("original_url", video_id).limit(1).execute()
            
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking if video processed: {e}")
            return False  # Assume not processed on error
    
    async def _download_and_deliver(
        self,
        video: ScrapedVideo,
        channel_id: int,
        target_id: str,
        discord_channel_id: str
    ) -> bool:
        """
        Download video file and deliver to Discord channel.
        
        Args:
            video: ScrapedVideo object with video metadata.
            channel_id: Discord channel ID to send to.
            target_id: Social target ID from database.
            discord_channel_id: Discord channel record ID from database.
        
        Returns:
            True if successfully delivered, False otherwise.
        """
        temp_file: Optional[Path] = None
        
        try:
            # Download video to temporary file
            temp_file = await self._download_video(video.video_url)
            
            if temp_file is None:
                logger.warning(f"Failed to download video {video.video_id}")
                return False
            
            # Get Discord channel
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                logger.error(f"Discord channel {channel_id} not found")
                return False
            
            # Send video to Discord
            message = await self._send_to_discord(channel, video, temp_file)
            
            if message is None:
                return False
            
            # Record in database
            await self._record_processed_video(
                video, target_id, discord_channel_id, message.id
            )
            
            logger.info(f"✅ Delivered video {video.video_id} to #{channel.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error delivering video {video.video_id}: {e}", exc_info=True)
            return False
        finally:
            # Always cleanup temporary file
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_file}: {e}")
    
    async def _download_video(self, video_url: str) -> Optional[Path]:
        """
        Download video file to temporary location with size validation.
        
        Args:
            video_url: URL of the video to download.
        
        Returns:
            Path to downloaded file, or None if download failed or file too large.
        """
        try:
            # Stream download to check size
            async with self.http_client.stream("GET", video_url) as response:
                response.raise_for_status()
                
                # Check Content-Length header
                content_length = response.headers.get("content-length")
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if int(content_length) > MAX_FILE_SIZE_BYTES:
                        logger.warning(
                            f"Video exceeds {MAX_FILE_SIZE_MB}MB limit "
                            f"({size_mb:.2f}MB), skipping download"
                        )
                        return None
                
                # Create temporary file
                temp_file = Path(tempfile.mktemp(suffix=".mp4"))
                
                # Download with size tracking
                downloaded_bytes = 0
                with open(temp_file, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        downloaded_bytes += len(chunk)
                        
                        # Check size during download
                        if downloaded_bytes > MAX_FILE_SIZE_BYTES:
                            logger.warning(
                                f"Video exceeded {MAX_FILE_SIZE_MB}MB during download, "
                                "aborting"
                            )
                            temp_file.unlink()
                            return None
                        
                        f.write(chunk)
                
                logger.debug(
                    f"Downloaded video: {downloaded_bytes / (1024 * 1024):.2f}MB"
                )
                return temp_file
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error downloading video: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    async def _send_to_discord(
        self,
        channel: discord.TextChannel,
        video: ScrapedVideo,
        file_path: Path
    ) -> Optional[discord.Message]:
        """
        Send video file to Discord channel.
        
        Args:
            channel: Discord text channel to send to.
            video: ScrapedVideo metadata.
            file_path: Path to video file.
        
        Returns:
            Sent message object, or None if failed.
        """
        try:
            # Prepare caption
            caption = (
                f"**{video.caption[:100]}**\n"
                f"👤 @{video.author}\n"
                f"🔗 {video.original_post_url}"
            )
            
            # Send file
            with open(file_path, "rb") as f:
                discord_file = discord.File(f, filename=f"{video.video_id}.mp4")
                message = await channel.send(content=caption, file=discord_file)
            
            return message
            
        except discord.HTTPException as e:
            logger.error(f"Discord API error sending video: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending video to Discord: {e}")
            return None
    
    async def _record_processed_video(
        self,
        video: ScrapedVideo,
        target_id: str,
        discord_channel_id: str,
        message_id: int
    ) -> None:
        """
        Record processed video in database.
        
        Args:
            video: ScrapedVideo metadata.
            target_id: Social target ID.
            discord_channel_id: Discord channel record ID.
            message_id: Discord message ID.
        """
        try:
            video_data = {
                "social_target_id": target_id,
                "discord_channel_id": discord_channel_id,
                "platform": video.platform,
                "original_url": video.video_id,  # Using video_id as unique key
                "video_file_url": video.video_url,
                "thumbnail_url": video.thumbnail_url,
                "caption": video.caption,
                "author": video.author,
                "author_url": video.author_url,
                "duration_seconds": video.duration_seconds,
                "discord_message_id": str(message_id),
                "delivery_status": "sent",
                "metadata": video.metadata,
                "processed_at": datetime.utcnow().isoformat(),
            }
            
            self.supabase.table("processed_videos").insert(video_data).execute()
            logger.debug(f"Recorded video {video.video_id} in database")
            
        except Exception as e:
            logger.error(f"Failed to record processed video: {e}")
    
    @staticmethod
    def _extract_username(target_url: str) -> str:
        """
        Extract username from target URL.
        
        Args:
            target_url: Full URL or username.
        
        Returns:
            Extracted username without @ symbol.
        """
        # Handle various URL formats
        if "/" in target_url:
            # Extract from URL like https://tiktok.com/@username
            parts = target_url.rstrip("/").split("/")
            username = parts[-1]
        else:
            username = target_url
        
        # Remove @ symbol if present
        return username.lstrip("@")
    
    async def cleanup(self) -> None:
        """Cleanup resources when shutting down."""
        await self.http_client.aclose()
        logger.info("Media orchestrator cleaned up")
