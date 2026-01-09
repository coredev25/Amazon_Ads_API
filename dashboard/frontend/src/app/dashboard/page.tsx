'use client';

import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  DollarSign,
  ShoppingCart,
  Target,
  TrendingUp,
  MousePointerClick,
  Eye,
  Zap,
  Activity,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import MetricCard from '@/components/MetricCard';
import { SpendSalesChart, HealthGauge } from '@/components/Charts';
import EngineStatus from '@/components/EngineStatus';
import DateRangePicker, { DateRange } from '@/components/DateRangePicker';
import { fetchOverviewMetrics, fetchTrends, fetchAlerts, fetchTopPerformers, fetchNeedsAttention, fetchAIInsights } from '@/utils/api';
import {
  formatCurrency,
  formatPercentage,
  getPriorityBadge,
  formatRelativeTime,
  cn,
} from '@/utils/helpers';

// Helper function to calculate date range (similar to DateRangePicker's calculateDateRange)
function calculateDateRange(type: DateRange['type']): { startDate: Date; endDate: Date } {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  let endDate = new Date(today);
  endDate.setHours(23, 59, 59, 999);
  
  let startDate = new Date(today);

  switch (type) {
    case 'last_7_days':
      startDate.setDate(startDate.getDate() - 6);
      break;
    case 'last_14_days':
      startDate.setDate(startDate.getDate() - 13);
      break;
    case 'last_30_days':
      startDate.setDate(startDate.getDate() - 29);
      break;
    default:
      startDate.setDate(startDate.getDate() - 6); // Default to 7 days
  }

  return { startDate, endDate };
}

