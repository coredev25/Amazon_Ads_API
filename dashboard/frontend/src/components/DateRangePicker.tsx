'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Calendar, ChevronDown, ChevronLeft, ChevronRight, X, Info } from 'lucide-react';
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
  | 'this_year'
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
  { value: 'year_to_date', label: 'Year to Date' },
  { value: 'this_year', label: 'This Year' },
  { value: 'lifetime', label: 'Lifetime' },
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
    case 'this_year':
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

interface CalendarProps {
  year: number;
  month: number;
  startDate?: Date;
  endDate?: Date;
  onDateClick: (date: Date) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
}

function CalendarView({ year, month, startDate, endDate, onDateClick, onPrevMonth, onNextMonth }: CalendarProps) {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const firstDayOfWeek = firstDay.getDay();
  const daysInMonth = lastDay.getDate();
  
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const isDateInRange = (date: Date) => {
    if (!startDate || !endDate) return false;
    const dateTime = date.getTime();
    const startTime = startDate.getTime();
    const endTime = endDate.getTime();
    return dateTime >= startTime && dateTime <= endTime;
  };

  const isDateSelected = (date: Date) => {
    if (!startDate && !endDate) return false;
    const dateTime = date.getTime();
    if (startDate && dateTime === startDate.getTime()) return true;
    if (endDate && dateTime === endDate.getTime()) return true;
    return false;
  };

  const isDateToday = (date: Date) => {
    return date.getTime() === today.getTime();
  };

  const days = [];
  const weekDays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
  
  // Add empty cells for days before the first day of the month
  for (let i = 0; i < firstDayOfWeek; i++) {
    days.push(null);
  }
  
  // Add days of the month
  for (let day = 1; day <= daysInMonth; day++) {
    days.push(day);
  }

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onPrevMonth();
          }}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <ChevronLeft className="w-4 h-4 text-gray-600 dark:text-gray-400" />
        </button>
        <div className="text-sm font-semibold text-gray-900 dark:text-white">
          {monthNames[month]} {year}
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onNextMonth();
          }}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <ChevronRight className="w-4 h-4 text-gray-600 dark:text-gray-400" />
        </button>
      </div>
      
      <div className="grid grid-cols-7 gap-1 mb-2">
        {weekDays.map((day) => (
          <div
            key={day}
            className="text-xs font-medium text-gray-500 dark:text-gray-400 text-center py-1"
          >
            {day}
          </div>
        ))}
      </div>
      
      <div className="grid grid-cols-7 gap-1">
        {days.map((day, index) => {
          if (day === null) {
            return <div key={`empty-${index}`} className="aspect-square" />;
          }
          
          const date = new Date(year, month, day);
          const inRange = isDateInRange(date);
          const isSelected = isDateSelected(date);
          const isToday = isDateToday(date);
          const isStart = startDate && date.getTime() === startDate.getTime();
          const isEnd = endDate && date.getTime() === endDate.getTime();
          
          return (
            <button
              key={day}
              onClick={() => onDateClick(date)}
              className={cn(
                'aspect-square text-xs font-medium rounded transition-colors',
                'hover:bg-gray-100 dark:hover:bg-gray-700',
                inRange && !isSelected && 'bg-blue-50 dark:bg-blue-900/20',
                isSelected && 'bg-blue-600 text-white hover:bg-blue-700',
                !isSelected && !inRange && 'text-gray-700 dark:text-gray-300',
                isToday && !isSelected && 'ring-2 ring-blue-500',
                isStart && 'rounded-l-full',
                isEnd && 'rounded-r-full'
              )}
            >
              {day}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function DateRangePicker({ value, onChange, className }: DateRangePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedStartDate, setSelectedStartDate] = useState<Date | undefined>(value.startDate);
  const [selectedEndDate, setSelectedEndDate] = useState<Date | undefined>(value.endDate);
  const [leftCalendarMonth, setLeftCalendarMonth] = useState(new Date().getMonth());
  const [leftCalendarYear, setLeftCalendarYear] = useState(new Date().getFullYear());
  const [rightCalendarMonth, setRightCalendarMonth] = useState(new Date().getMonth() + 1);
  const [rightCalendarYear, setRightCalendarYear] = useState(new Date().getFullYear());
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Initialize calendar months
  useEffect(() => {
    if (value.startDate) {
      setSelectedStartDate(value.startDate);
      setLeftCalendarMonth(value.startDate.getMonth());
      setLeftCalendarYear(value.startDate.getFullYear());
    }
    if (value.endDate) {
      setSelectedEndDate(value.endDate);
      setRightCalendarMonth(value.endDate.getMonth());
      setRightCalendarYear(value.endDate.getFullYear());
    }
  }, [value.startDate, value.endDate]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
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
    const { startDate, endDate } = calculateDateRange(type);
    setSelectedStartDate(startDate);
    setSelectedEndDate(endDate);
    
    onChange({
      type,
      startDate,
      endDate,
      days: type === 'last_7_days' ? 7 : type === 'last_14_days' ? 14 : type === 'last_30_days' ? 30 : undefined,
    });
    
    // Update calendars to show the selected range
    setLeftCalendarMonth(startDate.getMonth());
    setLeftCalendarYear(startDate.getFullYear());
    setRightCalendarMonth(endDate.getMonth());
    setRightCalendarYear(endDate.getFullYear());
    
    // Close picker immediately for predefined options
    setIsOpen(false);
  };

  const handleDateClick = (date: Date) => {
    if (!selectedStartDate || (selectedStartDate && selectedEndDate)) {
      // Start new selection
      setSelectedStartDate(date);
      setSelectedEndDate(undefined);
    } else if (selectedStartDate && !selectedEndDate) {
      // Complete the selection
      if (date < selectedStartDate) {
        // If clicked date is before start, swap them
        setSelectedEndDate(selectedStartDate);
        setSelectedStartDate(date);
      } else {
        setSelectedEndDate(date);
      }
    }
  };

  const handleApply = () => {
    if (selectedStartDate && selectedEndDate) {
      const end = new Date(selectedEndDate);
      end.setHours(23, 59, 59, 999);
      
      onChange({
        type: 'custom',
        startDate: selectedStartDate,
        endDate: end,
      });
      setIsOpen(false);
    }
  };

  const handleCancel = () => {
    // Reset to current value
    setSelectedStartDate(value.startDate);
    setSelectedEndDate(value.endDate);
    setIsOpen(false);
  };

  const navigateMonth = (calendar: 'left' | 'right', direction: 'prev' | 'next') => {
    if (calendar === 'left') {
      if (direction === 'prev') {
        if (leftCalendarMonth === 0) {
          setLeftCalendarYear(leftCalendarYear - 1);
          setLeftCalendarMonth(11);
        } else {
          setLeftCalendarMonth(leftCalendarMonth - 1);
        }
      } else {
        if (leftCalendarMonth === 11) {
          setLeftCalendarYear(leftCalendarYear + 1);
          setLeftCalendarMonth(0);
        } else {
          setLeftCalendarMonth(leftCalendarMonth + 1);
        }
      }
    } else {
      if (direction === 'prev') {
        if (rightCalendarMonth === 0) {
          setRightCalendarYear(rightCalendarYear - 1);
          setRightCalendarMonth(11);
        } else {
          setRightCalendarMonth(rightCalendarMonth - 1);
        }
      } else {
        if (rightCalendarMonth === 11) {
          setRightCalendarYear(rightCalendarYear + 1);
          setRightCalendarMonth(0);
        } else {
          setRightCalendarMonth(rightCalendarMonth + 1);
        }
      }
    }
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
        <div className="absolute top-full right-0 mt-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl z-[100] overflow-hidden">
          <div className="flex">
            {/* Left Panel - Predefined Options */}
            <div className="w-64 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
              <div className="p-4">
                <div className="space-y-1">
                  {dateRangeOptions.map((option) => {
                    const isSelected = value.type === option.value;
                    return (
                      <button
                        key={option.value}
                        onClick={() => handleRangeSelect(option.value)}
                        className={cn(
                          'w-full text-left px-3 py-2 rounded-md transition-all duration-150',
                          'text-sm font-medium',
                          isSelected
                            ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white'
                            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                        )}
                      >
                        {option.label}
                      </button>
                    );
                  })}
                </div>
                
                {/* Info note */}
                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-start gap-2 text-xs text-gray-500 dark:text-gray-400">
                    <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                    <div>
                      <span>Dates are based on the campaign's country.</span>{' '}
                      <button className="text-blue-600 dark:text-blue-400 hover:underline">
                        Learn more
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Panel - Calendar Views */}
            <div className="w-[560px] p-4">
              <div className="flex gap-4">
                {/* Left Calendar */}
                <div className="flex-1">
                  <CalendarView
                    year={leftCalendarYear}
                    month={leftCalendarMonth}
                    startDate={selectedStartDate}
                    endDate={selectedEndDate}
                    onDateClick={handleDateClick}
                    onPrevMonth={() => navigateMonth('left', 'prev')}
                    onNextMonth={() => navigateMonth('left', 'next')}
                  />
                </div>

                {/* Right Calendar */}
                <div className="flex-1">
                  <CalendarView
                    year={rightCalendarYear}
                    month={rightCalendarMonth}
                    startDate={selectedStartDate}
                    endDate={selectedEndDate}
                    onDateClick={handleDateClick}
                    onPrevMonth={() => navigateMonth('right', 'prev')}
                    onNextMonth={() => navigateMonth('right', 'next')}
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-2 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={handleCancel}
                  className={cn(
                    'px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200',
                    'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300',
                    'border border-gray-300 dark:border-gray-600',
                    'hover:bg-gray-50 dark:hover:bg-gray-600',
                    'focus:outline-none focus:ring-2 focus:ring-gray-400/50'
                  )}
                >
                  Cancel
                </button>
                <button
                  onClick={handleApply}
                  disabled={!selectedStartDate || !selectedEndDate}
                  className={cn(
                    'px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200',
                    'bg-blue-600 text-white hover:bg-blue-700',
                    'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-600',
                    'focus:outline-none focus:ring-2 focus:ring-blue-500/50'
                  )}
                >
                  Apply
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
