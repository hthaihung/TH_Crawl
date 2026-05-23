"""
Discord bot core functionality.

This module contains the Discord bot initialization, event handlers,
and automated channel synchronization with Supabase.
"""

import os
import logging
from typing import Optional
import discord
from discord.ext import commands

from database.supabase_client import get_supabase_client, SupabaseClientError


# Configure logging
logger = logging.getLogger(__name__)


class CrawlStoryBot(commands.Bot):
    """
    Custom Discord bot for CrawlStory.
    
    Handles automated channel synchronization with Supabase and provides
    command handlers for managing social media targets and mappings.
    
    Attributes:
        guild_id: The Discord guild (server) ID to monitor.
        supabase: Supabase client instance for database operations.
    """
    
    def __init__(self, guild_id: int, *args, **kwargs):
        """
        Initialize the CrawlStory bot.
        
        Args:
            guild_id: Discord guild ID to synchronize channels from.
            *args: Additional positional arguments for commands.Bot.
            **kwargs: Additional keyword arguments for commands.Bot.
        """
        # Set up intents
        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_messages = True
        
        # Initialize parent Bot class
        super().__init__(
            command_prefix="!",
            intents=intents,
            *args,
            **kwargs
        )
        
        self.guild_id = guild_id
        self.supabase = None
        self.orchestrator = None
    
    async def setup_hook(self) -> None:
        """
        Async initialization hook called when the bot is starting.
        
        Initializes the Supabase client connection and media orchestrator.
        """
        try:
            self.supabase = get_supabase_client()
            logger.info("Supabase client initialized for bot")
            
            # Import here to avoid circular dependency
            from .scheduler import MediaOrchestrator
            
            # Initialize and start media orchestrator
            self.orchestrator = MediaOrchestrator(self)
            self.orchestrator.start()
            logger.info("Media orchestrator initialized and started")
            
        except SupabaseClientError as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    async def on_ready(self) -> None:
        """
        Event handler triggered when the bot successfully connects to Discord.
        
        Performs automated channel synchronization with Supabase.
        """
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        
        # Trigger channel synchronization
        await self.sync_channels()
    
    async def sync_channels(self) -> None:
        """
        Synchronize Discord channels with Supabase database.
        
        Fetches all text channels from the configured guild and upserts them
        into the discord_channels table. Uses channel_id as the unique key
        for conflict resolution.
        
        Raises:
            ValueError: If the configured guild is not found.
        """
        # Fetch the target guild
        guild = self.get_guild(self.guild_id)
        
        if guild is None:
            error_msg = (
                f"Guild with ID {self.guild_id} not found. "
                "Ensure the bot is invited to the server and DISCORD_GUILD_ID is correct."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Starting channel synchronization for guild: {guild.name} (ID: {guild.id})")
        
        synced_count = 0
        failed_count = 0
        
        # Loop through all text channels
        for channel in guild.text_channels:
            try:
                # Prepare channel data for upsert
                channel_data = {
                    "channel_id": str(channel.id),
                    "channel_name": channel.name,
                    "guild_id": str(guild.id),
                    "guild_name": guild.name,
                    "is_active": True,
                    "description": channel.topic or None,  # Channel topic as description
                }
                
                # Upsert into Supabase (insert or update on conflict)
                # Using upsert with on_conflict parameter for channel_id
                response = self.supabase.table("discord_channels").upsert(
                    channel_data,
                    on_conflict="channel_id"
                ).execute()
                
                synced_count += 1
                logger.debug(f"Synced channel: #{channel.name} (ID: {channel.id})")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to sync channel #{channel.name} (ID: {channel.id}): {e}")
        
        # Log summary
        total_channels = len(guild.text_channels)
        logger.info(
            f"Channel synchronization complete: "
            f"{synced_count}/{total_channels} channels synced successfully"
        )
        
        if failed_count > 0:
            logger.warning(f"{failed_count} channels failed to sync")
    
    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """
        Global error handler for bot events.
        
        Args:
            event_method: Name of the event that raised the error.
            *args: Event arguments.
            **kwargs: Event keyword arguments.
        """
        logger.exception(f"Error in event {event_method}")


def create_bot(guild_id: int) -> CrawlStoryBot:
    """
    Factory function to create and configure a CrawlStoryBot instance.
    
    Args:
        guild_id: Discord guild ID to monitor.
    
    Returns:
        CrawlStoryBot: Configured bot instance ready to run.
    
    Example:
        >>> bot = create_bot(guild_id=123456789)
        >>> bot.run(token)
    """
    return CrawlStoryBot(guild_id=guild_id)


async def run_bot(token: str, guild_id: int) -> None:
    """
    Run the Discord bot with the provided token.
    
    Args:
        token: Discord bot token from environment variables.
        guild_id: Discord guild ID to synchronize channels from.
    
    Raises:
        discord.LoginFailure: If the token is invalid.
        discord.HTTPException: If Discord API request fails.
    """
    bot = create_bot(guild_id)
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("Invalid Discord bot token")
        raise
    except Exception as e:
        logger.error(f"Bot encountered an error: {e}")
        raise
    finally:
        # Cleanup orchestrator
        if bot.orchestrator:
            bot.orchestrator.stop()
            await bot.orchestrator.cleanup()
        
        if not bot.is_closed():
            await bot.close()
            logger.info("Bot connection closed gracefully")
