'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  DollarSign,
  TrendingUp,
  Target,
  AlertTriangle,
  Download,
  Filter,
  RefreshCw,
} from 'lucide-react';
import SmartGrid from '@/components/SmartGrid';
import DateRangePicker, { DateRange } from '@/components/DateRangePicker';
import { DonutChart } from '@/components/Charts';
import { fetchFinancialMetrics, type FinancialMetrics } from '@/utils/api';
import { cn, formatCurrency, formatPercentage, formatNumber } from '@/utils/helpers';
import { useLiveSettings } from '@/contexts/LiveSettingsContext';

interface FinancialMetricsExtended extends FinancialMetrics {
  profitMargin: number;
  tacosPercentage: number;
  breakEvenStatus: 'profitable' | 'at-risk' | 'unprofitable';
}

export default function FinancialPage() {
  const [dateRange, setDateRange] = useState<DateRange>({
    type: 'last_30_days',
    startDate: new Date(new Date().setDate(new Date().getDate() - 29)),
    endDate: new Date(),
    days: 30,
  });

  const [asinFilter, setAsinFilter] = useState('');
  const [sortBy, setSortBy] = useState('net_profit');

  const liveSettings = useLiveSettings();

  const { data: metrics, isLoading, refetch } = useQuery({
    queryKey: ['financial-metrics', dateRange.days],
    queryFn: () => fetchFinancialMetrics(dateRange.days || 30),
    refetchInterval: liveSettings.autoRefresh ? liveSettings.refreshInterval : undefined,
  });

  const processedMetrics = (metrics || []).map((m) => {
    const profitMargin = m.sales > 0 ? (m.net_profit / m.sales) * 100 : 0;
    const tacosPercentage = m.sales > 0 ? (m.ad_spend / m.sales) * 100 : 0;
    
    let breakEvenStatus: 'profitable' | 'at-risk' | 'unprofitable' = 'unprofitable';
    if (m.net_profit > 0 && profitMargin > 10) breakEvenStatus = 'profitable';
    else if (m.net_profit > 0) breakEvenStatus = 'at-risk';

    return {
      ...m,
      profitMargin,
      tacosPercentage,
      breakEvenStatus,
    };
  }).filter(m => !asinFilter || m.asin.includes(asinFilter.toUpperCase()))
    .sort((a, b) => {
      if (sortBy === 'net_profit') return b.net_profit - a.net_profit;
      if (sortBy === 'profit_margin') return b.profitMargin - a.profitMargin;
      if (sortBy === 'tacos') return a.tacosPercentage - b.tacosPercentage;
      return b.sales - a.sales;
    });

  const totalMetrics = processedMetrics.reduce(
    (acc, m) => ({
      sales: acc.sales + m.sales,
      cogs: acc.cogs + m.cogs,
      amazon_fees: acc.amazon_fees + m.amazon_fees,
      ad_spend: acc.ad_spend + m.ad_spend,
      gross_profit: acc.gross_profit + m.gross_profit,
      net_profit: acc.net_profit + m.net_profit,
    }),
    { sales: 0, cogs: 0, amazon_fees: 0, ad_spend: 0, gross_profit: 0, net_profit: 0 }
  );

  const avgProfitMargin = totalMetrics.sales > 0 ? (totalMetrics.net_profit / totalMetrics.sales) * 100 : 0;
  const avgTACOS = totalMetrics.sales > 0 ? (totalMetrics.ad_spend / totalMetrics.sales) * 100 : 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <DollarSign className="w-6 h-6 text-amazon-orange" />
            Financial Metrics
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Profitability analysis with COGS, fees, and break-even metrics
          </p>
        </div>
        <div className="flex items-center gap-3">
          <DateRangePicker value={dateRange} onChange={setDateRange} />
          <button
            onClick={() => refetch()}
            className="btn btn-secondary"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4 stagger-animation">
        <div className="card p-4 hover-lift">
          <p className="text-sm text-gray-600 dark:text-gray-400">Total Sales</p>
          <p className="text-2xl font-bold text-green-400 mt-1 tabular-nums">{formatCurrency(totalMetrics.sales)}</p>
        </div>
        <div className="card p-4 hover-lift">
          <p className="text-sm text-gray-600 dark:text-gray-400">Total COGS</p>
          <p className="text-2xl font-bold text-red-400 mt-1 tabular-nums">{formatCurrency(totalMetrics.cogs)}</p>
        </div>
        <div className="card p-4 hover-lift">
          <p className="text-sm text-gray-600 dark:text-gray-400">Amazon Fees</p>
          <p className="text-2xl font-bold text-orange-400 mt-1 tabular-nums">{formatCurrency(totalMetrics.amazon_fees)}</p>
        </div>
        <div className="card p-4 hover-lift">
          <p className="text-sm text-gray-600 dark:text-gray-400">Ad Spend</p>
          <p className="text-2xl font-bold text-blue-400 mt-1 tabular-nums">{formatCurrency(totalMetrics.ad_spend)}</p>
        </div>
        <div className="card p-4 hover-lift">
          <p className="text-sm text-gray-600 dark:text-gray-400">Net Profit</p>
          <p className={cn('text-2xl font-bold mt-1 tabular-nums', totalMetrics.net_profit > 0 ? 'text-green-400' : 'text-red-400')}>
            {formatCurrency(totalMetrics.net_profit)}
          </p>
        </div>
        <div className="card p-4 hover-lift">
          <p className="text-sm text-gray-600 dark:text-gray-400">Profit Margin</p>
          <p className={cn('text-2xl font-bold mt-1 tabular-nums', avgProfitMargin > 10 ? 'text-green-400' : avgProfitMargin > 0 ? 'text-yellow-400' : 'text-red-400')}>
            {formatPercentage(avgProfitMargin)}
          </p>
        </div>
      </div>

      {/* Charts Row */}
      {processedMetrics.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fade-in-up">
          {/* Cost Breakdown */}
          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Cost Breakdown</h3>
            <div className="flex items-center gap-6">
              <DonutChart
                data={[
                  { name: 'COGS', value: Math.round(totalMetrics.cogs), color: '#EF4444' },
                  { name: 'Amazon Fees', value: Math.round(totalMetrics.amazon_fees), color: '#F59E0B' },
                  { name: 'Ad Spend', value: Math.round(totalMetrics.ad_spend), color: '#3B82F6' },
                  { name: 'Net Profit', value: Math.max(0, Math.round(totalMetrics.net_profit)), color: '#10B981' },
                ]}
                height={180}
                innerRadius={45}
                outerRadius={70}
                centerLabel="Total"
                centerValue={formatCurrency(totalMetrics.sales)}
              />
              <div className="space-y-2 flex-1">
                {[
                  { label: 'COGS', value: totalMetrics.cogs, color: 'bg-red-500', pct: totalMetrics.sales > 0 ? (totalMetrics.cogs / totalMetrics.sales * 100) : 0 },
                  { label: 'Amz Fees', value: totalMetrics.amazon_fees, color: 'bg-amber-500', pct: totalMetrics.sales > 0 ? (totalMetrics.amazon_fees / totalMetrics.sales * 100) : 0 },
                  { label: 'Ad Spend', value: totalMetrics.ad_spend, color: 'bg-blue-500', pct: totalMetrics.sales > 0 ? (totalMetrics.ad_spend / totalMetrics.sales * 100) : 0 },
                  { label: 'Net Profit', value: Math.max(0, totalMetrics.net_profit), color: 'bg-green-500', pct: avgProfitMargin > 0 ? avgProfitMargin : 0 },
                ].map(item => (
                  <div key={item.label} className="flex items-center gap-2 text-xs">
                    <div className={cn('w-2.5 h-2.5 rounded-full flex-shrink-0', item.color)} />
                    <span className="text-gray-600 dark:text-gray-400 w-16">{item.label}</span>
                    <span className="text-gray-900 dark:text-white font-medium tabular-nums">{formatCurrency(item.value)}</span>
                    <span className="text-gray-400 tabular-nums">({item.pct.toFixed(1)}%)</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Profitability Distribution */}
          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Profitability Distribution</h3>
            <div className="flex items-center gap-6">
              <DonutChart
                data={[
                  { name: 'Profitable', value: processedMetrics.filter(m => m.breakEvenStatus === 'profitable').length, color: '#10B981' },
                  { name: 'At Risk', value: processedMetrics.filter(m => m.breakEvenStatus === 'at-risk').length, color: '#F59E0B' },
                  { name: 'Unprofitable', value: processedMetrics.filter(m => m.breakEvenStatus === 'unprofitable').length, color: '#EF4444' },
                ]}
                height={180}
                innerRadius={45}
                outerRadius={70}
                centerLabel="ASINs"
                centerValue={String(processedMetrics.length)}
              />
              <div className="space-y-3 flex-1">
                {[
                  { label: 'Profitable', count: processedMetrics.filter(m => m.breakEvenStatus === 'profitable').length, color: 'text-green-500', bg: 'bg-green-500' },
                  { label: 'At Risk', count: processedMetrics.filter(m => m.breakEvenStatus === 'at-risk').length, color: 'text-amber-500', bg: 'bg-amber-500' },
                  { label: 'Unprofitable', count: processedMetrics.filter(m => m.breakEvenStatus === 'unprofitable').length, color: 'text-red-500', bg: 'bg-red-500' },
                ].map(item => (
                  <div key={item.label}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2 text-xs">
                        <div className={cn('w-2.5 h-2.5 rounded-full', item.bg)} />
                        <span className="text-gray-700 dark:text-gray-300">{item.label}</span>
                      </div>
                      <span className={cn('text-sm font-bold', item.color)}>{item.count}</span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                      <div
                        className={cn('h-1.5 rounded-full transition-all duration-500', item.bg)}
                        style={{ width: `${processedMetrics.length > 0 ? (item.count / processedMetrics.length * 100) : 0}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Filter by ASIN..."
                value={asinFilter}
                onChange={(e) => setAsinFilter(e.target.value)}
                className="input text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">Sort by:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="select text-sm"
              >
                <option value="net_profit">Net Profit (High to Low)</option>
                <option value="profit_margin">Profit Margin (High to Low)</option>
                <option value="tacos">TACoS (Low to High)</option>
                <option value="sales">Sales (High to Low)</option>
              </select>
            </div>
          </div>
          <button className="btn btn-secondary">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Financial Metrics Table */}
      <SmartGrid
        data={processedMetrics}
        keyField="asin"
        loading={isLoading}
        columns={[
          {
            key: 'asin',
            header: 'ASIN',
            sortable: true,
            render: (value: unknown) => (
              <span className="font-mono text-blue-400">{String(value)}</span>
            ),
          },
          {
            key: 'sales',
            header: 'Sales',
            sortable: true,
            render: (value: unknown) => <span className="font-mono text-green-400">{formatCurrency(value as number)}</span>,
          },
          {
            key: 'cogs',
            header: 'COGS',
            sortable: true,
            render: (value: unknown) => <span className="font-mono text-red-400">{formatCurrency(value as number)}</span>,
          },
          {
            key: 'amazon_fees',
            header: 'Amazon Fees',
            sortable: true,
            render: (value: unknown) => <span className="font-mono text-orange-400">{formatCurrency(value as number)}</span>,
          },
          {
            key: 'gross_profit',
            header: 'Gross Profit',
            sortable: true,
            render: (value: unknown) => (
              <span className={cn('font-mono', Number(value) > 0 ? 'text-green-400' : 'text-red-400')}>
                {formatCurrency(value as number)}
              </span>
            ),
          },
          {
            key: 'ad_spend',
            header: 'Ad Spend',
            sortable: true,
            render: (value: unknown) => <span className="font-mono text-blue-400">{formatCurrency(value as number)}</span>,
          },
          {
            key: 'net_profit',
            header: 'Net Profit',
            sortable: true,
            render: (value: unknown) => (
              <span className={cn('font-mono font-bold', Number(value) > 0 ? 'text-green-400' : 'text-red-400')}>
                {formatCurrency(value as number)}
              </span>
            ),
          },
          {
            key: 'profitMargin',
            header: 'Profit Margin %',
            sortable: true,
            render: (value: unknown, row: FinancialMetricsExtended) => (
              <span className={cn(
                'font-mono',
                row.profitMargin > 10 ? 'text-green-400' : row.profitMargin > 0 ? 'text-yellow-400' : 'text-red-400'
              )}>
                {formatPercentage(value as number)}
              </span>
            ),
          },
          {
            key: 'tacos',
            header: 'TACoS %',
            sortable: true,
            render: (value: unknown) => (
              <span className={cn(
                'font-mono',
                Number(value) < 30 ? 'text-green-400' : Number(value) < 50 ? 'text-yellow-400' : 'text-red-400'
              )}>
                {formatPercentage(value as number)}
              </span>
            ),
          },
          {
            key: 'break_even_acos',
            header: 'Break-Even ACOS %',
            sortable: true,
            render: (value: unknown) => (
              <span className="font-mono text-blue-400">{formatPercentage(value as number)}</span>
            ),
          },
          {
            key: 'breakEvenStatus',
            header: 'Status',
            render: (value: unknown, row: FinancialMetricsExtended) => (
              <div className="flex items-center gap-2">
                {row.breakEvenStatus === 'profitable' && (
                  <span className="badge badge-success">Profitable</span>
                )}
                {row.breakEvenStatus === 'at-risk' && (
                  <span className="badge badge-warning flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    At Risk
                  </span>
                )}
                {row.breakEvenStatus === 'unprofitable' && (
                  <span className="badge badge-danger">Unprofitable</span>
                )}
              </div>
            ),
          },
        ]}
        onBulkAction={async () => {}}
      />

      {/* Legend */}
      <div className="card p-4 bg-blue-50/50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Metrics Legend</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm text-gray-700 dark:text-gray-300">
          <div>
            <p className="font-medium">Gross Profit</p>
            <p className="text-xs">Sales - COGS - Amazon Fees</p>
          </div>
          <div>
            <p className="font-medium">Net Profit</p>
            <p className="text-xs">Gross Profit - Ad Spend</p>
          </div>
          <div>
            <p className="font-medium">TACoS (Total Advertising Cost of Sales)</p>
            <p className="text-xs">Ad Spend ÷ Sales × 100</p>
          </div>
          <div>
            <p className="font-medium">Break-Even ACOS</p>
            <p className="text-xs">(Sales - COGS - Fees) ÷ Sales × 100</p>
          </div>
        </div>
      </div>
    </div>
  );
}
