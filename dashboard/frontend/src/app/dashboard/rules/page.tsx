'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BookOpen,
  CheckCircle,
  XCircle,
  Clock,
  ChevronRight,
  Activity,
  Target,
  DollarSign,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react';
import { fetchRules, type Rule } from '@/utils/api';
import { cn, formatRelativeTime } from '@/utils/helpers';

export default function RulesPage() {
  const [selectedRule, setSelectedRule] = useState<string | null>(null);

  const { data: rules, isLoading } = useQuery({
    queryKey: ['rules'],
    queryFn: fetchRules,
  });

  const getRuleIcon = (ruleId: string) => {
    if (ruleId.includes('acos')) return <Target className="w-5 h-5" />;
    if (ruleId.includes('roas')) return <TrendingUp className="w-5 h-5" />;
    if (ruleId.includes('ctr')) return <Activity className="w-5 h-5" />;
    if (ruleId.includes('budget')) return <DollarSign className="w-5 h-5" />;
    if (ruleId.includes('negative')) return <AlertTriangle className="w-5 h-5" />;
    return <BookOpen className="w-5 h-5" />;
  };

  const getRuleColor = (ruleId: string) => {
    if (ruleId.includes('acos')) return 'bg-orange-500/20 text-orange-400';
    if (ruleId.includes('roas')) return 'bg-green-500/20 text-green-400';
    if (ruleId.includes('ctr')) return 'bg-blue-500/20 text-blue-400';
    if (ruleId.includes('budget')) return 'bg-purple-500/20 text-purple-400';
    if (ruleId.includes('negative')) return 'bg-red-500/20 text-red-400';
    return 'bg-gray-500/20 text-gray-400';
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Rule Engine</h1>
          <p className="text-gray-400 mt-1">
            View and manage AI optimization rules
          </p>
        </div>
      </div>

      {/* Rules List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Rules Cards */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Active Rules</h2>
          
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="card p-4 animate-pulse">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-gray-200 dark:bg-gray-700" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
                      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-4 stagger-animation">
              {rules?.map((rule) => (
                <div
                  key={rule.id}
                  onClick={() => setSelectedRule(rule.id === selectedRule ? null : rule.id)}
                  className={cn(
                    'card p-4 cursor-pointer transition-all hover:border-amazon-orange/30',
                    selectedRule === rule.id && 'border-amazon-orange'
                  )}
                >
                  <div className="flex items-start gap-4">
                    <div className={cn('p-2.5 rounded-lg', getRuleColor(rule.id))}>
                      {getRuleIcon(rule.id)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-gray-900 dark:text-white">{rule.name}</h3>
                        {rule.is_active ? (
                          <span className="badge badge-success flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            Active
                          </span>
                        ) : (
                          <span className="badge badge-neutral flex items-center gap-1">
                            <XCircle className="w-3 h-3" />
                            Inactive
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-400 mt-1">
                        {rule.description}
                      </p>
                      <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {rule.trigger_frequency}
                        </span>
                        {rule.last_execution && (
                          <span>
                            Last run: {formatRelativeTime(rule.last_execution)}
                          </span>
                        )}
                      </div>
                    </div>
                    <ChevronRight className={cn(
                      'w-5 h-5 text-gray-400 transition-transform',
                      selectedRule === rule.id && 'rotate-90'
                    )} />
                  </div>

                  {/* Expanded Details */}
                  {selectedRule === rule.id && (
                    <div className="mt-4 pt-4 border-t border-surface-dark-border animate-fade-in">
                      <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Rule Logic</h4>
                      <pre className="text-xs text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto">
                        {rule.logic}
                      </pre>
                      {rule.last_result && (
                        <div className="mt-4">
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Last Result</h4>
                          <p className="text-sm text-gray-400">{rule.last_result}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Rule Documentation */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Rule Documentation</h2>
          
          <div className="card">
            <div className="card-body space-y-6">
              <div>
                <h3 className="font-medium text-gray-900 dark:text-white mb-2">ACOS Rule</h3>
                <p className="text-sm text-gray-400">
                  Adjusts bids based on Advertising Cost of Sales (ACOS).
                  Target ACOS is 9% with ±5% tolerance.
                </p>
                <div className="mt-2 text-sm">
                  <p className="text-gray-500">Triggers:</p>
                  <ul className="list-disc list-inside text-gray-400 mt-1">
                    <li>ACOS exceeds 14% → reduce bid</li>
                    <li>ACOS below 4% → increase bid</li>
                  </ul>
                </div>
              </div>

              <div className="border-t border-surface-dark-border pt-6">
                <h3 className="font-medium text-gray-900 dark:text-white mb-2">ROAS Rule</h3>
                <p className="text-sm text-gray-400">
                  Adjusts bids based on Return on Ad Spend (ROAS).
                  Target ROAS is 11.11:1.
                </p>
                <div className="mt-2 text-sm">
                  <p className="text-gray-500">Triggers:</p>
                  <ul className="list-disc list-inside text-gray-400 mt-1">
                    <li>ROAS below 10.61:1 → reduce bid</li>
                    <li>ROAS above 11.61:1 → increase bid</li>
                  </ul>
                </div>
              </div>

              <div className="border-t border-surface-dark-border pt-6">
                <h3 className="font-medium text-gray-900 dark:text-white mb-2">Safety Limits</h3>
                <div className="grid grid-cols-2 gap-4 mt-2 text-sm">
                  <div>
                    <p className="text-gray-500">Bid Floor</p>
                    <p className="text-gray-900 dark:text-white">$0.02</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Bid Cap</p>
                    <p className="text-gray-900 dark:text-white">$4.52</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Max Daily Adjustments</p>
                    <p className="text-gray-900 dark:text-white">3 per entity</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Cooldown Period</p>
                    <p className="text-gray-900 dark:text-white">6 hours</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

