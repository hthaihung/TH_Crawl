"""
Media orchestrator and automated delivery scheduler.

This module implements the core orchestration loop that connects the
Supabase database, scraper factory, and Discord bot to automatically
fetch, process, and deliver social media videos to Discord channels.
"""

import os
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from datetime import datetime

import discord
import httpx
from discord.ext import tasks

from scrapers import ScraperFactory, ScrapedVideo, ScraperError
from database.supabase_client import get_supabase_client
from .delivery import download_video, send_to_discord, record_processed_video

if TYPE_CHECKING:
    from .core import CrawlStoryBot

logger = logging.getLogger(__name__)

SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "20"))
VIDEO_DOWNLOAD_TIMEOUT = int(os.getenv("VIDEO_DOWNLOAD_TIMEOUT", "60"))


class MediaOrchestrator:
    """
    Orchestrates automated video scraping and delivery to Discord.
    
    Attributes:
        bot: The Discord bot instance.
        supabase: Supabase client for database operations.
        http_client: Async HTTP client for downloading videos.
    """
    
    def __init__(self, bot: "CrawlStoryBot"):
        self.bot = bot
        self.supabase = get_supabase_client()
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(VIDEO_DOWNLOAD_TIMEOUT),
            follow_redirects=True,
        )
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
        """Main orchestration loop that runs periodically."""
        logger.info("=" * 60)
        logger.info("Starting orchestration cycle")
        logger.info("=" * 60)
        
        session_stats = {"videos_processed": 0, "videos_delivered": 0, "videos_skipped": 0, "errors": 0}
        
        try:
            mappings = await self._fetch_approved_mappings()
            logger.info(f"Found {len(mappings)} approved mappings")
            
            for mapping in mappings:
                try:
                    result = await self._process_mapping(mapping)
                    session_stats["videos_processed"] += result["processed"]
                    session_stats["videos_delivered"] += result["delivered"]
                    session_stats["videos_skipped"] += result["skipped"]
                except Exception as e:
                    session_stats["errors"] += 1
                    logger.error(f"Error processing mapping {mapping.get('id')}: {e}", exc_info=True)
            
            self.stats["total_runs"] += 1
            self.stats["total_videos_processed"] += session_stats["videos_processed"]
            self.stats["total_videos_delivered"] += session_stats["videos_delivered"]
            self.stats["total_errors"] += session_stats["errors"]
            
        except Exception as e:
            logger.error(f"Fatal error in orchestration loop: {e}", exc_info=True)
            session_stats["errors"] += 1
        
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
        """Fetch approved mappings with joined data from Supabase."""
        try:
            response = self.supabase.table("ai_mappings").select(
                "id, "
                "social_targets(id, platform, target_url, display_name, is_active), "
                "discord_channels(id, channel_id, channel_name, is_active)"
            ).eq("status", "approved").execute()
            
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
        """Process a single mapping: scrape videos and deliver to Discord."""
        stats = {"processed": 0, "delivered": 0, "skipped": 0}
        
        target = mapping.get("social_targets", {})
        channel_data = mapping.get("discord_channels", {})
        
        platform = target.get("platform")
        username = self._extract_username(target.get("target_url", ""))
        channel_id = int(channel_data.get("channel_id"))
        
        logger.info(f"Processing: {platform}/@{username} → #{channel_data.get('channel_name')}")
        
        try:
            scraper = ScraperFactory.get_scraper(platform)
            videos = await scraper.fetch_latest_videos(username, limit=10)
            logger.info(f"Fetched {len(videos)} videos from {platform}/@{username}")
        except ScraperError as e:
            logger.error(f"Scraper error for {platform}/@{username}: {e}")
            return stats
        
        for video in videos:
            stats["processed"] += 1
            
            if await self._is_video_processed(video):
                logger.debug(f"Video {video.video_id} already processed, skipping")
                stats["skipped"] += 1
                continue
            
            delivered = await self._download_and_deliver(
                video, channel_id, target.get("id"), channel_data.get("id")
            )
            
            if delivered:
                stats["delivered"] += 1
            else:
                stats["skipped"] += 1
        
        return stats
    
    async def _is_video_processed(self, video: ScrapedVideo) -> bool:
        """Check if a video has already been processed."""
        try:
            # Check by original_url to properly deduplicate
            response = self.supabase.table("processed_videos").select(
                "original_url"
            ).eq("original_url", video.original_post_url).limit(1).execute()
            
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking if video processed: {e}")
            return False
    
    async def _download_and_deliver(
        self,
        video: ScrapedVideo,
        channel_id: int,
        target_id: str,
        discord_channel_id: str
    ) -> bool:
        """Download video file and deliver to Discord channel."""
        temp_file: Optional[Path] = None
        
        try:
            temp_file = await download_video(self.http_client, video.video_url)
            
            if temp_file is None:
                logger.warning(f"Failed to download video {video.video_id}")
                return False
            
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                logger.error(f"Discord channel {channel_id} not found")
                return False
            
            message = await send_to_discord(channel, video, temp_file)
            
            if message is None:
                return False
            
            await record_processed_video(
                self.supabase, video, target_id, discord_channel_id, message.id
            )
            
            logger.info(f"✅ Delivered video {video.video_id} to #{channel.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error delivering video {video.video_id}: {e}", exc_info=True)
            return False
        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_file}: {e}")
    
    @staticmethod
    def _extract_username(target_url: str) -> str:
        """Extract username from target URL."""
        if "/" in target_url:
            parts = target_url.rstrip("/").split("/")
            username = parts[-1]
        else:
            username = target_url
        return username.lstrip("@")
    
    async def cleanup(self) -> None:
        """Cleanup resources when shutting down."""
        await self.http_client.aclose()
        logger.info("Media orchestrator cleaned up")
