"""
Video download and delivery logic.

This module handles downloading videos, delivering them to Discord,
and recording their processed state in the database.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime

import discord
import httpx

from scrapers import ScrapedVideo

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


async def download_video(
    http_client: httpx.AsyncClient, video_url: str
) -> Optional[Path]:
    """
    Download video file to temporary location with size validation.
    
    Args:
        http_client: Async HTTP client.
        video_url: URL of the video to download.
    
    Returns:
        Path to downloaded file, or None if download failed or file too large.
    """
    try:
        async with http_client.stream("GET", video_url) as response:
            response.raise_for_status()
            
            content_length = response.headers.get("content-length")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if int(content_length) > MAX_FILE_SIZE_BYTES:
                    logger.warning(
                        f"Video exceeds {MAX_FILE_SIZE_MB}MB limit "
                        f"({size_mb:.2f}MB), skipping download"
                    )
                    return None
            
            temp_file = Path(tempfile.mktemp(suffix=".mp4"))
            
            downloaded_bytes = 0
            with open(temp_file, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    downloaded_bytes += len(chunk)
                    
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


async def send_to_discord(
    channel: discord.TextChannel,
    video: ScrapedVideo,
    file_path: Path
) -> Optional[discord.Message]:
    """
    Send video file to Discord channel.
    
    Sends a clean media grid with NO TEXT.
    
    Args:
        channel: Discord text channel to send to.
        video: ScrapedVideo metadata.
        file_path: Path to video file.
    
    Returns:
        Sent message object, or None if failed.
    """
    try:
        with open(file_path, "rb") as f:
            discord_file = discord.File(f, filename=f"{video.video_id}.mp4")
            # User strictly wants a clean, minimalist UI inside Discord. No text.
            message = await channel.send(content="", file=discord_file)
        
        return message
        
    except discord.HTTPException as e:
        logger.error(f"Discord API error sending video: {e}")
        return None
    except Exception as e:
        logger.error(f"Error sending video to Discord: {e}")
        return None


async def record_processed_video(
    supabase,
    video: ScrapedVideo,
    target_id: str,
    discord_channel_id: str,
    message_id: int
) -> None:
    """
    Record processed video in database.
    
    Args:
        supabase: Supabase client instance.
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
            "original_url": video.original_post_url,  # Unique identifier
            "video_file_url": video.video_url,
            "thumbnail_url": video.thumbnail_url,
            "caption": video.caption[:500] if video.caption else None,
            "author": video.author,
            "author_url": video.author_url,
            "duration_seconds": video.duration_seconds,
            "discord_message_id": str(message_id),
            "delivery_status": "sent",
            "metadata": video.metadata or {},
            "processed_at": datetime.utcnow().isoformat(),
        }
        
        supabase.table("processed_videos").insert(video_data).execute()
        logger.debug(f"Recorded video {video.video_id} in database")
        
    except Exception as e:
        logger.error(f"Failed to record processed video: {e}")
