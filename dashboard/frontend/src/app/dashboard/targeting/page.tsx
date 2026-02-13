'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Download,
  RefreshCw,
  AlertCircle,
  Target,
  Crosshair,
  Package,
  Tag,
} from 'lucide-react';
import SmartGrid, { type Column } from '@/components/SmartGrid';
import DateRangePicker, { type DateRange } from '@/components/DateRangePicker';
import { fetchProductTargets, type ProductTarget } from '@/utils/api';
import {
  formatCurrency,
  formatAcos,
  formatRoas,
  formatNumber,
  formatPercentage,
  cn,
} from '@/utils/helpers';

interface ProductTargetingExtended extends ProductTarget {
  targetingTypeBadge?: string;
  profitability?: 'profitable' | 'breakeven' | 'unprofitable';
}

export default function ProductTargetingPage() {
  const [dateRange, setDateRange] = useState<DateRange>({
    type: 'last_7_days',
    days: 7,
  });
  const [targetingTypeFilter, setTargetingTypeFilter] = useState<string>('all');
  const [stateFilter, setStateFilter] = useState<string>('all');
  const [selectedRows, setSelectedRows] = useState<Set<string | number>>(new Set());
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  
  const queryClient = useQueryClient();

  // Calculate days from dateRange
  const days = dateRange.days || (dateRange.type === 'last_7_days' ? 7 : dateRange.type === 'last_14_days' ? 14 : dateRange.type === 'last_30_days' ? 30 : 7);

  const { data: targetingResponse, isLoading, refetch } = useQuery({
    queryKey: ['product-targets', dateRange.type, targetingTypeFilter, days, page, pageSize],
    queryFn: async () => {
      const res = await fetchProductTargets({
        days,
        targeting_type: targetingTypeFilter !== 'all' ? targetingTypeFilter as 'asin' | 'category' | 'brand' : undefined,
        page,
        page_size: pageSize,
      });
      return {
        ...res,
        data: res.data.map((target: ProductTarget) => ({
          ...target,
          targetingTypeBadge: getTargetingTypeBadge(target.targeting_type),
          profitability: calculateProfitability(target.acos ?? 0, 0.09), // Default 9% target ACOS
        })),
      };
    },
  });

  const targets = targetingResponse?.data ?? [];

  // Targeting type to UI badge mapping
  const getTargetingTypeBadge = (type: string): string => {
    const typeMap: Record<string, string> = {
      'asin': 'ASIN Targeting',
      'category': 'Category Targeting',
      'brand': 'Brand Targeting',
      'keyword': 'Keyword Targeting',
    };
    return typeMap[type] || type;
  };

  // Calculate profitability
  const calculateProfitability = (acos: number, targetAcos: number): 'profitable' | 'breakeven' | 'unprofitable' => {
    if (acos <= targetAcos * 0.8) return 'profitable';
    if (acos <= targetAcos * 1.2) return 'breakeven';
    return 'unprofitable';
  };

  // Grid columns configuration
  const columns: Column<ProductTargetingExtended>[] = [
    {
      key: 'targeting_id',
      header: 'Target ID',
      width: 100,
      sortable: true,
    },
    {
      key: 'targeting_value',
      header: 'Target Value',
      width: 180,
      sortable: true,
      render: (value: unknown, row: ProductTargetingExtended) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{String(value)}</span>
          <span className={cn(
            'px-2 py-1 rounded text-xs font-semibold',
            row.targeting_type === 'asin' && 'bg-blue-500/20 text-blue-700 dark:text-blue-300',
            row.targeting_type === 'category' && 'bg-purple-500/20 text-purple-700 dark:text-purple-300',
            row.targeting_type === 'brand' && 'bg-green-500/20 text-green-700 dark:text-green-300',
          )}>
            {row.targetingTypeBadge}
          </span>
        </div>
      ),
    },
    {
      key: 'campaign_name',
      header: 'Campaign',
      width: 150,
      sortable: true,
    },
    {
      key: 'ad_group_name',
      header: 'Ad Group',
      width: 150,
      sortable: true,
    },
    {
      key: 'bid',
      header: 'Bid',
      width: 100,
      editable: true,
      editType: 'currency',
      sortable: true,
      render: (value: unknown) => <span className="font-mono">{formatCurrency(Number(value))}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      width: 100,
      sortable: true,
      render: (value: unknown) => {
        const status = String(value);
        return (
          <span className={cn(
            'px-2 py-1 rounded-full text-xs font-semibold',
            status === 'enabled' && 'bg-green-500/20 text-green-700 dark:text-green-300',
            status === 'paused' && 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-300',
            status === 'archived' && 'bg-gray-500/20 text-gray-700 dark:text-gray-300',
          )}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </span>
        );
      },
    },
    {
      key: 'impressions',
      header: 'Impressions',
      width: 120,
      sortable: true,
      render: (value: unknown) => formatNumber(Number(value)),
    },
    {
      key: 'clicks',
      header: 'Clicks',
      width: 100,
      sortable: true,
      render: (value: unknown) => formatNumber(Number(value)),
    },
    {
      key: 'spend',
      header: 'Spend',
      width: 120,
      sortable: true,
      render: (value: unknown) => <span className="font-mono font-semibold">{formatCurrency(Number(value))}</span>,
    },
    {
      key: 'sales',
      header: 'Sales',
      width: 120,
      sortable: true,
      render: (value: unknown) => <span className="font-mono font-semibold">{formatCurrency(Number(value))}</span>,
    },
    {
      key: 'acos',
      header: 'ACoS',
      width: 100,
      sortable: true,
      render: (value: unknown, row: ProductTargetingExtended) => {
        const numValue = Number(value);
        const color = numValue < 0.09 ? 'text-green-600' : numValue > 0.15 ? 'text-red-600' : 'text-yellow-600';
        return <span className={cn('font-mono font-semibold', color)}>{formatAcos(numValue)}</span>;
      },
    },
    {
      key: 'roas',
      header: 'RoAS',
      width: 100,
      sortable: true,
      render: (value: unknown) => <span className="font-mono">{formatRoas(Number(value))}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-amazon-orange/20 rounded-lg">
              <Crosshair className="w-6 h-6 text-amazon-orange" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Product Targeting</h1>
          </div>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage ASIN, Category, and Brand targeting for Sponsored Products
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="btn btn-secondary flex items-center gap-2"
          disabled={isLoading}
        >
          <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Targeting Type Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 stagger-animation">
        <div className="card p-4 border border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20 hover-lift">
          <div className="flex items-center gap-2 mb-2">
            <Package className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h3 className="font-semibold text-gray-900 dark:text-white">ASIN Targeting</h3>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Target specific product ASINs to reach exact product audiences
          </p>
        </div>
        <div className="card p-4 border border-purple-200 dark:border-purple-800 bg-purple-50/50 dark:bg-purple-950/20 hover-lift">
          <div className="flex items-center gap-2 mb-2">
            <Tag className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Category Targeting</h3>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Target product categories to reach buyers browsing specific categories
          </p>
        </div>
        <div className="card p-4 border border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-950/20 hover-lift">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Brand Targeting</h3>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Target competitors' or complementary brands to reach their customers
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label">Date Range</label>
            <DateRangePicker value={dateRange} onChange={setDateRange} />
          </div>
          <div>
            <label className="label">Targeting Type</label>
            <select
              value={targetingTypeFilter}
              onChange={(e) => setTargetingTypeFilter(e.target.value)}
              className="input"
            >
              <option value="all">All Types</option>
              <option value="asin">ASIN Targeting</option>
              <option value="category">Category Targeting</option>
              <option value="brand">Brand Targeting</option>
            </select>
          </div>
          <div>
            <label className="label">Status</label>
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="input"
            >
              <option value="all">All Status</option>
              <option value="enabled">Enabled</option>
              <option value="paused">Paused</option>
              <option value="archived">Archived</option>
            </select>
          </div>
        </div>
      </div>

      {/* Smart Grid */}
      <div className="card overflow-hidden">
        <SmartGrid<ProductTargetingExtended>
          data={targets}
          columns={columns}
          keyField="targeting_id"
          loading={isLoading}
          emptyMessage="No product targets found. Create some ASIN, Category, or Brand targets to get started."
          enableSelection={true}
          selectedRows={selectedRows}
          pagination={targetingResponse ? {
            page: targetingResponse.page,
            pageSize: targetingResponse.page_size,
            total: targetingResponse.total,
            totalPages: targetingResponse.total_pages,
          } : undefined}
          onPageChange={setPage}
          onPageSizeChange={(s) => { setPageSize(s); setPage(1); }}
          onSelectRow={(id) => {
            const strId = String(id);
            const newSelected = new Set(selectedRows);
            if (newSelected.has(strId)) {
              newSelected.delete(strId);
            } else {
              newSelected.add(strId);
            }
            setSelectedRows(newSelected);
          }}
          onSelectAllRows={(ids, select) => {
            const newSelected = new Set(selectedRows);
            if (select) {
              ids.forEach(id => newSelected.add(String(id)));
            } else {
              ids.forEach(id => newSelected.delete(String(id)));
            }
            setSelectedRows(newSelected);
          }}
          onBulkAction={async (action, ids, params) => {
            console.log(`Bulk ${action} action for ${ids.length} targets`, params);
            // TODO: Implement bulk actions
          }}
          statusFilterOptions={[
            { value: 'all', label: 'All Status' },
            { value: 'enabled', label: 'Enabled' },
            { value: 'paused', label: 'Paused' },
            { value: 'archived', label: 'Archived' },
          ]}
        />
      </div>
    </div>
  );
}
