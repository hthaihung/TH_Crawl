# 🔧 Scraper Architecture Guide

Complete guide to the CrawlStory scraper architecture, implementation patterns, and how to add new platforms.

---

## 📐 Architecture Overview

The scraper system follows the **Factory Pattern** to provide a clean, extensible interface for fetching videos from multiple social media platforms.

### Core Components

```
src/scrapers/
├── base.py          # Abstract base class and data models
├── factory.py       # Factory for creating scraper instances
├── tiktok.py        # TikTok scraper implementation
└── __init__.py      # Module exports and auto-registration
```

### Design Principles

1. **Abstraction**: All scrapers inherit from `BaseScraper`
2. **Standardization**: All scrapers return `ScrapedVideo` objects
3. **Async-first**: All I/O operations use `asyncio`
4. **Error handling**: Specific exceptions for different failure modes
5. **Singleton pattern**: One instance per platform (memory optimization)
6. **Auto-registration**: Scrapers register themselves on import

---

## 🎯 ScrapedVideo Data Model

All scrapers must return videos in this standardized format:

```python
@dataclass
class ScrapedVideo:
    video_id: str                    # Platform-specific unique ID
    platform: str                    # 'tiktok', 'instagram', 'facebook'
    video_url: str                   # Direct link to video file
    thumbnail_url: Optional[str]     # Cover image URL
    caption: str                     # Video description/title
    author: str                      # Creator username
    author_url: str                  # Link to creator profile
    created_at: str                  # ISO 8601 or Unix timestamp
    duration_seconds: Optional[int]  # Video length
    view_count: Optional[int]        # Number of views
    like_count: Optional[int]        # Number of likes
    original_post_url: str           # Full URL to original post
    metadata: dict                   # Platform-specific extras
```

### Field Requirements

| Field | Required | Description |
|-------|----------|-------------|
| `video_id` | ✅ Yes | Must be unique within the platform |
| `platform` | ✅ Yes | Lowercase platform identifier |
| `video_url` | ✅ Yes | Direct video file URL or streaming URL |
| `caption` | ✅ Yes | Can be empty string if not available |
| `author` | ✅ Yes | Username without @ symbol |
| `author_url` | ✅ Yes | Full profile URL |
| `created_at` | ✅ Yes | ISO 8601 format preferred |
| `original_post_url` | ✅ Yes | Full URL to the post |
| `thumbnail_url` | ⚠️ Optional | Highly recommended |
| `duration_seconds` | ⚠️ Optional | Important for filtering |
| `view_count` | ⚠️ Optional | Useful for analytics |
| `like_count` | ⚠️ Optional | Useful for analytics |
| `metadata` | ✅ Yes | Can be empty dict |

---

## 🏗️ BaseScraper Interface

All platform scrapers must implement this interface:

```python
class BaseScraper(ABC):
    @abstractmethod
    async def fetch_latest_videos(
        self,
        username: str,
        limit: int = 10
    ) -> list[ScrapedVideo]:
        """Fetch latest videos from a user profile."""
        ...
    
    @abstractmethod
    def platform_name(self) -> str:
        """Return platform identifier."""
        ...
    
    async def validate_username(self, username: str) -> bool:
        """Optional: Validate username exists."""
        ...
```

### Method Specifications

#### `fetch_latest_videos(username, limit)`

**Purpose**: Fetch the most recent videos from a user's profile.

**Parameters**:
- `username` (str): Username without @ symbol
- `limit` (int): Maximum videos to fetch (default: 10)

**Returns**: `list[ScrapedVideo]` ordered by date (newest first)

**Raises**:
- `ScraperAPIError`: API returned an error
- `ScraperRateLimitError`: Rate limit exceeded
- `ScraperNotFoundError`: User not found
- `ScraperTimeoutError`: Request timed out

#### `platform_name()`

**Purpose**: Return the platform identifier.

**Returns**: Lowercase string ('tiktok', 'instagram', etc.)

---

## 🔨 Implementing a New Scraper

### Step 1: Create the Scraper Class

Create a new file `src/scrapers/yourplatform.py`:

