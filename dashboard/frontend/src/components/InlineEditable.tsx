'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Check, X } from 'lucide-react';
import { cn } from '@/utils/helpers';

interface InlineEditableCellProps {
  value: string | number;
  onSave: (newValue: string | number) => Promise<boolean>;
  type?: 'text' | 'number' | 'currency';
  min?: number;
  max?: number;
  className?: string;
  editable?: boolean;
}

export function InlineEditableCell({
  value: initialValue,
  onSave,
  type = 'text',
  min,
  max,
  className,
  editable = true
}: InlineEditableCellProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState(String(initialValue));
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setError(null);

      // Validate input
      if (type === 'number' || type === 'currency') {
        const numValue = parseFloat(value);
        if (isNaN(numValue)) {
          setError('Invalid number');
          setIsSaving(false);
          return;
        }
        if (min !== undefined && numValue < min) {
          setError(`Minimum value is ${min}`);
          setIsSaving(false);
          return;
        }
        if (max !== undefined && numValue > max) {
          setError(`Maximum value is ${max}`);
          setIsSaving(false);
          return;
        }
      }

      const success = await onSave(type === 'number' || type === 'currency' ? parseFloat(value) : value);
      
      if (success) {
        setIsEditing(false);
      } else {
        setError('Failed to save');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setValue(String(initialValue));
    setIsEditing(false);
    setError(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  if (!isEditing && editable) {
    return (
      <div
        onClick={() => setIsEditing(true)}
        className={cn(
          'px-2 py-1 cursor-pointer rounded hover:bg-blue-50 transition',
          'hover:underline hover:text-blue-600',
          className
        )}
      >
        {type === 'currency' ? `$${initialValue}` : initialValue}
      </div>
    );
  }

  if (isEditing) {
    return (
      <div className="flex items-center gap-1 bg-white border border-blue-400 rounded p-1">
        <input
          ref={inputRef}
          type={type === 'text' ? 'text' : 'number'}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          min={min}
          max={max}
          step={type === 'currency' ? '0.01' : undefined}
          className={cn(
            'flex-1 px-1 py-0 border-0 outline-none text-sm',
            error && 'text-red-600'
          )}
          disabled={isSaving}
        />
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="p-0.5 hover:bg-green-100 rounded transition"
          title="Save"
        >
          <Check size={16} className="text-green-600" />
        </button>
        <button
          onClick={handleCancel}
          disabled={isSaving}
          className="p-0.5 hover:bg-red-100 rounded transition"
          title="Cancel"
        >
          <X size={16} className="text-red-600" />
        </button>
        {error && (
          <div className="text-xs text-red-600 absolute top-full left-0 whitespace-nowrap bg-red-50 px-2 py-1 rounded">
            {error}
          </div>
        )}
      </div>
    );
  }

  return <div className={className}>{type === 'currency' ? `$${initialValue}` : initialValue}</div>;
}

interface InlineEditableBidProps {
  keywordId: string;
  currentBid: number;
  onBidSaved?: (newBid: number) => void;
}

export function InlineEditableBid({ keywordId, currentBid, onBidSaved }: InlineEditableBidProps) {
  const handleSaveBid = async (newBid: number | string) => {
    try {
      const response = await fetch('/api/inline-edit/bid', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keyword_id: keywordId,
          new_bid: parseFloat(String(newBid))
        })
      });

      if (response.ok) {
        const data = await response.json();
        onBidSaved?.(data.new_bid);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error updating bid:', error);
      return false;
    }
  };

  return (
    <InlineEditableCell
      value={currentBid}
      onSave={handleSaveBid}
      type="currency"
      min={0.02}
      max={10000}
    />
  );
}

interface InlineEditableBudgetProps {
  campaignId: string;
  currentBudget: number;
  onBudgetSaved?: (newBudget: number) => void;
}

export function InlineEditableBudget({ campaignId, currentBudget, onBudgetSaved }: InlineEditableBudgetProps) {
  const handleSaveBudget = async (newBudget: number | string) => {
    try {
      const response = await fetch('/api/inline-edit/budget', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaign_id: campaignId,
          new_budget: parseFloat(String(newBudget))
        })
      });

      if (response.ok) {
        const data = await response.json();
        onBudgetSaved?.(data.new_budget);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error updating budget:', error);
      return false;
    }
  };

  return (
    <InlineEditableCell
      value={currentBudget}
      onSave={handleSaveBudget}
      type="currency"
      min={1}
      max={1000000}
    />
  );
}
