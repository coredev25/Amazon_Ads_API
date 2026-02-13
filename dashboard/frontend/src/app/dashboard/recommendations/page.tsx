'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/contexts/ToastContext';
import {
  Check,
  X,
  Filter,
  Lightbulb,
  TrendingUp,
  DollarSign,
  Target,
  Ban,
  Clock,
  AlertTriangle,
} from 'lucide-react';
import {
  fetchRecommendations,
  approveRecommendation,
  rejectRecommendation,
  bulkApproveRecommendations,
  type Recommendation,
} from '@/utils/api';
import {
  formatCurrency,
  formatPercentage,
  cn,
  getPriorityBadge,
  formatRelativeTime,
  getRecommendationTypeIcon,
} from '@/utils/helpers';

export default function RecommendationsPage() {
  const toast = useToast();
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [selectedRecs, setSelectedRecs] = useState<Set<string>>(new Set());
  
  const queryClient = useQueryClient();

  const { data: recommendations, isLoading, refetch } = useQuery({
    queryKey: ['recommendations'],
    queryFn: () => fetchRecommendations({ limit: 100 }),
  });

  const approveMutation = useMutation({
    mutationFn: approveRecommendation,
    onSuccess: () => {
      toast.success('Recommendation Approved', 'Change has been applied and synced to Amazon');
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    },
    onError: (error: Error) => {
      toast.error('Approval Failed', error.message);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => rejectRecommendation(id),
    onSuccess: () => {
      toast.info('Recommendation Rejected', 'The recommendation has been dismissed');
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    },
    onError: (error: Error) => {
      toast.error('Rejection Failed', error.message);
    },
  });

  const bulkApproveMutation = useMutation({
    mutationFn: bulkApproveRecommendations,
    onSuccess: () => {
      toast.success('Bulk Approved', `${selectedRecs.size} recommendation(s) approved and applied`);
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      setSelectedRecs(new Set());
    },
    onError: (error: Error) => {
      toast.error('Bulk Approval Failed', error.message);
    },
  });

  // Ensure recommendations is always a flat array (handle both array and wrapped responses)
  const recsArray: Recommendation[] = Array.isArray(recommendations)
    ? recommendations
    : Array.isArray((recommendations as any)?.data)
      ? (recommendations as any).data
      : [];

  const filteredRecs = recsArray.filter((r) => {
    if (typeFilter !== 'all' && r.recommendation_type !== typeFilter) return false;
    if (priorityFilter !== 'all' && r.priority !== priorityFilter) return false;
    return true;
  });

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'bid':
        return <DollarSign className="w-4 h-4" />;
      case 'budget':
        return <Target className="w-4 h-4" />;
      case 'negative_keyword':
        return <Ban className="w-4 h-4" />;
      default:
        return <Lightbulb className="w-4 h-4" />;
    }
  };

  const toggleSelect = (id: string) => {
    const newSelection = new Set(selectedRecs);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedRecs(newSelection);
  };

  const selectAll = () => {
    if (selectedRecs.size === filteredRecs.length) {
      setSelectedRecs(new Set());
    } else {
      setSelectedRecs(new Set(filteredRecs.map((r) => String(r.id))));
    }
  };

  // Group by priority for summary
  const priorityCounts = recsArray.reduce(
    (acc, r) => {
      const p = r.priority || 'low';
      acc[p] = (acc[p] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">AI Recommendations</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Review and approve AI-suggested optimizations
          </p>
        </div>
        <div className="flex items-center gap-3">
          {selectedRecs.size > 0 && (
            <>
              <span className="text-sm text-gray-400">
                {selectedRecs.size} selected
              </span>
              <button
                onClick={() => bulkApproveMutation.mutate(Array.from(selectedRecs))}
                className="btn btn-success"
                disabled={bulkApproveMutation.isPending}
              >
                <Check className="w-4 h-4" />
                Approve Selected
              </button>
            </>
          )}
        </div>
      </div>

      {/* Summary Cards - Command Center style */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 stagger-animation">
        {/* Total */}
        <div className="metric-card" style={{ '--accent-color': '#FF9900' } as React.CSSProperties}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total</p>
              <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white tabular-nums">{recsArray.length}</p>
            </div>
            <div className="p-3 rounded-lg" style={{ backgroundColor: '#FF990020' }}>
              <Lightbulb className="w-5 h-5" style={{ color: '#FF9900' }} />
            </div>
          </div>
        </div>
        {/* Critical */}
        <div className="metric-card" style={{ '--accent-color': '#EF4444' } as React.CSSProperties}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Critical</p>
              <p className="mt-2 text-2xl font-bold text-red-600 dark:text-red-400 tabular-nums">{priorityCounts.critical || 0}</p>
            </div>
            <div className="p-3 rounded-lg" style={{ backgroundColor: '#EF444420' }}>
              <AlertTriangle className="w-5 h-5" style={{ color: '#EF4444' }} />
            </div>
          </div>
        </div>
        {/* High */}
        <div className="metric-card" style={{ '--accent-color': '#F97316' } as React.CSSProperties}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">High</p>
              <p className="mt-2 text-2xl font-bold text-orange-600 dark:text-orange-400 tabular-nums">{priorityCounts.high || 0}</p>
            </div>
            <div className="p-3 rounded-lg" style={{ backgroundColor: '#F9731620' }}>
              <TrendingUp className="w-5 h-5" style={{ color: '#F97316' }} />
            </div>
          </div>
        </div>
        {/* Medium */}
        <div className="metric-card" style={{ '--accent-color': '#F59E0B' } as React.CSSProperties}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Medium</p>
              <p className="mt-2 text-2xl font-bold text-yellow-600 dark:text-yellow-500 tabular-nums">{priorityCounts.medium || 0}</p>
            </div>
            <div className="p-3 rounded-lg" style={{ backgroundColor: '#F59E0B20' }}>
              <Target className="w-5 h-5" style={{ color: '#F59E0B' }} />
            </div>
          </div>
        </div>
        {/* Low */}
        <div className="metric-card" style={{ '--accent-color': '#6B7280' } as React.CSSProperties}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Low</p>
              <p className="mt-2 text-2xl font-bold text-gray-600 dark:text-gray-400 tabular-nums">{priorityCounts.low || 0}</p>
            </div>
            <div className="p-3 rounded-lg" style={{ backgroundColor: '#6B728020' }}>
              <Clock className="w-5 h-5" style={{ color: '#6B7280' }} />
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="select"
              >
                <option value="all">All Types</option>
                <option value="bid">Bid Changes</option>
                <option value="budget">Budget Changes</option>
                <option value="negative_keyword">Negative Keywords</option>
              </select>
            </div>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="select"
            >
              <option value="all">All Priorities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {filteredRecs.length} of {recsArray.length} recommendations
            </span>
            <button
              onClick={selectAll}
              className="btn btn-ghost text-sm"
            >
              {selectedRecs.size === filteredRecs.length && filteredRecs.length > 0 ? 'Deselect All' : 'Select All'}
            </button>
          </div>
        </div>
      </div>

      {/* Recommendations List */}
      {isLoading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card p-4 animate-pulse">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-gray-200 dark:bg-gray-700" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
                  <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : filteredRecs.length === 0 ? (
        <div className="card p-12 text-center">
          <Lightbulb className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <p className="text-gray-400">No recommendations available</p>
          <p className="text-sm text-gray-500 mt-1">
            {recsArray.length > 0
              ? 'No recommendations match the current filters'
              : "The AI engine hasn't found any optimization opportunities"}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredRecs.map((rec, index) => {
            const recId = String(rec.id ?? `rec-${index}`);
            const adjPct = Number(rec.adjustment_percentage) || 0;
            const confidence = Number(rec.confidence) || 0;
            const currentVal = Number(rec.current_value) || 0;
            const recommendedVal = Number(rec.recommended_value) || 0;

            return (
              <div
                key={recId}
                className={cn(
                  'card p-4 transition-all hover:border-amazon-orange/30 animate-fade-in',
                  selectedRecs.has(recId) && 'border-amazon-orange bg-amazon-orange/5'
                )}
              >
                <div className="flex items-start gap-4">
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={selectedRecs.has(recId)}
                    onChange={() => toggleSelect(recId)}
                    className="mt-1 rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
                  />

                  {/* Type Icon */}
                  <div className={cn(
                    'p-2.5 rounded-lg',
                    rec.priority === 'critical' ? 'bg-red-500/20 text-red-400' :
                    rec.priority === 'high' ? 'bg-orange-500/20 text-orange-400' :
                    rec.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-gray-500/20 text-gray-400'
                  )}>
                    {getTypeIcon(rec.recommendation_type)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn('badge', getPriorityBadge(rec.priority))}>
                        {rec.priority}
                      </span>
                      <span className="badge badge-neutral">
                        {rec.recommendation_type}
                      </span>
                    </div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      <span
                        className="entity-link"
                        onClick={(e) => { e.stopPropagation(); }}
                      >
                        {rec.entity_name || `${rec.entity_type} ${rec.entity_id}`}
                      </span>
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {rec.reason || 'AI-suggested optimization'}
                    </p>

                    {/* Value Change */}
                    <div className="flex items-center gap-4 mt-3">
                      <div>
                        <p className="text-xs text-gray-600 dark:text-gray-500">Current</p>
                        <p className="font-mono text-gray-900 dark:text-white">
                          {formatCurrency(currentVal)}
                        </p>
                      </div>
                      <div className="text-gray-500 dark:text-gray-400">&rarr;</div>
                      <div>
                        <p className="text-xs text-gray-600 dark:text-gray-500">Suggested</p>
                        <p className={cn(
                          'font-mono font-medium',
                          adjPct > 0 ? 'text-green-400' : 'text-red-400'
                        )}>
                          {formatCurrency(recommendedVal)}
                        </p>
                      </div>
                      <div className={cn(
                        'badge',
                        adjPct > 0 ? 'badge-success' : 'badge-danger'
                      )}>
                        {adjPct > 0 ? '+' : ''}
                        {adjPct.toFixed(1)}%
                      </div>
                      {rec.estimated_impact && (
                        <span className="text-sm text-gray-400">
                          Est. Impact: {rec.estimated_impact}
                        </span>
                      )}
                    </div>

                    {/* Confidence & Time */}
                    <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                      <span>Confidence: {(confidence * 100).toFixed(0)}%</span>
                      <span>{rec.created_at ? formatRelativeTime(rec.created_at) : 'Recently'}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => approveMutation.mutate(recId)}
                      disabled={approveMutation.isPending}
                      className="btn btn-success"
                      title="Approve"
                    >
                      <Check className="w-4 h-4" />
                      Approve
                    </button>
                    <button
                      onClick={() => rejectMutation.mutate(recId)}
                      disabled={rejectMutation.isPending}
                      className="btn btn-danger"
                      title="Reject"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

