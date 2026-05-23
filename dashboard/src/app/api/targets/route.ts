import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { platform, targetUrl, displayName, description, discordChannelId } = body;

    console.log('[API] Creating target:', { platform, targetUrl, displayName, discordChannelId });

    // 1. Insert social_target
    const { data: newTarget, error: targetError } = await supabase
      .from('social_targets')
      .insert({
        platform,
        target_url: targetUrl,
        display_name: displayName,
        description: description || null,
        target_type: 'profile',
        is_active: true,
      })
      .select()
      .single();

    if (targetError) {
      console.error('[API] Target insert error:', targetError);
      return NextResponse.json({ error: targetError.message }, { status: 500 });
    }

    console.log('[API] Target created:', newTarget);

    // 2. Create AI mapping with APPROVED status
    if (discordChannelId) {
      const { data: mapping, error: mappingError } = await supabase
        .from('ai_mappings')
        .insert({
          social_target_id: newTarget.id,
          discord_channel_id: discordChannelId,
          status: 'approved',
          confidence_score: 1.0,
          reasoning: 'Manually assigned by user',
        })
        .select()
        .single();

      if (mappingError) {
        console.error('[API] Mapping insert error:', mappingError);
        return NextResponse.json({ error: mappingError.message }, { status: 500 });
      }

      console.log('[API] Mapping created:', mapping);
      return NextResponse.json({ target: newTarget, mapping }, { status: 201 });
    }

    return NextResponse.json({ target: newTarget }, { status: 201 });
  } catch (error: any) {
    console.error('[API] Unexpected error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { targetId, discordChannelId } = body;

    console.log('[API] Updating mapping:', { targetId, discordChannelId });

    // Check if mapping exists
    const { data: existingMapping } = await supabase
      .from('ai_mappings')
      .select('id')
      .eq('social_target_id', targetId)
      .single();

    if (existingMapping) {
      // Update existing mapping
      const { data, error } = await supabase
        .from('ai_mappings')
        .update({
          discord_channel_id: discordChannelId,
          status: 'approved',
          reviewed_at: new Date().toISOString(),
        })
        .eq('social_target_id', targetId)
        .select()
        .single();

      if (error) {
        console.error('[API] Mapping update error:', error);
        return NextResponse.json({ error: error.message }, { status: 500 });
      }

      console.log('[API] Mapping updated:', data);
      return NextResponse.json({ mapping: data }, { status: 200 });
    } else {
      // Create new mapping
      const { data, error } = await supabase
        .from('ai_mappings')
        .insert({
          social_target_id: targetId,
          discord_channel_id: discordChannelId,
          status: 'approved',
          confidence_score: 1.0,
          reasoning: 'Manually assigned by user',
        })
        .select()
        .single();

      if (error) {
        console.error('[API] Mapping insert error:', error);
        return NextResponse.json({ error: error.message }, { status: 500 });
      }

      console.log('[API] Mapping created:', data);
      return NextResponse.json({ mapping: data }, { status: 201 });
    }
  } catch (error: any) {
    console.error('[API] Unexpected error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
