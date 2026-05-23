"""
Supabase client initialization and configuration.

This module provides a singleton Supabase client instance for the worker
to interact with the database. Uses the service role key to bypass RLS.
"""

import os
from typing import Optional
from supabase import create_client, Client


class SupabaseClientError(Exception):
    """Custom exception for Supabase client initialization errors."""
    pass


# Singleton instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create a Supabase client instance.
    
    This function implements the singleton pattern to ensure only one
    Supabase client is created throughout the application lifecycle.
    
    Returns:
        Client: Initialized Supabase client instance.
        
    Raises:
        SupabaseClientError: If required environment variables are missing
                            or client initialization fails.
    
    Example:
        >>> from database.supabase_client import get_supabase_client
        >>> client = get_supabase_client()
        >>> response = client.table('social_targets').select('*').execute()
    """
    global _supabase_client
    
    # Return existing instance if already initialized
    if _supabase_client is not None:
        return _supabase_client
    
    # Validate required environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url:
        raise SupabaseClientError(
            "SUPABASE_URL environment variable is not set. "
            "Please check your .env file."
        )
    
    if not supabase_key:
        raise SupabaseClientError(
            "SUPABASE_SERVICE_ROLE_KEY environment variable is not set. "
            "Please check your .env file."
        )
    
    # Validate URL format
    if not supabase_url.startswith("https://"):
        raise SupabaseClientError(
            f"Invalid SUPABASE_URL format: '{supabase_url}'. "
            "URL must start with 'https://'"
        )
    
    # Initialize Supabase client
    try:
        _supabase_client = create_client(supabase_url, supabase_key)
        return _supabase_client
    except TypeError as e:
        # Handle version compatibility issues
        if "proxy" in str(e):
            raise SupabaseClientError(
                f"Supabase client initialization failed due to version incompatibility. "
                f"Please ensure supabase-py is version 2.0.0 or higher. Error: {str(e)}"
            ) from e
        raise SupabaseClientError(
            f"Failed to initialize Supabase client: {str(e)}"
        ) from e
    except Exception as e:
        raise SupabaseClientError(
            f"Failed to initialize Supabase client: {str(e)}"
        ) from e


def reset_client() -> None:
    """
    Reset the singleton Supabase client instance.
    
    This is primarily useful for testing purposes to force
    re-initialization of the client with different credentials.
    
    Warning:
        This should not be used in production code.
    """
    global _supabase_client
    _supabase_client = None
