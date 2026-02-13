'use client';

import { useIsFetching } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

export default function LoadingBar() {
  const isFetching = useIsFetching();
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const completeTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isFetching > 0) {
      // Start loading
      setVisible(true);
      setProgress(15);

      // Simulate incremental progress
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) return prev;
          // Slow down as we approach 90
          const increment = Math.max(0.5, (90 - prev) * 0.08);
          return Math.min(90, prev + increment);
        });
      }, 200);
    } else {
      // Complete
      if (timerRef.current) clearInterval(timerRef.current);
      setProgress(100);

      // Hide after completion animation
      if (completeTimerRef.current) clearTimeout(completeTimerRef.current);
      completeTimerRef.current = setTimeout(() => {
        setVisible(false);
        setProgress(0);
      }, 400);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isFetching]);

  if (!visible && progress === 0) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[9999] pointer-events-none">
      <div
        className="h-[3px] transition-all ease-out"
        style={{
          width: `${progress}%`,
          transitionDuration: progress === 100 ? '200ms' : '400ms',
          background: 'linear-gradient(90deg, #FF9900, #FFB84D, #FF9900)',
          boxShadow: '0 0 10px rgba(255, 153, 0, 0.5), 0 0 5px rgba(255, 153, 0, 0.3)',
          opacity: progress === 100 ? 0 : 1,
        }}
      />
    </div>
  );
}