```python
"""
YourPlatform scraper implementation.
"""

import logging
import httpx
from typing import Optional

from .base import (
    BaseScraper,
    ScrapedVideo,
    ScraperAPIError,
    ScraperNotFoundError,
    ScraperTimeoutError,
)

logger = logging.getLogger(__name__)


class YourPlatformScraper(BaseScraper):
    """
    YourPlatform video scraper.
    
    Fetches videos from YourPlatform user profiles using [API name].
    """
    
    def __init__(self):
        """Initialize the scraper."""
        self.api_base_url = "https://api.yourplatform.com"
        self.timeout = 30
        self.client = httpx.AsyncClient(timeout=self.timeout)
    
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "yourplatform"
    
    async def fetch_latest_videos(
        self,
        username: str,
        limit: int = 10
    ) -> list[ScrapedVideo]:
        """
        Fetch latest videos from a YourPlatform user.
        
        Args:
            username: YourPlatform username.
            limit: Maximum videos to fetch.
        
        Returns:
            List of ScrapedVideo objects.
        """
        logger.info(f"Fetching {limit} videos for @{username}")
        
        try:
            # Make API request
            response = await self.client.get(
                f"{self.api_base_url}/users/{username}/videos",
                params={"limit": limit}
            )
            
            # Handle errors
            if response.status_code == 404:
                raise ScraperNotFoundError(f"User not found: @{username}")
            
            if response.status_code != 200:
                raise ScraperAPIError(f"API error: {response.status_code}")
            
            # Parse response
            data = response.json()
            videos = data.get("videos", [])
            
            # Convert to ScrapedVideo objects
            scraped_videos = []
            for video_data in videos[:limit]:
                scraped_video = self._parse_video(video_data)
                scraped_videos.append(scraped_video)
            
            logger.info(f"Fetched {len(scraped_videos)} videos")
            return scraped_videos
            
        except httpx.TimeoutException as e:
            raise ScraperTimeoutError("Request timed out") from e
        except httpx.HTTPError as e:
            raise ScraperAPIError(f"HTTP error: {e}") from e
    
    def _parse_video(self, video_data: dict) -> ScrapedVideo:
        """Parse API response into ScrapedVideo."""
        return ScrapedVideo(
            video_id=str(video_data["id"]),
            platform="yourplatform",
            video_url=video_data["video_url"],
            thumbnail_url=video_data.get("thumbnail"),
            caption=video_data.get("caption", ""),
            author=video_data["author"]["username"],
            author_url=f"https://yourplatform.com/{video_data['author']['username']}",
            created_at=video_data["created_at"],
            duration_seconds=video_data.get("duration"),
            view_count=video_data.get("views"),
            like_count=video_data.get("likes"),
            original_post_url=video_data["url"],
            metadata={
                "comments": video_data.get("comments"),
                "shares": video_data.get("shares"),
            }
        )
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup HTTP client."""
        await self.client.aclose()
```

### Step 2: Register the Scraper

Update `src/scrapers/__init__.py`:

```python
from .yourplatform import YourPlatformScraper

# Auto-register
ScraperFactory.register("yourplatform", YourPlatformScraper)

__all__ = [
    # ... existing exports ...
    "YourPlatformScraper",
]
```

### Step 3: Add Configuration

Update `.env.example`:

```env
# === YourPlatform Scraper ===
YOURPLATFORM_API_KEY=your-api-key-here
YOURPLATFORM_API_TIMEOUT=30
```

### Step 4: Test the Scraper

```python
import asyncio
from src.scrapers import ScraperFactory

async def test():
    scraper = ScraperFactory.get_scraper("yourplatform")
    videos = await scraper.fetch_latest_videos("testuser", limit=5)
    print(f"Fetched {len(videos)} videos")

asyncio.run(test())
```

---

## 🎨 Best Practices

### Error Handling

Always use specific exceptions:

```python
# ✅ Good
if response.status_code == 404:
    raise ScraperNotFoundError(f"User not found: @{username}")

# ❌ Bad
if response.status_code == 404:
    raise Exception("Not found")
```

### Retry Logic

Implement exponential backoff for transient errors:

```python
async def fetch_with_retry(self, url: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await self.client.get(url)
        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                await asyncio.sleep(wait_time)
            else:
                raise
```

### Logging

Use structured logging:

```python
logger.info(f"Fetching videos for @{username}")
logger.debug(f"API response: {response.status_code}")
logger.warning(f"Rate limit approaching: {remaining} requests left")
logger.error(f"Failed to parse video: {video_id}", exc_info=True)
```

