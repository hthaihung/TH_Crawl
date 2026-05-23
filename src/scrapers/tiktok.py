"""
TikTok scraper implementation with multi-source fallback.

Uses a cascading strategy to fetch TikTok videos:
  1. TikWM API via POST (CF sometimes allows POST through)
  2. yt-dlp subprocess (battle-tested anti-bot bypass)

The fallback chain ensures reliability when the primary
source is blocked by Cloudflare on datacenter IPs.
"""

import os
import logging
import asyncio

from .base import (
    BaseScraper,
    ScrapedVideo,
    ScraperAPIError,
    ScraperNotFoundError,
    ScraperRateLimitError,
    ScraperTimeoutError,
)
from .tiktok_sources import try_tikwm_post, try_ytdlp, try_ytdlp_stories


logger = logging.getLogger(__name__)


class TikTokScraper(BaseScraper):
    """
    Multi-source TikTok scraper with automatic fallback.

    Tries data sources in order of speed/reliability:
      1. TikWM API via POST + curl_cffi Chrome impersonation
      2. yt-dlp subprocess (works from datacenter IPs)

    Environment Variables:
        TIKTOK_API_BASE_URL: TikWM base URL (default: tikwm.com)
        TIKTOK_API_TIMEOUT: Per-strategy timeout secs (default: 30)
        TIKTOK_MAX_RETRIES: Max retries per strategy (default: 3)
        TIKTOK_YTDLP_TIMEOUT: yt-dlp timeout secs (default: 60)

    Example:
        >>> async with TikTokScraper() as scraper:
        ...     videos = await scraper.fetch_latest_videos("user", 5)
    """

    def __init__(self):
        """Initialize the TikTok scraper with configuration."""
        self.timeout = int(os.getenv("TIKTOK_API_TIMEOUT", "30"))
        self.ytdlp_timeout = int(
            os.getenv("TIKTOK_YTDLP_TIMEOUT", "60")
        )
        self.max_retries = int(os.getenv("TIKTOK_MAX_RETRIES", "3"))

    def platform_name(self) -> str:
        """Return the platform identifier."""
        return "tiktok"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_latest_videos(
        self,
        username: str,
        limit: int = 10,
    ) -> list[ScrapedVideo]:
        """
        Fetch the latest videos from a TikTok user profile.

        Tries each data source in order; the first one that
        succeeds wins.  If all fail, raises with combined errors.

        Args:
            username: TikTok username (without @ symbol).
            limit: Maximum number of videos to fetch.

        Returns:
            List of ScrapedVideo objects (newest first).

        Raises:
            ScraperAPIError: If all sources fail.
            ScraperNotFoundError: If the user does not exist.
        """
        username = username.lstrip("@")
        logger.info(
            f"Fetching latest {limit} videos for @{username}"
        )

        videos_data, source = await self._fetch_with_fallback(
            username, limit
        )

        scraped: list[ScrapedVideo] = []
        for v in videos_data[:limit]:
            try:
                if source == "ytdlp":
                    sv = self._parse_ytdlp_entry(v, username)
                else:
                    sv = self._parse_tikwm_entry(v, username)
                scraped.append(sv)
            except Exception as e:
                logger.warning(
                    f"Skipping unparseable video for @{username}: {e}"
                )
                continue

        logger.info(
            f"✅ Fetched {len(scraped)} videos for @{username} "
            f"via {source}"
        )

        # Also fetch stories (best-effort, don't fail if stories unavailable)
        try:
            stories = await self.fetch_stories(username)
            scraped.extend(stories)
            if stories:
                logger.info(f"📖 Also fetched {len(stories)} stories for @{username}")
        except Exception as e:
            logger.debug(f"Stories fetch skipped for @{username}: {e}")

        return scraped

    async def fetch_stories(self, username: str) -> list[ScrapedVideo]:
        """Fetch TikTok stories (ephemeral content) for a user."""
        try:
            stories_data = await try_ytdlp_stories(username, self.ytdlp_timeout)
            scraped_stories = []
            for s in stories_data:
                try:
                    sv = self._parse_ytdlp_entry(s, username)
                    sv.metadata["is_story"] = True
                    scraped_stories.append(sv)
                except Exception:
                    continue
            return scraped_stories
        except Exception as e:
            logger.error(f"Error fetching stories for @{username}: {e}")
            return []

    # ------------------------------------------------------------------
    # Fallback orchestrator
    # ------------------------------------------------------------------

    async def _fetch_with_fallback(
        self, username: str, limit: int
    ) -> tuple[list[dict], str]:
        """Try each strategy in order. Return (videos, source)."""
        strategies = [
            (
                "tikwm_post",
                lambda: try_tikwm_post(
                    username, limit, self.timeout
                ),
            ),
            (
                "ytdlp",
                lambda: try_ytdlp(
                    username, limit, self.ytdlp_timeout
                ),
            ),
        ]

        errors: list[str] = []

        for name, fetch_fn in strategies:
            for attempt in range(self.max_retries):
                try:
                    logger.info(
                        f"[{name}] attempt {attempt + 1}/"
                        f"{self.max_retries} for @{username}"
                    )
                    videos = await fetch_fn()
                    if videos:
                        return videos, name
                    logger.warning(
                        f"[{name}] returned 0 videos for @{username}"
                    )
                    break  # 0 videos is not retryable
                except ScraperNotFoundError:
                    raise  # user doesn't exist → stop
                except ScraperRateLimitError as e:
                    errors.append(f"{name}: {e}")
                    break  # don't retry rate limits
                except (
                    ScraperTimeoutError, ScraperAPIError
                ) as e:
                    errors.append(f"{name}[{attempt+1}]: {e}")
                    if attempt < self.max_retries - 1:
                        wait = 2 ** attempt
                        logger.warning(
                            f"[{name}] failed, retry in {wait}s"
                        )
                        await asyncio.sleep(wait)
                except Exception as e:
                    errors.append(f"{name}: unexpected {e}")
                    break

        raise ScraperAPIError(
            f"All TikTok sources failed for @{username}:\n"
            + "\n".join(f"  • {e}" for e in errors)
        )

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_tikwm_entry(
        v: dict, username: str
    ) -> ScrapedVideo:
        """Parse a TikWM API video dict into ScrapedVideo."""
        video_id = str(v.get("video_id", ""))
        author = v.get("author", {}).get("unique_id", username)

        return ScrapedVideo(
            video_id=video_id,
            platform="tiktok",
            video_url=(
                v.get("play", "")
                or v.get("wmplay", "")
                or v.get("download_addr", "")
            ),
            thumbnail_url=(
                v.get("cover", "")
                or v.get("origin_cover", "")
            ),
            caption=v.get("title", "") or v.get("desc", ""),
            author=author,
            author_url=f"https://www.tiktok.com/@{author}",
            created_at=str(v.get("create_time", "")),
            duration_seconds=v.get("duration"),
            view_count=v.get("play_count"),
            like_count=v.get("digg_count"),
            original_post_url=(
                f"https://www.tiktok.com/@{author}/video/{video_id}"
            ),
            metadata={
                "source": "tikwm",
                "share_count": v.get("share_count"),
                "comment_count": v.get("comment_count"),
                "music": v.get("music"),
                "hashtags": [
                    t.get("name")
                    for t in v.get("text_extra", [])
                    if t.get("type") == 1
                ],
            },
        )

    @staticmethod
    def _parse_ytdlp_entry(
        v: dict, username: str
    ) -> ScrapedVideo:
        """Parse a yt-dlp JSON entry into ScrapedVideo."""
        video_id = str(v.get("id", ""))
        author = v.get("uploader_id", username) or username

        return ScrapedVideo(
            video_id=video_id,
            platform="tiktok",
            video_url=v.get("url", "") or v.get("webpage_url", ""),
            thumbnail_url=v.get("thumbnail"),
            caption=(
                v.get("description", "") or v.get("title", "")
            ),
            author=author,
            author_url=(
                v.get("uploader_url", "")
                or f"https://www.tiktok.com/@{author}"
            ),
            created_at=str(v.get("timestamp", "")),
            duration_seconds=v.get("duration"),
            view_count=v.get("view_count"),
            like_count=v.get("like_count"),
            original_post_url=(
                v.get("webpage_url", "")
                or f"https://www.tiktok.com/@{author}/video/"
                f"{video_id}"
            ),
            metadata={
                "source": "ytdlp",
                "comment_count": v.get("comment_count"),
                "repost_count": v.get("repost_count"),
                "track": v.get("track"),
                "artist": v.get("artist"),
                "hashtags": v.get("tags", []),
                "is_story": v.get("_is_story", False),
            },
        )

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit (no persistent client)."""
        pass
