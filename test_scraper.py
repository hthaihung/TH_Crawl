"""
Simple test script to demonstrate the scraper functionality.

This script shows how to use the ScraperFactory to fetch videos
from TikTok. It's meant for testing and demonstration purposes.

Usage:
    python test_scraper.py
"""

import asyncio
import sys
from src.scrapers import ScraperFactory, ScraperError


async def test_tiktok_scraper():
    """Test the TikTok scraper with a known public profile."""
    print("=" * 60)
    print("CrawlStory Scraper Test")
    print("=" * 60)
    print()
    
    # Check supported platforms
    platforms = ScraperFactory.get_supported_platforms()
    print(f"✅ Supported platforms: {', '.join(platforms)}")
    print()
    
    # Test TikTok scraper
    try:
        print("🔍 Testing TikTok scraper...")
        scraper = ScraperFactory.get_scraper("tiktok")
        print(f"   Platform: {scraper.platform_name()}")
        print()
        
        # Fetch videos from a popular TikTok account
        # Using "tiktok" as a test username (TikTok's official account)
        username = "tiktok"
        limit = 3
        
        print(f"📥 Fetching latest {limit} videos from @{username}...")
        videos = await scraper.fetch_latest_videos(username, limit=limit)
        
        print(f"✅ Successfully fetched {len(videos)} videos!")
        print()
        
        # Display video details
        for i, video in enumerate(videos, 1):
            print(f"Video {i}:")
            print(f"  ID: {video.video_id}")
            print(f"  Author: @{video.author}")
            print(f"  Caption: {video.caption[:80]}..." if len(video.caption) > 80 else f"  Caption: {video.caption}")
            print(f"  Duration: {video.duration_seconds}s")
            print(f"  Views: {video.view_count:,}" if video.view_count else "  Views: N/A")
            print(f"  Likes: {video.like_count:,}" if video.like_count else "  Likes: N/A")
            print(f"  URL: {video.original_post_url}")
            
            # Show hashtags if available
            hashtags = video.metadata.get("hashtags", [])
            if hashtags:
                print(f"  Hashtags: {', '.join(f'#{tag}' for tag in hashtags[:5])}")
            print()
        
        print("=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
        
    except ScraperError as e:
        print(f"❌ Scraper error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def test_unsupported_platform():
    """Test error handling for unsupported platforms."""
    print("\n🧪 Testing unsupported platform error handling...")
    try:
        scraper = ScraperFactory.get_scraper("myspace")
        print("❌ Should have raised UnsupportedPlatformError")
    except Exception as e:
        print(f"✅ Correctly raised error: {e}")


async def main():
    """Main test function."""
    await test_tiktok_scraper()
    await test_unsupported_platform()


if __name__ == "__main__":
    asyncio.run(main())