### Resource Cleanup

Always implement async context manager:

```python
async def __aenter__(self):
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    await self.client.aclose()
```

---

## 🧪 Testing

### Unit Test Template

```python
import pytest
from src.scrapers import ScraperFactory, ScraperNotFoundError

@pytest.mark.asyncio
async def test_fetch_videos():
    scraper = ScraperFactory.get_scraper("tiktok")
    videos = await scraper.fetch_latest_videos("tiktok", limit=3)
    
    assert len(videos) <= 3
    assert all(v.platform == "tiktok" for v in videos)
    assert all(v.video_id for v in videos)

@pytest.mark.asyncio
async def test_user_not_found():
    scraper = ScraperFactory.get_scraper("tiktok")
    
    with pytest.raises(ScraperNotFoundError):
        await scraper.fetch_latest_videos("nonexistentuser12345", limit=1)
```

### Manual Testing

Use the provided test script:

```bash
python test_scraper.py
```

---

## 📊 Performance Considerations

### Concurrency

Fetch multiple users concurrently:

```python
import asyncio

async def fetch_all_users(usernames: list[str]):
    scraper = ScraperFactory.get_scraper("tiktok")
    
    tasks = [
        scraper.fetch_latest_videos(username, limit=10)
        for username in usernames
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Rate Limiting

Respect API rate limits:

```python
from asyncio import Semaphore

async def fetch_with_rate_limit(usernames: list[str], max_concurrent: int = 3):
    scraper = ScraperFactory.get_scraper("tiktok")
    semaphore = Semaphore(max_concurrent)
    
    async def fetch_one(username: str):
        async with semaphore:
            return await scraper.fetch_latest_videos(username)
    
    tasks = [fetch_one(u) for u in usernames]
    return await asyncio.gather(*tasks)
```

---

## 🔍 Troubleshooting

### Common Issues

**Issue**: `ScraperTimeoutError` on every request

**Solution**: Increase timeout in environment variables:
```env
TIKTOK_API_TIMEOUT=60
```

---

**Issue**: `ScraperRateLimitError` frequently

**Solution**: 
1. Reduce concurrent requests
2. Increase scrape interval
3. Use API key if available

---

**Issue**: Videos missing `video_url`

**Solution**: Check API response structure and update parser:
```python
video_url = (
    video_data.get("play_url") or
    video_data.get("download_url") or
    video_data.get("stream_url")
)
```

---

## 📚 API Resources

### TikTok (Tikwm)

- **Base URL**: `https://www.tikwm.com/api`
- **Endpoint**: `/user/posts?unique_id={username}&count={limit}`
- **Rate Limit**: ~100 requests/hour (free tier)
- **Documentation**: https://www.tikwm.com/api

### Future Platforms

When adding new platforms, document their API details here.

---

## 🎓 Examples

### Fetch Videos from Multiple Platforms

```python
import asyncio
from src.scrapers import ScraperFactory

async def fetch_from_all_platforms(username: str):
    platforms = ScraperFactory.get_supported_platforms()
    
    for platform in platforms:
        scraper = ScraperFactory.get_scraper(platform)
        try:
            videos = await scraper.fetch_latest_videos(username, limit=5)
            print(f"{platform}: {len(videos)} videos")
        except Exception as e:
            print(f"{platform}: Error - {e}")

asyncio.run(fetch_from_all_platforms("testuser"))
```

### Filter Videos by Duration

```python
async def fetch_short_videos(username: str, max_duration: int = 30):
    scraper = ScraperFactory.get_scraper("tiktok")
    videos = await scraper.fetch_latest_videos(username, limit=20)
    
    short_videos = [
        v for v in videos
        if v.duration_seconds and v.duration_seconds <= max_duration
    ]
    
    return short_videos
```

---

## 🚀 Next Steps

1. **Add Instagram scraper** (Task: TBD)
2. **Add Facebook scraper** (Task: TBD)
3. **Add YouTube Shorts scraper** (Task: TBD)
4. **Implement caching layer** for API responses
5. **Add video download functionality**

---

**Questions?** Check the main [README.md](README.md) or [ARCHITECTURE-SPEC.md](ARCHITECTURE-SPEC.md).
