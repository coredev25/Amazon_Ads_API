/**
 * Helper utilities for the dashboard
 */

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Merge Tailwind classes
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Format currency
export function formatCurrency(value: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

// Format number with commas
export function formatNumber(value: number, decimals: number = 0): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

// Format percentage
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`;
}

// Format ACOS/ROAS
export function formatAcos(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return `${value.toFixed(1)}%`;
}

export function formatRoas(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  return `${value.toFixed(2)}x`;
}

// Format date
export function formatDate(date: string | Date, format: 'short' | 'long' | 'time' = 'short'): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  
  switch (format) {
    case 'long':
      return d.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    case 'time':
      return d.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      });
    default:
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      });
  }
}

// Format relative time
export function formatRelativeTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  
  return formatDate(d);
}

// Get priority color class
export function getPriorityColor(priority: string): string {
  switch (priority.toLowerCase()) {
    case 'critical':
      return 'text-red-400';
    case 'high':
      return 'text-orange-400';
    case 'medium':
      return 'text-yellow-400';
    case 'low':
      return 'text-gray-400';
    default:
      return 'text-gray-400';
  }
}

// Get priority badge class
export function getPriorityBadge(priority: string): string {
  switch (priority.toLowerCase()) {
    case 'critical':
      return 'badge-danger';
    case 'high':
      return 'badge-warning';
    case 'medium':
      return 'badge-info';
    case 'low':
      return 'badge-neutral';
    default:
      return 'badge-neutral';
  }
}

// Get status badge class
export function getStatusBadge(status: string): string {
  switch (status.toLowerCase()) {
    case 'enabled':
    case 'active':
    case 'approved':
    case 'success':
      return 'badge-success';
    case 'paused':
    case 'pending':
      return 'badge-warning';
    case 'disabled':
    case 'rejected':
    case 'failed':
      return 'badge-danger';
    default:
      return 'badge-neutral';
  }
}

// Get recommendation type icon
export function getRecommendationTypeIcon(type: string): string {
  switch (type) {
    case 'bid':
      return '💰';
    case 'budget':
      return '📊';
    case 'negative_keyword':
      return '🚫';
    case 'pause':
      return '⏸️';
    case 'enable':
      return '▶️';
    default:
      return '📝';
  }
}

// Calculate trend direction
export function getTrendDirection(current: number, previous: number): 'up' | 'down' | 'neutral' {
  if (current > previous * 1.01) return 'up';
  if (current < previous * 0.99) return 'down';
  return 'neutral';
}

// Get trend class
export function getTrendClass(direction: 'up' | 'down' | 'neutral', inverted: boolean = false): string {
  if (direction === 'neutral') return 'trend-neutral';
  
  if (inverted) {
    return direction === 'up' ? 'trend-down' : 'trend-up';
  }
  
  return direction === 'up' ? 'trend-up' : 'trend-down';
}

// Truncate text
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

// Debounce function
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// Generate unique ID
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// Calculate health score color
export function getHealthScoreColor(score: number): string {
  if (score >= 80) return 'text-green-400';
  if (score >= 60) return 'text-yellow-400';
  if (score >= 40) return 'text-orange-400';
  return 'text-red-400';
}

// Get health score gradient
export function getHealthScoreGradient(score: number): string {
  if (score >= 80) return 'from-green-500 to-emerald-400';
  if (score >= 60) return 'from-yellow-500 to-amber-400';
  if (score >= 40) return 'from-orange-500 to-amber-500';
  return 'from-red-500 to-rose-400';
}

