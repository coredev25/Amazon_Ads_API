'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/contexts/ToastContext';
import {
  History,
  Filter,
  RotateCcw,
  Search,
  Calendar,
  User,
  FileText,
  ArrowLeft,
  FileDown,
} from 'lucide-react';
import SmartGrid from '@/components/SmartGrid';
import DateRangePicker, { type DateRange } from '@/components/DateRangePicker';
import { DonutChart } from '@/components/Charts';
import { fetchChangeHistory, revertChange, type ChangeHistoryEntry } from '@/utils/api';
import { formatRelativeTime, cn } from '@/utils/helpers';
import { exportTableToPDF } from '@/utils/pdfExport';

export default function ChangeHistoryPage() {
  const toast = useToast();
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('all');
  const [dateRange, setDateRange] = useState<DateRange>({
    type: 'last_30_days',
    days: 30,
  });
  const [searchQuery, setSearchQuery] = useState('');
  const queryClient = useQueryClient();

  const { data: history, isLoading, refetch } = useQuery({
    queryKey: ['change-history', entityTypeFilter, dateRange],
    queryFn: () => fetchChangeHistory(
      entityTypeFilter !== 'all' ? entityTypeFilter : undefined,
      undefined,
      500
    ),
  });

  const undoMutation = useMutation({
    mutationFn: async (entry: ChangeHistoryEntry) => {
      return await revertChange(entry.id);
    },
    onSuccess: () => {
      toast.success('Change Reverted', 'The change has been successfully undone');
      queryClient.invalidateQueries({ queryKey: ['change-history'] });
    },
    onError: (error: Error) => {
      toast.error('Undo Failed', error.message);
    },
  });

  const filteredHistory = history?.filter((entry) => {
    // Date range filter
    if (dateRange.startDate || dateRange.endDate) {
      const changeDate = new Date(entry.change_date);
      if (dateRange.startDate && changeDate < dateRange.startDate) return false;
      if (dateRange.endDate) {
        const endOfDay = new Date(dateRange.endDate);
        endOfDay.setHours(23, 59, 59, 999);
        if (changeDate > endOfDay) return false;
      }
    } else if (dateRange.days) {
      const changeDate = new Date(entry.change_date);
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - dateRange.days);
      if (changeDate < cutoff) return false;
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        entry.entity_name?.toLowerCase().includes(query) ||
        entry.field_name.toLowerCase().includes(query) ||
        entry.old_value?.toLowerCase().includes(query) ||
        entry.new_value?.toLowerCase().includes(query) ||
        entry.reason?.toLowerCase().includes(query)
      );
    }
    return true;
  }) || [];

  const getEntityTypeIcon = (type: string) => {
    switch (type) {
      case 'campaign':
        return '🎯';
      case 'ad_group':
        return '📦';
      case 'keyword':
        return '🔑';
      case 'target':
        return '🎯';
      default:
        return '📄';
    }
  };

  const getChangeTypeColor = (type: string) => {
    switch (type) {
      case 'create':
        return 'badge-success';
      case 'update':
        return 'badge-info';
      case 'delete':
        return 'badge-danger';
      case 'status_change':
        return 'badge-warning';
      default:
        return 'badge-secondary';
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <History className="w-6 h-6 text-amazon-orange" />
            Change History / Audit Log
          </h1>
          <p className="text-gray-400 mt-1">
            Complete audit trail of all changes made to your campaigns
          </p>
        </div>
        <div className="flex items-center gap-3">
          <DateRangePicker value={dateRange} onChange={setDateRange} />
          <button
            onClick={() => {
              exportTableToPDF(
                'change-history-table',
                'Change History',
                `change-history-${new Date().toISOString().split('T')[0]}.pdf`
              ).catch(err => console.error('PDF export failed:', err));
            }}
            className="btn btn-secondary"
          >
            <FileDown className="w-4 h-4" />
            Export PDF
          </button>
          <button
            onClick={() => refetch()}
            className="btn btn-secondary"
          >
            <RotateCcw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={entityTypeFilter}
              onChange={(e) => setEntityTypeFilter(e.target.value)}
              className="select"
            >
              <option value="all">All Entities</option>
              <option value="portfolio">Portfolios</option>
              <option value="campaign">Campaigns</option>
              <option value="ad_group">Ad Groups</option>
              <option value="keyword">Keywords</option>
              <option value="target">Product Targets</option>
            </select>
          </div>
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search changes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10 w-full"
            />
          </div>
        </div>
      </div>

      {/* Summary Stats + Entity Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="card p-4 hover-lift">
          <p className="text-sm text-gray-400">Total Changes</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1 tabular-nums">
            {history?.length || 0}
          </p>
        </div>
        <div className="card p-4 hover-lift">
          <p className="text-sm text-gray-400">Today</p>
          <p className="text-2xl font-bold text-green-400 mt-1 tabular-nums">
            {history?.filter(h => {
              const changeDate = new Date(h.change_date);
              const today = new Date();
              return changeDate.toDateString() === today.toDateString();
            }).length || 0}
          </p>
        </div>
        <div className="card p-4 hover-lift">
          <p className="text-sm text-gray-400">This Week</p>
          <p className="text-2xl font-bold text-blue-400 mt-1 tabular-nums">
            {history?.filter(h => {
              const changeDate = new Date(h.change_date);
              const weekAgo = new Date();
              weekAgo.setDate(weekAgo.getDate() - 7);
              return changeDate >= weekAgo;
            }).length || 0}
          </p>
        </div>
        <div className="card p-4 hover-lift">
          <p className="text-sm text-gray-400">Manual Changes</p>
          <p className="text-2xl font-bold text-amazon-orange mt-1 tabular-nums">
            {history?.filter(h => h.triggered_by === 'manual' || h.triggered_by === 'dashboard_manual').length || 0}
          </p>
        </div>
        {/* Entity type chart */}
        {history && history.length > 0 && (
          <div className="card p-4 flex items-center gap-3 hover-lift">
            <DonutChart
              data={(() => {
                const counts: Record<string, number> = {};
                history.forEach(h => { counts[h.entity_type] = (counts[h.entity_type] || 0) + 1; });
                const colors: Record<string, string> = { campaign: '#FF9900', keyword: '#3B82F6', ad_group: '#10B981', negative_keyword: '#EF4444' };
                return Object.entries(counts).map(([name, value]) => ({ name, value, color: colors[name] || '#8B5CF6' }));
              })()}
              height={80}
              innerRadius={20}
              outerRadius={35}
            />
            <div className="space-y-1">
              {(() => {
                const counts: Record<string, number> = {};
                (history || []).forEach(h => { counts[h.entity_type] = (counts[h.entity_type] || 0) + 1; });
                const colors: Record<string, string> = { campaign: 'bg-amazon-orange', keyword: 'bg-blue-500', ad_group: 'bg-green-500', negative_keyword: 'bg-red-500' };
                return Object.entries(counts).slice(0, 4).map(([type, count]) => (
                  <div key={type} className="flex items-center gap-1.5 text-[10px]">
                    <div className={cn('w-2 h-2 rounded-full', colors[type] || 'bg-purple-500')} />
                    <span className="text-gray-500 capitalize">{type.replace('_', ' ')}</span>
                    <span className="font-bold text-gray-900 dark:text-white tabular-nums">{count}</span>
                  </div>
                ));
              })()}
            </div>
          </div>
        )}
      </div>

      {/* Change History Table */}
      <div id="change-history-table">
        <SmartGrid
          data={filteredHistory}
        columns={[
          {
            key: 'change_date',
            header: 'Date & Time',
            sortable: true,
            render: (value: unknown) => (
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {new Date(value as string).toLocaleDateString()}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {formatRelativeTime(value as string)}
                  </p>
                </div>
              </div>
            ),
          },
          {
            key: 'entity_type',
            header: 'Entity',
            sortable: true,
            render: (value: unknown, row: ChangeHistoryEntry) => (
              <div className="flex items-center gap-2">
                <span className="text-lg">{getEntityTypeIcon(value as string)}</span>
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                    {value as string}
                  </p>
                  {row.entity_name && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {row.entity_name}
                    </p>
                  )}
                </div>
              </div>
            ),
          },
          {
            key: 'field_name',
            header: 'Field',
            sortable: true,
            render: (value: unknown) => (
              <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                {(value as string).replace(/_/g, ' ')}
              </span>
            ),
          },
          {
            key: 'old_value',
            header: 'Old Value',
            render: (value: unknown) => (
              <span className="text-sm text-gray-600 dark:text-gray-400 font-mono">
                {value ? String(value) : '—'}
              </span>
            ),
          },
          {
            key: 'new_value',
            header: 'New Value',
            render: (value: unknown) => (
              <span className="text-sm text-gray-900 dark:text-white font-mono font-medium">
                {value ? String(value) : '—'}
              </span>
            ),
          },
          {
            key: 'change_type',
            header: 'Type',
            sortable: true,
            render: (value: unknown) => (
              <span className={cn('badge capitalize', getChangeTypeColor(value as string))}>
                {value as string}
              </span>
            ),
          },
          {
            key: 'triggered_by',
            header: 'Triggered By',
            sortable: true,
            render: (value: unknown) => (
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">
                  {(value as string).replace(/_/g, ' ')}
                </span>
              </div>
            ),
          },
          {
            key: 'reason',
            header: 'Reason',
            render: (value: unknown) => (
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {value ? String(value) : '—'}
              </span>
            ),
          },
          {
            key: 'actions',
            header: 'Actions',
            render: (value: unknown, row: ChangeHistoryEntry) => (
              <button
                onClick={() => undoMutation.mutate(row)}
                disabled={undoMutation.isPending || row.change_type === 'delete'}
                className="btn btn-sm btn-secondary"
                title={row.change_type === 'delete' ? 'Cannot undo deletions' : 'Undo this change'}
              >
                <RotateCcw className="w-4 h-4" />
                Undo
              </button>
            ),
          },
        ]}
        keyField="id"
          loading={isLoading}
          emptyMessage="No change history found"
        />
      </div>
    </div>
  );
}

