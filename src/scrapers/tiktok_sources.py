"""
TikTok data source strategies.

Each strategy is an async function that fetches video data
from a different source. They share a common return type:
list[dict] where each dict contains raw video metadata.

Strategies:
  1. tikwm_post  – TikWM API via POST (bypasses some CF configs)
  2. ytdlp       – yt-dlp subprocess (battle-tested anti-bot)
"""

import os
import json
import logging
import asyncio

from .base import (
    ScraperAPIError,
    ScraperNotFoundError,
    ScraperRateLimitError,
    ScraperTimeoutError,
)


logger = logging.getLogger(__name__)


async def try_tikwm_post(
    username: str, limit: int, timeout: int
) -> list[dict]:
    """
    Strategy 1: TikWM API via POST with form data.

    Cloudflare sometimes allows POST requests through when
    GET is blocked by a JS/Turnstile challenge, because many
    CF WAF rulesets only trigger on navigation (GET) requests.
    """
    from curl_cffi.requests import AsyncSession

    api_url = os.getenv(
        "TIKTOK_API_BASE_URL", "https://www.tikwm.com/api"
    )
    url = f"{api_url}/user/posts"

    async with AsyncSession(
        timeout=timeout, impersonate="chrome"
    ) as session:
        response = await session.post(
            url,
            data={
                "unique_id": username,
                "count": min(limit, 35),
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Referer": "https://www.tikwm.com/",
            },
            allow_redirects=True,
        )

    if response.status_code == 403:
        raise ScraperAPIError(
            "TikWM POST blocked (403). CF Turnstile active."
        )
    if response.status_code == 429:
        raise ScraperRateLimitError("TikWM rate limit exceeded.")
    if response.status_code != 200:
        raise ScraperAPIError(
            f"TikWM returned {response.status_code}: "
            f"{response.text[:200]}"
        )

    data = response.json()
    if data.get("code") != 0:
        msg = data.get("msg", "Unknown error")
        if "not found" in msg.lower():
            raise ScraperNotFoundError(
                f"TikTok user not found: @{username}"
            )
        raise ScraperAPIError(f"TikWM API error: {msg}")

    return data.get("data", {}).get("videos", [])


async def try_ytdlp(
    username: str, limit: int, timeout: int
) -> list[dict]:
    """
    Strategy 2: yt-dlp subprocess.

    yt-dlp handles all anti-bot measures (TLS fingerprinting,
    cookie management, JS rendering) and is updated regularly.

    Requires: yt-dlp installed on the VPS (pip install yt-dlp).
    """
    tiktok_url = f"https://www.tiktok.com/@{username}"

    proc = await asyncio.create_subprocess_exec(
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--playlist-end", str(min(limit, 35)),
        "--no-warnings",
        "--quiet",
        tiktok_url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise ScraperTimeoutError(
            f"yt-dlp timed out after {timeout}s"
        )

    if proc.returncode != 0:
        err = stderr.decode(errors="replace").strip()
        if "not found" in err.lower() or "does not exist" in err.lower():
            raise ScraperNotFoundError(
                f"TikTok user not found: @{username}"
            )
        raise ScraperAPIError(
            f"yt-dlp failed (exit {proc.returncode}): {err[:300]}"
        )

    videos: list[dict] = []
    for line in stdout.decode(errors="replace").strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            videos.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return videos


async def try_ytdlp_stories(
    username: str, timeout: int
) -> list[dict]:
    """Fetch TikTok stories via yt-dlp."""
    # Stories URL format for yt-dlp
    stories_url = f"https://www.tiktok.com/@{username}"
    
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--no-warnings",
        "--quiet",
        "--extractor-args", "tiktok:api_hostname=api16-normal-c-useast1a.tiktokv.com",
        f"{stories_url}/stories",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        return []  # Stories are optional, don't raise
    
    if proc.returncode != 0:
        return []  # Stories might not exist, return empty
    
    videos: list[dict] = []
    for line in stdout.decode(errors="replace").strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            entry["_is_story"] = True  # Mark as story
            videos.append(entry)
        except json.JSONDecodeError:
            continue
    
    return videos
