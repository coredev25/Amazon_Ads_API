'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Check, X, Edit2, Save, Columns, GripVertical, MoreVertical } from 'lucide-react';
import { Sparkline } from './Charts';
import { cn, formatCurrency, formatAcos } from '@/utils/helpers';

interface Column<T> {
  key: keyof T | string;
  header: string;
  width?: number;
  sortable?: boolean;
  editable?: boolean;
  render?: (value: T[keyof T], row: T, isEditing: boolean, onSave: (value: any) => void) => React.ReactNode;
  className?: string;
  showSparkline?: boolean;
  sparklineData?: (row: T) => number[];
}

interface SmartGridProps<T extends Record<string, unknown>> {
  data: T[];
  columns: Column<T>[];
  keyField: keyof T;
  onRowClick?: (row: T) => void;
  selectedRows?: Set<string | number>;
  onSelectRow?: (id: string | number) => void;
  enableSelection?: boolean;
  loading?: boolean;
  emptyMessage?: string;
  className?: string;
  onCellEdit?: (row: T, column: string, newValue: any) => Promise<void>;
  onBulkAction?: (action: string, selectedIds: (string | number)[]) => Promise<void>;
  columnLayout?: {
    visibility: Record<string, boolean>;
    order: string[];
    widths: Record<string, number>;
  };
  onColumnLayoutChange?: (layout: {
    visibility: Record<string, boolean>;
    order: string[];
    widths: Record<string, number>;
  }) => void;
}

