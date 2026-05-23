"""
Media orchestrator and automated delivery scheduler.

This module implements the core orchestration loop that connects the
Supabase database, scraper factory, and Discord bot to automatically
fetch, process, and deliver social media videos to Discord channels.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timedelta

import discord
import httpx
from discord.ext import tasks

from scrapers import ScraperFactory, ScrapedVideo, ScraperError
from database.supabase_client import get_supabase_client
from .delivery import (
    download_video, 
    send_batch_to_discord, 
    record_processed_video,
    save_to_queue,
    QUEUE_DIR
)

if TYPE_CHECKING:
    from .core import CrawlStoryBot

logger = logging.getLogger(__name__)

SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "20"))
VIDEO_DOWNLOAD_TIMEOUT = int(os.getenv("VIDEO_DOWNLOAD_TIMEOUT", "60"))


class MediaOrchestrator:
    """Orchestrates automated video scraping and delivery to Discord."""
    
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
        """Start the orchestration and queue loops."""
        self.orchestration_loop.start()
        self.retry_queue_loop.start()
        logger.info(f"Media orchestrator started with {SCRAPE_INTERVAL_MINUTES}m interval")
    
    def stop(self) -> None:
        """Stop the background loops."""
        self.orchestration_loop.cancel()
        self.retry_queue_loop.cancel()
        logger.info("Media orchestrator stopped")
    
    @tasks.loop(minutes=5)
    async def retry_queue_loop(self) -> None:
        """Process failed deliveries from the local queue."""
        if not QUEUE_DIR.exists():
            return
            
        for queue_file in QUEUE_DIR.glob("*.json"):
            try:
                with open(queue_file, "r") as f:
                    data = json.load(f)
                
                # Reconstruct ScrapedVideo
                video = ScrapedVideo(**data["video"])
                target_id = data["target_id"]
                channel_id = data["discord_channel_id"]
                file_path = Path(data["file_path"])
                
                channel_record = self.supabase.table("discord_channels").select("channel_id").eq("id", channel_id).execute()
                if not channel_record.data:
                    continue
                
                discord_channel = self.bot.get_channel(int(channel_record.data[0]["channel_id"]))
                if discord_channel and file_path.exists():
                    msg = await send_batch_to_discord(discord_channel, [(video, file_path)])
                    if msg:
                        recorded = await record_processed_video(
                            self.supabase, video, target_id, channel_id, msg.id
                        )
                        if recorded:
                            # Success, clean up queue
                            queue_file.unlink()
                            file_path.unlink()
                            logger.info(f"Successfully retried delivery for {video.video_id}")
            except Exception as e:
                logger.error(f"Error processing queue file {queue_file.name}: {e}")

    @tasks.loop(minutes=SCRAPE_INTERVAL_MINUTES)
    async def orchestration_loop(self) -> None:
        """Main orchestration loop."""
        logger.info("=" * 60)
        logger.info("Starting orchestration cycle")
        
        session_stats = {"processed": 0, "delivered": 0, "skipped": 0, "errors": 0}
        
        try:
            mappings = await self._fetch_approved_mappings()
            
            for mapping in mappings:
                try:
                    result = await self._process_mapping(mapping)
                    session_stats["processed"] += result["processed"]
                    session_stats["delivered"] += result["delivered"]
                    session_stats["skipped"] += result["skipped"]
                except Exception as e:
                    session_stats["errors"] += 1
                    logger.error(f"Error processing mapping: {e}", exc_info=True)
            
            self.stats["total_runs"] += 1
            self.stats["total_videos_processed"] += session_stats["processed"]
            self.stats["total_videos_delivered"] += session_stats["delivered"]
            
        except Exception as e:
            logger.error(f"Fatal error in orchestration loop: {e}")
            session_stats["errors"] += 1
        
        logger.info(f"Cycle Complete: {session_stats['delivered']} delivered")
        logger.info("=" * 60)
    
    @orchestration_loop.before_loop
    @retry_queue_loop.before_loop
    async def before_loops(self) -> None:
        await self.bot.wait_until_ready()
    
    async def _fetch_approved_mappings(self) -> list[dict]:
        """Fetch approved mappings."""
        try:
            response = self.supabase.table("ai_mappings").select(
                "id, social_targets(id, platform, target_url, display_name, is_active), "
                "discord_channels(id, channel_id, channel_name, is_active)"
            ).eq("status", "approved").execute()
            
            return [
                m for m in response.data
                if m.get("social_targets", {}).get("is_active")
                and m.get("discord_channels", {}).get("is_active")
            ]
        except Exception as e:
            logger.error(f"Failed to fetch mappings: {e}")
            return []
    
    async def _process_mapping(self, mapping: dict) -> dict:
        """Process a single mapping: scrape videos and deliver via batching."""
        stats = {"processed": 0, "delivered": 0, "skipped": 0}
        
        target = mapping.get("social_targets", {})
        channel_data = mapping.get("discord_channels", {})
        platform = target.get("platform")
        username = self._extract_username(target.get("target_url", ""))
        channel_id = int(channel_data.get("channel_id"))
        
        discord_channel = self.bot.get_channel(channel_id)
        if not discord_channel:
            return stats
            
        try:
            scraper = ScraperFactory.get_scraper(platform)
            videos = await scraper.fetch_latest_videos(username, limit=10)
        except ScraperError as e:
            logger.error(f"Scraper error for {platform}/@{username}: {e}")
            return stats
            
        # Heartbeat Check
        if not videos:
            self._check_heartbeat(target.get("id"), username)
            return stats
            
        new_videos = []
        for video in videos:
            stats["processed"] += 1
            if await self._is_video_processed(video):
                stats["skipped"] += 1
            else:
                new_videos.append(video)
                
        if not new_videos:
            self._check_heartbeat(target.get("id"), username)
            return stats
            
        # Batch Delivery
        await self._deliver_batches(new_videos, discord_channel, target.get("id"), channel_data.get("id"), stats)
        return stats

    def _check_heartbeat(self, target_id: str, username: str) -> None:
        """Log a heartbeat if no videos found in 24h."""
        try:
            res = self.supabase.table("processed_videos").select("processed_at")\
                .eq("social_target_id", target_id).order("processed_at", desc=True).limit(1).execute()
            
            if not res.data:
                logger.info(f"STATUS CHECK: No new media for @{username} in the last 24h.")
                return
                
            last_dt = datetime.fromisoformat(res.data[0]["processed_at"].replace("Z", "+00:00"))
            if datetime.utcnow().replace(tzinfo=last_dt.tzinfo) - last_dt > timedelta(hours=24):
                logger.info(f"STATUS CHECK: No new media for @{username} in the last 24h.")
        except Exception:
            pass

    async def _deliver_batches(self, videos: list, channel: discord.TextChannel, target_id: str, db_channel_id: str, stats: dict) -> None:
        """Download and batch deliver videos to Discord."""
        # Split into chunks of 10
        for i in range(0, len(videos), 10):
            batch = videos[i:i+10]
            downloaded = []
            
            for video in batch:
                temp_file = await download_video(self.http_client, video.video_url)
                if temp_file:
                    downloaded.append((video, temp_file))
                else:
                    save_to_queue(video, target_id, db_channel_id, Path("dummy"))
            
            if not downloaded:
                continue
                
            msg = await send_batch_to_discord(channel, downloaded)
            
            if msg:
                for video, temp_file in downloaded:
                    recorded = await record_processed_video(self.supabase, video, target_id, db_channel_id, msg.id)
                    if not recorded:
                        save_to_queue(video, target_id, db_channel_id, temp_file)
                    else:
                        stats["delivered"] += 1
                        try:
                            temp_file.unlink()
                        except:
                            pass
            else:
                # Batch failed to send to Discord
                for video, temp_file in downloaded:
                    save_to_queue(video, target_id, db_channel_id, temp_file)

    async def _is_video_processed(self, video: ScrapedVideo) -> bool:
        """Check if a video has already been processed."""
        try:
            response = self.supabase.table("processed_videos").select("original_url").eq("original_url", video.original_post_url).limit(1).execute()
            return len(response.data) > 0
        except Exception:
            return False

    @staticmethod
    def _extract_username(target_url: str) -> str:
        parts = target_url.rstrip("/").split("/")
        return parts[-1].lstrip("@") if "/" in target_url else target_url.lstrip("@")
    
    async def cleanup(self) -> None:
        await self.http_client.aclose()
