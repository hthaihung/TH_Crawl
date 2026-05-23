import { NextResponse } from 'next/server';
import { supabase } from '../../../../lib/supabase';
import { findBestMatches } from '../../../../lib/similarity';

const CONFIDENCE_THRESHOLD = 40;

export async function POST() {
  try {
    const { data: targets, error: targetsError } = await supabase
      .from('social_targets')
      .select('*')
      .eq('is_active', true);
      
    if (targetsError) throw targetsError;

    const { data: existingMappings, error: mappingsError } = await supabase
      .from('ai_mappings')
      .select('social_target_id');
      
    if (mappingsError) throw mappingsError;

    const mappedTargetIds = new Set(
      existingMappings?.map(m => m.social_target_id) || []
    );
    
    const unmappedTargets = targets?.filter(
      t => !mappedTargetIds.has(t.id)
    ) || [];
    
    if (unmappedTargets.length === 0) {
      return NextResponse.json({ success: true, count: 0 });
    }

    const { data: channels, error: channelsError } = await supabase
      .from('discord_channels')
      .select('*')
      .eq('is_active', true);
      
    if (channelsError) throw channelsError;
    
    if (!channels || channels.length === 0) {
      return NextResponse.json({ success: true, count: 0 });
    }

    let insertedCount = 0;

    for (const target of unmappedTargets) {
      const matches = findBestMatches(
        channels,
        target.display_name,
        target.description,
        CONFIDENCE_THRESHOLD
      );
      
      for (const match of matches) {
        const { error: insertError } = await supabase.from('ai_mappings').insert({
          social_target_id: target.id,
          discord_channel_id: match.channelId,
          status: 'pending',
          confidence_score: match.score / 100,
          reasoning: `Auto-suggested: ${match.score}% text similarity`,
        });
        
        if (!insertError) {
          insertedCount++;
        } else {
          console.error('Error inserting mapping:', insertError);
        }
      }
    }

    return NextResponse.json({ success: true, count: insertedCount });
  } catch (error) {
    console.error('Error in approval recommend API:', error);
    return NextResponse.json(
      { success: false, error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}
