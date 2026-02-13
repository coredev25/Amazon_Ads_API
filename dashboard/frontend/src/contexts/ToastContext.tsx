'use client';

import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X, Loader2 } from 'lucide-react';
import { cn } from '@/utils/helpers';

// ============================================================================
// Types
// ============================================================================

export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number; // ms, 0 = persistent
  amazonSynced?: boolean; // shows Amazon sync badge
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
  success: (title: string, message?: string, opts?: Partial<Toast>) => string;
  error: (title: string, message?: string, opts?: Partial<Toast>) => string;
  warning: (title: string, message?: string, opts?: Partial<Toast>) => string;
  info: (title: string, message?: string, opts?: Partial<Toast>) => string;
  loading: (title: string, message?: string) => string;
  dismiss: (id: string) => void;
  /** Update an existing toast (e.g. turn a loading toast into success) */
  update: (id: string, updates: Partial<Omit<Toast, 'id'>>) => void;
}

// ============================================================================
// Context
// ============================================================================

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

// ============================================================================
// Provider
// ============================================================================

let toastCounter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const removeToast = useCallback((id: string) => {
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (toast: Omit<Toast, 'id'>): string => {
      const id = `toast-${++toastCounter}-${Date.now()}`;
      const duration = toast.duration ?? (toast.type === 'error' ? 6000 : toast.type === 'loading' ? 0 : 4000);
      const newToast: Toast = { ...toast, id, duration };

      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        const timer = setTimeout(() => removeToast(id), duration);
        timers.current.set(id, timer);
      }

      return id;
    },
    [removeToast]
  );

  const update = useCallback(
    (id: string, updates: Partial<Omit<Toast, 'id'>>) => {
      setToasts((prev) =>
        prev.map((t) => {
          if (t.id !== id) return t;
          const updated = { ...t, ...updates };
          // If changing from loading to something else, auto-dismiss
          if (t.type === 'loading' && updates.type && updates.type !== 'loading') {
            const dur = updates.duration ?? (updates.type === 'error' ? 6000 : 4000);
            const oldTimer = timers.current.get(id);
            if (oldTimer) clearTimeout(oldTimer);
            if (dur > 0) {
              const timer = setTimeout(() => removeToast(id), dur);
              timers.current.set(id, timer);
            }
            updated.duration = dur;
          }
          return updated;
        })
      );
    },
    [removeToast]
  );

  const success = useCallback(
    (title: string, message?: string, opts?: Partial<Toast>) =>
      addToast({ type: 'success', title, message, ...opts }),
    [addToast]
  );
  const error = useCallback(
    (title: string, message?: string, opts?: Partial<Toast>) =>
      addToast({ type: 'error', title, message, ...opts }),
    [addToast]
  );
  const warning = useCallback(
    (title: string, message?: string, opts?: Partial<Toast>) =>
      addToast({ type: 'warning', title, message, ...opts }),
    [addToast]
  );
  const info = useCallback(
    (title: string, message?: string, opts?: Partial<Toast>) =>
      addToast({ type: 'info', title, message, ...opts }),
    [addToast]
  );
  const loading = useCallback(
    (title: string, message?: string) => addToast({ type: 'loading', title, message, duration: 0 }),
    [addToast]
  );

  return (
    <ToastContext.Provider
      value={{ toasts, addToast, removeToast, success, error, warning, info, loading, dismiss: removeToast, update }}
    >
      {children}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </ToastContext.Provider>
  );
}

// ============================================================================
// Toast Container & Item (rendered as a portal-like fixed overlay)
// ============================================================================

function ToastContainer({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  return (
    <div
      aria-live="polite"
      className="fixed bottom-4 right-4 z-[9999] flex flex-col-reverse gap-3 max-w-sm w-full pointer-events-none"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

const iconMap: Record<ToastType, React.ElementType> = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
  loading: Loader2,
};

const colorMap: Record<ToastType, string> = {
  success: 'text-green-500',
  error: 'text-red-500',
  warning: 'text-yellow-500',
  info: 'text-blue-500',
  loading: 'text-amazon-orange',
};

const borderMap: Record<ToastType, string> = {
  success: 'border-l-green-500',
  error: 'border-l-red-500',
  warning: 'border-l-yellow-500',
  info: 'border-l-blue-500',
  loading: 'border-l-amazon-orange',
};

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const Icon = iconMap[toast.type];

  return (
    <div
      className={cn(
        'pointer-events-auto animate-slide-in-right',
        'bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700',
        'border-l-4 p-4 flex items-start gap-3 min-w-[300px]',
        'transition-all duration-300',
        borderMap[toast.type]
      )}
      role="alert"
    >
      <Icon
        className={cn(
          'w-5 h-5 flex-shrink-0 mt-0.5',
          colorMap[toast.type],
          toast.type === 'loading' && 'animate-spin'
        )}
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900 dark:text-white">{toast.title}</p>
        {toast.message && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 leading-relaxed">{toast.message}</p>
        )}
        {toast.amazonSynced !== undefined && (
          <div className="flex items-center gap-1 mt-1.5">
            <span
              className={cn(
                'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold',
                toast.amazonSynced
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                  : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
              )}
            >
              {toast.amazonSynced ? 'Amazon Synced' : 'Local Only — Amazon sync pending'}
            </span>
          </div>
        )}
      </div>
      {toast.type !== 'loading' && (
        <button
          onClick={() => onDismiss(toast.id)}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex-shrink-0"
        >
          <X className="w-4 h-4 text-gray-400" />
        </button>
      )}
    </div>
  );
}
