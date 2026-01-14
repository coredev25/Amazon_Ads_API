'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Ban,
  Check,
  Clock,
  Filter,
  AlertTriangle,
  DollarSign,
  MousePointerClick,
  X,
  Eye,
  RefreshCw,
} from 'lucide-react';
import SmartGrid from '@/components/SmartGrid';
import {
  fetchNegativeCandidates,
  approveNegativeKeyword,
  rejectNegativeKeyword,
  holdNegativeKeyword,
  type NegativeCandidate,
} from '@/utils/api';
import {
  formatCurrency,
  formatNumber,
  formatPercentage,
  cn,
  getPriorityBadge,
} from '@/utils/helpers';

export default function NegativesPage() {
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  
  const queryClient = useQueryClient();

  const { data: candidates, isLoading, refetch } = useQuery({
    queryKey: ['negative-candidates'],
    queryFn: () => fetchNegativeCandidates({ limit: 100 }),
  });

  const approveMutation = useMutation({
    mutationFn: ({ keywordId, matchType }: { keywordId: number; matchType: string }) =>
      approveNegativeKeyword(keywordId, matchType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['negative-candidates'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (keywordId: number) => rejectNegativeKeyword(keywordId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['negative-candidates'] });
    },
  });

  const holdMutation = useMutation({
    mutationFn: ({ keywordId, days }: { keywordId: number; days: number }) =>
      holdNegativeKeyword(keywordId, days),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['negative-candidates'] });
    },
  });

  const filteredCandidates = candidates?.filter((c) => {
    if (severityFilter !== 'all' && c.severity !== severityFilter) return false;
    if (statusFilter !== 'all' && c.status !== statusFilter) return false;
    return true;
  });

  // Calculate wasted spend
  const totalWastedSpend = candidates?.reduce((sum, c) => {
    if (c.orders === 0) return sum + c.spend;
    return sum;
  }, 0) || 0;

  // Calculate potential savings
  const potentialSavings = candidates?.filter(c => c.status === 'pending').reduce((sum, c) => sum + c.spend, 0) || 0;

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'high': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const columns = [
    {
      key: 'keyword_text',
      header: 'Keyword / Search Term',
      sortable: true,
      render: (value: unknown, row: NegativeCandidate) => (
        <div className="max-w-xs">
          <p className="font-medium text-gray-900 dark:text-white truncate">{row.keyword_text}</p>
          {row.search_term && (
            <p className="text-xs text-gray-400 truncate">Term: {row.search_term}</p>
          )}
        </div>
      ),
    },
    {
      key: 'match_type',
      header: 'Match',
      sortable: true,
      render: (value: unknown, row: NegativeCandidate) => (
        <span className="badge badge-neutral">{row.match_type}</span>
      ),
    },
    {
      key: 'spend',
      header: 'Spend',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: NegativeCandidate) => (
        <span className={cn('font-mono', row.orders === 0 && 'text-red-400')}>
          {formatCurrency(row.spend)}
        </span>
      ),
    },
    {
      key: 'impressions',
      header: 'Impr.',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: NegativeCandidate) => formatNumber(row.impressions),
    },
    {
      key: 'clicks',
      header: 'Clicks',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: NegativeCandidate) => formatNumber(row.clicks),
    },
    {
      key: 'orders',
      header: 'Orders',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: NegativeCandidate) => (
        <span className={cn(row.orders === 0 && 'text-red-400 font-medium')}>
          {formatNumber(row.orders)}
        </span>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      sortable: true,
      render: (value: unknown, row: NegativeCandidate) => (
        <span className={cn('badge border', getSeverityColor(row.severity))}>
          {row.severity}
        </span>
      ),
    },
    {
      key: 'confidence',
      header: 'Confidence',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: NegativeCandidate) => (
        <div className="flex items-center gap-2 justify-end">
          <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all',
                row.confidence >= 0.8 ? 'bg-green-500' :
                row.confidence >= 0.5 ? 'bg-yellow-500' :
                'bg-red-500'
              )}
              style={{ width: `${row.confidence * 100}%` }}
            />
          </div>
          <span className="text-sm text-gray-300">{(row.confidence * 100).toFixed(0)}%</span>
        </div>
      ),
    },
    {
      key: 'reason',
      header: 'Reason',
      render: (value: unknown, row: NegativeCandidate) => (
        <span className="text-xs text-gray-400 max-w-xs truncate block" title={row.reason}>
          {row.reason}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (value: unknown, row: NegativeCandidate) => (
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              approveMutation.mutate({
                keywordId: row.keyword_id,
                matchType: row.suggested_action || 'negative_exact',
              });
            }}
            disabled={approveMutation.isPending || row.status !== 'pending'}
            className={cn(
              'btn btn-success py-1 px-2 text-xs',
              row.status !== 'pending' && 'opacity-50 cursor-not-allowed'
            )}
            title="Add as Negative"
          >
            <Ban className="w-3 h-3" />
            Negate
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              holdMutation.mutate({
                keywordId: row.keyword_id,
                days: 30,
              });
            }}
            disabled={holdMutation.isPending || row.status !== 'pending'}
            className={cn(
              'btn btn-secondary py-1 px-2 text-xs',
              row.status !== 'pending' && 'opacity-50 cursor-not-allowed'
            )}
            title="Put on 30-day hold"
          >
            <Clock className="w-3 h-3" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              rejectMutation.mutate(row.keyword_id);
            }}
            disabled={rejectMutation.isPending || row.status !== 'pending'}
            className={cn(
              'btn btn-ghost py-1 px-2 text-xs text-gray-400 hover:text-red-400',
              row.status !== 'pending' && 'opacity-50 cursor-not-allowed'
            )}
            title="Reject - Keep keyword active"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Negative Keywords & Waste Analyzer</h1>
          <p className="text-gray-400 mt-1">
            Identify and manage wasted spend opportunities with AI-powered analysis
          </p>
        </div>
        <button onClick={() => refetch()} className="btn btn-secondary">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-red-500/20 text-red-400">
              <DollarSign className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Wasted Spend</p>
              <p className="text-xl font-bold text-red-400">
                {formatCurrency(totalWastedSpend)}
              </p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-green-500/20 text-green-400">
              <DollarSign className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Potential Savings</p>
              <p className="text-xl font-bold text-green-400">
                {formatCurrency(potentialSavings)}
              </p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-orange-500/20 text-orange-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Candidates Found</p>
              <p className="text-xl font-bold text-gray-900 dark:text-white">
                {candidates?.length || 0}
              </p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-red-500/20 text-red-400">
              <Ban className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Critical</p>
              <p className="text-xl font-bold text-red-400">
                {candidates?.filter((c) => c.severity === 'critical').length || 0}
              </p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-yellow-500/20 text-yellow-400">
              <MousePointerClick className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Zero Orders</p>
              <p className="text-xl font-bold text-yellow-400">
                {candidates?.filter((c) => c.orders === 0).length || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="alert alert-info">
        <Eye className="w-5 h-5" />
        <div>
          <p className="font-medium">How it works</p>
          <p className="text-sm">
            The AI analyzes search terms and keywords with high spend and zero/low conversions over multiple windows.
            Critical severity indicates consistent poor performance across 3+ lookback windows.
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="select"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="select"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="applied">Applied</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      {/* Data Table */}
      <SmartGrid
        data={filteredCandidates || []}
        columns={columns}
        keyField="keyword_id"
        loading={isLoading}
        emptyMessage="No negative keyword candidates found. The AI is analyzing your search terms."
      />

      {/* Help Text */}
      <div className="card p-4 bg-gray-50 dark:bg-gray-800/50">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Actions Explained</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-400">
          <div className="flex items-start gap-2">
            <Ban className="w-4 h-4 text-green-400 mt-0.5" />
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Negate</p>
              <p>Add keyword as a negative to stop showing ads for this term</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Clock className="w-4 h-4 text-yellow-400 mt-0.5" />
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Hold</p>
              <p>Put on temporary 30-day hold; will be re-evaluated later</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <X className="w-4 h-4 text-red-400 mt-0.5" />
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Reject</p>
              <p>Keep keyword active; you believe it will convert</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
