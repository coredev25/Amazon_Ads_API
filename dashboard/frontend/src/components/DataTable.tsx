'use client';

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { ChevronUp, ChevronDown, ChevronsUpDown, Columns, GripVertical, X } from 'lucide-react';
import { cn } from '@/utils/helpers';

interface Column<T> {
  key: string;
  header: string;
  width?: string | number;
  sortable?: boolean;
  render?: (value: T[keyof T], row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T extends Record<string, unknown>> {
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
  showToolbar?: boolean;
  toolbarLeft?: React.ReactNode;
  toolbarRight?: React.ReactNode;
  onColumnsClick?: () => void;
  renderColumnsButton?: (onClick: () => void) => React.ReactNode;
  columnModalOpen?: boolean;
  onColumnModalClose?: () => void;
}

export default function DataTable<T extends Record<string, unknown>>({
  data,
  columns,
  keyField,
  onRowClick,
  selectedRows,
  onSelectRow,
  enableSelection = false,
  loading = false,
  emptyMessage = 'No data available',
  className,
  columnLayout,
  onColumnLayoutChange,
  showToolbar = false,
  toolbarLeft,
  toolbarRight,
  onColumnsClick,
  renderColumnsButton,
  columnModalOpen,
  onColumnModalClose,
}: DataTableProps<T>) {
  const [sortConfig, setSortConfig] = useState<{
    key: string;
    direction: 'asc' | 'desc';
  } | null>(null);
  const [internalShowColumnModal, setInternalShowColumnModal] = useState(false);
  
  // Use controlled or internal state for modal
  const showColumnModal = columnModalOpen !== undefined ? columnModalOpen : internalShowColumnModal;
  const setShowColumnModal = (value: boolean) => {
    if (onColumnModalClose && !value) {
      onColumnModalClose();
    } else if (columnModalOpen === undefined) {
      setInternalShowColumnModal(value);
    }
  };
  const [draggedColumn, setDraggedColumn] = useState<string | null>(null);
  const [modalDraggedColumn, setModalDraggedColumn] = useState<string | null>(null);
  const [modalDragOverColumn, setModalDragOverColumn] = useState<string | null>(null);
  const [resizingColumn, setResizingColumn] = useState<string | null>(null);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const [columnVisibility, setColumnVisibility] = useState<Record<string, boolean>>({});
  const [columnOrder, setColumnOrder] = useState<string[]>(columns.map(c => c.key));
  const tableRef = useRef<HTMLTableElement>(null);

  // Initialize from props or defaults
  useEffect(() => {
    if (columnLayout) {
      setColumnVisibility(columnLayout.visibility);
      setColumnOrder(columnLayout.order.length > 0 ? columnLayout.order : columns.map(c => c.key));
      setColumnWidths(columnLayout.widths);
    } else {
      setColumnVisibility(columns.reduce((acc, col) => ({ ...acc, [col.key]: true }), {}));
      setColumnOrder(columns.map(c => c.key));
      setColumnWidths(columns.reduce((acc, col) => {
        const defaultWidth = typeof col.width === 'number' ? col.width : 
                            typeof col.width === 'string' ? parseInt(col.width) || 150 : 150;
        return { ...acc, [col.key]: defaultWidth };
      }, {}));
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

  const sortedData = useMemo(() => {
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

  const getSortIcon = (key: string) => {
    if (sortConfig?.key !== key) {
      return <ChevronsUpDown className="w-4 h-4 text-gray-500" />;
    }
    return sortConfig.direction === 'asc' ? (
      <ChevronUp className="w-4 h-4 text-amazon-orange" />
    ) : (
      <ChevronDown className="w-4 h-4 text-amazon-orange" />
    );
  };

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

  const handleModalColumnDrop = (targetColumnKey: string) => {
    if (!modalDraggedColumn || modalDraggedColumn === targetColumnKey) {
      setModalDraggedColumn(null);
      setModalDragOverColumn(null);
      return;
    }

    const newOrder = [...columnOrder];
    const draggedIndex = newOrder.indexOf(modalDraggedColumn);
    const targetIndex = newOrder.indexOf(targetColumnKey);

    newOrder.splice(draggedIndex, 1);
    newOrder.splice(targetIndex, 0, modalDraggedColumn);

    setColumnOrder(newOrder);
    setModalDraggedColumn(null);
    setModalDragOverColumn(null);
  };

  const handleColumnResize = (columnKey: string, newWidth: number) => {
    setColumnWidths(prev => ({
      ...prev,
      [columnKey]: Math.max(100, newWidth),
    }));
  };

  // Get visible and ordered columns
  const visibleColumns = columnOrder
    .map(key => columns.find(c => c.key === key))
    .filter((col): col is Column<T> => col !== undefined && columnVisibility[col.key] !== false);

  if (loading) {
    return (
      <div className={cn('card overflow-hidden', className)}>
        <div className="animate-pulse">
          <div className="h-12 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" />
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="h-14 border-b border-gray-200/50 dark:border-gray-700/50 flex items-center px-4 gap-4"
            >
              {columns.map((_, j) => (
                <div
                  key={j}
                  className="h-4 bg-gray-200 dark:bg-gray-700 rounded flex-1"
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className={cn('card p-12 text-center', className)}>
        <p className="text-gray-600 dark:text-gray-400">{emptyMessage}</p>
      </div>
    );
  }

  // Get ordered columns for modal (all columns, not just visible)
  const orderedColumnsForModal = columnOrder
    .map(key => columns.find(c => c.key === key))
    .filter((col): col is Column<T> => col !== undefined);

  const handleColumnsClick = () => {
    if (onColumnsClick) {
      onColumnsClick();
    } else {
      setShowColumnModal(true);
    }
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Toolbar */}
      {showToolbar && (
        <div className="card p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {toolbarLeft}
            </div>
            <div className="flex items-center gap-2">
              {toolbarRight}
              {renderColumnsButton ? (
                renderColumnsButton(handleColumnsClick)
              ) : (
                <button
                  onClick={handleColumnsClick}
                  className="btn btn-sm btn-secondary flex items-center gap-2"
                  title="Manage Columns"
                >
                  <Columns className="w-4 h-4" />
                  Columns
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Column Picker Button (only shown if toolbar is not enabled) */}
      {!showToolbar && (
        <div className="flex justify-end">
          <button
            onClick={handleColumnsClick}
            className="btn btn-sm btn-secondary"
            title="Manage Columns"
          >
            <Columns className="w-4 h-4" />
            Columns
          </button>
        </div>
      )}

      {/* Column Management Modal */}
      {showColumnModal && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowColumnModal(false);
            }
          }}
        >
          <div className="card p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto bg-white dark:bg-gray-800">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Manage Columns</h3>
              <button
                onClick={() => {
                  setShowColumnModal(false);
                }}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
            
            <div className="space-y-3">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Drag columns to reorder, and toggle checkboxes to show/hide columns.
              </p>
              
              {orderedColumnsForModal.map((column) => {
                const columnKey = column.key;
                const isVisible = columnVisibility[columnKey] !== false;
                
                return (
                  <div
                    key={columnKey}
                    draggable
                    onDragStart={() => setModalDraggedColumn(columnKey)}
                    onDragOver={(e) => {
                      e.preventDefault();
                      setModalDragOverColumn(columnKey);
                    }}
                    onDragLeave={() => {
                      setModalDragOverColumn(null);
                    }}
                    onDrop={(e) => {
                      e.preventDefault();
                      handleModalColumnDrop(columnKey);
                    }}
                    className={cn(
                      'flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700',
                      'hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-move',
                      modalDraggedColumn === columnKey && 'opacity-50',
                      modalDragOverColumn === columnKey && modalDraggedColumn !== columnKey && 'opacity-50 bg-gray-100 dark:bg-gray-700'
                    )}
                  >
                    <GripVertical className="w-5 h-5 text-gray-400 flex-shrink-0" />
                    <label className="flex items-center gap-2 flex-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isVisible}
                        onChange={() => toggleColumnVisibility(columnKey)}
                        onClick={(e) => e.stopPropagation()}
                        className="rounded accent-amazon-orange w-4 h-4"
                      />
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {column.header}
                      </span>
                    </label>
                  </div>
                );
              })}
            </div>
            
            <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setShowColumnModal(false)}
                className="btn btn-secondary"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden border border-gray-200 dark:border-gray-700">
        <div className="overflow-x-auto max-w-full">
          <table ref={tableRef} className="data-table min-w-full border-collapse">
            <thead>
              <tr>
                {enableSelection && (
                  <th className="w-12 border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 py-3">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
                      onChange={(e) => {
                        if (e.target.checked) {
                          sortedData.forEach(row => {
                            const rowId = row[keyField] as string | number;
                            onSelectRow?.(rowId);
                          });
                        } else {
                          selectedRows?.forEach(id => onSelectRow?.(id));
                        }
                      }}
                    />
                  </th>
                )}
                {visibleColumns.map((column) => {
                  const width = columnWidths[column.key] || 
                               (typeof column.width === 'number' ? column.width : 
                                typeof column.width === 'string' ? parseInt(column.width) || 150 : 150);
                  
                  return (
                    <th
                      key={column.key}
                      style={{ width: `${width}px`, minWidth: `${width}px`, position: 'relative' }}
                      className={cn(
                        'border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 py-3 text-left',
                        column.sortable && 'cursor-pointer hover:text-gray-900 dark:hover:text-white',
                        column.className
                      )}
                      draggable
                      onDragStart={() => handleColumnDragStart(column.key)}
                      onDragOver={(e) => {
                        e.preventDefault();
                        e.currentTarget.style.opacity = '0.5';
                      }}
                      onDragLeave={(e) => {
                        e.currentTarget.style.opacity = '1';
                      }}
                      onDrop={(e) => {
                        e.currentTarget.style.opacity = '1';
                        handleColumnDrop(column.key);
                      }}
                    >
                      <div className="flex items-center gap-2">
                        <GripVertical className="w-4 h-4 text-gray-400 cursor-move flex-shrink-0" />
                        <button
                          onClick={() => column.sortable && handleSort(column.key)}
                          className="flex-1 text-left flex items-center gap-2"
                        >
                          {column.header}
                          {column.sortable && getSortIcon(column.key)}
                        </button>
                        <div
                          className="w-1 h-6 bg-gray-300 dark:bg-gray-600 cursor-col-resize hover:bg-amazon-orange flex-shrink-0 transition-colors"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            setResizingColumn(column.key);
                            const startX = e.clientX;
                            const startWidth = width;

                            const handleMouseMove = (e: MouseEvent) => {
                              const diff = e.clientX - startX;
                              handleColumnResize(column.key, startWidth + diff);
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
            <tbody>
              {sortedData.length === 0 ? (
                <tr>
                  <td
                    colSpan={visibleColumns.length + (enableSelection ? 1 : 0)}
                    className="px-4 py-12 text-center text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700"
                  >
                    {emptyMessage}
                  </td>
                </tr>
              ) : (
                sortedData.map((row, rowIndex) => {
                  const rowId = row[keyField] as string | number;
                  const isSelected = selectedRows?.has(rowId);

                  return (
                    <tr
                      key={rowId}
                      onClick={() => onRowClick?.(row)}
                      className={cn(
                        'border-b border-gray-200 dark:border-gray-700',
                        onRowClick && 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50',
                        isSelected && 'bg-amazon-orange/10',
                        rowIndex === sortedData.length - 1 && 'border-b-0'
                      )}
                    >
                      {enableSelection && (
                        <td className="border-r border-gray-200 dark:border-gray-700 px-4 py-3">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => onSelectRow?.(rowId)}
                            onClick={(e) => e.stopPropagation()}
                            className="rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
                          />
                        </td>
                      )}
                      {visibleColumns.map((column, colIndex) => {
                        const width = columnWidths[column.key] || 
                                     (typeof column.width === 'number' ? column.width : 
                                      typeof column.width === 'string' ? parseInt(column.width) || 150 : 150);
                        
                        return (
                          <td 
                            key={column.key} 
                            className={cn(
                              'border-r border-gray-200 dark:border-gray-700 px-4 py-3',
                              colIndex === visibleColumns.length - 1 && 'border-r-0',
                              column.className
                            )}
                            style={{ width: `${width}px`, minWidth: `${width}px` }}
                          >
                            {column.render
                              ? column.render(row[column.key as keyof T], row)
                              : String(row[column.key as keyof T] ?? '-')}
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

