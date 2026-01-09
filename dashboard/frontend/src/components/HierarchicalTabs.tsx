'use client';

import React from 'react';
import { ChevronRight, Folder, Target, Layers, FileText, Key, Crosshair, Search, MapPin } from 'lucide-react';
import { cn } from '@/utils/helpers';

export type TabType = 'portfolios' | 'campaigns' | 'ad_groups' | 'ads' | 'keywords' | 'targeting' | 'search_terms' | 'placements';

interface BreadcrumbItem {
  type: TabType;
  id?: number;
  name?: string;
}

interface HierarchicalTabsProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  breadcrumbs?: BreadcrumbItem[];
  onBreadcrumbClick?: (item: BreadcrumbItem) => void;
}

const tabConfig: Record<TabType, { label: string; icon: React.ComponentType<{ className?: string }> }> = {
  portfolios: { label: 'Portfolios', icon: Folder },
  campaigns: { label: 'Campaigns', icon: Target },
  ad_groups: { label: 'Ad Groups', icon: Layers },
  ads: { label: 'Ads', icon: FileText },
  keywords: { label: 'Keywords', icon: Key },
  targeting: { label: 'Targeting', icon: Crosshair },
  search_terms: { label: 'Search Terms', icon: Search },
  placements: { label: 'Placements', icon: MapPin },
};

export default function HierarchicalTabs({
  activeTab,
  onTabChange,
  breadcrumbs = [],
  onBreadcrumbClick,
}: HierarchicalTabsProps) {
  const tabs: TabType[] = ['portfolios', 'campaigns', 'ad_groups', 'ads', 'keywords', 'targeting', 'search_terms', 'placements'];

  return (
    <div className="space-y-4">
      {/* Breadcrumbs */}
      {breadcrumbs.length > 0 && (
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <button
            onClick={() => onBreadcrumbClick?.({ type: 'campaigns' })}
            className="hover:text-amazon-orange transition-colors"
          >
            All Campaigns
          </button>
          {breadcrumbs.map((crumb, index) => (
            <React.Fragment key={`${crumb.type}-${crumb.id || index}`}>
              <ChevronRight className="w-4 h-4" />
              <button
                onClick={() => onBreadcrumbClick?.(crumb)}
                className="hover:text-amazon-orange transition-colors"
              >
                {crumb.name || tabConfig[crumb.type].label}
              </button>
            </React.Fragment>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex space-x-1 overflow-x-auto" aria-label="Tabs">
          {tabs.map((tab) => {
            const config = tabConfig[tab];
            const Icon = config.icon;
            const isActive = activeTab === tab;

            return (
              <button
                key={tab}
                onClick={() => onTabChange(tab)}
                className={cn(
                  'flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors whitespace-nowrap',
                  isActive
                    ? 'border-amazon-orange text-amazon-orange'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                )}
              >
                <Icon className="w-4 h-4" />
                {config.label}
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}

