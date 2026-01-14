'use client';

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { 
  Check, X, Edit2, Save, Columns, Filter, 
  Play, Pause, Archive, TrendingUp, TrendingDown, DollarSign,
  Percent, Package, Target, ChevronDown, XCircle, ChevronUp, ChevronsUpDown
} from 'lucide-react';
import { Sparkline } from './Charts';
import { cn, formatCurrency, formatAcos } from '@/utils/helpers';

interface Column<T> {
  key: keyof T | string;
  header: string;
  width?: number;
  sortable?: boolean;
  editable?: boolean;
  filterable?: boolean;
  filterType?: 'number' | 'text' | 'select';
  filterOptions?: string[];
  render?: (value: T[keyof T], row: T, isEditing: boolean, onSave: (value: any) => void) => React.ReactNode;
  className?: string;
  showSparkline?: boolean;
  sparklineData?: (row: T) => number[];
  editType?: 'text' | 'number' | 'currency' | 'status';
  statusOptions?: { value: string; label: string }[];
}

interface SmartGridProps<T extends Record<string, unknown>> {
  data: T[];
  columns: Column<T>[];
  keyField: keyof T;
  onRowClick?: (row: T) => void;
  selectedRows?: Set<string | number>;
  onSelectRow?: (id: string | number) => void;
  onSelectAllRows?: (ids: (string | number)[], select: boolean) => void;
  enableSelection?: boolean;
  loading?: boolean;
  emptyMessage?: string;
  className?: string;
  onCellEdit?: (row: T, column: string, newValue: any) => Promise<void>;
  onBulkAction?: (action: string, selectedIds: (string | number)[], params?: any) => Promise<void>;
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
  statusFilter?: string;
  onStatusFilterChange?: (status: string) => void;
  statusFilterOptions?: { value: string; label: string }[];
  onSaveColumnLayout?: (layout: {
    visibility: Record<string, boolean>;
    order: string[];
    widths: Record<string, number>;
  }) => Promise<void>;
}

