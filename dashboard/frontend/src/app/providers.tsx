'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { ToastProvider } from '@/contexts/ToastContext';
import { LiveSettingsProvider } from '@/contexts/LiveSettingsContext';
import LoadingBar from '@/components/LoadingBar';

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000,      // 5 minutes — avoid refetching data that hasn't changed
            gcTime: 15 * 60 * 1000,         // 15 minutes — keep cache longer
            refetchOnWindowFocus: false,
            refetchOnMount: 'always',
            retry: 1,                        // Only retry once on failure
            retryDelay: 1000,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <LoadingBar />
      <ThemeProvider>
        <AuthProvider>
          <LiveSettingsProvider>
            <ToastProvider>
              {children}
            </ToastProvider>
          </LiveSettingsProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

