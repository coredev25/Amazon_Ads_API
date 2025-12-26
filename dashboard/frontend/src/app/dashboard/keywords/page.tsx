'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Filter,
  Download,
  RefreshCw,
  Edit3,
  Check,
  X,
  TrendingUp,
  TrendingDown,
  Lock,
  Unlock,
  AlertCircle,
} from 'lucide-react';
import DataTable from '@/components/DataTable';
import { fetchKeywords, updateKeywordBid, lockKeywordBid, unlockKeywordBid, type Keyword } from '@/utils/api';
import {
  formatCurrency,
  formatAcos,
  formatRoas,
  formatNumber,
  formatPercentage,
  cn,
} from '@/utils/helpers';

export default function KeywordsPage() {
  const [dateRange, setDateRange] = useState(7);
  const [matchTypeFilter, setMatchTypeFilter] = useState<string>('all');
  const [stateFilter, setStateFilter] = useState<string>('all');
  const [editingKeyword, setEditingKeyword] = useState<number | null>(null);
  const [editBidValue, setEditBidValue] = useState<string>('');
  const [lockingKeyword, setLockingKeyword] = useState<number | null>(null);
  
  const queryClient = useQueryClient();

  const { data: keywords, isLoading, refetch } = useQuery({
    queryKey: ['keywords', dateRange],
    queryFn: () => fetchKeywords({ days: dateRange, limit: 200 }),
  });

  const bidMutation = useMutation({
    mutationFn: ({ keywordId, newBid, oldBid }: { keywordId: number; newBid: number; oldBid: number }) =>
      updateKeywordBid(keywordId, { new_value: newBid, old_value: oldBid }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keywords'] });
      setEditingKeyword(null);
    },
  });

  const lockMutation = useMutation({
    mutationFn: ({ keywordId, days }: { keywordId: number; days: number }) =>
      lockKeywordBid(keywordId, days, 'Manual lock from dashboard'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keywords'] });
      setLockingKeyword(null);
    },
  });

  const unlockMutation = useMutation({
    mutationFn: (keywordId: number) => unlockKeywordBid(keywordId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keywords'] });
    },
  });

  const filteredKeywords = keywords?.filter((k) => {
    if (matchTypeFilter !== 'all' && k.match_type?.toLowerCase() !== matchTypeFilter.toLowerCase()) return false;
    if (stateFilter !== 'all' && k.state?.toLowerCase() !== stateFilter.toLowerCase()) return false;
    return true;
  });

  const handleEditBid = (keyword: Keyword) => {
    if (keyword.is_locked) {
      alert(`This keyword is locked: ${keyword.lock_reason}`);
      return;
    }
    setEditingKeyword(keyword.keyword_id);
    setEditBidValue(keyword.bid.toFixed(2));
  };

  const handleSaveBid = (keyword: Keyword) => {
    const newBid = parseFloat(editBidValue);
    if (!isNaN(newBid) && newBid > 0) {
      bidMutation.mutate({
        keywordId: keyword.keyword_id,
        newBid,
        oldBid: keyword.bid,
      });
    }
  };

  const handleLock = (keyword: Keyword, days: number) => {
    lockMutation.mutate({ keywordId: keyword.keyword_id, days });
  };

  const handleUnlock = (keyword: Keyword) => {
    unlockMutation.mutate(keyword.keyword_id);
  };

  const getMatchTypeBadge = (matchType: string) => {
    const type = matchType?.toLowerCase();
    const badges: Record<string, string> = {
      exact: 'bg-blue-500/20 text-blue-400',
      phrase: 'bg-purple-500/20 text-purple-400',
      broad: 'bg-gray-500/20 text-gray-400',
    };
    return badges[type] || 'bg-gray-500/20 text-gray-400';
  };

  const getStateBadge = (state: string) => {
    const s = state?.toLowerCase();
    if (s === 'enabled') return 'badge-success';
    if (s === 'paused') return 'badge-warning';
    return 'badge-neutral';
  };

  const columns = [
    {
      key: 'keyword_text',
      header: 'Keyword',
      sortable: true,
      render: (value: unknown, row: Keyword) => (
        <div className="max-w-xs">
          <div className="flex items-center gap-2">
            <p className="font-medium text-gray-900 dark:text-white truncate">{row.keyword_text}</p>
            {row.is_locked && (
              <Lock className="w-3 h-3 text-amber-400 flex-shrink-0" title={row.lock_reason || 'Locked'} />
            )}
          </div>
          {row.is_locked && (
            <p className="text-xs text-amber-400/80 truncate">{row.lock_reason}</p>
          )}
        </div>
      ),
    },
    {
      key: 'match_type',
      header: 'Match',
      sortable: true,
      render: (value: unknown, row: Keyword) => (
        <span className={cn('badge', getMatchTypeBadge(row.match_type))}>
          {row.match_type}
        </span>
      ),
    },
    {
      key: 'state',
      header: 'State',
      sortable: true,
      render: (value: unknown, row: Keyword) => (
        <span className={cn('badge', getStateBadge(row.state))}>
          {row.state}
        </span>
      ),
    },
    {
      key: 'bid',
      header: 'Current Bid',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Keyword) => {
        if (editingKeyword === row.keyword_id) {
          return (
            <div className="flex items-center gap-2 justify-end">
              <input
                type="number"
                value={editBidValue}
                onChange={(e) => setEditBidValue(e.target.value)}
                className="input w-24 py-1 px-2 text-right"
                step="0.01"
                min="0.02"
                autoFocus
              />
              <button
                onClick={() => handleSaveBid(row)}
                className="p-1 text-green-400 hover:bg-green-500/20 rounded"
              >
                <Check className="w-4 h-4" />
              </button>
              <button
                onClick={() => setEditingKeyword(null)}
                className="p-1 text-red-400 hover:bg-red-500/20 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        }
        return (
          <div className="flex items-center gap-2 justify-end">
            <span className={cn('font-mono', row.is_locked && 'text-amber-400')}>{formatCurrency(row.bid)}</span>
            {!row.is_locked ? (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleEditBid(row);
                }}
                className="p-1 text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-200 dark:hover:bg-gray-700 rounded opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Edit3 className="w-3 h-3" />
              </button>
            ) : (
              <Lock className="w-3 h-3 text-amber-400" />
            )}
          </div>
        );
      },
    },
    {
      key: 'ai_suggested_bid',
      header: 'AI Suggested',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Keyword) => {
        if (!row.ai_suggested_bid) return <span className="text-gray-500">-</span>;
        
        const diff = ((row.ai_suggested_bid - row.bid) / row.bid) * 100;
        const isIncrease = diff > 0;
        
        return (
          <div className="flex items-center gap-2 justify-end">
            <span className={cn(
              'font-mono',
              isIncrease ? 'text-green-400' : 'text-red-400'
            )}>
              {formatCurrency(row.ai_suggested_bid)}
            </span>
            {isIncrease ? (
              <TrendingUp className="w-3 h-3 text-green-400" />
            ) : (
              <TrendingDown className="w-3 h-3 text-red-400" />
            )}
          </div>
        );
      },
    },
    {
      key: 'spend',
      header: 'Spend',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Keyword) => (
        <span className="font-mono">{formatCurrency(row.spend)}</span>
      ),
    },
    {
      key: 'sales',
      header: 'Sales',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Keyword) => (
        <span className="font-mono text-green-400">{formatCurrency(row.sales)}</span>
      ),
    },
    {
      key: 'acos',
      header: 'ACOS',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Keyword) => {
        const acos = row.acos;
        const color = acos === null ? 'text-gray-400' :
          acos < 9 ? 'text-green-400' :
          acos < 15 ? 'text-yellow-400' :
          'text-red-400';
        return <span className={cn('font-mono', color)}>{formatAcos(acos)}</span>;
      },
    },
    {
      key: 'impressions',
      header: 'Impr.',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Keyword) => formatNumber(row.impressions),
    },
    {
      key: 'clicks',
      header: 'Clicks',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Keyword) => formatNumber(row.clicks),
    },
    {
      key: 'orders',
      header: 'Orders',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Keyword) => formatNumber(row.orders),
    },
    {
      key: 'actions',
      header: 'Lock',
      render: (value: unknown, row: Keyword) => (
        <div className="flex items-center gap-1">
          {row.is_locked ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleUnlock(row);
              }}
              disabled={unlockMutation.isPending}
              className="p-1.5 text-amber-400 hover:bg-amber-500/20 rounded transition-colors"
              title="Unlock keyword for AI changes"
            >
              <Unlock className="w-4 h-4" />
            </button>
          ) : (
            <div className="relative">
              {lockingKeyword === row.keyword_id ? (
                <div className="flex items-center gap-1">
                  {[3, 7, 14].map((days) => (
                    <button
                      key={days}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleLock(row, days);
                      }}
                      className="px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700 rounded hover:bg-amber-500/20 text-gray-700 dark:text-gray-300 hover:text-amber-600 dark:hover:text-amber-400"
                    >
                      {days}d
                    </button>
                  ))}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setLockingKeyword(null);
                    }}
                    className="p-1 text-gray-400 hover:text-gray-900 dark:hover:text-white"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setLockingKeyword(row.keyword_id);
                  }}
                  className="p-1.5 text-gray-400 hover:text-amber-400 hover:bg-amber-500/20 rounded transition-colors opacity-0 group-hover:opacity-100"
                  title="Lock keyword from AI changes"
                >
                  <Lock className="w-4 h-4" />
                </button>
              )}
            </div>
          )}
        </div>
      ),
    },
  ];

  // Calculate locked count
  const lockedCount = keywords?.filter(k => k.is_locked).length || 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Keywords & Targeting</h1>
          <p className="text-gray-400 mt-1">
            Manage keyword bids, view AI suggestions, and lock keywords from changes
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(Number(e.target.value))}
            className="select"
          >
            <option value={7}>Last 7 Days</option>
            <option value={14}>Last 14 Days</option>
            <option value={30}>Last 30 Days</option>
          </select>
          <button
            onClick={() => refetch()}
            className="btn btn-secondary"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400" />
              <select
                value={matchTypeFilter}
                onChange={(e) => setMatchTypeFilter(e.target.value)}
                className="select"
              >
                <option value="all">All Match Types</option>
                <option value="exact">Exact</option>
                <option value="phrase">Phrase</option>
                <option value="broad">Broad</option>
              </select>
            </div>
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="select"
            >
              <option value="all">All States</option>
              <option value="enabled">Enabled</option>
              <option value="paused">Paused</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <button className="btn btn-secondary">
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="card p-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">Total Keywords</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            {keywords?.length || 0}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">With AI Suggestions</p>
          <p className="text-2xl font-bold text-amazon-orange mt-1">
            {keywords?.filter((k) => k.ai_suggested_bid).length || 0}
          </p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-amber-400" />
            <p className="text-sm text-gray-400">Locked</p>
          </div>
          <p className="text-2xl font-bold text-amber-400 mt-1">
            {lockedCount}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Avg. Bid</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            {formatCurrency(
              keywords?.length
                ? keywords.reduce((sum, k) => sum + k.bid, 0) / keywords.length
                : 0
            )}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Total Spend</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            {formatCurrency(keywords?.reduce((sum, k) => sum + k.spend, 0) || 0)}
          </p>
        </div>
      </div>

      {/* Lock Info Banner */}
      {lockedCount > 0 && (
        <div className="alert alert-warning">
          <Lock className="w-5 h-5" />
          <span>
            {lockedCount} keyword{lockedCount !== 1 ? 's are' : ' is'} locked from AI bid changes. 
            Locked keywords maintain their current bids until unlocked.
          </span>
        </div>
      )}

      {/* Data Table */}
      <DataTable
        data={filteredKeywords || []}
        columns={columns}
        keyField="keyword_id"
        loading={isLoading}
        emptyMessage="No keywords found"
        className="[&_tbody_tr]:group"
      />
    </div>
  );
}
