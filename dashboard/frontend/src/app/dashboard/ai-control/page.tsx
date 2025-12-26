'use client';

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Settings,
  Save,
  RotateCcw,
  Zap,
  Shield,
  TrendingUp,
  TrendingDown,
  Target,
  DollarSign,
  AlertTriangle,
  RefreshCw,
  Lock,
  Unlock,
  Activity,
  Brain,
  Sliders,
  BarChart3,
  Clock,
  ShoppingCart,
  XCircle,
} from 'lucide-react';
import {
  fetchAIControlConfig,
  updateAIControlConfig,
  fetchBidLocks,
  fetchOscillations,
  fetchLearningStats,
  type AIControlConfig,
  type BidLock,
  type Oscillation,
  type LearningStats,
} from '@/utils/api';
import { cn, formatPercentage, formatCurrency, formatRelativeTime } from '@/utils/helpers';

export default function AIControlPage() {
  const queryClient = useQueryClient();
  
  const { data: currentConfig, isLoading: configLoading } = useQuery({
    queryKey: ['ai-control-config'],
    queryFn: fetchAIControlConfig,
  });

  const { data: bidLocks } = useQuery({
    queryKey: ['bid-locks'],
    queryFn: () => fetchBidLocks(),
  });

  const { data: oscillations } = useQuery({
    queryKey: ['oscillations'],
    queryFn: fetchOscillations,
  });

  const { data: learningStats } = useQuery({
    queryKey: ['learning-stats'],
    queryFn: () => fetchLearningStats(30),
  });

  const [config, setConfig] = useState<AIControlConfig | null>(null);
  const [activeTab, setActiveTab] = useState<'core' | 'safety' | 'scaling' | 'learning' | 'monitoring'>('core');

  useEffect(() => {
    if (currentConfig) {
      setConfig(currentConfig);
    }
  }, [currentConfig]);

  const updateMutation = useMutation({
    mutationFn: updateAIControlConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-control-config'] });
    },
  });

  const handleSave = () => {
    if (config) {
      updateMutation.mutate(config);
    }
  };

  const handleReset = () => {
    if (currentConfig) {
      setConfig(currentConfig);
    }
  };

  const updateConfigValue = <K extends keyof AIControlConfig>(key: K, value: AIControlConfig[K]) => {
    if (config) {
      setConfig({ ...config, [key]: value });
    }
  };

  if (configLoading || !config) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
        <div className="grid grid-cols-2 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-48 bg-gray-200 dark:bg-gray-700 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'core', label: 'Core Settings', icon: <Target className="w-4 h-4" /> },
    { id: 'safety', label: 'Safety Controls', icon: <Shield className="w-4 h-4" /> },
    { id: 'scaling', label: 'Bid Scaling', icon: <TrendingUp className="w-4 h-4" /> },
    { id: 'learning', label: 'Learning Loop', icon: <Brain className="w-4 h-4" /> },
    { id: 'monitoring', label: 'Monitoring', icon: <Activity className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Zap className="w-7 h-7 text-amazon-orange" />
            AI Rule Engine Control
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Fine-tune AI bid optimization parameters and safety controls
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleReset} className="btn btn-secondary">
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={updateMutation.isPending}
            className="btn btn-primary"
          >
            <Save className="w-4 h-4" />
            {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {updateMutation.isSuccess && (
        <div className="alert alert-success">
          <Zap className="w-5 h-5" />
          <span>AI configuration saved successfully! Changes take effect immediately.</span>
        </div>
      )}

      {updateMutation.isError && (
        <div className="alert alert-danger">
          <XCircle className="w-5 h-5" />
          <span>Failed to save configuration. Please check your values.</span>
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amazon-orange/20">
              <Target className="w-5 h-5 text-amazon-orange" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Target ACOS</p>
              <p className="text-xl font-bold text-gray-900 dark:text-white">{formatPercentage(config.target_acos * 100)}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/20">
              <TrendingUp className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Learning Success Rate</p>
              <p className="text-xl font-bold text-green-600 dark:text-green-400">
                {learningStats ? `${learningStats.success_rate.toFixed(1)}%` : 'N/A'}
              </p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/20">
              <Lock className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Active Bid Locks</p>
              <p className="text-xl font-bold text-blue-600 dark:text-blue-400">{bidLocks?.length || 0}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/20">
              <RefreshCw className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Oscillating Keywords</p>
              <p className="text-xl font-bold text-amber-600 dark:text-amber-400">{oscillations?.length || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-amazon-orange text-amazon-orange'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:border-gray-300 dark:hover:border-gray-600'
              )}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {/* Core Settings Tab */}
        {activeTab === 'core' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* ACOS & ROAS Targets */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Target className="w-5 h-5 text-amazon-orange" />
                  Performance Targets
                </h2>
              </div>
              <div className="card-body space-y-6">
                {/* Target ACOS */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Target ACOS</label>
                    <span className="text-sm font-mono text-orange-600 dark:text-amazon-orange">
                      {formatPercentage(config.target_acos * 100)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.01"
                    max="0.50"
                    step="0.01"
                    value={config.target_acos}
                    onChange={(e) => updateConfigValue('target_acos', parseFloat(e.target.value))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-600 dark:text-gray-500 mt-1">
                    <span>1% (Profit)</span>
                    <span>50% (Launch)</span>
                  </div>
                </div>

                {/* ACOS Tolerance */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">ACOS Tolerance (±)</label>
                    <span className="text-sm font-mono text-gray-900 dark:text-gray-300">
                      {formatPercentage(config.acos_tolerance * 100)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.01"
                    max="0.20"
                    step="0.01"
                    value={config.acos_tolerance}
                    onChange={(e) => updateConfigValue('acos_tolerance', parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>

                {/* Target ROAS */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Target ROAS</label>
                    <span className="text-sm font-mono text-green-600 dark:text-green-400">
                      {config.roas_target.toFixed(2)}:1
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="30"
                    step="0.5"
                    value={config.roas_target}
                    onChange={(e) => updateConfigValue('roas_target', parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
              </div>
            </div>

            {/* Bid Limits */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-amazon-orange" />
                  Bid Limits
                </h2>
              </div>
              <div className="card-body space-y-6">
                {/* Bid Floor */}
                <div>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Bid Floor</label>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600 dark:text-gray-400">$</span>
                    <input
                      type="number"
                      min="0.02"
                      max="1.00"
                      step="0.01"
                      value={config.bid_floor}
                      onChange={(e) => updateConfigValue('bid_floor', parseFloat(e.target.value))}
                      className="input w-24 text-right"
                    />
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-500 mt-1">Minimum bid the AI will recommend</p>
                </div>

                {/* Bid Cap */}
                <div>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Bid Cap</label>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600 dark:text-gray-400">$</span>
                    <input
                      type="number"
                      min="0.50"
                      max="100"
                      step="0.01"
                      value={config.bid_cap}
                      onChange={(e) => updateConfigValue('bid_cap', parseFloat(e.target.value))}
                      className="input w-24 text-right"
                    />
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-500 mt-1">Maximum bid the AI will recommend</p>
                </div>

                {/* Max Adjustment */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Max Adjustment per Cycle</label>
                    <span className="text-sm font-mono text-gray-700 dark:text-gray-300">
                      {formatPercentage(config.bid_max_adjustment * 100)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.10"
                    max="1.00"
                    step="0.05"
                    value={config.bid_max_adjustment}
                    onChange={(e) => updateConfigValue('bid_max_adjustment', parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
              </div>
            </div>

            {/* Performance Thresholds */}
            <div className="card lg:col-span-2">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-amazon-orange" />
                  Minimum Data Thresholds
                </h2>
              </div>
              <div className="card-body">
                <div className="grid grid-cols-3 gap-6">
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Min Impressions</label>
                    <input
                      type="number"
                      min="10"
                      max="1000"
                      value={config.min_impressions}
                      onChange={(e) => updateConfigValue('min_impressions', parseInt(e.target.value))}
                      className="input w-full"
                    />
                    <p className="text-xs text-gray-500 mt-1">Required before AI makes decisions</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Min Clicks</label>
                    <input
                      type="number"
                      min="1"
                      max="50"
                      value={config.min_clicks}
                      onChange={(e) => updateConfigValue('min_clicks', parseInt(e.target.value))}
                      className="input w-full"
                    />
                    <p className="text-xs text-gray-500 mt-1">Required for bid adjustments</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Min Conversions</label>
                    <input
                      type="number"
                      min="0"
                      max="10"
                      value={config.min_conversions}
                      onChange={(e) => updateConfigValue('min_conversions', parseInt(e.target.value))}
                      className="input w-full"
                    />
                    <p className="text-xs text-gray-500 mt-1">For aggressive scaling</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Safety Controls Tab */}
        {activeTab === 'safety' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Re-entry Control */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Clock className="w-5 h-5 text-amazon-orange" />
                  Re-entry Control
                </h2>
              </div>
              <div className="card-body space-y-4">
                <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Enable Re-entry Control</p>
                    <p className="text-sm text-gray-400">Prevent rapid bid oscillations</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.enable_re_entry_control}
                    onChange={(e) => updateConfigValue('enable_re_entry_control', e.target.checked)}
                    className="w-5 h-5 rounded accent-amazon-orange"
                  />
                </label>

                <div className={cn(!config.enable_re_entry_control && 'opacity-50 pointer-events-none')}>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Cooldown Period (Days)</label>
                  <input
                    type="number"
                    min="1"
                    max="14"
                    value={config.bid_change_cooldown_days}
                    onChange={(e) => updateConfigValue('bid_change_cooldown_days', parseInt(e.target.value))}
                    className="input w-24"
                  />
                  <p className="text-xs text-gray-500 mt-1">Days to wait before re-adjusting same entity</p>
                </div>

                <div className={cn(!config.enable_re_entry_control && 'opacity-50 pointer-events-none')}>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Min Change Threshold</label>
                    <span className="text-sm font-mono text-gray-700 dark:text-gray-300">
                      {formatPercentage(config.min_bid_change_threshold * 100)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.01"
                    max="0.20"
                    step="0.01"
                    value={config.min_bid_change_threshold}
                    onChange={(e) => updateConfigValue('min_bid_change_threshold', parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
              </div>
            </div>

            {/* Oscillation Detection */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <RefreshCw className="w-5 h-5 text-amazon-orange" />
                  Oscillation Prevention
                </h2>
              </div>
              <div className="card-body space-y-4">
                <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Enable Oscillation Detection</p>
                    <p className="text-sm text-gray-400">Detect and prevent bid flip-flopping</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.enable_oscillation_detection}
                    onChange={(e) => updateConfigValue('enable_oscillation_detection', e.target.checked)}
                    className="w-5 h-5 rounded accent-amazon-orange"
                  />
                </label>

                <div className={cn(!config.enable_oscillation_detection && 'opacity-50 pointer-events-none')}>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Lookback Days</label>
                  <input
                    type="number"
                    min="7"
                    max="30"
                    value={config.oscillation_lookback_days}
                    onChange={(e) => updateConfigValue('oscillation_lookback_days', parseInt(e.target.value))}
                    className="input w-24"
                  />
                </div>

                <div className={cn(!config.enable_oscillation_detection && 'opacity-50 pointer-events-none')}>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Direction Changes Threshold</label>
                  <input
                    type="number"
                    min="2"
                    max="10"
                    value={config.oscillation_direction_change_threshold}
                    onChange={(e) => updateConfigValue('oscillation_direction_change_threshold', parseInt(e.target.value))}
                    className="input w-24"
                  />
                  <p className="text-xs text-gray-500 mt-1">Changes required to flag oscillation</p>
                </div>
              </div>
            </div>

            {/* Spend Safeguards */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amazon-orange" />
                  Spend Safeguards
                </h2>
              </div>
              <div className="card-body space-y-4">
                <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Enable Spend Safeguard</p>
                    <p className="text-sm text-gray-400">Detect spend spikes and react</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.enable_spend_safeguard}
                    onChange={(e) => updateConfigValue('enable_spend_safeguard', e.target.checked)}
                    className="w-5 h-5 rounded accent-amazon-orange"
                  />
                </label>

                <div className={cn(!config.enable_spend_safeguard && 'opacity-50 pointer-events-none')}>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Spike Threshold</label>
                    <span className="text-sm font-mono text-amber-600 dark:text-amber-400">
                      {(config.spend_spike_threshold * 100).toFixed(0)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1.5"
                    max="5"
                    step="0.1"
                    value={config.spend_spike_threshold}
                    onChange={(e) => updateConfigValue('spend_spike_threshold', parseFloat(e.target.value))}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">Spend increase % that triggers safeguard</p>
                </div>
              </div>
            </div>

            {/* Account Daily Limit */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Shield className="w-5 h-5 text-amazon-orange" />
                  Account Protection
                </h2>
              </div>
              <div className="card-body space-y-4">
                <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Enable Safety Veto</p>
                    <p className="text-sm text-gray-400">Comprehensive safety-first layer</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.enable_comprehensive_safety_veto}
                    onChange={(e) => updateConfigValue('enable_comprehensive_safety_veto', e.target.checked)}
                    className="w-5 h-5 rounded accent-amazon-orange"
                  />
                </label>

                <div>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Account Daily Limit</label>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600 dark:text-gray-400">$</span>
                    <input
                      type="number"
                      min="100"
                      max="1000000"
                      step="100"
                      value={config.account_daily_limit}
                      onChange={(e) => updateConfigValue('account_daily_limit', parseFloat(e.target.value))}
                      className="input w-32 text-right"
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Maximum daily account spend limit</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Bid Scaling Tab */}
        {activeTab === 'scaling' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Order-Based Scaling */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <ShoppingCart className="w-5 h-5 text-amazon-orange" />
                  Order-Based Scaling
                </h2>
              </div>
              <div className="card-body space-y-4">
                <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Enable Order-Based Scaling</p>
                    <p className="text-sm text-gray-400">Scale bids based on conversion count</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.enable_order_based_scaling}
                    onChange={(e) => updateConfigValue('enable_order_based_scaling', e.target.checked)}
                    className="w-5 h-5 rounded accent-amazon-orange"
                  />
                </label>

                <div className={cn('space-y-4', !config.enable_order_based_scaling && 'opacity-50 pointer-events-none')}>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">1 Conversion (Min Adjust)</label>
                      <span className="text-sm font-mono text-gray-700 dark:text-gray-300">
                        {formatPercentage(config.order_tier_1_adjustment * 100)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.01"
                      max="0.20"
                      step="0.01"
                      value={config.order_tier_1_adjustment}
                      onChange={(e) => updateConfigValue('order_tier_1_adjustment', parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">2-3 Conversions (Moderate)</label>
                      <span className="text-sm font-mono text-blue-600 dark:text-blue-400">
                        {formatPercentage(config.order_tier_2_3_adjustment * 100)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.05"
                      max="0.30"
                      step="0.01"
                      value={config.order_tier_2_3_adjustment}
                      onChange={(e) => updateConfigValue('order_tier_2_3_adjustment', parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">4+ Conversions (Aggressive)</label>
                      <span className="text-sm font-mono text-green-600 dark:text-green-400">
                        {formatPercentage(config.order_tier_4_plus_adjustment * 100)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.10"
                      max="0.50"
                      step="0.01"
                      value={config.order_tier_4_plus_adjustment}
                      onChange={(e) => updateConfigValue('order_tier_4_plus_adjustment', parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Spend No-Sale Logic */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <TrendingDown className="w-5 h-5 text-amazon-orange" />
                  Spend No-Sale Reductions
                </h2>
              </div>
              <div className="card-body space-y-4">
                <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Enable Spend No-Sale Logic</p>
                    <p className="text-sm text-gray-400">Reduce bids for spending without sales</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.enable_spend_no_sale_logic}
                    onChange={(e) => updateConfigValue('enable_spend_no_sale_logic', e.target.checked)}
                    className="w-5 h-5 rounded accent-amazon-orange"
                  />
                </label>

                <div className={cn('space-y-4', !config.enable_spend_no_sale_logic && 'opacity-50 pointer-events-none')}>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">$10-15 Spend (Tier 1)</label>
                      <span className="text-sm font-mono text-yellow-600 dark:text-yellow-400">
                        -{formatPercentage(config.no_sale_reduction_tier_1 * 100)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.05"
                      max="0.30"
                      step="0.01"
                      value={config.no_sale_reduction_tier_1}
                      onChange={(e) => updateConfigValue('no_sale_reduction_tier_1', parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">$16-30 Spend (Tier 2)</label>
                      <span className="text-sm font-mono text-orange-600 dark:text-orange-400">
                        -{formatPercentage(config.no_sale_reduction_tier_2 * 100)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.10"
                      max="0.40"
                      step="0.01"
                      value={config.no_sale_reduction_tier_2}
                      onChange={(e) => updateConfigValue('no_sale_reduction_tier_2', parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">&gt;$30 Spend (Tier 3)</label>
                      <span className="text-sm font-mono text-red-600 dark:text-red-400">
                        -{formatPercentage(config.no_sale_reduction_tier_3 * 100)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.15"
                      max="0.50"
                      step="0.01"
                      value={config.no_sale_reduction_tier_3}
                      onChange={(e) => updateConfigValue('no_sale_reduction_tier_3', parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Learning Loop Tab */}
        {activeTab === 'learning' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Learning Configuration */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Brain className="w-5 h-5 text-amazon-orange" />
                  Learning Loop Settings
                </h2>
              </div>
              <div className="card-body space-y-4">
                <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Enable Learning Loop</p>
                    <p className="text-sm text-gray-400">Track and learn from outcomes</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.enable_learning_loop}
                    onChange={(e) => updateConfigValue('enable_learning_loop', e.target.checked)}
                    className="w-5 h-5 rounded accent-amazon-orange"
                  />
                </label>

                <div className={cn('space-y-4', !config.enable_learning_loop && 'opacity-50 pointer-events-none')}>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Success Threshold</label>
                      <span className="text-sm font-mono text-green-600 dark:text-green-400">
                        +{formatPercentage(config.learning_success_threshold * 100)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.01"
                      max="0.30"
                      step="0.01"
                      value={config.learning_success_threshold}
                      onChange={(e) => updateConfigValue('learning_success_threshold', parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <p className="text-xs text-gray-500 mt-1">Improvement % required for success label</p>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Failure Threshold</label>
                      <span className="text-sm font-mono text-red-600 dark:text-red-400">
                        {formatPercentage(config.learning_failure_threshold * 100)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="-0.30"
                      max="0"
                      step="0.01"
                      value={config.learning_failure_threshold}
                      onChange={(e) => updateConfigValue('learning_failure_threshold', parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <p className="text-xs text-gray-500 mt-1">Decline % that marks as failure</p>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Min Training Samples</label>
                    <input
                      type="number"
                      min="10"
                      max="1000"
                      value={config.min_training_samples}
                      onChange={(e) => updateConfigValue('min_training_samples', parseInt(e.target.value))}
                      className="input w-32"
                    />
                    <p className="text-xs text-gray-500 mt-1">Samples needed before ML kicks in</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Feature Flags */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Sliders className="w-5 h-5 text-amazon-orange" />
                  Feature Flags
                </h2>
              </div>
              <div className="card-body space-y-4">
                <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Warm-Up Mode</p>
                    <p className="text-sm text-gray-400">Use math rules when ML has insufficient data</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.enable_warm_up_mode}
                    onChange={(e) => updateConfigValue('enable_warm_up_mode', e.target.checked)}
                    className="w-5 h-5 rounded accent-amazon-orange"
                  />
                </label>

                <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Intelligence Engines</p>
                    <p className="text-sm text-gray-400">Enable advanced context-aware signals</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.enable_intelligence_engines}
                    onChange={(e) => updateConfigValue('enable_intelligence_engines', e.target.checked)}
                    className="w-5 h-5 rounded accent-amazon-orange"
                  />
                </label>

                <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Advanced Bid Optimization</p>
                    <p className="text-sm text-gray-400">Enable multi-factor bid calculations</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.enable_advanced_bid_optimization}
                    onChange={(e) => updateConfigValue('enable_advanced_bid_optimization', e.target.checked)}
                    className="w-5 h-5 rounded accent-amazon-orange"
                  />
                </label>
              </div>
            </div>

            {/* Learning Stats */}
            {learningStats && (
              <div className="card lg:col-span-2">
                <div className="card-header">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-amazon-orange" />
                    Learning Performance (Last 30 Days)
                  </h2>
                </div>
                <div className="card-body">
                  <div className="grid grid-cols-5 gap-4 mb-6">
                    <div className="text-center">
                      <p className="text-3xl font-bold text-gray-900 dark:text-white">{learningStats.total_outcomes}</p>
                      <p className="text-sm text-gray-400">Total Outcomes</p>
                    </div>
                    <div className="text-center">
                      <p className="text-3xl font-bold text-green-400">{learningStats.successes}</p>
                      <p className="text-sm text-gray-400">Successes</p>
                    </div>
                    <div className="text-center">
                      <p className="text-3xl font-bold text-red-400">{learningStats.failures}</p>
                      <p className="text-sm text-gray-400">Failures</p>
                    </div>
                    <div className="text-center">
                      <p className="text-3xl font-bold text-gray-400">{learningStats.neutrals}</p>
                      <p className="text-sm text-gray-400">Neutral</p>
                    </div>
                    <div className="text-center">
                      <p className="text-3xl font-bold text-amazon-orange">
                        {learningStats.success_rate.toFixed(1)}%
                      </p>
                      <p className="text-sm text-gray-400">Success Rate</p>
                    </div>
                  </div>

                  {learningStats.recent_training_runs.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-300 mb-3">Recent Model Training Runs</h3>
                      <div className="space-y-2">
                        {learningStats.recent_training_runs.map((run, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                            <div className="flex items-center gap-3">
                              <span className="text-sm font-mono text-gray-700 dark:text-gray-300">v{run.model_version}</span>
                              <span className={cn(
                                'badge',
                                run.status === 'completed' ? 'badge-success' :
                                run.status === 'running' ? 'badge-warning' : 'badge-neutral'
                              )}>
                                {run.status}
                              </span>
                              {run.promoted && (
                                <span className="badge badge-success">Promoted</span>
                              )}
                            </div>
                            <div className="flex items-center gap-4 text-sm">
                              {run.test_accuracy && (
                                <span className="text-gray-400">
                                  Accuracy: <span className="text-gray-900 dark:text-white">{(run.test_accuracy * 100).toFixed(1)}%</span>
                                </span>
                              )}
                              {run.test_auc && (
                                <span className="text-gray-400">
                                  AUC: <span className="text-gray-900 dark:text-white">{run.test_auc.toFixed(3)}</span>
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Monitoring Tab */}
        {activeTab === 'monitoring' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Active Bid Locks */}
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Lock className="w-5 h-5 text-amazon-orange" />
                  Active Bid Locks
                </h2>
                <span className="badge badge-neutral">{bidLocks?.length || 0}</span>
              </div>
              <div className="card-body p-0 max-h-96 overflow-y-auto">
                {!bidLocks || bidLocks.length === 0 ? (
                  <div className="p-6 text-center text-gray-400">
                    <Unlock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>No active bid locks</p>
                  </div>
                ) : (
                  <div className="divide-y divide-surface-dark-border/50">
                    {bidLocks.map((lock, idx) => (
                      <div key={idx} className="p-4 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-gray-900 dark:text-white">
                              {lock.entity_type} #{lock.entity_id}
                            </p>
                            <p className="text-xs text-gray-400">{lock.lock_reason}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-gray-400">Locked until</p>
                            <p className="text-sm text-amber-400">
                              {formatRelativeTime(lock.locked_until)}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Oscillating Entities */}
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <RefreshCw className="w-5 h-5 text-amazon-orange" />
                  Oscillating Keywords
                </h2>
                <span className="badge badge-warning">{oscillations?.length || 0}</span>
              </div>
              <div className="card-body p-0 max-h-96 overflow-y-auto">
                {!oscillations || oscillations.length === 0 ? (
                  <div className="p-6 text-center text-gray-400">
                    <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>No oscillation detected</p>
                  </div>
                ) : (
                  <div className="divide-y divide-surface-dark-border/50">
                    {oscillations.map((osc, idx) => (
                      <div key={idx} className="p-4 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-gray-900 dark:text-white">
                              {osc.entity_name || `${osc.entity_type} #${osc.entity_id}`}
                            </p>
                            <p className="text-xs text-gray-400">
                              {osc.direction_changes} direction changes detected
                            </p>
                          </div>
                          <span className="badge badge-warning">Oscillating</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Warning */}
      <div className="alert alert-warning">
        <AlertTriangle className="w-5 h-5 flex-shrink-0" />
        <div>
          <p className="font-medium">Important</p>
          <p className="text-sm">
            Changes to AI control settings take effect immediately. The AI engine will use the new
            parameters for all future bid calculations. Consider testing changes during low-traffic periods.
          </p>
        </div>
      </div>
    </div>
  );
}

