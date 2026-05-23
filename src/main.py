"""
Main entry point for the CrawlStory worker.

This module initializes the application, loads configuration,
and starts the Discord bot with database integration.
"""

import os
import sys
import logging
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def validate_environment() -> dict[str, str]:
    """
    Validate that all required environment variables are set.
    
    Returns:
        dict: Dictionary of validated environment variables.
    
    Raises:
        SystemExit: If any required variables are missing.
    """
    required_vars = {
        "SUPABASE_URL": "Supabase project URL",
        "SUPABASE_SERVICE_ROLE_KEY": "Supabase service role key",
        "DISCORD_BOT_TOKEN": "Discord bot token",
        "DISCORD_GUILD_ID": "Discord guild (server) ID to monitor"
    }
    
    env_values = {}
    missing_vars = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"{var} ({description})")
        else:
            env_values[var] = value
    
    if missing_vars:
        logger.error("Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        logger.error("Please check your .env file against .env.example")
        sys.exit(1)
    
    return env_values


def test_database_connection() -> None:
    """
    Test the Supabase database connection.
    
    Raises:
        SystemExit: If database connection fails.
    """
    try:
        from database.supabase_client import get_supabase_client
        client = get_supabase_client()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        sys.exit(1)


async def main_async() -> None:
    """
    Async main function that runs the Discord bot.
    
    Initializes the bot and starts the event loop.
    """
    logger.info("🚀 CrawlStory Worker Starting...")
    
    # Validate environment variables
    env_vars = validate_environment()
    
    # Test database connection
    test_database_connection()
    
    # Extract Discord configuration
    bot_token = env_vars["DISCORD_BOT_TOKEN"]
    guild_id = int(env_vars["DISCORD_GUILD_ID"])
    
    logger.info(f"Starting Discord bot for guild ID: {guild_id}")
    
    # Import and run the bot
    from bot.core import run_bot
    
    try:
        await run_bot(token=bot_token, guild_id=guild_id)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping bot...")
    except Exception as e:
        logger.error(f"Bot encountered a fatal error: {e}")
        sys.exit(1)


def main() -> None:
    """
    Main entry point for the CrawlStory worker application.
    
    Sets up the async event loop and runs the bot.
    """
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("✅ CrawlStory Worker shut down gracefully")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
