"""
Video download and delivery logic with batching and resilience.

Handles downloading videos, batching them into Discord grid format,
recording state in Supabase, and queuing failures locally.
"""

import os
import json
import logging
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import asdict

import discord
import httpx

from scrapers import ScrapedVideo

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
QUEUE_DIR = Path("queue")

# Ensure queue directory exists
QUEUE_DIR.mkdir(exist_ok=True)


async def download_video(
    http_client: httpx.AsyncClient, video_url: str
) -> Optional[Path]:
    """Download video file to temporary location with size validation."""
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
                        logger.warning(f"Video exceeded {MAX_FILE_SIZE_MB}MB during download")
                        temp_file.unlink()
                        return None
                    
                    f.write(chunk)
            
            return temp_file
            
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None


async def send_batch_to_discord(
    channel: discord.TextChannel,
    videos_and_paths: list[tuple[ScrapedVideo, Path]]
) -> Optional[discord.Message]:
    """
    Send up to 10 video files to Discord in a single message.
    Forces native Discord gallery/grid view without text.
    """
    if not videos_and_paths:
        return None
        
    try:
        discord_files = []
        file_handles = []
        
        for video, file_path in videos_and_paths[:10]:
            f = open(file_path, "rb")
            file_handles.append(f)
            discord_files.append(discord.File(f, filename=f"{video.video_id}.mp4"))
            
        message = await channel.send(content="", files=discord_files)
        
        for f in file_handles:
            f.close()
            
        return message
        
    except Exception as e:
        logger.error(f"Discord API error sending batch: {e}")
        # Ensure we close file handles on error
        for f in locals().get('file_handles', []):
            try:
                f.close()
            except:
                pass
        return None


async def record_processed_video(
    supabase,
    video: ScrapedVideo,
    target_id: str,
    discord_channel_id: str,
    message_id: int
) -> bool:
    """Record processed video in database. Returns False if failed."""
    try:
        video_data = {
            "social_target_id": target_id,
            "discord_channel_id": discord_channel_id,
            "platform": video.platform,
            "original_url": video.original_post_url,
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
        return True
    except Exception as e:
        logger.error(f"Failed to record processed video: {e}")
        return False


def save_to_queue(
    video: ScrapedVideo,
    target_id: str,
    discord_channel_id: str,
    file_path: Path
) -> None:
    """Save failed delivery to local queue for retry loop."""
    try:
        queue_id = f"{datetime.utcnow().timestamp()}_{video.video_id}"
        queue_file = QUEUE_DIR / f"{queue_id}.json"
        
        # We need to persist the file. Since temp_file gets deleted, we move it to queue.
        persisted_file = QUEUE_DIR / f"{queue_id}.mp4"
        if file_path.exists():
            import shutil
            shutil.copy2(file_path, persisted_file)
            
        queue_data = {
            "video": asdict(video),
            "target_id": target_id,
            "discord_channel_id": discord_channel_id,
            "file_path": str(persisted_file)
        }
        
        with open(queue_file, "w") as f:
            json.dump(queue_data, f)
            
        logger.info(f"Saved video {video.video_id} to retry queue")
    except Exception as e:
        logger.error(f"Failed to save to queue: {e}")