export default function CommandCenter() {
  // Initialize date range with calculated dates
  const initialDateRange = useMemo(() => {
    const { startDate, endDate } = calculateDateRange('last_7_days');
    return {
      type: 'last_7_days' as const,
      days: 7,
      startDate,
      endDate,
    };
  }, []);

  const [dateRange, setDateRange] = useState<DateRange>(initialDateRange);
  const [timelineView, setTimelineView] = useState<'daily' | 'weekly'>('daily');

  // Calculate days for metrics (for backward compatibility)
  const metricsDays = useMemo(() => {
    if (dateRange.days) return dateRange.days;
    if (dateRange.type === 'last_7_days') return 7;
    if (dateRange.type === 'last_14_days') return 14;
    if (dateRange.type === 'last_30_days') return 30;
    return 7;
  }, [dateRange]);

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['overview-metrics', metricsDays],
    queryFn: () => fetchOverviewMetrics(metricsDays),
  });

  const { data: trends, isLoading: trendsLoading } = useQuery({
    queryKey: ['overview-trends', dateRange.type, dateRange.startDate?.toISOString(), dateRange.endDate?.toISOString(), dateRange.days],
    queryFn: () => fetchTrends(
      dateRange.days,
      dateRange.startDate,
      dateRange.endDate
    ),
  });

  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => fetchAlerts(5),
  });

  const { data: topPerformers } = useQuery({
    queryKey: ['top-performers', metricsDays],
    queryFn: () => fetchTopPerformers(metricsDays, 3),
  });

  const { data: needsAttention } = useQuery({
    queryKey: ['needs-attention', metricsDays],
    queryFn: () => fetchNeedsAttention(metricsDays, 3),
  });

  const { data: aiInsights } = useQuery({
    queryKey: ['ai-insights', metricsDays],
    queryFn: () => fetchAIInsights(metricsDays),
  });

  // Helper function to generate all dates in a range
  const generateDateRange = (start: Date, end: Date): Date[] => {
    const dates: Date[] = [];
    const current = new Date(start);
    current.setHours(0, 0, 0, 0);
    const endDate = new Date(end);
    endDate.setHours(23, 59, 59, 999);
    
    while (current <= endDate) {
      dates.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }
    return dates;
  };

  // Aggregate trends by timeline view - only show data within selected date range
  // Fill missing dates with zero values
  const processedTrends = useMemo(() => {
    // Get the actual date range boundaries
    const rangeStart = dateRange.startDate ? new Date(dateRange.startDate) : null;
    const rangeEnd = dateRange.endDate ? new Date(dateRange.endDate) : null;
    
    if (!rangeStart || !rangeEnd) return [];
    
    // Normalize dates
    rangeStart.setHours(0, 0, 0, 0);
    rangeEnd.setHours(23, 59, 59, 999);
    
    // Create a map of existing data by date string (YYYY-MM-DD)
    const dataMap = new Map<string, { spend: number; sales: number; acos: number; roas: number }>();
    
    if (trends && trends.length > 0) {
      trends.forEach(t => {
        const trendDate = new Date(t.date);
        trendDate.setHours(0, 0, 0, 0);
        
        // Only include dates within the selected range
        if (trendDate >= rangeStart && trendDate <= rangeEnd) {
          const dateKey = trendDate.toISOString().split('T')[0];
          dataMap.set(dateKey, {
            spend: t.spend || 0,
            sales: t.sales || 0,
            acos: t.acos || 0,
            roas: t.roas || 0,
          });
        }
      });
    }
    
    if (timelineView === 'daily') {
      // Generate all dates in the range and fill missing ones with zeros
      const allDates = generateDateRange(rangeStart, rangeEnd);
      
      return allDates.map(date => {
        const dateKey = date.toISOString().split('T')[0];
        const data = dataMap.get(dateKey) || { spend: 0, sales: 0, acos: 0, roas: 0 };
        
        return {
          date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          spend: data.spend,
          sales: data.sales,
          acos: data.acos,
          roas: data.roas,
        };
      });
    } else {
      // Weekly view: Generate all dates, then aggregate by week
      const allDates = generateDateRange(rangeStart, rangeEnd);
      
      // Aggregate by week
      const weeklyData: Record<string, { 
        spend: number; 
        sales: number; 
        count: number;
        dates: Date[];
      }> = {};
      
      allDates.forEach(date => {
        // Get the start of the week (Sunday)
        const weekStart = new Date(date);
        weekStart.setDate(date.getDate() - date.getDay());
        weekStart.setHours(0, 0, 0, 0);
        const weekKey = weekStart.toISOString().split('T')[0];
        
        if (!weeklyData[weekKey]) {
          weeklyData[weekKey] = { 
            spend: 0, 
            sales: 0, 
            count: 0,
            dates: []
          };
        }
        
        const dateKey = date.toISOString().split('T')[0];
        const data = dataMap.get(dateKey) || { spend: 0, sales: 0, acos: 0, roas: 0 };
        
        weeklyData[weekKey].spend += data.spend;
        weeklyData[weekKey].sales += data.sales;
        weeklyData[weekKey].count += 1;
        weeklyData[weekKey].dates.push(new Date(date));
      });
      
      return Object.entries(weeklyData)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([weekKey, data]) => {
          // Get min/max dates within the selected range for this week
          const datesInRange = data.dates.filter(d => d >= rangeStart && d <= rangeEnd);
          if (datesInRange.length === 0) {
            // Fallback to week boundaries if no dates in range
            const weekStartDate = new Date(weekKey);
            const weekEndDate = new Date(weekStartDate);
            weekEndDate.setDate(weekStartDate.getDate() + 6);
            return {
              date: `${weekStartDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${weekEndDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`,
              spend: data.spend,
              sales: data.sales,
              acos: data.sales > 0 ? (data.spend / data.sales) * 100 : 0,
              roas: data.spend > 0 ? data.sales / data.spend : 0,
            };
          }
          
          const minDate = new Date(Math.min(...datesInRange.map(d => d.getTime())));
          const maxDate = new Date(Math.max(...datesInRange.map(d => d.getTime())));
          
          // Clamp to range boundaries
          const displayStart = minDate < rangeStart ? rangeStart : minDate;
          const displayEnd = maxDate > rangeEnd ? rangeEnd : maxDate;
          
          const avgAcos = data.sales > 0 ? (data.spend / data.sales) * 100 : 0;
          const avgRoas = data.spend > 0 ? data.sales / data.spend : 0;
          
          return {
            date: `${displayStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${displayEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`,
            spend: data.spend,
            sales: data.sales,
            acos: avgAcos,
            roas: avgRoas,
          };
        });
    }
  }, [trends, timelineView, dateRange.startDate, dateRange.endDate]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Command Center</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Real-time overview of your Amazon PPC performance
          </p>
        </div>
        <div className="flex items-center gap-3">
          <DateRangePicker
            value={dateRange}
            onChange={setDateRange}
            className="z-10"
          />
        </div>
      </div>

      {/* Pulse Cards - Top Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 stagger-animation">
        <MetricCard
          title="Total Spend"
          value={metrics?.spend || 0}
          format="currency"
          trend={metrics?.spend_comparison ? {
            value: metrics.spend_comparison.change_percentage,
            direction: metrics.spend_comparison.direction,
            isGood: false
          } : undefined}
          icon={<DollarSign className="w-5 h-5" />}
          accentColor="#FF9900"
        />
        <MetricCard
          title="Ad Sales"
          value={metrics?.sales || 0}
          format="currency"
          trend={metrics?.sales_comparison ? {
            value: metrics.sales_comparison.change_percentage,
            direction: metrics.sales_comparison.direction,
            isGood: true
          } : undefined}
          icon={<ShoppingCart className="w-5 h-5" />}
          accentColor="#10B981"
        />
        <MetricCard
          title="ACOS"
          value={metrics?.acos || 0}
          format="percentage"
          trend={metrics?.acos_comparison ? {
            value: metrics.acos_comparison.change_percentage,
            direction: metrics.acos_comparison.direction,
            isGood: metrics.acos_comparison.direction === 'down'
          } : undefined}
          icon={<Target className="w-5 h-5" />}
          accentColor="#F59E0B"
        />
        <MetricCard
          title="ROAS"
          value={metrics?.roas || 0}
          format="multiplier"
          trend={metrics?.roas_comparison ? {
            value: metrics.roas_comparison.change_percentage,
            direction: metrics.roas_comparison.direction,
            isGood: true
          } : undefined}
          icon={<TrendingUp className="w-5 h-5" />}
          accentColor="#3B82F6"
        />
      </div>

      {/* Second Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 stagger-animation">
        <MetricCard
          title="Orders"
          value={metrics?.orders || 0}
          format="number"
          icon={<ShoppingCart className="w-5 h-5" />}
          accentColor="#8B5CF6"
        />
        <MetricCard
          title="CTR"
          value={metrics?.ctr || 0}
          format="percentage"
          icon={<MousePointerClick className="w-5 h-5" />}
          accentColor="#EC4899"
        />
        <MetricCard
          title="CVR"
          value={metrics?.cvr || 0}
          format="percentage"
          icon={<Activity className="w-5 h-5" />}
          accentColor="#14B8A6"
        />
        <MetricCard
          title="AI Actions Today"
          value={metrics?.ai_activity_count || 0}
          format="number"
          icon={<Zap className="w-5 h-5" />}
          accentColor="#FF9900"
        />
      </div>

      {/* Engine Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <EngineStatus />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trend Chart */}
        <div className="lg:col-span-2 card">
          <div className="card-header flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Spend vs Sales Trend
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setTimelineView('daily')}
                className={`px-3 py-1.5 text-sm rounded transition-colors ${
                  timelineView === 'daily'
                    ? 'bg-amazon-orange text-black'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                Daily
              </button>
              <button
                onClick={() => setTimelineView('weekly')}
                className={`px-3 py-1.5 text-sm rounded transition-colors ${
                  timelineView === 'weekly'
                    ? 'bg-amazon-orange text-black'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                Weekly
              </button>
            </div>
          </div>
          <div className="card-body">
            {trendsLoading ? (
              <div className="h-[300px] skeleton" />
            ) : (
              <SpendSalesChart data={processedTrends} height={300} />
            )}
          </div>
        </div>

        {/* Health Score & Alerts */}
        <div className="space-y-6">
          {/* Health Score */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Account Health</h2>
            </div>
              <div className="card-body flex flex-col items-center">
                <HealthGauge value={metrics?.account_health_score || 0} size={160} />
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-4 text-center">
                {(metrics?.account_health_score || 0) >= 80
                  ? 'Excellent performance! Keep it up.'
                  : (metrics?.account_health_score || 0) >= 60
                  ? 'Good performance with room for improvement.'
                  : 'Attention needed. Review recommendations.'}
              </p>
            </div>
          </div>

          {/* Alerts */}
          <div className="card">
            <div className="card-header flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
                Active Alerts
              </h2>
              <span className="badge badge-warning">
                {alerts?.length || 0}
              </span>
            </div>
            <div className="card-body p-0">
              {alerts?.length === 0 ? (
                <div className="p-6 text-center text-gray-600 dark:text-gray-400">
                  No active alerts. All systems normal.
                </div>
              ) : (
                <div className="divide-y divide-surface-dark-border/50">
                  {alerts?.map((alert) => (
                    <div
                      key={alert.id}
                      className="p-4 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors cursor-pointer"
                    >
                      <div className="flex items-start gap-3">
                        <span className={cn('badge', getPriorityBadge(alert.severity))}>
                          {alert.severity}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-900 dark:text-white truncate">
                            {alert.message}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {formatRelativeTime(alert.created_at)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Top Performing */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <ArrowUpRight className="w-4 h-4 text-green-400" />
              Top Performers
            </h3>
          </div>
          <div className="card-body p-0">
            {!topPerformers || topPerformers.length === 0 ? (
              <div className="p-6 text-center text-gray-600 dark:text-gray-400">
                No top performers found for this period.
              </div>
            ) : (
              <div className="divide-y divide-surface-dark-border/50">
                {topPerformers.map((campaign) => (
                  <div key={campaign.campaign_id} className="p-4 flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {campaign.campaign_name}
                      </p>
                      <p className="text-xs text-gray-600 dark:text-gray-400">
                        ACOS: {formatPercentage(campaign.acos)}
                      </p>
                    </div>
                    <span className="badge badge-success">
                      {campaign.change_percentage > 0 ? '+' : ''}{campaign.change_percentage.toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Needs Attention */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <ArrowDownRight className="w-4 h-4 text-red-400" />
              Needs Attention
            </h3>
          </div>
          <div className="card-body p-0">
            {!needsAttention || needsAttention.length === 0 ? (
              <div className="p-6 text-center text-gray-600 dark:text-gray-400">
                No campaigns need attention. All performing well!
              </div>
            ) : (
              <div className="divide-y divide-surface-dark-border/50">
                {needsAttention.map((campaign) => (
                  <div key={campaign.campaign_id} className="p-4 flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {campaign.campaign_name}
                      </p>
                      <p className="text-xs text-gray-600 dark:text-gray-400">
                        ACOS: {formatPercentage(campaign.acos)}
                      </p>
                      <p className="text-xs text-red-400 mt-1">{campaign.issue}</p>
                    </div>
                    <span className="badge badge-danger">
                      {campaign.change_percentage > 0 ? '+' : ''}{campaign.change_percentage.toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* AI Insights */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amazon-orange" />
              AI Insights
            </h3>
          </div>
          <div className="card-body">
            {!aiInsights || aiInsights.length === 0 ? (
              <div className="p-6 text-center text-gray-600 dark:text-gray-400">
                No AI insights available at this time.
              </div>
            ) : (
              <div className="space-y-3">
                {aiInsights.map((insight, index) => {
                  const colorClasses = {
                    green: 'bg-green-500/10 border-green-500/20 text-green-400',
                    orange: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
                    blue: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
                    red: 'bg-red-500/10 border-red-500/20 text-red-400',
                  };
                  const colorClass = colorClasses[insight.color as keyof typeof colorClasses] || colorClasses.blue;
                  
                  return (
                    <div key={index} className={`p-3 rounded-lg border ${colorClass}`}>
                      <p className="text-sm">{insight.message}</p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

