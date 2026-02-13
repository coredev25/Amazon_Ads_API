'use client';

import React from 'react';
import { cn } from '@/utils/helpers';
import { Inbox, Search, BarChart3, Target, Key, Lightbulb, Ban, History, DollarSign, Settings } from 'lucide-react';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
  compact?: boolean;
}

const defaultIcons: Record<string, typeof Inbox> = {
  campaign: Target,
  keyword: Key,
  recommendation: Lightbulb,
  negative: Ban,
  history: History,
  financial: DollarSign,
  settings: Settings,
  search: Search,
  chart: BarChart3,
};

export default function EmptyState({
  icon,
  title,
  description,
  action,
  className,
  compact = false,
}: EmptyStateProps) {
  return (
    <div className={cn(
      'flex flex-col items-center justify-center text-center',
      compact ? 'py-8 px-4' : 'py-16 px-6',
      'animate-fade-in-up',
      className
    )}>
      <div className={cn(
        'rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4',
        compact ? 'w-12 h-12' : 'w-16 h-16'
      )}>
        {icon || <Inbox className={cn('text-gray-400 dark:text-gray-500', compact ? 'w-6 h-6' : 'w-8 h-8')} />}
      </div>
      <h3 className={cn(
        'font-semibold text-gray-900 dark:text-white mb-1',
        compact ? 'text-sm' : 'text-lg'
      )}>
        {title}
      </h3>
      {description && (
        <p className={cn(
          'text-gray-500 dark:text-gray-400 max-w-sm',
          compact ? 'text-xs' : 'text-sm'
        )}>
          {description}
        </p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 btn btn-primary text-sm"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

export { defaultIcons };
