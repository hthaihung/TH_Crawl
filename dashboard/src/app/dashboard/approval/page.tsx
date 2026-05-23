'use client';

export const dynamic = 'force-dynamic';

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, ArrowLeft, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { supabase } from '../../../lib/supabase';
import type { AIMappingWithRelations } from '../../../types/database';
import Button from '../../../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';

export default function ApprovalPage() {
  const [mappings, setMappings] = useState<AIMappingWithRelations[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);

  useEffect(() => {
    async function init() {
      try {
        await fetch('/api/approval/recommend', { method: 'POST' });
      } catch (err) {
        console.error('Failed to compute missing suggestions:', err);
      }
      await fetchPendingMappings();
    }
    init();
  }, []);

  async function fetchPendingMappings() {
    try {
      const { data, error } = await supabase
        .from('ai_mappings')
        .select(`
          *,
          social_targets (*),
          discord_channels (*)
        `)
        .eq('status', 'pending')
        .order('confidence_score', { ascending: false });

      if (error) throw error;
      setMappings(data || []);
    } catch (error) {
      console.error('Error fetching mappings:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(mappingId: string) {
    setProcessingId(mappingId);
    try {
      const { error } = await supabase
        .from('ai_mappings')
        .update({
          status: 'approved',
          reviewed_at: new Date().toISOString(),
        })
        .eq('id', mappingId);

      if (error) throw error;

      // Remove from list
      setMappings((prev) => prev.filter((m) => m.id !== mappingId));
    } catch (error) {
      console.error('Error approving mapping:', error);
      alert('Failed to approve mapping');
    } finally {
      setProcessingId(null);
    }
  }

  async function handleReject(mappingId: string) {
    setProcessingId(mappingId);
    try {
      const { error } = await supabase
        .from('ai_mappings')
        .update({
          status: 'rejected',
          reviewed_at: new Date().toISOString(),
        })
        .eq('id', mappingId);

      if (error) throw error;

      // Remove from list
      setMappings((prev) => prev.filter((m) => m.id !== mappingId));
    } catch (error) {
      console.error('Error rejecting mapping:', error);
      alert('Failed to reject mapping');
    } finally {
      setProcessingId(null);
    }
  }

  function getConfidenceColor(score: number | null): string {
    if (!score) return 'text-gray-500';
    const percentage = score * 100;
    if (percentage >= 80) return 'text-green-600';
    if (percentage >= 60) return 'text-yellow-600';
    return 'text-orange-600';
  }

  function getConfidenceBadgeColor(score: number | null): string {
    if (!score) return 'bg-gray-100 text-gray-800';
    const percentage = score * 100;
    if (percentage >= 80) return 'bg-green-100 text-green-800';
    if (percentage >= 60) return 'bg-yellow-100 text-yellow-800';
    return 'bg-orange-100 text-orange-800';
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
            <h1 className="text-3xl font-bold">AI Mapping Approval</h1>
          </div>
          <div className="text-sm text-gray-600">
            {mappings.length} pending {mappings.length === 1 ? 'mapping' : 'mappings'}
          </div>
        </div>

        {mappings.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">All caught up!</h2>
              <p className="text-gray-600">
                No pending AI mapping suggestions to review.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {mappings.map((mapping) => (
              <Card key={mapping.id} className="overflow-hidden">
                <CardContent className="p-0">
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-blue-600" />
                        <span className="text-sm font-medium text-gray-600">
                          AI Suggestion
                        </span>
                      </div>
                      <span
                        className={`px-3 py-1 rounded-full text-sm font-semibold ${getConfidenceBadgeColor(
                          mapping.confidence_score
                        )}`}
                      >
                        {mapping.confidence_score
                          ? `${Math.round(mapping.confidence_score * 100)}% Match`
                          : 'N/A'}
                      </span>
                    </div>

                    <div className="grid md:grid-cols-2 gap-6 mb-6">
                      {/* Discord Channel */}
                      <div className="bg-indigo-50 rounded-lg p-4">
                        <div className="text-xs font-medium text-indigo-600 mb-2">
                          DISCORD CHANNEL
                        </div>
                        <div className="font-semibold text-lg mb-1">
                          #{mapping.discord_channels.channel_name}
                        </div>
                        <div className="text-sm text-gray-600">
                          {mapping.discord_channels.guild_name}
                        </div>
                        {mapping.discord_channels.description && (
                          <div className="text-sm text-gray-500 mt-2">
                            {mapping.discord_channels.description}
                          </div>
                        )}
                        {mapping.discord_channels.content_tags &&
                          mapping.discord_channels.content_tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {mapping.discord_channels.content_tags.map((tag) => (
                                <span
                                  key={tag}
                                  className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs rounded"
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                      </div>

                      {/* Social Target */}
                      <div className="bg-blue-50 rounded-lg p-4">
                        <div className="text-xs font-medium text-blue-600 mb-2">
                          SOCIAL MEDIA TARGET
                        </div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="px-2 py-0.5 bg-blue-200 text-blue-800 text-xs font-medium rounded">
                            {mapping.social_targets.platform}
                          </span>
                          <div className="font-semibold text-lg">
                            {mapping.social_targets.display_name}
                          </div>
                        </div>
                        <div className="text-sm text-gray-600 mb-2">
                          {mapping.social_targets.target_url}
                        </div>
                        {mapping.social_targets.description && (
                          <div className="text-sm text-gray-500">
                            {mapping.social_targets.description}
                          </div>
                        )}
                      </div>
                    </div>

                    {mapping.reasoning && (
                      <div className="bg-gray-50 rounded-lg p-3 mb-4">
                        <div className="text-xs font-medium text-gray-600 mb-1">
                          AI REASONING
                        </div>
                        <div className="text-sm text-gray-700">
                          {mapping.reasoning}
                        </div>
                      </div>
                    )}

                    <div className="flex gap-3">
                      <Button
                        onClick={() => handleApprove(mapping.id)}
                        disabled={processingId === mapping.id}
                        className="flex-1"
                      >
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Approve
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={() => handleReject(mapping.id)}
                        disabled={processingId === mapping.id}
                        className="flex-1"
                      >
                        <XCircle className="w-4 h-4 mr-2" />
                        Reject
                      </Button>
                    </div>
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
