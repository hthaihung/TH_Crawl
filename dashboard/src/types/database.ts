/**
 * TypeScript type definitions for Supabase database tables.
 * 
 * These types match the schema defined in ARCHITECTURE-SPEC.md.
 */

export interface DiscordChannel {
  id: string;
  guild_id: string;
  channel_id: string;
  channel_name: string;
  guild_name: string;
  webhook_url: string | null;
  is_active: boolean;
  description: string | null;
  content_tags: string[] | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface SocialTarget {
  id: string;
  platform: 'tiktok' | 'instagram' | 'youtube' | 'twitter';
  target_url: string;
  target_type: 'profile' | 'hashtag' | 'playlist' | 'search';
  display_name: string;
  description: string | null;
  is_active: boolean;
  scrape_interval_minutes: number;
  scraper_config: Record<string, any>;
  last_scraped_at: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface AIMapping {
  id: string;
  social_target_id: string;
  discord_channel_id: string;
  status: 'pending' | 'approved' | 'rejected';
  confidence_score: number | null;
  reasoning: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface AIMappingWithRelations extends AIMapping {
  social_targets: SocialTarget;
  discord_channels: DiscordChannel;
}

export interface ProcessedVideo {
  id: string;
  social_target_id: string;
  discord_channel_id: string | null;
  platform: string;
  original_url: string;
  video_file_url: string | null;
  thumbnail_url: string | null;
  caption: string | null;
  author: string | null;
  author_url: string | null;
  duration_seconds: number | null;
  discord_message_id: string | null;
  delivery_status: 'scraped' | 'processing' | 'queued' | 'sent' | 'failed';
  metadata: Record<string, any>;
  processed_at: string | null;
  created_at: string;
}
