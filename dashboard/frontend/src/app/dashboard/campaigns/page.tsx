'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Play,
  Pause,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle,
  Filter,
  Download,
  RefreshCw,
} from 'lucide-react';
import DataTable from '@/components/DataTable';
import { fetchCampaigns, applyCampaignAction, type Campaign } from '@/utils/api';
import {
  formatCurrency,
  formatAcos,
  formatRoas,
  formatNumber,
  formatPercentage,
  cn,
  getStatusBadge,
} from '@/utils/helpers';

export default function CampaignManager() {
  const [dateRange, setDateRange] = useState(7);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedCampaigns, setSelectedCampaigns] = useState<Set<number>>(new Set());
  
  const queryClient = useQueryClient();

  const { data: campaigns, isLoading, refetch } = useQuery({
    queryKey: ['campaigns', dateRange],
    queryFn: () => fetchCampaigns(dateRange),
  });

  const actionMutation = useMutation({
    mutationFn: ({ campaignId, action }: { campaignId: number; action: { action_type: string; new_value: number } }) =>
      applyCampaignAction(campaignId, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const filteredCampaigns = campaigns?.filter((c) => {
    if (statusFilter === 'all') return true;
    return c.status === statusFilter;
  });

  const getAIRecommendationBadge = (recommendation: string | null) => {
    if (!recommendation) return null;
    
    const badges: Record<string, { color: string; label: string }> = {
      budget_constrained: { color: 'badge-warning', label: '💰 Budget Limited' },
      wasted_spend: { color: 'badge-danger', label: '⚠️ Wasted Spend' },
      scaling_opportunity: { color: 'badge-success', label: '🚀 Scale Up' },
    };
    
    const badge = badges[recommendation];
    if (!badge) return null;
    
    return <span className={cn('badge', badge.color)}>{badge.label}</span>;
  };

  const columns = [
    {
      key: 'campaign_name',
      header: 'Campaign Name',
      sortable: true,
      render: (value: unknown, row: Campaign) => (
        <div>
          <p className="font-medium text-gray-900 dark:text-white">{row.campaign_name}</p>
          <p className="text-xs text-gray-400">{row.campaign_type}</p>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (value: unknown, row: Campaign) => (
        <span className={cn('badge', getStatusBadge(row.status))}>
          {row.status}
        </span>
      ),
    },
    {
      key: 'spend',
      header: 'Spend',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Campaign) => (
        <span className="font-mono">{formatCurrency(row.spend)}</span>
      ),
    },
    {
      key: 'sales',
      header: 'Sales',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Campaign) => (
        <span className="font-mono text-green-400">{formatCurrency(row.sales)}</span>
      ),
    },
    {
      key: 'acos',
      header: 'ACOS',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Campaign) => {
        const acos = row.acos;
        const color = acos === null ? 'text-gray-400' :
          acos < 9 ? 'text-green-400' :
          acos < 15 ? 'text-yellow-400' :
          'text-red-400';
        return <span className={cn('font-mono', color)}>{formatAcos(acos)}</span>;
      },
    },
    {
      key: 'roas',
      header: 'ROAS',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Campaign) => (
        <span className="font-mono">{formatRoas(row.roas)}</span>
      ),
    },
    {
      key: 'orders',
      header: 'Orders',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Campaign) => formatNumber(row.orders),
    },
    {
      key: 'budget',
      header: 'Budget',
      sortable: true,
      className: 'text-right',
      render: (value: unknown, row: Campaign) => {
        const utilization = row.budget > 0 ? (row.spend / row.budget) * 100 : 0;
        return (
          <div className="text-right">
            <span className="font-mono">{formatCurrency(row.budget)}</span>
            <div className="mt-1 w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full',
                  utilization >= 90 ? 'bg-red-500' :
                  utilization >= 70 ? 'bg-yellow-500' :
                  'bg-green-500'
                )}
                style={{ width: `${Math.min(utilization, 100)}%` }}
              />
            </div>
          </div>
        );
      },
    },
    {
      key: 'ai_recommendation',
      header: 'AI Signal',
      render: (value: unknown, row: Campaign) => getAIRecommendationBadge(row.ai_recommendation),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (value: unknown, row: Campaign) => (
        <div className="flex items-center gap-2">
          {row.status === 'enabled' ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                actionMutation.mutate({
                  campaignId: row.campaign_id,
                  action: { action_type: 'pause', new_value: 0 },
                });
              }}
              className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
              title="Pause Campaign"
            >
              <Pause className="w-4 h-4 text-gray-400" />
            </button>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                actionMutation.mutate({
                  campaignId: row.campaign_id,
                  action: { action_type: 'enable', new_value: 1 },
                });
              }}
              className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
              title="Enable Campaign"
            >
              <Play className="w-4 h-4 text-gray-400" />
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Campaign Manager</h1>
          <p className="text-gray-400 mt-1">
            View and manage all your advertising campaigns
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

      {/* Filters & Actions Bar */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="select"
              >
                <option value="all">All Status</option>
                <option value="enabled">Enabled</option>
                <option value="paused">Paused</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {selectedCampaigns.size > 0 && (
              <span className="text-sm text-gray-400">
                {selectedCampaigns.size} selected
              </span>
            )}
            <button className="btn btn-secondary">
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-sm text-gray-400">Total Campaigns</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            {campaigns?.length || 0}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Active Campaigns</p>
          <p className="text-2xl font-bold text-green-400 mt-1">
            {campaigns?.filter((c) => c.status === 'enabled').length || 0}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Total Spend</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            {formatCurrency(campaigns?.reduce((sum, c) => sum + c.spend, 0) || 0)}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Total Sales</p>
          <p className="text-2xl font-bold text-green-400 mt-1">
            {formatCurrency(campaigns?.reduce((sum, c) => sum + c.sales, 0) || 0)}
          </p>
        </div>
      </div>

      {/* Data Table */}
      <DataTable
        data={filteredCampaigns || []}
        columns={columns}
        keyField="campaign_id"
        loading={isLoading}
        enableSelection
        selectedRows={selectedCampaigns as unknown as Set<string | number>}
        onSelectRow={(id) => {
          const newSelection = new Set(selectedCampaigns);
          if (newSelection.has(id as number)) {
            newSelection.delete(id as number);
          } else {
            newSelection.add(id as number);
          }
          setSelectedCampaigns(newSelection);
        }}
        emptyMessage="No campaigns found"
      />
    </div>
  );
}

