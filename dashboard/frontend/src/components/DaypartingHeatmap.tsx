'use client';

import React, { useState } from 'react';
import { Clock, Save, RotateCcw } from 'lucide-react';
import { cn, formatCurrency, formatPercentage } from '@/utils/helpers';

interface DaypartingData {
  day_of_week: number; // 0 = Monday, 6 = Sunday
  hour_of_day: number; // 0-23
  value: number; // Sales, Spend, ACOS, etc.
  metric: 'sales' | 'spend' | 'acos' | 'ctr' | 'cvr';
}

interface DaypartingConfig {
  day_of_week: number;
  hour_of_day: number;
  bid_multiplier: number;
  is_active: boolean;
}

interface DaypartingHeatmapProps {
  data: DaypartingData[];
  config?: DaypartingConfig[];
  entityType: 'campaign' | 'ad_group' | 'keyword';
  entityId: number;
  metric: 'sales' | 'spend' | 'acos' | 'ctr' | 'cvr';
  onConfigChange?: (config: DaypartingConfig[]) => Promise<void>;
  className?: string;
}

const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const hours = Array.from({ length: 24 }, (_, i) => i);

export default function DaypartingHeatmap({
  data,
  config = [],
  entityType,
  entityId,
  metric,
  onConfigChange,
  className,
}: DaypartingHeatmapProps) {
  const [editingConfig, setEditingConfig] = useState<DaypartingConfig[]>(config);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Create a map for quick lookup
  const dataMap = new Map<string, number>();
  data.forEach((d) => {
    const key = `${d.day_of_week}-${d.hour_of_day}`;
    dataMap.set(key, d.value);
  });

  const configMap = new Map<string, DaypartingConfig>();
  editingConfig.forEach((c) => {
    const key = `${c.day_of_week}-${c.hour_of_day}`;
    configMap.set(key, c);
  });

  // Get value for a cell
  const getCellValue = (day: number, hour: number): number => {
    const key = `${day}-${hour}`;
    return dataMap.get(key) || 0;
  };

  // Get max value for normalization
  const maxValue = Math.max(...Array.from(dataMap.values()), 1);

  // Get color intensity based on value
  const getCellColor = (value: number, multiplier: number = 1.0): string => {
    const normalized = (value / maxValue) * multiplier;
    
    if (metric === 'acos') {
      // Lower ACOS is better (green), higher is worse (red)
      if (normalized < 0.3) return 'bg-green-500';
      if (normalized < 0.5) return 'bg-green-400';
      if (normalized < 0.7) return 'bg-yellow-400';
      if (normalized < 0.9) return 'bg-orange-400';
      return 'bg-red-500';
    } else {
      // Higher values are better (green)
      if (normalized > 0.8) return 'bg-green-500';
      if (normalized > 0.6) return 'bg-green-400';
      if (normalized > 0.4) return 'bg-yellow-400';
      if (normalized > 0.2) return 'bg-orange-400';
      return 'bg-red-300';
    }
  };

  const getCellOpacity = (value: number): number => {
    const normalized = value / maxValue;
    return Math.max(0.3, Math.min(1, normalized));
  };

  const handleCellClick = (day: number, hour: number) => {
    if (!isEditing) return;

    const key = `${day}-${hour}`;
    const existing = configMap.get(key);

    if (existing) {
      // Toggle active or adjust multiplier
      const newConfig = editingConfig.map((c) =>
        c.day_of_week === day && c.hour_of_day === hour
          ? { ...c, is_active: !c.is_active }
          : c
      );
      setEditingConfig(newConfig);
    } else {
      // Add new config
      setEditingConfig([
        ...editingConfig,
        {
          day_of_week: day,
          hour_of_day: hour,
          bid_multiplier: 1.0,
          is_active: true,
        },
      ]);
    }
  };

  const handleMultiplierChange = (day: number, hour: number, multiplier: number) => {
    const key = `${day}-${hour}`;
    const existing = configMap.get(key);

    if (existing) {
      setEditingConfig(
        editingConfig.map((c) =>
          c.day_of_week === day && c.hour_of_day === hour
            ? { ...c, bid_multiplier: multiplier }
            : c
        )
      );
    } else {
      setEditingConfig([
        ...editingConfig,
        {
          day_of_week: day,
          hour_of_day: hour,
          bid_multiplier: multiplier,
          is_active: true,
        },
      ]);
    }
  };

  const handleSave = async () => {
    if (!onConfigChange) return;

    setIsSaving(true);
    try {
      await onConfigChange(editingConfig);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to save dayparting config:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    setEditingConfig(config);
    setIsEditing(false);
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Clock className="w-5 h-5 text-amazon-orange" />
            Dayparting Analysis - {metric.toUpperCase()}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Performance by hour of day and day of week
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isEditing ? (
            <>
              <button
                onClick={handleReset}
                className="btn btn-sm btn-secondary"
                disabled={isSaving}
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>
              <button
                onClick={handleSave}
                className="btn btn-sm btn-primary"
                disabled={isSaving}
              >
                <Save className="w-4 h-4" />
                {isSaving ? 'Saving...' : 'Save Schedule'}
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsEditing(true)}
              className="btn btn-sm btn-primary"
            >
              Edit Schedule
            </button>
          )}
        </div>
      </div>

      {/* Heatmap */}
      <div className="card p-4 overflow-x-auto">
        <div className="min-w-max">
          {/* Header row with hours */}
          <div className="flex mb-2">
            <div className="w-16 flex-shrink-0"></div>
            {hours.map((hour) => (
              <div
                key={hour}
                className="w-12 text-center text-xs font-medium text-gray-600 dark:text-gray-400"
              >
                {hour.toString().padStart(2, '0')}
              </div>
            ))}
          </div>

          {/* Rows for each day */}
          {daysOfWeek.map((day, dayIndex) => (
            <div key={dayIndex} className="flex items-center mb-1">
              <div className="w-16 flex-shrink-0 text-sm font-medium text-gray-700 dark:text-gray-300">
                {day}
              </div>
              {hours.map((hour) => {
                const value = getCellValue(dayIndex, hour);
                const cellConfig = configMap.get(`${dayIndex}-${hour}`);
                const multiplier = cellConfig?.bid_multiplier || 1.0;
                const isActive = cellConfig?.is_active !== false;
                const color = getCellColor(value, multiplier);
                const opacity = getCellOpacity(value);

                return (
                  <div
                    key={hour}
                    className={cn(
                      'w-12 h-12 mx-0.5 rounded border-2 cursor-pointer transition-all relative group',
                      color,
                      isEditing && 'hover:ring-2 hover:ring-amazon-orange',
                      !isActive && 'opacity-30',
                      isEditing && cellConfig && 'ring-2 ring-blue-500'
                    )}
                    style={{ opacity }}
                    onClick={() => handleCellClick(dayIndex, hour)}
                    title={`${day} ${hour}:00 - ${metric}: ${value.toFixed(2)}${metric === 'acos' || metric === 'ctr' || metric === 'cvr' ? '%' : ''} | Multiplier: ${multiplier.toFixed(2)}x`}
                  >
                    {isEditing && cellConfig && (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-xs font-bold text-white drop-shadow">
                          {multiplier.toFixed(1)}x
                        </span>
                      </div>
                    )}
                    {isEditing && (
                      <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-10">
                        Click to toggle | Right-click to set multiplier
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="mt-4 flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
          <div className="flex items-center gap-4">
            <span>Intensity:</span>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 bg-red-300 rounded" />
              <span>Low</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 bg-yellow-400 rounded" />
              <span>Medium</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 bg-green-500 rounded" />
              <span>High</span>
            </div>
          </div>
          {isEditing && (
            <div className="text-amazon-orange">
              Editing mode: Click cells to toggle, adjust multipliers in schedule manager
            </div>
          )}
        </div>
      </div>

      {/* Schedule Manager (when editing) */}
      {isEditing && editingConfig.length > 0 && (
        <div className="card p-4">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            Bid Multiplier Schedule
          </h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {editingConfig.map((c, index) => (
              <div
                key={index}
                className="flex items-center gap-4 p-2 bg-gray-50 dark:bg-gray-800 rounded"
              >
                <span className="text-sm text-gray-700 dark:text-gray-300 w-32">
                  {daysOfWeek[c.day_of_week]} {c.hour_of_day.toString().padStart(2, '0')}:00
                </span>
                <input
                  type="number"
                  min="0"
                  max="5"
                  step="0.1"
                  value={c.bid_multiplier}
                  onChange={(e) =>
                    handleMultiplierChange(
                      c.day_of_week,
                      c.hour_of_day,
                      parseFloat(e.target.value) || 1.0
                    )
                  }
                  className="input w-24"
                />
                <span className="text-sm text-gray-600 dark:text-gray-400">x</span>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={c.is_active}
                    onChange={() => handleCellClick(c.day_of_week, c.hour_of_day)}
                    className="rounded accent-amazon-orange"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-400">Active</span>
                </label>
                <button
                  onClick={() =>
                    setEditingConfig(editingConfig.filter((_, i) => i !== index))
                  }
                  className="ml-auto text-red-600 hover:text-red-700 text-sm"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

