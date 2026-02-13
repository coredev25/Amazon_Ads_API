'use client';

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';

interface LiveSettings {
  autoRefresh: boolean;
  refreshInterval: number; // ms
  lastSyncedAt: Date | null;
  toggleAutoRefresh: () => void;
  setRefreshInterval: (ms: number) => void;
  markSynced: () => void;
  getTimeSinceSync: () => string;
}

const LiveSettingsContext = createContext<LiveSettings | undefined>(undefined);

export function LiveSettingsProvider({ children }: { children: React.ReactNode }) {
  const [autoRefresh, setAutoRefresh] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('autoRefresh') === 'true';
    }
    return false;
  });
  const [refreshInterval, setRefreshIntervalState] = useState(60000);
  const [lastSyncedAt, setLastSyncedAt] = useState<Date | null>(null);
  const [, setTick] = useState(0); // Force re-render for relative time
  const tickRef = useRef<NodeJS.Timeout | null>(null);

  // Tick every 30s to update "last synced X ago" text
  useEffect(() => {
    tickRef.current = setInterval(() => setTick(t => t + 1), 30000);
    return () => { if (tickRef.current) clearInterval(tickRef.current); };
  }, []);

  const toggleAutoRefresh = useCallback(() => {
    setAutoRefresh(prev => {
      const next = !prev;
      localStorage.setItem('autoRefresh', String(next));
      return next;
    });
  }, []);

  const setRefreshInterval = useCallback((ms: number) => {
    setRefreshIntervalState(ms);
  }, []);

  const markSynced = useCallback(() => {
    setLastSyncedAt(new Date());
  }, []);

  const getTimeSinceSync = useCallback(() => {
    if (!lastSyncedAt) return 'Never';
    const seconds = Math.floor((Date.now() - lastSyncedAt.getTime()) / 1000);
    if (seconds < 10) return 'Just now';
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  }, [lastSyncedAt]);

  return (
    <LiveSettingsContext.Provider value={{
      autoRefresh,
      refreshInterval,
      lastSyncedAt,
      toggleAutoRefresh,
      setRefreshInterval,
      markSynced,
      getTimeSinceSync,
    }}>
      {children}
    </LiveSettingsContext.Provider>
  );
}

export function useLiveSettings() {
  const ctx = useContext(LiveSettingsContext);
  if (!ctx) throw new Error('useLiveSettings must be used within LiveSettingsProvider');
  return ctx;
}
