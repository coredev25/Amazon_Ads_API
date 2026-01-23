'use client';

import React, { useState, useRef, useEffect } from 'react';
import { GripHorizontal, Settings2 } from 'lucide-react';
import { cn } from '@/utils/helpers';

interface Column {
  key: string;
  header: string;
  width: number;
  visible: boolean;
  sortable?: boolean;
}

interface ResizableSmartGridProps {
  columns: Column[];
  data: any[];
  onColumnResize: (columns: Column[]) => void;
  onColumnToggle: (columns: Column[]) => void;
  className?: string;
}

export function ResizableSmartGrid({
  columns: initialColumns,
  data,
  onColumnResize,
  onColumnToggle,
  className
}: ResizableSmartGridProps) {
  const [columns, setColumns] = useState<Column[]>(initialColumns);
  const [resizingColumn, setResizingColumn] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Handle column resize
  const handleMouseDown = (e: React.MouseEvent, columnKey: string) => {
    e.preventDefault();
    setResizingColumn(columnKey);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!resizingColumn || !containerRef.current) return;

      const delta = e.movementX;
      const newColumns = columns.map(col => {
        if (col.key === resizingColumn) {
          return { ...col, width: Math.max(50, col.width + delta) };
        }
        return col;
      });

      setColumns(newColumns);
      onColumnResize(newColumns);
    };

    const handleMouseUp = () => {
      setResizingColumn(null);
    };

    if (resizingColumn) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [resizingColumn, columns, onColumnResize]);

  const toggleColumn = (columnKey: string) => {
    const newColumns = columns.map(col =>
      col.key === columnKey ? { ...col, visible: !col.visible } : col
    );
    setColumns(newColumns);
    onColumnToggle(newColumns);
  };

  const visibleColumns = columns.filter(col => col.visible);

  return (
    <div ref={containerRef} className={cn('relative overflow-x-auto', className)}>
      {/* Column Settings Button */}
      <div className="absolute top-4 right-4 z-10">
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="p-2 hover:bg-gray-100 rounded-lg transition"
          title="Column Settings"
        >
          <Settings2 size={20} />
        </button>

        {/* Column Settings Menu */}
        {showSettings && (
          <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded-lg shadow-lg p-4 z-20">
            <h3 className="font-semibold mb-3">Visible Columns</h3>
            <div className="space-y-2">
              {columns.map(col => (
                <label key={col.key} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={col.visible}
                    onChange={() => toggleColumn(col.key)}
                    className="rounded"
                  />
                  <span className="text-sm">{col.header}</span>
                </label>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            {visibleColumns.map((col, idx) => (
              <th
                key={col.key}
                className="px-4 py-2 text-left text-sm font-semibold relative group"
                style={{ width: `${col.width}px` }}
              >
                {col.header}
                {idx < visibleColumns.length - 1 && (
                  <div
                    onMouseDown={(e) => handleMouseDown(e, col.key)}
                    className={cn(
                      'absolute right-0 top-0 bottom-0 w-1 cursor-col-resize',
                      'bg-blue-400 opacity-0 group-hover:opacity-100 transition-opacity',
                      resizingColumn === col.key && 'opacity-100 bg-blue-600'
                    )}
                  />
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => (
            <tr key={rowIdx} className="border-b border-gray-100 hover:bg-gray-50">
              {visibleColumns.map(col => (
                <td
                  key={col.key}
                  className="px-4 py-3 text-sm"
                  style={{ width: `${col.width}px` }}
                >
                  {row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
