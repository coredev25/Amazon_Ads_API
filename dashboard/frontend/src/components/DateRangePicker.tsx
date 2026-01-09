'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Calendar, ChevronDown, X } from 'lucide-react';
import { cn } from '@/utils/helpers';

export type DateRangeType = 
  | 'today'
  | 'yesterday'
  | 'last_7_days'
  | 'last_14_days'
  | 'last_30_days'
  | 'this_week'
  | 'last_week'
  | 'this_month'
  | 'last_month'
  | 'year_to_date'
  | 'lifetime'
  | 'custom';

export interface DateRange {
  type: DateRangeType;
  startDate?: Date;
  endDate?: Date;
  days?: number;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
  className?: string;
}

const dateRangeOptions: Array<{ value: DateRangeType; label: string }> = [
  { value: 'today', label: 'Today' },
  { value: 'yesterday', label: 'Yesterday' },
  { value: 'last_7_days', label: 'Last 7 Days' },
  { value: 'last_14_days', label: 'Last 14 Days' },
  { value: 'last_30_days', label: 'Last 30 Days' },
  { value: 'this_week', label: 'This Week' },
  { value: 'last_week', label: 'Last Week' },
  { value: 'this_month', label: 'This Month' },
  { value: 'last_month', label: 'Last Month' },
  { value: 'custom', label: 'Custom Range' },
];

function calculateDateRange(type: DateRangeType): { startDate: Date; endDate: Date } {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  let endDate = new Date(today);
  endDate.setHours(23, 59, 59, 999);
  
  let startDate = new Date(today);

  switch (type) {
    case 'today':
      startDate = new Date(today);
      break;
    case 'yesterday':
      startDate = new Date(today);
      startDate.setDate(startDate.getDate() - 1);
      endDate.setDate(endDate.getDate() - 1);
      endDate.setHours(23, 59, 59, 999);
      break;
    case 'last_7_days':
      startDate.setDate(startDate.getDate() - 6);
      break;
    case 'last_14_days':
      startDate.setDate(startDate.getDate() - 13);
      break;
    case 'last_30_days':
      startDate.setDate(startDate.getDate() - 29);
      break;
    case 'this_week':
      const dayOfWeek = today.getDay();
      startDate.setDate(today.getDate() - dayOfWeek);
      break;
    case 'last_week':
      const lastWeekDay = today.getDay();
      startDate.setDate(today.getDate() - lastWeekDay - 7);
      endDate.setDate(today.getDate() - lastWeekDay - 1);
      endDate.setHours(23, 59, 59, 999);
      break;
    case 'this_month':
      startDate = new Date(today.getFullYear(), today.getMonth(), 1);
      break;
    case 'last_month':
      startDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      endDate = new Date(today.getFullYear(), today.getMonth(), 0);
      endDate.setHours(23, 59, 59, 999);
      break;
    case 'year_to_date':
      startDate = new Date(today.getFullYear(), 0, 1);
      break;
    case 'lifetime':
      startDate = new Date(2020, 0, 1); // Arbitrary start date
      break;
    default:
      return { startDate, endDate };
  }

  return { startDate, endDate };
}

