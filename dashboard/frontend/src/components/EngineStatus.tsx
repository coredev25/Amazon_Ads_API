'use client';

import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, RefreshCw, Clock, CheckCircle, XCircle, Loader, History } from 'lucide-react';
import { fetchEngineStatus, triggerEngineExecution, fetchEngineHistory, type EngineStatus, type EngineHistory } from '@/utils/api';
import { formatRelativeTime, cn } from '@/utils/helpers';

export default function EngineStatus() {
  const queryClient = useQueryClient();
  
  const { data: status, refetch } = useQuery({
    queryKey: ['engine-status'],
    queryFn: fetchEngineStatus,
    refetchInterval: (query) => {
      const data = query.state.data as EngineStatus | undefined;
      return data?.is_running ? 2000 : 10000;
    }
  });

  const { data: history } = useQuery({
    queryKey: ['engine-history'],
    queryFn: () => fetchEngineHistory(5),
    refetchInterval: 30000
  });

  const triggerMutation = useMutation({
    mutationFn: triggerEngineExecution,
    onSuccess: () => {
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['engine-status'] });
        refetch();
      }, 1000);
    }
  });

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs.toFixed(0)}s`;
  };

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <RefreshCw className={cn("w-5 h-5", status?.is_running && "animate-spin")} />
          AI Rule Engine Status
        </h3>
        <button
          onClick={() => triggerMutation.mutate({})}
          disabled={status?.is_running || triggerMutation.isPending}
          className="btn btn-primary btn-sm"
        >
          {status?.is_running || triggerMutation.isPending ? (
            <Loader className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          <span className="ml-2">
            {status?.is_running ? 'Running...' : 'Run Engine'}
          </span>
        </button>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-3 h-3 rounded-full",
            status?.is_running 
              ? 'bg-green-500 animate-pulse' 
              : status?.last_run?.status === 'completed'
              ? 'bg-gray-400'
              : status?.last_run?.status === 'failed'
              ? 'bg-red-400'
              : 'bg-gray-300'
          )} />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {status?.is_running ? 'Running' : status?.last_run ? 'Idle' : 'Not Started'}
          </span>
        </div>

        {status?.is_running && status.current_run && (
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="flex items-center gap-2 mb-2">
              <RefreshCw className="w-4 h-4 animate-spin text-blue-600 dark:text-blue-400" />
              <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                Execution in progress...
              </span>
            </div>
            <div className="text-xs text-blue-700 dark:text-blue-300 space-y-1">
              <div>Started: {formatRelativeTime(status.current_run.start_time)}</div>
              {status.current_run.elapsed_seconds !== undefined && (
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Elapsed: {formatDuration(status.current_run.elapsed_seconds)}
                </div>
              )}
            </div>
          </div>
        )}

        {status?.last_run && (
          <div className="space-y-2 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Last Run</span>
              <span className="text-gray-900 dark:text-white font-medium">
                {formatRelativeTime(status.last_run.end_time || status.last_run.start_time)}
              </span>
            </div>
            {status.last_run.duration_seconds !== undefined && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Duration
                </span>
                <span className="text-gray-900 dark:text-white font-medium">
                  {formatDuration(status.last_run.duration_seconds)}
                </span>
              </div>
            )}
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Status</span>
              <span className={cn(
                "badge flex items-center gap-1",
                status.last_run.status === 'completed' 
                  ? 'badge-success' 
                  : 'badge-danger'
              )}>
                {status.last_run.status === 'completed' ? (
                  <CheckCircle className="w-3 h-3" />
                ) : (
                  <XCircle className="w-3 h-3" />
                )}
                {status.last_run.status}
              </span>
            </div>
            {status.last_run.recommendations_count !== undefined && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Recommendations</span>
                <span className="text-gray-900 dark:text-white font-medium">
                  {status.last_run.recommendations_count}
                </span>
              </div>
            )}
            {status.last_run.error && (
              <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 rounded text-xs text-red-700 dark:text-red-300">
                Error: {status.last_run.error}
              </div>
            )}
          </div>
        )}

        {history && history.history.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <History className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Recent Runs ({history.total_runs} total)
              </span>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {history.history.map((run, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs p-2 bg-gray-50 dark:bg-gray-800 rounded">
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      run.status === 'completed' ? 'bg-green-500' : 'bg-red-500'
                    )} />
                    <span className="text-gray-600 dark:text-gray-400">
                      {new Date(run.start_time).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-gray-500 dark:text-gray-400">
                    {run.duration_seconds && (
                      <span>{formatDuration(run.duration_seconds)}</span>
                    )}
                    {run.recommendations_count !== undefined && (
                      <span>{run.recommendations_count} recs</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

