"""
Database module for CrawlStory.

Provides Supabase client initialization and database interaction utilities.
"""

from .supabase_client import get_supabase_client, SupabaseClientError

__all__ = ["get_supabase_client", "SupabaseClientError"]
