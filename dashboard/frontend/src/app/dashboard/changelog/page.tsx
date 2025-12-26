'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  History,
  Filter,
  RotateCcw,
  User,
  Zap,
  ChevronRight,
  Clock,
  DollarSign,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  XCircle,
  MinusCircle,
  BarChart3,
  Brain,
} from 'lucide-react';
import { fetchChangeLog, revertChange, fetchLearningStats, type ChangeLogEntry, type LearningStats } from '@/utils/api';
import {
  formatCurrency,
  cn,
  formatRelativeTime,
  getStatusBadge,
  formatPercentage,
} from '@/utils/helpers';

export default function ChangeLogPage() {
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('all');
  const [dateRange, setDateRange] = useState(7);
  const [showOutcomes, setShowOutcomes] = useState(true);
  
  const queryClient = useQueryClient();

  const { data: changelog, isLoading } = useQuery({
    queryKey: ['changelog', dateRange, entityTypeFilter],
    queryFn: () => fetchChangeLog({
      days: dateRange,
      entity_type: entityTypeFilter !== 'all' ? entityTypeFilter : undefined,
      limit: 200,
    }),
  });

  const { data: learningStats } = useQuery({
    queryKey: ['learning-stats', dateRange],
    queryFn: () => fetchLearningStats(dateRange),
  });

  const revertMutation = useMutation({
    mutationFn: revertChange,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['changelog'] });
    },
  });

  const getTriggeredByIcon = (triggeredBy: string) => {
    if (triggeredBy.includes('ai') || triggeredBy.includes('engine')) {
      return <Zap className="w-4 h-4 text-amazon-orange" />;
    }
    return <User className="w-4 h-4 text-blue-400" />;
  };

  const getChangeDirection = (oldValue: number, newValue: number) => {
    if (newValue > oldValue) {
      return { icon: <TrendingUp className="w-4 h-4" />, color: 'text-green-400' };
    }
    return { icon: <TrendingDown className="w-4 h-4" />, color: 'text-red-400' };
  };

  const getOutcomeIcon = (outcome: string | undefined) => {
    switch (outcome?.toLowerCase()) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'failure':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'neutral':
        return <MinusCircle className="w-4 h-4 text-gray-400" />;
      default:
        return null;
    }
  };

  const getOutcomeBadge = (outcome: string | undefined) => {
    switch (outcome?.toLowerCase()) {
      case 'success':
        return 'badge-success';
      case 'failure':
        return 'badge-danger';
      case 'neutral':
        return 'badge-neutral';
      default:
        return '';
    }
  };

  // Group by date
  const groupedChanges = changelog?.reduce((acc, entry) => {
    const date = new Date(entry.timestamp).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(entry);
    return acc;
  }, {} as Record<string, ChangeLogEntry[]>) || {};

  // Calculate outcome stats
  const outcomeStats = changelog?.reduce((acc, entry) => {
    if (entry.outcome_label) {
      acc[entry.outcome_label] = (acc[entry.outcome_label] || 0) + 1;
    }
    return acc;
  }, {} as Record<string, number>) || {};

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Transparency Log</h1>
          <p className="text-gray-400 mt-1">
            Complete audit trail of all bid and budget changes with learning outcomes
          </p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="card p-4">
          <p className="text-sm text-gray-400">Total Changes</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            {changelog?.length || 0}
          </p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amazon-orange" />
            <p className="text-sm text-gray-400">AI Changes</p>
          </div>
          <p className="text-2xl font-bold text-amazon-orange mt-1">
            {changelog?.filter((c) => c.triggered_by.includes('ai')).length || 0}
          </p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <p className="text-sm text-gray-400">Successful</p>
          </div>
          <p className="text-2xl font-bold text-green-400 mt-1">
            {outcomeStats['success'] || 0}
          </p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2">
            <XCircle className="w-4 h-4 text-red-400" />
            <p className="text-sm text-gray-400">Failed</p>
          </div>
          <p className="text-2xl font-bold text-red-400 mt-1">
            {outcomeStats['failure'] || 0}
          </p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-purple-400" />
            <p className="text-sm text-gray-400">Success Rate</p>
          </div>
          <p className="text-2xl font-bold text-purple-400 mt-1">
            {learningStats ? `${learningStats.success_rate.toFixed(1)}%` : 'N/A'}
          </p>
        </div>
      </div>

      {/* Learning Stats Bar */}
      {learningStats && learningStats.total_outcomes > 0 && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-amazon-orange" />
              Learning Loop Performance
            </h3>
            <span className="text-xs text-gray-400">
              {learningStats.total_outcomes} evaluated outcomes
            </span>
          </div>
          <div className="flex h-4 rounded-full overflow-hidden bg-gray-200 dark:bg-gray-700">
            <div 
              className="bg-green-500 transition-all" 
              style={{ width: `${(learningStats.successes / learningStats.total_outcomes) * 100}%` }}
              title={`${learningStats.successes} successes`}
            />
            <div 
              className="bg-gray-500 transition-all" 
              style={{ width: `${(learningStats.neutrals / learningStats.total_outcomes) * 100}%` }}
              title={`${learningStats.neutrals} neutral`}
            />
            <div 
              className="bg-red-500 transition-all" 
              style={{ width: `${(learningStats.failures / learningStats.total_outcomes) * 100}%` }}
              title={`${learningStats.failures} failures`}
            />
          </div>
          <div className="flex items-center justify-between mt-2 text-xs">
            <span className="text-green-400">Success: {learningStats.successes}</span>
            <span className="text-gray-400">Neutral: {learningStats.neutrals}</span>
            <span className="text-red-400">Failure: {learningStats.failures}</span>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select
                value={entityTypeFilter}
                onChange={(e) => setEntityTypeFilter(e.target.value)}
                className="select"
              >
                <option value="all">All Entities</option>
                <option value="campaign">Campaigns</option>
                <option value="ad_group">Ad Groups</option>
                <option value="keyword">Keywords</option>
              </select>
            </div>
            <select
              value={dateRange}
              onChange={(e) => setDateRange(Number(e.target.value))}
              className="select"
            >
              <option value={7}>Last 7 Days</option>
              <option value={14}>Last 14 Days</option>
              <option value={30}>Last 30 Days</option>
              <option value={90}>Last 90 Days</option>
            </select>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showOutcomes}
              onChange={(e) => setShowOutcomes(e.target.checked)}
              className="rounded accent-amazon-orange"
            />
            <span className="text-sm text-gray-400">Show Learning Outcomes</span>
          </label>
        </div>
      </div>

      {/* Timeline */}
      {isLoading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card p-4 animate-pulse">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
                  <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : Object.keys(groupedChanges).length === 0 ? (
        <div className="card p-12 text-center">
          <History className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <p className="text-gray-400">No changes recorded</p>
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(groupedChanges).map(([date, entries]) => (
            <div key={date}>
              <div className="flex items-center gap-4 mb-4">
                <div className="flex items-center gap-2 text-gray-400">
                  <Clock className="w-4 h-4" />
                  <span className="text-sm font-medium">{date}</span>
                </div>
                <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
                <span className="text-sm text-gray-500">
                  {entries.length} change{entries.length !== 1 ? 's' : ''}
                </span>
              </div>
              
              <div className="space-y-3 stagger-animation">
                {entries.map((entry) => {
                  const change = getChangeDirection(entry.old_value, entry.new_value);
                  const percentChange = entry.change_percentage || 
                    ((entry.new_value - entry.old_value) / entry.old_value * 100);
                  
                  return (
                    <div
                      key={entry.id}
                      className="card p-4 hover:border-amazon-orange/30 transition-all"
                    >
                      <div className="flex items-start gap-4">
                        {/* Triggered By Icon */}
                        <div className="p-2.5 rounded-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                          {getTriggeredByIcon(entry.triggered_by)}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="badge badge-neutral text-xs">
                              {entry.entity_type}
                            </span>
                            <span className={cn('badge', getStatusBadge(entry.status))}>
                              {entry.status}
                            </span>
                            {showOutcomes && entry.outcome_label && (
                              <span className={cn('badge flex items-center gap-1', getOutcomeBadge(entry.outcome_label))}>
                                {getOutcomeIcon(entry.outcome_label)}
                                {entry.outcome_label}
                              </span>
                            )}
                          </div>
                          <h3 className="font-medium text-gray-900 dark:text-white">
                            {entry.entity_name}
                          </h3>
                          <p className="text-sm text-gray-400 mt-1">
                            {entry.reason}
                          </p>

                          {/* Value Change */}
                          <div className="flex items-center gap-4 mt-3 flex-wrap">
                            <div className="flex items-center gap-2">
                              <DollarSign className="w-4 h-4 text-gray-400" />
                              <span className="text-gray-400">
                                {formatCurrency(entry.old_value)}
                              </span>
                              <ChevronRight className="w-4 h-4 text-gray-500" />
                              <span className={cn('font-medium', change.color)}>
                                {formatCurrency(entry.new_value)}
                              </span>
                            </div>
                            <span className={cn('flex items-center gap-1 text-sm', change.color)}>
                              {change.icon}
                              {percentChange > 0 ? '+' : ''}{percentChange.toFixed(1)}%
                            </span>
                            {showOutcomes && entry.outcome_score !== undefined && entry.outcome_score !== null && (
                              <span className="text-xs text-gray-500">
                                Outcome Score: {(entry.outcome_score * 100).toFixed(1)}%
                              </span>
                            )}
                          </div>

                          {/* Time */}
                          <p className="text-xs text-gray-500 mt-2">
                            {new Date(entry.timestamp).toLocaleTimeString('en-US', {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                            {' · '}
                            {entry.triggered_by}
                          </p>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => revertMutation.mutate(entry.id)}
                            disabled={revertMutation.isPending || entry.status === 'reverted'}
                            className={cn(
                              'btn btn-ghost py-1.5 px-3 text-sm',
                              entry.status === 'reverted' && 'opacity-50 cursor-not-allowed'
                            )}
                            title="Revert this change"
                          >
                            <RotateCcw className="w-4 h-4" />
                            Undo
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
