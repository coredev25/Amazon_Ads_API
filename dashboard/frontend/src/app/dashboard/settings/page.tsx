'use client';

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  Settings,
  Save,
  RotateCcw,
  Target,
  Zap,
  Shield,
  Clock,
  DollarSign,
  AlertTriangle,
  ChevronRight,
  Brain,
  ExternalLink,
} from 'lucide-react';
import { fetchStrategyConfig, updateStrategyConfig, fetchLearningStats, type StrategyConfig, type LearningStats } from '@/utils/api';
import { cn, formatPercentage, formatCurrency } from '@/utils/helpers';

export default function SettingsPage() {
  const queryClient = useQueryClient();
  
  const { data: currentConfig, isLoading } = useQuery({
    queryKey: ['strategy-config'],
    queryFn: fetchStrategyConfig,
  });

  const { data: learningStats } = useQuery({
    queryKey: ['learning-stats'],
    queryFn: () => fetchLearningStats(30),
  });

  const [config, setConfig] = useState<StrategyConfig>({
    strategy: 'growth',
    target_acos: 0.09,
    max_bid_cap: 4.52,
    min_bid_floor: 0.02,
    ai_mode: 'human_review',
    enable_dayparting: false,
    enable_inventory_protection: false,
    enable_brand_defense: false,
  });

  useEffect(() => {
    if (currentConfig) {
      setConfig(currentConfig);
    }
  }, [currentConfig]);

  const updateMutation = useMutation({
    mutationFn: updateStrategyConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy-config'] });
    },
  });

  const handleSave = () => {
    updateMutation.mutate(config);
  };

  const handleReset = () => {
    if (currentConfig) {
      setConfig(currentConfig);
    }
  };

  const strategies = [
    {
      id: 'launch',
      name: 'Launch',
      description: 'Aggressive bidding to maximize visibility for new products',
      acos: 0.15,
      color: 'bg-purple-500/20 border-purple-500 text-purple-400',
      icon: '🚀',
    },
    {
      id: 'growth',
      name: 'Growth',
      description: 'Balanced approach to scale sales while maintaining profitability',
      acos: 0.09,
      color: 'bg-green-500/20 border-green-500 text-green-400',
      icon: '📈',
    },
    {
      id: 'profit',
      name: 'Profit',
      description: 'Conservative bidding to maximize profit margins',
      acos: 0.05,
      color: 'bg-blue-500/20 border-blue-500 text-blue-400',
      icon: '💰',
    },
    {
      id: 'liquidate',
      name: 'Liquidate',
      description: 'High ACOS tolerance for inventory clearance',
      acos: 0.25,
      color: 'bg-orange-500/20 border-orange-500 text-orange-400',
      icon: '📦',
    },
  ];

  const aiModes = [
    {
      id: 'autonomous',
      name: 'Fully Autonomous',
      description: 'AI changes bids automatically without approval',
      icon: <Zap className="w-5 h-5" />,
      color: 'text-amazon-orange',
      badge: 'Full Auto',
    },
    {
      id: 'human_review',
      name: 'Human Review',
      description: 'AI suggests changes, human must approve',
      icon: <Shield className="w-5 h-5" />,
      color: 'text-green-400',
      badge: 'Recommended',
    },
    {
      id: 'warm_up',
      name: 'Warm Up Mode',
      description: 'Only uses math rules, no ML gating (for new accounts)',
      icon: <Clock className="w-5 h-5" />,
      color: 'text-yellow-400',
      badge: 'Safe Start',
    },
  ];

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
        <div className="grid grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Strategy Configuration</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Configure high-level AI behavior and optimization targets
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
          <span>Configuration saved successfully!</span>
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
              <p className="text-sm text-gray-600 dark:text-gray-400">Current Strategy</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white capitalize">{config.strategy}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/20">
              <DollarSign className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Target ACOS</p>
              <p className="text-lg font-bold text-green-400">{formatPercentage(config.target_acos * 100)}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/20">
              <Shield className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">AI Mode</p>
              <p className="text-lg font-bold text-blue-400 capitalize">{config.ai_mode.replace('_', ' ')}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/20">
              <Brain className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">ML Success Rate</p>
              <p className="text-lg font-bold text-purple-400">
                {learningStats ? `${learningStats.success_rate.toFixed(1)}%` : 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Strategy Selector */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Target className="w-5 h-5 text-amazon-orange" />
            Campaign Strategy
          </h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {strategies.map((strategy) => (
              <button
                key={strategy.id}
                onClick={() =>
                  setConfig((prev) => ({
                    ...prev,
                    strategy: strategy.id,
                    target_acos: strategy.acos,
                  }))
                }
                className={cn(
                  'p-4 rounded-xl border-2 text-left transition-all hover:scale-[1.02]',
                  config.strategy === strategy.id
                    ? strategy.color
                    : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
                )}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">{strategy.icon}</span>
                  <h3 className="font-semibold text-gray-900 dark:text-white">{strategy.name}</h3>
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">{strategy.description}</p>
                <p className="text-sm font-mono">
                  Target ACOS: {formatPercentage(strategy.acos * 100)}
                </p>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Target Sliders */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-amazon-orange" />
            Target Configuration
          </h2>
        </div>
        <div className="card-body space-y-6">
          {/* Target ACOS */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Target ACOS
              </label>
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
              onChange={(e) =>
                setConfig((prev) => ({
                  ...prev,
                  target_acos: parseFloat(e.target.value),
                }))
              }
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mt-1">
              <span>1% (Profit)</span>
              <span>50% (Launch)</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Min Bid Floor */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Min Bid Floor
                </label>
                <div className="flex items-center gap-2">
                  <span className="text-gray-600 dark:text-gray-400">$</span>
                  <input
                    type="number"
                    min="0.02"
                    max="1.00"
                    step="0.01"
                    value={config.min_bid_floor}
                    onChange={(e) =>
                      setConfig((prev) => ({
                        ...prev,
                        min_bid_floor: parseFloat(e.target.value),
                      }))
                    }
                    className="input w-24 py-1 text-right"
                  />
                </div>
              </div>
              <p className="text-xs text-gray-600 dark:text-gray-500">
                Minimum bid the AI will recommend
              </p>
            </div>

            {/* Max Bid Cap */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Max Bid Cap
                </label>
                <div className="flex items-center gap-2">
                  <span className="text-gray-600 dark:text-gray-400">$</span>
                  <input
                    type="number"
                    min="0.02"
                    max="100"
                    step="0.01"
                    value={config.max_bid_cap}
                    onChange={(e) =>
                      setConfig((prev) => ({
                        ...prev,
                        max_bid_cap: parseFloat(e.target.value),
                      }))
                    }
                    className="input w-24 py-1 text-right"
                  />
                </div>
              </div>
              <p className="text-xs text-gray-600 dark:text-gray-500">
                Maximum bid the AI will recommend
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* AI Mode */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-amazon-orange" />
            AI Mode
          </h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {aiModes.map((mode) => (
              <button
                key={mode.id}
                onClick={() =>
                  setConfig((prev) => ({ ...prev, ai_mode: mode.id }))
                }
                className={cn(
                  'p-4 rounded-xl border-2 text-left transition-all hover:scale-[1.02]',
                  config.ai_mode === mode.id
                    ? 'bg-amazon-orange/10 border-amazon-orange'
                    : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className={cn('', mode.color)}>{mode.icon}</div>
                  <span className={cn(
                    'badge',
                    mode.id === 'human_review' ? 'badge-success' :
                    mode.id === 'autonomous' ? 'badge-warning' : 'badge-info'
                  )}>
                    {mode.badge}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-white">{mode.name}</h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{mode.description}</p>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Advanced Toggles */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Settings className="w-5 h-5 text-amazon-orange" />
            Advanced Features
          </h2>
        </div>
        <div className="card-body space-y-4">
          <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Enable Dayparting</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Adjust bids based on time of day performance
              </p>
            </div>
            <input
              type="checkbox"
              checked={config.enable_dayparting}
              onChange={(e) =>
                setConfig((prev) => ({
                  ...prev,
                  enable_dayparting: e.target.checked,
                }))
              }
              className="w-5 h-5 rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 accent-amazon-orange"
            />
          </label>

          <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Inventory Protection</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Pause bidding when stock is below 2 weeks supply
              </p>
            </div>
            <input
              type="checkbox"
              checked={config.enable_inventory_protection}
              onChange={(e) =>
                setConfig((prev) => ({
                  ...prev,
                  enable_inventory_protection: e.target.checked,
                }))
              }
              className="w-5 h-5 rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 accent-amazon-orange"
            />
          </label>

          <label className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Brand Defense</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Ignore ACOS targets on brand keywords
              </p>
            </div>
            <input
              type="checkbox"
              checked={config.enable_brand_defense}
              onChange={(e) =>
                setConfig((prev) => ({
                  ...prev,
                  enable_brand_defense: e.target.checked,
                }))
              }
              className="w-5 h-5 rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 accent-amazon-orange"
            />
          </label>
        </div>
      </div>

      {/* Link to AI Control */}
      <Link href="/ai-control" className="card p-6 flex items-center justify-between group hover:border-amazon-orange/50 transition-colors">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-amazon-orange/20">
            <Brain className="w-6 h-6 text-amazon-orange" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white group-hover:text-amazon-orange transition-colors">
              Advanced AI Control
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Fine-tune bid optimization, safety controls, learning loop, and more
            </p>
          </div>
        </div>
        <ChevronRight className="w-6 h-6 text-gray-500 dark:text-gray-400 group-hover:text-amazon-orange transition-colors" />
      </Link>

      {/* Warning */}
      <div className="alert alert-warning">
        <AlertTriangle className="w-5 h-5 flex-shrink-0" />
        <div>
          <p className="font-medium">Important</p>
          <p className="text-sm">
            Changes to strategy configuration take effect immediately. The AI will use the new
            settings for all future recommendations. Existing recommendations will not be
            recalculated.
          </p>
        </div>
      </div>
    </div>
  );
}
