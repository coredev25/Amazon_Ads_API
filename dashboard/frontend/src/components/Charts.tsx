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
  PieChart as RePieChart,
  Pie,
  Cell,
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

// ============================================================================
// DONUT CHART — for distributions (severity, status, type)
// ============================================================================

const DONUT_COLORS = ['#FF9900', '#10B981', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6'];

interface DonutChartProps {
  data: Array<{ name: string; value: number; color?: string }>;
  height?: number;
  innerRadius?: number;
  outerRadius?: number;
  className?: string;
  centerLabel?: string;
  centerValue?: string | number;
}

export function DonutChart({
  data,
  height = 200,
  innerRadius = 50,
  outerRadius = 75,
  className,
  centerLabel,
  centerValue,
}: DonutChartProps) {
  const filteredData = data.filter(d => d.value > 0);

  return (
    <div className={className} style={{ position: 'relative' }}>
      <ResponsiveContainer width="100%" height={height}>
        <RePieChart>
          <Pie
            data={filteredData}
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={2}
            dataKey="value"
            stroke="none"
          >
            {filteredData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color || DONUT_COLORS[index % DONUT_COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const item = payload[0];
              return (
                <div className="custom-tooltip">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {item.name}: {item.value}
                  </p>
                </div>
              );
            }}
          />
        </RePieChart>
      </ResponsiveContainer>
      {centerLabel && (
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-lg font-bold text-gray-900 dark:text-white">{centerValue}</span>
          <span className="text-[10px] text-gray-500 dark:text-gray-400">{centerLabel}</span>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// MINI AREA CHART — compact chart for stat cards
// ============================================================================

interface MiniAreaChartProps {
  data: number[];
  color?: string;
  height?: number;
  className?: string;
}

export function MiniAreaChart({
  data,
  color = '#FF9900',
  height = 50,
  className,
}: MiniAreaChartProps) {
  const chartData = data.map((value, index) => ({ value, index }));
  const gradientId = `miniArea-${color.replace('#', '')}`;

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            fill={`url(#${gradientId})`}
            strokeWidth={1.5}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ============================================================================
// SIMPLE BAR CHART — vertical bars for activity frequency
// ============================================================================

interface SimpleBarChartProps {
  data: Array<{ label: string; value: number; color?: string }>;
  height?: number;
  className?: string;
  barColor?: string;
  valueFormatter?: (value: number) => string;
}

export function SimpleBarChart({
  data,
  height = 200,
  className,
  barColor = '#FF9900',
  valueFormatter,
}: SimpleBarChartProps) {
  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363D" vertical={false} />
          <XAxis
            dataKey="label"
            stroke="#8B949E"
            tick={{ fill: '#8B949E', fontSize: 10 }}
            axisLine={{ stroke: '#30363D' }}
            interval="preserveStartEnd"
          />
          <YAxis
            stroke="#8B949E"
            tick={{ fill: '#8B949E', fontSize: 10 }}
            axisLine={{ stroke: '#30363D' }}
            tickFormatter={valueFormatter}
            width={40}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="custom-tooltip">
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {valueFormatter ? valueFormatter(payload[0].value as number) : payload[0].value}
                  </p>
                </div>
              );
            }}
          />
          <Bar dataKey="value" fill={barColor} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ============================================================================
// DUAL LINE CHART — two metrics on same axis (e.g., ACOS vs TACoS)
// ============================================================================

interface DualLineChartProps {
  data: Array<{ label: string; line1: number; line2: number }>;
  line1Name?: string;
  line2Name?: string;
  line1Color?: string;
  line2Color?: string;
  height?: number;
  className?: string;
  yAxisFormatter?: (value: number) => string;
}

export function DualLineChart({
  data,
  line1Name = 'Line 1',
  line2Name = 'Line 2',
  line1Color = '#FF9900',
  line2Color = '#3B82F6',
  height = 200,
  className,
  yAxisFormatter,
}: DualLineChartProps) {
  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363D" />
          <XAxis
            dataKey="label"
            stroke="#8B949E"
            tick={{ fill: '#8B949E', fontSize: 10 }}
            axisLine={{ stroke: '#30363D' }}
            interval="preserveStartEnd"
          />
          <YAxis
            stroke="#8B949E"
            tick={{ fill: '#8B949E', fontSize: 10 }}
            axisLine={{ stroke: '#30363D' }}
            tickFormatter={yAxisFormatter}
            width={45}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="line1"
            name={line1Name}
            stroke={line1Color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="line2"
            name={line2Name}
            stroke={line2Color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            strokeDasharray="5 5"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
