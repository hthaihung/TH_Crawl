'use client';

import { useState, useEffect } from 'react';
import { Plus, Trash2, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { supabase } from '@/lib/supabase';
import { findBestMatches } from '@/lib/similarity';
import type { SocialTarget, DiscordChannel } from '@/types/database';
import Button from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

const CONFIDENCE_THRESHOLD = parseInt(
  process.env.NEXT_PUBLIC_AI_CONFIDENCE_THRESHOLD || '60'
);

export default function TargetsPage() {
  const [targets, setTargets] = useState<SocialTarget[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);

  useEffect(() => {
    fetchTargets();
  }, []);

  async function fetchTargets() {
    try {
      const { data, error } = await supabase
        .from('social_targets')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      setTargets(data || []);
    } catch (error) {
      console.error('Error fetching targets:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleAddTarget(formData: FormData) {
    const platform = formData.get('platform') as string;
    const targetUrl = formData.get('targetUrl') as string;
    const displayName = formData.get('displayName') as string;
    const description = formData.get('description') as string;

    try {
      // Insert new target
      const { data: newTarget, error: insertError } = await supabase
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

      if (insertError) throw insertError;

      // Fetch all Discord channels for AI matching
      const { data: channels, error: channelsError } = await supabase
        .from('discord_channels')
        .select('*')
        .eq('is_active', true);

      if (channelsError) throw channelsError;

      // Find best matches using AI similarity
      const matches = findBestMatches(
        channels || [],
        displayName,
        description || null,
        CONFIDENCE_THRESHOLD
      );

      // Create AI mapping suggestions
      for (const match of matches) {
        await supabase.from('ai_mappings').insert({
          social_target_id: newTarget.id,
          discord_channel_id: match.channelId,
          status: 'pending',
          confidence_score: match.score / 100,
          reasoning: `AI suggested based on ${match.score}% text similarity`,
        });
      }

      // Refresh targets list
      await fetchTargets();
      setShowAddForm(false);
    } catch (error) {
      console.error('Error adding target:', error);
      alert('Failed to add target');
    }
  }

  async function handleDeleteTarget(id: string) {
    if (!confirm('Are you sure you want to delete this target?')) return;

    try {
      const { error } = await supabase
        .from('social_targets')
        .delete()
        .eq('id', id);

      if (error) throw error;
      await fetchTargets();
    } catch (error) {
      console.error('Error deleting target:', error);
      alert('Failed to delete target');
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </Link>
            <h1 className="text-3xl font-bold">Social Media Targets</h1>
          </div>
          <Button onClick={() => setShowAddForm(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Target
          </Button>
        </div>

        {showAddForm && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Add New Target</CardTitle>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleAddTarget(new FormData(e.currentTarget));
                }}
                className="space-y-4"
              >
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Platform
                  </label>
                  <select
                    name="platform"
                    required
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="tiktok">TikTok</option>
                    <option value="instagram">Instagram</option>
                    <option value="youtube">YouTube</option>
                    <option value="twitter">Twitter</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Username/URL
                  </label>
                  <input
                    type="text"
                    name="targetUrl"
                    required
                    placeholder="@username or full URL"
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Display Name
                  </label>
                  <input
                    type="text"
                    name="displayName"
                    required
                    placeholder="Friendly name"
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Description (Optional)
                  </label>
                  <textarea
                    name="description"
                    rows={3}
                    placeholder="Content description for AI matching"
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
                <div className="flex gap-2">
                  <Button type="submit">Create Target</Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setShowAddForm(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-4">
          {targets.map((target) => (
            <Card key={target.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">
                        {target.platform}
                      </span>
                      <h3 className="text-lg font-semibold">
                        {target.display_name}
                      </h3>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">
                      {target.target_url}
                    </p>
                    {target.description && (
                      <p className="text-sm text-gray-500">
                        {target.description}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDeleteTarget(target.id)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}

          {targets.length === 0 && (
            <Card>
              <CardContent className="p-12 text-center text-gray-500">
                No targets yet. Click "Add Target" to get started.
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
