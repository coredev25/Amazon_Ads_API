'use client';

import React, { useState } from 'react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Eye, MousePointerClick, TrendingUp, DollarSign, Target, Activity } from 'lucide-react';
import { formatCurrency, formatPercentage, cn } from '@/utils/helpers';

interface ChartDataPoint {
  date: string;
  spend: number;
  sales: number;
  acos: number;
  roas: number;
  impressions?: number;
  clicks?: number;
  cpc?: number;
  ctr?: number;
  orders?: number;
  cvr?: number;
}

interface PreviousPeriodDataPoint {
  date: string;
  spend: number;
  sales: number;
  acos: number;
  roas: number;
}

interface MasterPerformanceChartProps {
  data: ChartDataPoint[];
  previousPeriodData?: PreviousPeriodDataPoint[];
  height?: number;
  className?: string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload) return null;

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
      <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">{label}</p>
      {payload.map((entry: any, index: number) => (
        <div key={index} className="flex items-center gap-2 text-sm mb-1">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-gray-600 dark:text-gray-400">{entry.name}:</span>
          <span className="text-gray-900 dark:text-white font-medium">
            {entry.name.toLowerCase().includes('spend') ||
            entry.name.toLowerCase().includes('sales')
              ? formatCurrency(entry.value)
              : entry.name.toLowerCase().includes('acos') ||
                entry.name.toLowerCase().includes('cpc')
              ? `${entry.value.toFixed(2)}${entry.name.toLowerCase().includes('acos') ? '%' : ''}`
              : entry.name.toLowerCase().includes('roas')
              ? `${entry.value.toFixed(2)}x`
              : entry.name.toLowerCase().includes('ctr') ||
                entry.name.toLowerCase().includes('cvr')
              ? formatPercentage(entry.value)
              : entry.value.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
};

export default function MasterPerformanceChart({
  data,
  previousPeriodData,
  height = 400,
  className,
}: MasterPerformanceChartProps) {
  const [visibleMetrics, setVisibleMetrics] = useState({
    spend: true,
    acos: true,
    sales: false,
    impressions: false,
    clicks: false,
    cpc: false,
    ctr: false,
    roas: false,
    cvr: false,
  });

  const toggleMetric = (metric: keyof typeof visibleMetrics) => {
    setVisibleMetrics((prev) => ({
      ...prev,
      [metric]: !prev[metric],
    }));
  };

  const metricButtons = [
    { key: 'spend' as const, label: 'Spend', icon: DollarSign, color: '#FF9900' },
    { key: 'sales' as const, label: 'Sales', icon: TrendingUp, color: '#10B981' },
    { key: 'acos' as const, label: 'ACOS', icon: Target, color: '#F59E0B' },
    { key: 'impressions' as const, label: 'Impressions', icon: Eye, color: '#3B82F6' },
    { key: 'clicks' as const, label: 'Clicks', icon: MousePointerClick, color: '#8B5CF6' },
    { key: 'cpc' as const, label: 'CPC', icon: DollarSign, color: '#EC4899' },
    { key: 'ctr' as const, label: 'CTR', icon: Activity, color: '#14B8A6' },
    { key: 'roas' as const, label: 'ROAS', icon: TrendingUp, color: '#10B981' },
    { key: 'cvr' as const, label: 'CVR', icon: Activity, color: '#14B8A6' },
  ];

  // Determine which metrics use left vs right axis
  const leftAxisMetrics = ['spend', 'sales', 'impressions', 'clicks'];
  const rightAxisMetrics = ['acos', 'cpc', 'ctr', 'cvr', 'roas'];

  return (
    <div className={cn('space-y-4', className)}>
      {/* Metric Toggles */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mr-2">Metrics:</span>
        {metricButtons.map(({ key, label, icon: Icon, color }) => (
          <button
            key={key}
            onClick={() => toggleMetric(key)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              visibleMetrics[key]
                ? 'bg-amazon-orange/20 text-amazon-orange border border-amazon-orange'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:bg-gray-200 dark:hover:bg-gray-700'
            )}
          >
            <Icon className="w-4 h-4" style={{ color: visibleMetrics[key] ? color : undefined }} />
            {label}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="card p-4">
        <ResponsiveContainer width="100%" height={height}>
          <ComposedChart data={data}>
            <defs>
              <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#FF9900" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#FF9900" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="salesGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#30363D" />
            <XAxis
              dataKey="date"
              stroke="#8B949E"
              tick={{ fill: '#8B949E', fontSize: 12 }}
              axisLine={{ stroke: '#30363D' }}
            />
            <YAxis
              yAxisId="left"
              stroke="#8B949E"
              tick={{ fill: '#8B949E', fontSize: 12 }}
              axisLine={{ stroke: '#30363D' }}
              tickFormatter={(value) => {
                if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
                if (value >= 1000) return `$${(value / 1000).toFixed(0)}k`;
                return `$${value}`;
              }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#8B949E"
              tick={{ fill: '#8B949E', fontSize: 12 }}
              axisLine={{ stroke: '#30363D' }}
              tickFormatter={(value) => {
                if (value >= 100) return `${(value / 100).toFixed(1)}%`;
                return `${value.toFixed(1)}${value < 10 ? '%' : ''}`;
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: '20px' }}
              iconType="circle"
            />

            {/* Left Axis Metrics (Bars) */}
            {visibleMetrics.spend && (
              <Bar
                yAxisId="left"
                dataKey="spend"
                name="Spend"
                fill="#FF9900"
                radius={[4, 4, 0, 0]}
                opacity={0.8}
              />
            )}
            {visibleMetrics.sales && (
              <Bar
                yAxisId="left"
                dataKey="sales"
                name="Sales"
                fill="#10B981"
                radius={[4, 4, 0, 0]}
                opacity={0.8}
              />
            )}
            {visibleMetrics.impressions && (
              <Bar
                yAxisId="left"
                dataKey="impressions"
                name="Impressions"
                fill="#3B82F6"
                radius={[4, 4, 0, 0]}
                opacity={0.6}
              />
            )}
            {visibleMetrics.clicks && (
              <Bar
                yAxisId="left"
                dataKey="clicks"
                name="Clicks"
                fill="#8B5CF6"
                radius={[4, 4, 0, 0]}
                opacity={0.6}
              />
            )}

            {/* Right Axis Metrics (Lines) */}
            {visibleMetrics.acos && (
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="acos"
                name="ACOS"
                stroke="#F59E0B"
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 6, strokeWidth: 2 }}
              />
            )}
            {visibleMetrics.cpc && (
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="cpc"
                name="CPC"
                stroke="#EC4899"
                strokeWidth={2}
                dot={false}
                strokeDasharray="5 5"
              />
            )}
            {visibleMetrics.ctr && (
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="ctr"
                name="CTR"
                stroke="#14B8A6"
                strokeWidth={2}
                dot={false}
                strokeDasharray="3 3"
              />
            )}
            {visibleMetrics.roas && (
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="roas"
                name="ROAS"
                stroke="#10B981"
                strokeWidth={2}
                dot={false}
                strokeDasharray="4 4"
              />
            )}
            {visibleMetrics.cvr && (
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="cvr"
                name="CVR"
                stroke="#14B8A6"
                strokeWidth={2}
                dot={false}
                strokeDasharray="2 2"
              />
            )}

            {/* Previous Period Comparison (Dotted Lines) */}
            {previousPeriodData && visibleMetrics.spend && (
              <Line
                yAxisId="left"
                type="monotone"
                dataKey={(entry: any) => {
                  const prev = previousPeriodData.find((p) => p.date === entry.date);
                  return prev?.spend;
                }}
                name="Previous Spend"
                stroke="#FF9900"
                strokeWidth={2}
                dot={false}
                strokeDasharray="5 5"
                strokeOpacity={0.5}
              />
            )}
            {previousPeriodData && visibleMetrics.acos && (
              <Line
                yAxisId="right"
                type="monotone"
                dataKey={(entry: any) => {
                  const prev = previousPeriodData.find((p) => p.date === entry.date);
                  return prev?.acos;
                }}
                name="Previous ACOS"
                stroke="#F59E0B"
                strokeWidth={2}
                dot={false}
                strokeDasharray="5 5"
                strokeOpacity={0.5}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