export default function DateRangePicker({ value, onChange, className }: DateRangePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [showCustomPicker, setShowCustomPicker] = useState(false);
  const [customStartDate, setCustomStartDate] = useState<string>('');
  const [customEndDate, setCustomEndDate] = useState<string>('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setShowCustomPicker(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleRangeSelect = (type: DateRangeType) => {
    if (type === 'custom') {
      setShowCustomPicker(true);
      return;
    }

    const { startDate, endDate } = calculateDateRange(type);
    onChange({
      type,
      startDate,
      endDate,
      days: type === 'last_7_days' ? 7 : type === 'last_14_days' ? 14 : type === 'last_30_days' ? 30 : undefined,
    });
    setIsOpen(false);
  };

  const handleCustomDateApply = () => {
    if (!customStartDate || !customEndDate) return;

    const start = new Date(customStartDate);
    const end = new Date(customEndDate);
    end.setHours(23, 59, 59, 999);

    onChange({
      type: 'custom',
      startDate: start,
      endDate: end,
    });
    setIsOpen(false);
    setShowCustomPicker(false);
  };

  const getDisplayLabel = () => {
    if (value.type === 'custom' && value.startDate && value.endDate) {
      const start = value.startDate.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: 'numeric'
      });
      const end = value.endDate.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: 'numeric'
      });
      return `${start} - ${end}`;
    }
    const option = dateRangeOptions.find(opt => opt.value === value.type);
    return option?.label || 'Select Date Range';
  };

  const formatDateRange = () => {
    if (value.startDate && value.endDate) {
      const start = value.startDate.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric'
      });
      const end = value.endDate.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: value.startDate.getFullYear() !== value.endDate.getFullYear() ? 'numeric' : undefined
      });
      return `${start} - ${end}`;
    }
    return null;
  };

  // Initialize custom date inputs when opening custom picker
  useEffect(() => {
    if (showCustomPicker && value.type === 'custom' && value.startDate && value.endDate) {
      setCustomStartDate(value.startDate.toISOString().split('T')[0]);
      setCustomEndDate(value.endDate.toISOString().split('T')[0]);
    }
  }, [showCustomPicker, value.type, value.startDate, value.endDate]);

  return (
    <div className={cn('relative', className)} ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2.5 px-4 py-2.5 rounded-lg border transition-all duration-200',
          'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600',
          'hover:border-amazon-orange/50 hover:bg-gray-50 dark:hover:bg-gray-700',
          'focus:outline-none focus:ring-2 focus:ring-amazon-orange/50 focus:border-amazon-orange',
          'shadow-sm hover:shadow-md',
          isOpen && 'border-amazon-orange ring-2 ring-amazon-orange/20 shadow-md'
        )}
      >
        <Calendar className="w-4 h-4 text-amazon-orange flex-shrink-0" />
        <span className="text-sm font-semibold text-gray-900 dark:text-white whitespace-nowrap">
          {getDisplayLabel()}
        </span>
        <ChevronDown 
          className={cn(
            'w-4 h-4 text-gray-500 dark:text-gray-400 transition-transform duration-200 flex-shrink-0',
            isOpen && 'rotate-180 text-amazon-orange'
          )} 
        />
      </button>

      {isOpen && (
        <div className="absolute top-full right-0 mt-2 w-72 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl z-50 overflow-hidden">
          {!showCustomPicker ? (
            <div className="py-2 max-h-96 overflow-y-auto">
              {/* Selected range display */}
              {value.startDate && value.endDate && (
                <div className="px-4 py-3 mb-2 bg-amazon-orange/5 border-b border-gray-200 dark:border-gray-700">
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Selected Range
                  </div>
                  <div className="text-sm font-semibold text-amazon-orange">
                    {formatDateRange()}
                  </div>
                </div>
              )}
              
              {/* Quick options */}
              <div className="px-2">
                {dateRangeOptions.map((option) => {
                  const isSelected = value.type === option.value;
                  return (
                    <button
                      key={option.value}
                      onClick={() => handleRangeSelect(option.value)}
                      className={cn(
                        'w-full text-left px-3 py-2.5 rounded-md transition-all duration-150',
                        'flex items-center justify-between group',
                        isSelected
                          ? 'bg-amazon-orange text-white shadow-sm'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                      )}
                    >
                      <span className={cn(
                        'text-sm font-medium',
                        isSelected ? 'text-white' : 'text-gray-700 dark:text-gray-300'
                      )}>
                        {option.label}
                      </span>
                      {isSelected && (
                        <svg 
                          className="w-4 h-4 text-white" 
                          fill="none" 
                          strokeLinecap="round" 
                          strokeLinejoin="round" 
                          strokeWidth="2" 
                          viewBox="0 0 24 24" 
                          stroke="currentColor"
                        >
                          <path d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="p-4 space-y-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                  Custom Date Range
                </h3>
                <button
                  onClick={() => {
                    setShowCustomPicker(false);
                    setCustomStartDate('');
                    setCustomEndDate('');
                  }}
                  className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <X className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                </button>
              </div>
              
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    Start Date
                  </label>
                  <input
                    type="date"
                    value={customStartDate}
                    onChange={(e) => setCustomStartDate(e.target.value)}
                    className="input w-full text-sm"
                    max={customEndDate || undefined}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    End Date
                  </label>
                  <input
                    type="date"
                    value={customEndDate}
                    onChange={(e) => setCustomEndDate(e.target.value)}
                    className="input w-full text-sm"
                    min={customStartDate || undefined}
                    max={new Date().toISOString().split('T')[0]}
                  />
                </div>
              </div>
              
              <div className="flex items-center gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={handleCustomDateApply}
                  disabled={!customStartDate || !customEndDate}
                  className={cn(
                    'flex-1 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200',
                    'bg-amazon-orange text-white hover:bg-orange-600',
                    'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-amazon-orange',
                    'focus:outline-none focus:ring-2 focus:ring-amazon-orange/50'
                  )}
                >
                  Apply
                </button>
                <button
                  onClick={() => {
                    setShowCustomPicker(false);
                    setCustomStartDate('');
                    setCustomEndDate('');
                  }}
                  className={cn(
                    'px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200',
                    'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
                    'hover:bg-gray-200 dark:hover:bg-gray-600',
                    'focus:outline-none focus:ring-2 focus:ring-gray-400/50'
                  )}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

