'use client';

import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn, formatCurrency, formatNumber, formatPercentage } from '@/utils/helpers';

interface MetricCardProps {
  title: string;
  value: number;
  format?: 'currency' | 'number' | 'percentage' | 'multiplier';
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
    isGood?: boolean;
  };
  icon?: React.ReactNode;
  accentColor?: string;
  className?: string;
}

export default function MetricCard({
  title,
  value,
  format = 'number',
  trend,
  icon,
  accentColor = '#FF9900',
  className,
}: MetricCardProps) {
  const formatValue = () => {
    switch (format) {
      case 'currency':
        return formatCurrency(value);
      case 'percentage':
        return formatPercentage(value);
      case 'multiplier':
        return `${value.toFixed(2)}x`;
      default:
        return formatNumber(value);
    }
  };

  const getTrendIcon = () => {
    if (!trend) return null;
    switch (trend.direction) {
      case 'up':
        return <TrendingUp className="w-4 h-4" />;
      case 'down':
        return <TrendingDown className="w-4 h-4" />;
      default:
        return <Minus className="w-4 h-4" />;
    }
  };

  const getTrendColor = () => {
    if (!trend) return '';
    if (trend.direction === 'neutral') return 'text-gray-500 dark:text-gray-400';
    
    // For some metrics like ACOS, down is good
    if (trend.isGood !== undefined) {
      return trend.isGood ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
    }
    
    return trend.direction === 'up' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  };

  return (
    <div
      className={cn('metric-card', className)}
      style={{ '--accent-color': accentColor } as React.CSSProperties}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
          <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">{formatValue()}</p>
          
          {trend && (
            <div className={cn('flex items-center gap-1 mt-2 text-sm', getTrendColor())}>
              {getTrendIcon()}
              <span>
                {trend.direction !== 'neutral' && (trend.direction === 'up' ? '+' : '')}
                {trend.value.toFixed(1)}%
              </span>
              <span className="text-gray-500 dark:text-gray-400">vs last period</span>
            </div>
          )}
        </div>
        
        {icon && (
          <div
            className="p-3 rounded-lg"
            style={{ backgroundColor: `${accentColor}20` }}
          >
            <div style={{ color: accentColor }}>{icon}</div>
          </div>
        )}
      </div>
    </div>
  );
}

