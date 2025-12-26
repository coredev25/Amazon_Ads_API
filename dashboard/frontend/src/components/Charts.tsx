'use client';

import React from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
} from 'recharts';
import { formatCurrency } from '@/utils/helpers';

interface ChartData {
  [key: string]: string | number;
}

interface ChartProps {
  data: ChartData[];
  height?: number;
  className?: string;
}

// Custom tooltip component
const CustomTooltip = ({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) => {
  if (!active || !payload) return null;

  return (
    <div className="custom-tooltip">
      <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">{label}</p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2 text-sm">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-gray-600 dark:text-gray-400">{entry.name}:</span>
          <span className="text-gray-900 dark:text-white font-medium">
            {entry.name.toLowerCase().includes('spend') ||
            entry.name.toLowerCase().includes('sales')
              ? formatCurrency(entry.value)
              : entry.name.toLowerCase().includes('acos') ||
                entry.name.toLowerCase().includes('roas')
              ? `${entry.value.toFixed(2)}${entry.name.toLowerCase().includes('acos') ? '%' : 'x'}`
              : entry.value.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
};

// Spend vs Sales chart (Main trend chart)
export function SpendSalesChart({ data, height = 300, className }: ChartProps) {
  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data}>
          <defs>
            <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#FF9900" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#FF9900" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="salesGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363D" />
          <XAxis
            dataKey="date"
            stroke="#8B949E"
            tick={{ fill: '#8B949E', fontSize: 12 }}
            axisLine={{ stroke: '#30363D' }}
          />
          <YAxis
            yAxisId="left"
            stroke="#8B949E"
            tick={{ fill: '#8B949E', fontSize: 12 }}
            axisLine={{ stroke: '#30363D' }}
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="#8B949E"
            tick={{ fill: '#8B949E', fontSize: 12 }}
            axisLine={{ stroke: '#30363D' }}
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="circle"
          />
          <Bar
            yAxisId="left"
            dataKey="spend"
            name="Spend"
            fill="#FF9900"
            radius={[4, 4, 0, 0]}
            opacity={0.8}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="sales"
            name="Sales"
            stroke="#10B981"
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 6, strokeWidth: 2 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// ACOS Trend Chart
export function AcosTrendChart({ data, height = 200, className }: ChartProps) {
  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="acosGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363D" />
          <XAxis
            dataKey="date"
            stroke="#8B949E"
            tick={{ fill: '#8B949E', fontSize: 12 }}
            axisLine={{ stroke: '#30363D' }}
          />
          <YAxis
            stroke="#8B949E"
            tick={{ fill: '#8B949E', fontSize: 12 }}
            axisLine={{ stroke: '#30363D' }}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="acos"
            name="ACOS"
            stroke="#F59E0B"
            fill="url(#acosGradient)"
            strokeWidth={2}
          />
          {/* Target line */}
          <Line
            type="monotone"
            dataKey={() => 9}
            stroke="#EF4444"
            strokeDasharray="5 5"
            strokeWidth={1}
            dot={false}
            name="Target ACOS"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// Performance Distribution Bar Chart
export function PerformanceBarChart({ data, height = 200, className }: ChartProps) {
  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="#30363D" horizontal={false} />
          <XAxis
            type="number"
            stroke="#8B949E"
            tick={{ fill: '#8B949E', fontSize: 12 }}
            axisLine={{ stroke: '#30363D' }}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="#8B949E"
            tick={{ fill: '#8B949E', fontSize: 12 }}
            axisLine={{ stroke: '#30363D' }}
            width={100}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar
            dataKey="value"
            fill="#FF9900"
            radius={[0, 4, 4, 0]}
            name="Value"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// Mini sparkline chart for tables
interface SparklineProps {
  data: number[];
  color?: string;
  height?: number;
  width?: number;
}

export function Sparkline({
  data,
  color = '#FF9900',
  height = 30,
  width = 80,
}: SparklineProps) {
  const chartData = data.map((value, index) => ({ value, index }));

  return (
    <ResponsiveContainer width={width} height={height}>
      <LineChart data={chartData}>
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// Health score gauge
interface GaugeProps {
  value: number;
  size?: number;
  className?: string;
}

export function HealthGauge({ value, size = 120, className }: GaugeProps) {
  const radius = (size - 20) / 2;
  const circumference = radius * Math.PI;
  const progress = (value / 100) * circumference;

  const getColor = () => {
    if (value >= 80) return '#10B981';
    if (value >= 60) return '#F59E0B';
    if (value >= 40) return '#F97316';
    return '#EF4444';
  };

  return (
    <div className={className} style={{ width: size, height: size / 2 + 20 }}>
      <svg width={size} height={size / 2 + 20} viewBox={`0 0 ${size} ${size / 2 + 20}`}>
        {/* Background arc */}
        <path
          d={`M 10 ${size / 2 + 10} A ${radius} ${radius} 0 0 1 ${size - 10} ${size / 2 + 10}`}
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          strokeLinecap="round"
          className="text-gray-300 dark:text-gray-700"
        />
        {/* Progress arc */}
        <path
          d={`M 10 ${size / 2 + 10} A ${radius} ${radius} 0 0 1 ${size - 10} ${size / 2 + 10}`}
          fill="none"
          stroke={getColor()}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${progress} ${circumference}`}
          style={{
            transition: 'stroke-dasharray 0.5s ease',
          }}
        />
        {/* Value text */}
        <text
          x={size / 2}
          y={size / 2}
          textAnchor="middle"
          fontSize="24"
          fontWeight="bold"
          className="fill-gray-900 dark:fill-white"
        >
          {value}
        </text>
        <text
          x={size / 2}
          y={size / 2 + 18}
          textAnchor="middle"
          fontSize="12"
          className="fill-gray-600 dark:fill-gray-400"
        >
          Health Score
        </text>
      </svg>
    </div>
  );
}

