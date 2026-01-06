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
import { fetchOverviewMetrics, fetchTrends, fetchAlerts, fetchTopPerformers, fetchNeedsAttention, fetchAIInsights } from '@/utils/api';
import {
  formatCurrency,
  formatPercentage,
  getPriorityBadge,
  formatRelativeTime,
  cn,
} from '@/utils/helpers';

export default function CommandCenter() {
  const [dateRange, setDateRange] = useState(7);
  const [timelineView, setTimelineView] = useState<'daily' | 'weekly'>('daily');

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['overview-metrics', dateRange],
    queryFn: () => fetchOverviewMetrics(dateRange),
  });

  const { data: trends, isLoading: trendsLoading } = useQuery({
    queryKey: ['overview-trends', 30],
    queryFn: () => fetchTrends(30),
  });

  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => fetchAlerts(5),
  });

  const { data: topPerformers } = useQuery({
    queryKey: ['top-performers', dateRange],
    queryFn: () => fetchTopPerformers(dateRange, 3),
  });

  const { data: needsAttention } = useQuery({
    queryKey: ['needs-attention', dateRange],
    queryFn: () => fetchNeedsAttention(dateRange, 3),
  });

  const { data: aiInsights } = useQuery({
    queryKey: ['ai-insights', dateRange],
    queryFn: () => fetchAIInsights(dateRange),
  });

  // Aggregate trends by timeline view
  const processedTrends = useMemo(() => {
    if (!trends || trends.length === 0) return [];
    
    if (timelineView === 'daily') {
      return trends.map(t => ({
        date: new Date(t.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        spend: t.spend,
        sales: t.sales,
        acos: t.acos,
        roas: t.roas,
      }));
    } else {
      // Aggregate by week
      const weeklyData: Record<string, { spend: number; sales: number; count: number }> = {};
      
      trends.forEach(t => {
        const date = new Date(t.date);
        // Get the start of the week (Sunday)
        const weekStart = new Date(date);
        weekStart.setDate(date.getDate() - date.getDay());
        const weekKey = weekStart.toISOString().split('T')[0];
        
        if (!weeklyData[weekKey]) {
          weeklyData[weekKey] = { spend: 0, sales: 0, count: 0 };
        }
        
        weeklyData[weekKey].spend += t.spend;
        weeklyData[weekKey].sales += t.sales;
        weeklyData[weekKey].count += 1;
      });
      
      return Object.entries(weeklyData)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([weekKey, data]) => {
          const weekStart = new Date(weekKey);
          const weekEnd = new Date(weekStart);
          weekEnd.setDate(weekStart.getDate() + 6);
          
          const avgAcos = data.sales > 0 ? (data.spend / data.sales) * 100 : 0;
          const avgRoas = data.spend > 0 ? data.sales / data.spend : 0;
          
          return {
            date: `${weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`,
            spend: data.spend,
            sales: data.sales,
            acos: avgAcos,
            roas: avgRoas,
          };
        });
    }
  }, [trends, timelineView]);

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
          <select
            value={dateRange}
            onChange={(e) => setDateRange(Number(e.target.value))}
            className="select"
          >
            <option value={7}>Last 7 Days</option>
            <option value={14}>Last 14 Days</option>
            <option value={30}>Last 30 Days</option>
          </select>
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

