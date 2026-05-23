'use client';

import { useState, useEffect } from 'react';
import { Link2, Edit, ArrowLeft, CheckCircle, XCircle } from 'lucide-react';
import Link from 'next/link';
import { supabase } from '../../../lib/supabase';
import Button from '../../../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';

interface Mapping {
  id: string;
  status: string;
  confidence_score: number | null;
  social_targets: {
    id: string;
    platform: string;
    display_name: string;
    target_url: string;
    is_active: boolean;
  };
  discord_channels: {
    id: string;
    channel_id: string;
    channel_name: string;
    guild_name: string;
    is_active: boolean;
  };
}

interface DiscordChannel {
  id: string;
  channel_id: string;
  channel_name: string;
  guild_name: string;
  is_active: boolean;
}

export default function MappingsPage() {
  const [mappings, setMappings] = useState<Mapping[]>([]);
  const [channels, setChannels] = useState<DiscordChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [selectedChannel, setSelectedChannel] = useState<string>('');

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      // Fetch all mappings with JOIN
      const { data: mappingsData, error: mappingsError } = await supabase
        .from('ai_mappings')
        .select(`
          id,
          status,
          confidence_score,
          social_targets (
            id,
            platform,
            display_name,
            target_url,
            is_active
          ),
          discord_channels (
            id,
            channel_id,
            channel_name,
            guild_name,
            is_active
          )
        `)
        .order('created_at', { ascending: false });

      if (mappingsError) {
        console.error('[UI] Mappings fetch error:', mappingsError);
      } else {
        console.log('[UI] Mappings loaded:', mappingsData);
        setMappings(mappingsData || []);
      }

      // Fetch all channels for dropdown
      const { data: channelsData, error: channelsError } = await supabase
        .from('discord_channels')
        .select('*')
        .eq('is_active', true)
        .order('channel_name');

      if (channelsError) {
        console.error('[UI] Channels fetch error:', channelsError);
      } else {
        console.log('[UI] Channels loaded:', channelsData);
        setChannels(channelsData || []);
      }
    } catch (error) {
      console.error('[UI] Fetch error:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpdateMapping(targetId: string, channelId: string) {
    try {
      console.log('[UI] Updating mapping:', { targetId, channelId });

      const response = await fetch('/api/targets', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ targetId, discordChannelId: channelId }),
      });

      const result = await response.json();
      console.log('[UI] Update result:', result);

      if (!response.ok) {
        alert(`Error: ${result.error}`);
        return;
      }

      alert('Mapping updated successfully!');
      setEditingId(null);
      await fetchData();
    } catch (error) {
      console.error('[UI] Update error:', error);
      alert('Failed to update mapping');
    }
  }

  function getStatusBadge(status: string) {
    const colors = {
      approved: 'bg-green-100 text-green-800',
      pending: 'bg-yellow-100 text-yellow-800',
      rejected: 'bg-red-100 text-red-800',
    };
    return colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg">Loading mappings...</div>
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
            <h1 className="text-3xl font-bold">Target → Channel Mappings</h1>
          </div>
          <div className="text-sm text-gray-600">
            {mappings.length} total {mappings.length === 1 ? 'mapping' : 'mappings'}
          </div>
        </div>

        {mappings.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <XCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">No mappings found</h2>
              <p className="text-gray-600">
                Create a target and assign it to a Discord channel to get started.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {mappings.map((mapping) => (
              <Card key={mapping.id}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusBadge(
                            mapping.status
                          )}`}
                        >
                          {mapping.status.toUpperCase()}
                        </span>
                        {mapping.confidence_score && (
                          <span className="text-sm text-gray-500">
                            {Math.round(mapping.confidence_score * 100)}% confidence
                          </span>
                        )}
                      </div>

                      <div className="grid md:grid-cols-2 gap-4">
                        {/* Social Target */}
                        <div className="bg-blue-50 rounded-lg p-4">
                          <div className="text-xs font-medium text-blue-600 mb-2">
                            SOCIAL TARGET
                          </div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="px-2 py-0.5 bg-blue-200 text-blue-800 text-xs font-medium rounded uppercase">
                              {mapping.social_targets.platform}
                            </span>
                            <div className="font-semibold">
                              {mapping.social_targets.display_name}
                            </div>
                          </div>
                          <div className="text-sm text-gray-600">
                            {mapping.social_targets.target_url}
                          </div>
                          <div className="mt-2">
                            {mapping.social_targets.is_active ? (
                              <span className="text-xs text-green-600 flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" /> Active
                              </span>
                            ) : (
                              <span className="text-xs text-red-600 flex items-center gap-1">
                                <XCircle className="w-3 h-3" /> Inactive
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Discord Channel */}
                        <div className="bg-indigo-50 rounded-lg p-4">
                          <div className="text-xs font-medium text-indigo-600 mb-2">
                            DISCORD CHANNEL
                          </div>
                          {editingId === mapping.id ? (
                            <div className="space-y-2">
                              <select
                                value={selectedChannel}
                                onChange={(e) => setSelectedChannel(e.target.value)}
                                className="w-full px-3 py-2 border rounded-md text-sm"
                              >
                                <option value="">Select channel...</option>
                                {channels.map((ch) => (
                                  <option key={ch.id} value={ch.id}>
                                    #{ch.channel_name} ({ch.guild_name})
                                  </option>
                                ))}
                              </select>
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  onClick={() => {
                                    if (selectedChannel) {
                                      handleUpdateMapping(
                                        mapping.social_targets.id,
                                        selectedChannel
                                      );
                                    }
                                  }}
                                  disabled={!selectedChannel}
                                >
                                  Save
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => {
                                    setEditingId(null);
                                    setSelectedChannel('');
                                  }}
                                >
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <div className="font-semibold text-lg mb-1">
                                #{mapping.discord_channels.channel_name}
                              </div>
                              <div className="text-sm text-gray-600 mb-2">
                                {mapping.discord_channels.guild_name}
                              </div>
                              <div className="text-xs text-gray-500">
                                ID: {mapping.discord_channels.channel_id}
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    {editingId !== mapping.id && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditingId(mapping.id);
                          setSelectedChannel(mapping.discord_channels.id);
                        }}
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
