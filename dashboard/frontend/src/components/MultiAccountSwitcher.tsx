'use client';

import React, { useState } from 'react';
import { ChevronDown, Check, Store } from 'lucide-react';
import { cn } from '@/utils/helpers';

interface Account {
  account_id: string;
  account_name: string;
  marketplace_id?: string;
  region?: string;
  is_active: boolean;
}

interface MultiAccountSwitcherProps {
  accounts: Account[];
  currentAccountId?: string;
  onAccountChange: (accountId: string) => void;
  className?: string;
}

export default function MultiAccountSwitcher({
  accounts,
  currentAccountId,
  onAccountChange,
  className,
}: MultiAccountSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const currentAccount = accounts.find(a => a.account_id === currentAccountId) || accounts[0];
  const filteredAccounts = accounts.filter(a =>
    a.account_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.account_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-amazon-orange transition-colors"
      >
        <Store className="w-4 h-4 text-gray-500" />
        <span className="text-sm font-medium text-gray-900 dark:text-white">
          {currentAccount?.account_name || 'Select Account'}
        </span>
        {currentAccount?.region && (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            ({currentAccount.region})
          </span>
        )}
        <ChevronDown className={cn('w-4 h-4 text-gray-500 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-2 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20">
            {/* Search */}
            <div className="p-2 border-b border-gray-200 dark:border-gray-700">
              <input
                type="text"
                placeholder="Search accounts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input w-full text-sm"
                onClick={(e) => e.stopPropagation()}
              />
            </div>

            {/* Account List */}
            <div className="max-h-64 overflow-y-auto">
              {filteredAccounts.length === 0 ? (
                <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
                  No accounts found
                </div>
              ) : (
                filteredAccounts.map((account) => (
                  <button
                    key={account.account_id}
                    onClick={() => {
                      onAccountChange(account.account_id);
                      setIsOpen(false);
                      setSearchQuery('');
                    }}
                    className={cn(
                      'w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors',
                      currentAccountId === account.account_id && 'bg-amazon-orange/10'
                    )}
                  >
                    <Store className="w-4 h-4 text-gray-400" />
                    <div className="flex-1 min-w-0">
                      <p className={cn(
                        'text-sm font-medium truncate',
                        currentAccountId === account.account_id
                          ? 'text-amazon-orange'
                          : 'text-gray-900 dark:text-white'
                      )}>
                        {account.account_name}
                      </p>
                      {account.region && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {account.region} • {account.marketplace_id || account.account_id}
                        </p>
                      )}
                    </div>
                    {currentAccountId === account.account_id && (
                      <Check className="w-4 h-4 text-amazon-orange flex-shrink-0" />
                    )}
                    {!account.is_active && (
                      <span className="text-xs text-red-500">Inactive</span>
                    )}
                  </button>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}




