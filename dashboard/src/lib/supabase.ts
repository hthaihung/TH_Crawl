/**
 * Supabase client configuration for browser-side operations.
 * 
 * This module provides a singleton Supabase client instance configured
 * with the anon key for client-side data fetching with RLS enforcement.
 * 
 * IMPORTANT: The client is created lazily to prevent build-time crashes
 * when environment variables are not available during static generation.
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

let _supabase: SupabaseClient | null = null;

/**
 * Get the Supabase client singleton.
 * Lazily initializes the client on first access to avoid
 * throwing during Next.js static page generation (build time).
 */
function getSupabaseClient(): SupabaseClient {
  if (_supabase) return _supabase;

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(
      'Missing Supabase environment variables. ' +
      'Please check NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local'
    );
  }

  _supabase = createClient(supabaseUrl, supabaseAnonKey);
  return _supabase;
}

/**
 * Supabase client proxy.
 * Uses a Proxy so that `supabase.from(...)` etc. work transparently,
 * but the actual client isn't created until the first property access
 * (which only happens at runtime in the browser, never during SSR/build).
 */
export const supabase = new Proxy({} as SupabaseClient, {
  get(_target, prop, receiver) {
    const client = getSupabaseClient();
    const value = Reflect.get(client, prop, receiver);
    if (typeof value === 'function') {
      return value.bind(client);
    }
    return value;
  },
});