export default function SmartGrid<T extends Record<string, unknown>>({
  data,
  columns,
  keyField,
  onRowClick,
  selectedRows = new Set(),
  onSelectRow,
  enableSelection = false,
  loading = false,
  emptyMessage = 'No data available',
  className,
  onCellEdit,
  onBulkAction,
  columnLayout,
  onColumnLayoutChange,
}: SmartGridProps<T>) {
  const [editingCell, setEditingCell] = useState<{ rowId: string | number; column: string } | null>(null);
  const [editValue, setEditValue] = useState<any>('');
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);
  const [showColumnPicker, setShowColumnPicker] = useState(false);
  const [draggedColumn, setDraggedColumn] = useState<string | null>(null);
  const [resizingColumn, setResizingColumn] = useState<string | null>(null);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const [columnVisibility, setColumnVisibility] = useState<Record<string, boolean>>({});
  const [columnOrder, setColumnOrder] = useState<string[]>(columns.map(c => String(c.key)));

  const inputRef = useRef<HTMLInputElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);

  // Initialize from props or defaults
  useEffect(() => {
    if (columnLayout) {
      setColumnVisibility(columnLayout.visibility);
      setColumnOrder(columnLayout.order.length > 0 ? columnLayout.order : columns.map(c => String(c.key)));
      setColumnWidths(columnLayout.widths);
    } else {
      setColumnVisibility(columns.reduce((acc, col) => ({ ...acc, [String(col.key)]: true }), {}));
      setColumnOrder(columns.map(c => String(c.key)));
      setColumnWidths(columns.reduce((acc, col) => ({ ...acc, [String(col.key)]: col.width || 150 }), {}));
    }
  }, [columns, columnLayout]);

  // Save layout changes
  useEffect(() => {
    if (onColumnLayoutChange) {
      onColumnLayoutChange({
        visibility: columnVisibility,
        order: columnOrder,
        widths: columnWidths,
      });
    }
  }, [columnVisibility, columnOrder, columnWidths, onColumnLayoutChange]);

  const handleSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig?.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const sortedData = React.useMemo(() => {
    if (!sortConfig) return data;

    return [...data].sort((a, b) => {
      const aVal = a[sortConfig.key as keyof T];
      const bVal = b[sortConfig.key as keyof T];

      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
      }

      const aStr = String(aVal);
      const bStr = String(bVal);
      return sortConfig.direction === 'asc'
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr);
    });
  }, [data, sortConfig]);

  const handleCellClick = (row: T, column: Column<T>) => {
    if (!column.editable || !onCellEdit) return;
    
    const rowId = String(row[keyField]);
    setEditingCell({ rowId, column: String(column.key) });
    setEditValue(row[column.key as keyof T]);
  };

  const handleCellSave = async () => {
    if (!editingCell || !onCellEdit) return;

    const row = data.find(r => String(r[keyField]) === editingCell.rowId);
    if (row) {
      try {
        await onCellEdit(row, editingCell.column, editValue);
        setEditingCell(null);
        setEditValue('');
      } catch (error) {
        console.error('Failed to save cell:', error);
      }
    }
  };

  const handleCellCancel = () => {
    setEditingCell(null);
    setEditValue('');
  };

  useEffect(() => {
    if (editingCell && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingCell]);

  const toggleColumnVisibility = (columnKey: string) => {
    setColumnVisibility(prev => ({
      ...prev,
      [columnKey]: !prev[columnKey],
    }));
  };

  const handleColumnDragStart = (columnKey: string) => {
    setDraggedColumn(columnKey);
  };

  const handleColumnDrop = (targetColumnKey: string) => {
    if (!draggedColumn || draggedColumn === targetColumnKey) return;

    const newOrder = [...columnOrder];
    const draggedIndex = newOrder.indexOf(draggedColumn);
    const targetIndex = newOrder.indexOf(targetColumnKey);

    newOrder.splice(draggedIndex, 1);
    newOrder.splice(targetIndex, 0, draggedColumn);

    setColumnOrder(newOrder);
    setDraggedColumn(null);
  };

  const handleColumnResize = (columnKey: string, newWidth: number) => {
    setColumnWidths(prev => ({
      ...prev,
      [columnKey]: Math.max(100, newWidth),
    }));
  };

  // Get visible and ordered columns
  const visibleColumns = columnOrder
    .map(key => columns.find(c => String(c.key) === key))
    .filter((col): col is Column<T> => col !== undefined && columnVisibility[String(col.key)] !== false);

  const allSelected = selectedRows.size > 0 && selectedRows.size === data.length;
  const someSelected = selectedRows.size > 0 && selectedRows.size < data.length;

  if (loading) {
    return (
      <div className={cn('card overflow-hidden', className)}>
        <div className="animate-pulse p-8">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4" />
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-200 dark:bg-gray-700 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {enableSelection && selectedRows.size > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {selectedRows.size} selected
              </span>
              {onBulkAction && (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => onBulkAction('pause', Array.from(selectedRows))}
                    className="btn btn-sm btn-secondary"
                  >
                    Pause
                  </button>
                  <button
                    onClick={() => onBulkAction('enable', Array.from(selectedRows))}
                    className="btn btn-sm btn-secondary"
                  >
                    Enable
                  </button>
                  <button
                    onClick={() => onBulkAction('adjust_bids', Array.from(selectedRows))}
                    className="btn btn-sm btn-secondary"
                  >
                    Adjust Bids
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowColumnPicker(!showColumnPicker)}
            className="btn btn-sm btn-secondary"
          >
            <Columns className="w-4 h-4" />
            Columns
          </button>
        </div>
      </div>

      {/* Column Picker */}
      {showColumnPicker && (
        <div className="card p-4">
          <h3 className="text-sm font-semibold mb-3">Column Visibility</h3>
          <div className="space-y-2">
            {columns.map(column => (
              <label key={String(column.key)} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility[String(column.key)] !== false}
                  onChange={() => toggleColumnVisibility(String(column.key))}
                  className="rounded accent-amazon-orange"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">{column.header}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table ref={tableRef} className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
              <tr>
                {enableSelection && (
                  <th className="px-4 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      ref={(el) => {
                        if (el) el.indeterminate = someSelected && !allSelected;
                      }}
                      onChange={(e) => {
                        if (e.target.checked) {
                          data.forEach(row => onSelectRow?.(String(row[keyField])));
                        } else {
                          selectedRows.forEach(id => onSelectRow?.(id));
                        }
                      }}
                      className="rounded accent-amazon-orange"
                    />
                  </th>
                )}
                {visibleColumns.map((column) => {
                  const columnKey = String(column.key);
                  const width = columnWidths[columnKey] || column.width || 150;
                  
                  return (
                    <th
                      key={columnKey}
                      className={cn(
                        'px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider',
                        column.className
                      )}
                      style={{ width: `${width}px`, minWidth: `${width}px` }}
                      draggable
                      onDragStart={() => handleColumnDragStart(columnKey)}
                      onDragOver={(e) => {
                        e.preventDefault();
                      }}
                      onDrop={() => handleColumnDrop(columnKey)}
                    >
                      <div className="flex items-center gap-2">
                        <GripVertical className="w-4 h-4 text-gray-400 cursor-move" />
                        <button
                          onClick={() => column.sortable && handleSort(columnKey)}
                          className={cn(
                            'flex-1 text-left',
                            column.sortable && 'hover:text-amazon-orange cursor-pointer'
                          )}
                        >
                          {column.header}
                        </button>
                        <div
                          className="w-1 h-6 bg-gray-300 dark:bg-gray-600 cursor-col-resize hover:bg-amazon-orange"
                          onMouseDown={(e) => {
                            setResizingColumn(columnKey);
                            const startX = e.clientX;
                            const startWidth = width;

                            const handleMouseMove = (e: MouseEvent) => {
                              const diff = e.clientX - startX;
                              handleColumnResize(columnKey, startWidth + diff);
                            };

                            const handleMouseUp = () => {
                              setResizingColumn(null);
                              document.removeEventListener('mousemove', handleMouseMove);
                              document.removeEventListener('mouseup', handleMouseUp);
                            };

                            document.addEventListener('mousemove', handleMouseMove);
                            document.addEventListener('mouseup', handleMouseUp);
                          }}
                        />
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {sortedData.length === 0 ? (
                <tr>
                  <td
                    colSpan={visibleColumns.length + (enableSelection ? 1 : 0)}
                    className="px-4 py-12 text-center text-gray-500 dark:text-gray-400"
                  >
                    {emptyMessage}
                  </td>
                </tr>
              ) : (
                sortedData.map((row) => {
                  const rowId = String(row[keyField]);
                  const isEditing = editingCell?.rowId === rowId;

                  return (
                    <tr
                      key={rowId}
                      onClick={() => !isEditing && onRowClick?.(row)}
                      className={cn(
                        'hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors',
                        selectedRows.has(rowId) && 'bg-amazon-orange/5',
                        isEditing && 'bg-blue-50 dark:bg-blue-900/20'
                      )}
                    >
                      {enableSelection && (
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={selectedRows.has(rowId)}
                            onChange={() => onSelectRow?.(rowId)}
                            onClick={(e) => e.stopPropagation()}
                            className="rounded accent-amazon-orange"
                          />
                        </td>
                      )}
                      {visibleColumns.map((column) => {
                        const columnKey = String(column.key);
                        const value = row[column.key as keyof T];
                        const isCellEditing = isEditing && editingCell?.column === columnKey;
                        const width = columnWidths[columnKey] || column.width || 150;

                        return (
                          <td
                            key={columnKey}
                            className={cn('px-4 py-3', column.className)}
                            style={{ width: `${width}px`, minWidth: `${width}px` }}
                            onClick={() => handleCellClick(row, column)}
                          >
                            {isCellEditing && column.editable ? (
                              <div className="flex items-center gap-2">
                                <input
                                  ref={inputRef}
                                  type={typeof value === 'number' ? 'number' : 'text'}
                                  value={editValue}
                                  onChange={(e) => setEditValue(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      handleCellSave();
                                    } else if (e.key === 'Escape') {
                                      handleCellCancel();
                                    }
                                  }}
                                  className="input flex-1"
                                  onClick={(e) => e.stopPropagation()}
                                />
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleCellSave();
                                  }}
                                  className="p-1 text-green-600 hover:text-green-700"
                                >
                                  <Check className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleCellCancel();
                                  }}
                                  className="p-1 text-red-600 hover:text-red-700"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center gap-2">
                                {column.render ? (
                                  column.render(value, row, false, () => {})
                                ) : (
                                  <span className="text-gray-900 dark:text-white">
                                    {String(value ?? '')}
                                  </span>
                                )}
                                {column.showSparkline && column.sparklineData && (
                                  <div className="ml-auto">
                                    <Sparkline
                                      data={column.sparklineData(row)}
                                      width={60}
                                      height={20}
                                    />
                                  </div>
                                )}
                                {column.editable && (
                                  <Edit2 className="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 ml-auto" />
                                )}
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