export default function SmartGrid<T extends Record<string, unknown>>({
  data,
  columns,
  keyField,
  onRowClick,
  selectedRows = new Set(),
  onSelectRow,
  onSelectAllRows,
  enableSelection = false,
  loading = false,
  emptyMessage = 'No data available',
  className,
  onCellEdit,
  onBulkAction,
  columnLayout,
  onColumnLayoutChange,
  statusFilter = 'all',
  onStatusFilterChange,
  statusFilterOptions = [
    { value: 'all', label: 'All Status' },
    { value: 'enabled', label: 'Enabled' },
    { value: 'paused', label: 'Paused' },
    { value: 'archived', label: 'Archived' },
    { value: 'incomplete', label: 'Incomplete' },
    { value: 'out_of_budget', label: 'Out of Budget' },
  ],
  onSaveColumnLayout,
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
  const [columnFilters, setColumnFilters] = useState<Record<string, { type: string; value: any; operator?: string }>>({});
  const [showFilterMenu, setShowFilterMenu] = useState<string | null>(null);
  const [showBulkActionMenu, setShowBulkActionMenu] = useState(false);
  const [bulkActionParams, setBulkActionParams] = useState<any>({});

  const inputRef = useRef<HTMLInputElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);
  const filterMenuRef = useRef<HTMLDivElement>(null);

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
      const layout = {
        visibility: columnVisibility,
        order: columnOrder,
        widths: columnWidths,
      };
      onColumnLayoutChange(layout);
      
      // Persist to user profile if callback provided
      if (onSaveColumnLayout) {
        onSaveColumnLayout(layout).catch(err => {
          console.error('Failed to save column layout:', err);
        });
      }
    }
  }, [columnVisibility, columnOrder, columnWidths, onColumnLayoutChange, onSaveColumnLayout]);

  // Close filter menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (filterMenuRef.current && !filterMenuRef.current.contains(event.target as Node)) {
        setShowFilterMenu(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig?.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  // Apply filters to data
  const filteredData = useMemo(() => {
    let result = [...data];

    // Apply status filter
    if (statusFilter !== 'all' && onStatusFilterChange) {
      result = result.filter(row => {
        const status = (row as any).status || (row as any).state;
        return status?.toLowerCase() === statusFilter.toLowerCase();
      });
    }

    // Apply column filters
    Object.entries(columnFilters).forEach(([columnKey, filter]) => {
      if (!filter.value) return;
      
      result = result.filter(row => {
        const value = row[columnKey as keyof T];
        if (value === null || value === undefined) return false;

        if (filter.type === 'number') {
          const numValue = typeof value === 'number' ? value : parseFloat(String(value));
          const filterNum = parseFloat(filter.value);
          
          if (filter.operator === '>') return numValue > filterNum;
          if (filter.operator === '<') return numValue < filterNum;
          if (filter.operator === '>=') return numValue >= filterNum;
          if (filter.operator === '<=') return numValue <= filterNum;
          if (filter.operator === '=') return numValue === filterNum;
          return true;
        } else if (filter.type === 'text') {
          return String(value).toLowerCase().includes(String(filter.value).toLowerCase());
        } else if (filter.type === 'select') {
          return String(value) === String(filter.value);
        }

        return String(value) === String(filter.value);
      });
    });

    return result;
  }, [data, statusFilter, columnFilters, onStatusFilterChange]);

  const sortedData = useMemo(() => {
    if (!sortConfig) return filteredData;

    return [...filteredData].sort((a, b) => {
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
  }, [filteredData, sortConfig]);

  const handleCellClick = (row: T, column: Column<T>) => {
    if (!column.editable || !onCellEdit) return;
    
    const rowId = String(row[keyField]);
    setEditingCell({ rowId, column: String(column.key) });
    
    // Initialize edit value based on type
    const rawValue = row[column.key as keyof T];
    if (column.editType === 'currency' && typeof rawValue === 'number') {
      setEditValue(rawValue.toFixed(2));
    } else {
      setEditValue(rawValue);
    }
  };

  const handleCellSave = async () => {
    if (!editingCell || !onCellEdit) return;

    const row = data.find(r => String(r[keyField]) === editingCell.rowId);
    if (row) {
      try {
        let finalValue = editValue;
        
        // Convert based on edit type
        const column = columns.find(c => String(c.key) === editingCell.column);
        if (column?.editType === 'currency' || column?.editType === 'number') {
          finalValue = parseFloat(editValue) || 0;
        }
        
        await onCellEdit(row, editingCell.column, finalValue);
        setEditingCell(null);
        setEditValue('');
      } catch (error) {
        console.error('Failed to save cell:', error);
        // Keep editing state on error so user can retry
      }
    }
  };

  const handleCellCancel = () => {
    setEditingCell(null);
    setEditValue('');
  };

  const handleStatusToggle = async (row: T, newStatus: string) => {
    if (!onCellEdit) return;
    
    try {
      await onCellEdit(row, 'status', newStatus);
    } catch (error) {
      console.error('Failed to update status:', error);
    }
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

  const handleFilterChange = (columnKey: string, filter: { type: string; value: any; operator?: string }) => {
    setColumnFilters(prev => {
      if (!filter.value) {
        const newFilters = { ...prev };
        delete newFilters[columnKey];
        return newFilters;
      }
      return { ...prev, [columnKey]: filter };
    });
    setShowFilterMenu(null);
  };

  const clearFilter = (columnKey: string) => {
    setColumnFilters(prev => {
      const newFilters = { ...prev };
      delete newFilters[columnKey];
      return newFilters;
    });
  };

  // Get visible and ordered columns
  const visibleColumns = columnOrder
    .map(key => columns.find(c => String(c.key) === key))
    .filter((col): col is Column<T> => col !== undefined && columnVisibility[String(col.key)] !== false);

  // Calculate selection state based on filtered/sorted data
  const selectableRowIds = new Set(sortedData.map(row => String(row[keyField])));
  const selectedCount = Array.from(selectedRows).filter(id => selectableRowIds.has(String(id))).length;
  const allSelected = sortedData.length > 0 && selectedCount === sortedData.length && selectedCount > 0;
  const someSelected = selectedCount > 0 && selectedCount < sortedData.length;

  // Bulk action handlers
  const handleBulkAction = async (action: string, params?: any) => {
    if (!onBulkAction || selectedRows.size === 0) return;
    
    try {
      await onBulkAction(action, Array.from(selectedRows), params);
      setShowBulkActionMenu(false);
      setBulkActionParams({});
    } catch (error) {
      console.error('Bulk action failed:', error);
    }
  };

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
    <div className={cn('space-y-4 relative', className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Status Filter */}
          {onStatusFilterChange && (
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => onStatusFilterChange(e.target.value)}
                className="select text-sm"
              >
                {statusFilterOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
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

      {/* Floating Action Bar */}
      {enableSelection && selectedRows.size > 0 && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50">
          <div className="card p-4 shadow-2xl border-2 border-amazon-orange/20 bg-white dark:bg-gray-800">
            <div className="flex items-center gap-4">
              <span className="text-sm font-semibold text-gray-900 dark:text-white">
                {selectedRows.size} selected
              </span>
              <div className="flex items-center gap-2 border-l border-gray-200 dark:border-gray-700 pl-4">
                <button
                  onClick={() => handleBulkAction('pause')}
                  className="btn btn-sm btn-secondary flex items-center gap-1"
                >
                  <Pause className="w-3 h-3" />
                  Pause
                </button>
                <button
                  onClick={() => handleBulkAction('enable')}
                  className="btn btn-sm btn-secondary flex items-center gap-1"
                >
                  <Play className="w-3 h-3" />
                  Enable
                </button>
                <button
                  onClick={() => handleBulkAction('archive')}
                  className="btn btn-sm btn-secondary flex items-center gap-1"
                >
                  <Archive className="w-3 h-3" />
                  Archive
                </button>
                <div className="relative">
                  <button
                    onClick={() => setShowBulkActionMenu(!showBulkActionMenu)}
                    className="btn btn-sm btn-secondary flex items-center gap-1"
                  >
                    <DollarSign className="w-3 h-3" />
                    Adjust Bids
                    <ChevronDown className="w-3 h-3" />
                  </button>
                  {showBulkActionMenu && (
                    <div className="absolute bottom-full mb-2 left-0 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-2 min-w-[200px]">
                      <div className="space-y-2">
                        <button
                          onClick={() => {
                            const percent = prompt('Increase by percentage:', '10');
                            if (percent) {
                              handleBulkAction('adjust_bids', { type: 'increase', percent: parseFloat(percent) });
                            }
                          }}
                          className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded flex items-center gap-2"
                        >
                          <TrendingUp className="w-4 h-4" />
                          Increase by %
                        </button>
                        <button
                          onClick={() => {
                            const percent = prompt('Decrease by percentage:', '10');
                            if (percent) {
                              handleBulkAction('adjust_bids', { type: 'decrease', percent: parseFloat(percent) });
                            }
                          }}
                          className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded flex items-center gap-2"
                        >
                          <TrendingDown className="w-4 h-4" />
                          Decrease by %
                        </button>
                        <button
                          onClick={() => {
                            const amount = prompt('Set bid to:', '');
                            if (amount) {
                              handleBulkAction('adjust_bids', { type: 'set', amount: parseFloat(amount) });
                            }
                          }}
                          className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded flex items-center gap-2"
                        >
                          <DollarSign className="w-4 h-4" />
                          Set to $
                        </button>
                      </div>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => {
                    const amount = prompt('Adjust budgets by amount:', '');
                    if (amount) {
                      handleBulkAction('adjust_budgets', { amount: parseFloat(amount) });
                    }
                  }}
                  className="btn btn-sm btn-secondary flex items-center gap-1"
                >
                  <DollarSign className="w-3 h-3" />
                  Adjust Budgets
                </button>
                <button
                  onClick={() => {
                    const portfolioId = prompt('Portfolio ID:', '');
                    if (portfolioId) {
                      handleBulkAction('move_to_portfolio', { portfolioId: parseInt(portfolioId) });
                    }
                  }}
                  className="btn btn-sm btn-secondary flex items-center gap-1"
                >
                  <Package className="w-3 h-3" />
                  Move to Portfolio
                </button>
                <div className="relative">
                  <button
                    onClick={() => {
                      const strategy = prompt('Bidding Strategy (dynamic_down/up_and_down/fixed):', '');
                      if (strategy) {
                        handleBulkAction('apply_bidding_strategy', { strategy });
                      }
                    }}
                    className="btn btn-sm btn-secondary flex items-center gap-1"
                  >
                    <Target className="w-3 h-3" />
                    Bidding Strategy
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table ref={tableRef} className="w-full border-collapse">
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
                        const shouldSelect = e.target.checked;
                        
                        // Collect all row IDs that need to be changed
                        const rowIdsToChange: (string | number)[] = [];
                        
                        sortedData.forEach(row => {
                          const rowId = String(row[keyField]);
                          const isCurrentlySelected = selectedRows.has(rowId);
                          
                          // Collect IDs that need state change
                          if (shouldSelect && !isCurrentlySelected) {
                            rowIdsToChange.push(rowId);
                          } else if (!shouldSelect && isCurrentlySelected) {
                            rowIdsToChange.push(rowId);
                          }
                        });
                        
                        // Use batch selection if available
                        if (onSelectAllRows && rowIdsToChange.length > 0) {
                          // Batch operation - select/deselect all at once
                          onSelectAllRows(rowIdsToChange, shouldSelect);
                        } else if (onSelectRow && rowIdsToChange.length > 0) {
                          // Fallback: batch process all rows using React's automatic batching
                          // React 18+ automatically batches state updates in event handlers
                          // Process all selections in a single batch
                          rowIdsToChange.forEach((rowId) => {
                            onSelectRow(rowId);
                          });
                        }
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded accent-amazon-orange cursor-pointer"
                      title={allSelected ? "Deselect all" : "Select all"}
                    />
                  </th>
                )}
                {visibleColumns.map((column, index) => {
                  const columnKey = String(column.key);
                  const width = columnWidths[columnKey] || column.width || 150;
                  const hasFilter = columnFilters[columnKey];
                  const isLastColumn = index === visibleColumns.length - 1;
                  
                  return (
                    <th
                      key={columnKey}
                      className={cn(
                        'px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider relative',
                        column.className,
                        !isLastColumn && 'border-r border-gray-200 dark:border-gray-700'
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
                        <button
                          onClick={() => column.sortable && handleSort(columnKey)}
                          className={cn(
                            'flex-1 text-left flex items-center gap-1',
                            column.sortable && 'hover:text-amazon-orange cursor-pointer'
                          )}
                        >
                          {column.header}
                          {column.sortable && (
                            <span className="text-gray-400">
                              {sortConfig?.key === columnKey ? (
                                sortConfig.direction === 'asc' ? (
                                  <ChevronUp className="w-3 h-3" />
                                ) : (
                                  <ChevronDown className="w-3 h-3" />
                                )
                              ) : (
                                <ChevronsUpDown className="w-3 h-3" />
                              )}
                            </span>
                          )}
                        </button>
                        {column.filterable && (
                          <div className="relative" ref={showFilterMenu === columnKey ? filterMenuRef : null}>
                            <button
                              onClick={() => setShowFilterMenu(showFilterMenu === columnKey ? null : columnKey)}
                              className={cn(
                                'p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700',
                                hasFilter && 'text-amazon-orange'
                              )}
                            >
                              <Filter className="w-3 h-3" />
                            </button>
                            {showFilterMenu === columnKey && (
                              <div className="absolute top-full right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 z-50 min-w-[200px]">
                                {column.filterType === 'number' ? (
                                  <div className="space-y-2">
                                    <select
                                      value={columnFilters[columnKey]?.operator || '>'}
                                      onChange={(e) => {
                                        const current = columnFilters[columnKey];
                                        handleFilterChange(columnKey, {
                                          type: 'number',
                                          operator: e.target.value,
                                          value: current?.value || '',
                                        });
                                      }}
                                      className="select text-sm w-full"
                                    >
                                      <option value=">">Greater than</option>
                                      <option value="<">Less than</option>
                                      <option value=">=">Greater or equal</option>
                                      <option value="<=">Less or equal</option>
                                      <option value="=">Equal to</option>
                                    </select>
                                    <input
                                      type="number"
                                      placeholder="Value"
                                      value={columnFilters[columnKey]?.value || ''}
                                      onChange={(e) => {
                                        handleFilterChange(columnKey, {
                                          type: 'number',
                                          operator: columnFilters[columnKey]?.operator || '>',
                                          value: e.target.value,
                                        });
                                      }}
                                      className="input text-sm w-full"
                                    />
                                  </div>
                                ) : column.filterType === 'select' ? (
                                  <select
                                    value={columnFilters[columnKey]?.value || ''}
                                    onChange={(e) => {
                                      handleFilterChange(columnKey, {
                                        type: 'select',
                                        value: e.target.value,
                                      });
                                    }}
                                    className="select text-sm w-full"
                                  >
                                    <option value="">All</option>
                                    {column.filterOptions?.map(opt => (
                                      <option key={opt} value={opt}>{opt}</option>
                                    ))}
                                  </select>
                                ) : (
                                  <input
                                    type="text"
                                    placeholder="Filter..."
                                    value={columnFilters[columnKey]?.value || ''}
                                    onChange={(e) => {
                                      handleFilterChange(columnKey, {
                                        type: 'text',
                                        value: e.target.value,
                                      });
                                    }}
                                    className="input text-sm w-full"
                                  />
                                )}
                                {hasFilter && (
                                  <button
                                    onClick={() => clearFilter(columnKey)}
                                    className="mt-2 text-xs text-red-600 hover:text-red-700 flex items-center gap-1"
                                  >
                                    <XCircle className="w-3 h-3" />
                                    Clear filter
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      {/* Resizable border - entire right border is draggable */}
                      {!isLastColumn && (
                        <div
                          className="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:w-1.5 hover:bg-amazon-orange transition-all"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
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
                          style={{ 
                            zIndex: 10,
                            userSelect: 'none',
                            marginRight: '-1px'
                          }}
                        />
                      )}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700 border-collapse">
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
                        'hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group',
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
                      {visibleColumns.map((column, colIndex) => {
                        const columnKey = String(column.key);
                        const value = row[column.key as keyof T];
                        const isCellEditing = isEditing && editingCell?.column === columnKey;
                        const width = columnWidths[columnKey] || column.width || 150;
                        const isLastColumn = colIndex === visibleColumns.length - 1;

                        return (
                          <td
                            key={columnKey}
                            className={cn(
                              'px-4 py-3 relative',
                              column.className,
                              !isLastColumn && 'border-r border-gray-200 dark:border-gray-700'
                            )}
                            style={{ width: `${width}px`, minWidth: `${width}px` }}
                            onClick={() => column.editable && handleCellClick(row, column)}
                          >
                            {isCellEditing && column.editable ? (
                              <div className="flex items-center gap-2">
                                {column.editType === 'status' && column.statusOptions ? (
                                  <select
                                    ref={inputRef as any}
                                    value={editValue}
                                    onChange={(e) => setEditValue(e.target.value)}
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter') {
                                        handleCellSave();
                                      } else if (e.key === 'Escape') {
                                        handleCellCancel();
                                      }
                                    }}
                                    className="select flex-1"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {column.statusOptions.map(opt => (
                                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                  </select>
                                ) : (
                                  <input
                                    ref={inputRef}
                                    type={column.editType === 'currency' || column.editType === 'number' ? 'number' : 'text'}
                                    step={column.editType === 'currency' ? '0.01' : undefined}
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
                                    placeholder={column.editType === 'currency' ? '$0.00' : ''}
                                  />
                                )}
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
                                {column.editType === 'status' && column.editable ? (
                                  <div className="flex items-center gap-2">
                                    <select
                                      value={String(value || '')}
                                      onChange={(e) => {
                                        e.stopPropagation();
                                        handleStatusToggle(row, e.target.value);
                                      }}
                                      className="select text-sm"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {column.statusOptions?.map(opt => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                      ))}
                                    </select>
                                  </div>
                                ) : column.render ? (
                                  column.render(value, row, false, () => {})
                                ) : (
                                  <span className="text-gray-900 dark:text-white">
                                    {column.editType === 'currency' && typeof value === 'number'
                                      ? formatCurrency(value)
                                      : String(value ?? '')}
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
                                {column.editable && column.editType !== 'status' && (
                                  <Edit2 className="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 ml-auto" />
                                )}
                              </div>
                            )}
                            {/* Resizable border for cells - entire right border is draggable */}
                            {!isLastColumn && (
                              <div
                                className="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:w-1.5 hover:bg-amazon-orange transition-all"
                                onMouseDown={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
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
                                style={{ 
                                  zIndex: 10,
                                  userSelect: 'none',
                                  marginRight: '-1px'
                                }}
                              />
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
