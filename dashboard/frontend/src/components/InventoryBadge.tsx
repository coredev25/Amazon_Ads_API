'use client';

import React from 'react';
import { Package, AlertTriangle } from 'lucide-react';
import { cn } from '@/utils/helpers';

interface InventoryBadgeProps {
  inventoryStatus: 'in_stock' | 'low_stock' | 'out_of_stock' | 'unknown';
  currentInventory?: number;
  daysOfSupply?: number;
  className?: string;
}

export default function InventoryBadge({
  inventoryStatus,
  currentInventory,
  daysOfSupply,
  className,
}: InventoryBadgeProps) {
  const getBadgeConfig = () => {
    switch (inventoryStatus) {
      case 'out_of_stock':
        return {
          label: 'Out of Stock',
          color: 'badge-danger',
          icon: AlertTriangle,
          bgColor: 'bg-red-500/20',
          textColor: 'text-red-400',
        };
      case 'low_stock':
        return {
          label: `Low Stock (${daysOfSupply || '?'} days)`,
          color: 'badge-warning',
          icon: Package,
          bgColor: 'bg-yellow-500/20',
          textColor: 'text-yellow-400',
        };
      case 'in_stock':
        return {
          label: currentInventory ? `In Stock (${currentInventory})` : 'In Stock',
          color: 'badge-success',
          icon: Package,
          bgColor: 'bg-green-500/20',
          textColor: 'text-green-400',
        };
      default:
        return {
          label: 'Unknown',
          color: 'badge-secondary',
          icon: Package,
          bgColor: 'bg-gray-500/20',
          textColor: 'text-gray-400',
        };
    }
  };

  const config = getBadgeConfig();
  const Icon = config.icon;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium',
        config.bgColor,
        config.textColor,
        className
      )}
      title={
        inventoryStatus === 'out_of_stock'
          ? 'This product is out of stock. Bidding actions are disabled.'
          : inventoryStatus === 'low_stock'
          ? `Low stock: ${daysOfSupply} days of supply remaining`
          : undefined
      }
    >
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  );
}




