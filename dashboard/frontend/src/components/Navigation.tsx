'use client';

import React, { useState } from 'react';
import { ChevronRight, Home } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/utils/helpers';

interface BreadcrumbItem {
  label: string;
  url: string;
  icon?: React.ReactNode;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  current: string;
  className?: string;
}

export function Breadcrumbs({ items, current, className }: BreadcrumbsProps) {
  return (
    <nav className={cn('flex items-center gap-2 px-4 py-2 text-sm', className)}>
      <Link href="/dashboard" className="flex items-center gap-1 hover:text-blue-600">
        <Home size={16} />
        <span>Dashboard</span>
      </Link>

      {items.map((item, idx) => (
        <React.Fragment key={idx}>
          <ChevronRight size={16} className="text-gray-400" />
          <Link href={item.url} className="hover:text-blue-600 flex items-center gap-1">
            {item.icon}
            <span>{item.label}</span>
          </Link>
        </React.Fragment>
      ))}

      {current && (
        <>
          <ChevronRight size={16} className="text-gray-400" />
          <span className="text-gray-600 font-medium">{current}</span>
        </>
      )}
    </nav>
  );
}

interface TabItem {
  tab_id: string;
  label: string;
  entity_type: string;
  icon?: React.ReactNode;
}

interface TabbedNavigationProps {
  tabs: TabItem[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  parentEntity?: string;
  parentId?: string;
  className?: string;
}

export function TabbedNavigation({
  tabs,
  activeTab,
  onTabChange,
  className
}: TabbedNavigationProps) {
  return (
    <div className={cn('flex gap-1 border-b border-gray-200 bg-gray-50', className)}>
      {tabs.map((tab) => (
        <button
          key={tab.tab_id}
          onClick={() => onTabChange(tab.tab_id)}
          className={cn(
            'px-4 py-2 text-sm font-medium flex items-center gap-2 transition',
            'border-b-2 border-transparent hover:text-blue-600 hover:border-blue-300',
            activeTab === tab.tab_id && 'text-blue-600 border-blue-600 bg-white'
          )}
        >
          {tab.icon}
          {tab.label}
        </button>
      ))}
    </div>
  );
}

interface DrillDownNavigationProps {
  entityType: string;
  entityId: string;
  onDrillDown: (targetEntity: string, data: any) => void;
}

export function DrillDownNavigation({
  entityType,
  entityId,
  onDrillDown
}: DrillDownNavigationProps) {
  const [loading, setLoading] = useState(false);

  const handleDrillDown = async (targetEntity: string) => {
    try {
      setLoading(true);
      const response = await fetch('/api/navigation/drill-down', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parent_entity: entityType,
          parent_id: entityId,
          target_entity: targetEntity
        })
      });

      if (response.ok) {
        const data = await response.json();
        onDrillDown(targetEntity, data);
      }
    } catch (error) {
      console.error('Error drilling down:', error);
    } finally {
      setLoading(false);
    }
  };

  const drillDownOptions: Array<{ label: string; entity: string }> = 
    entityType === 'campaign' ? [
      { label: 'Ad Groups', entity: 'adgroups' },
      { label: 'Keywords', entity: 'keywords' },
      { label: 'Product Targeting', entity: 'targets' }
    ] : entityType === 'adgroup' ? [
      { label: 'Keywords', entity: 'keywords' },
      { label: 'Product Targeting', entity: 'targets' }
    ] : [];

  if (drillDownOptions.length === 0) return null;

  return (
    <div className="flex gap-2 p-2">
      {drillDownOptions.map(({ label, entity }) => (
        <button
          key={entity}
          onClick={() => handleDrillDown(entity)}
          disabled={loading}
          className={cn(
            'px-3 py-1 text-sm rounded-lg transition',
            'bg-blue-100 text-blue-700 hover:bg-blue-200',
            loading && 'opacity-50 cursor-not-allowed'
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
