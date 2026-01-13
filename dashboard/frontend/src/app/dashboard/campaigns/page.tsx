'use client';

import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Play,
  Pause,
  Filter,
  Download,
  RefreshCw,
  ChevronRight,
  Package,
  AlertTriangle,
  FileDown,
  Target,
  Settings,
  ChevronDown,
} from 'lucide-react';
import { exportDashboardToPDF } from '@/utils/pdfExport';
import DataTable from '@/components/DataTable';
import SmartGrid from '@/components/SmartGrid';
import HierarchicalTabs, { type TabType } from '@/components/HierarchicalTabs';
import DateRangePicker, { type DateRange } from '@/components/DateRangePicker';
import MasterPerformanceChart from '@/components/MasterPerformanceChart';
import InventoryBadge from '@/components/InventoryBadge';
import {
  fetchCampaigns,
  fetchPortfolios,
  fetchAdGroups,
  fetchKeywords,
  fetchProductTargeting,
  fetchSearchTerms,
  fetchPlacements,
  applyCampaignAction,
  addSearchTermAsKeyword,
  addSearchTermAsNegative,
  getInventoryStatus,
  fetchTrends,
  addCampaignToPortfolio,
  bulkAddCampaignsToPortfolio,
  type Campaign,
  type SearchTerm,
  type Portfolio,
} from '@/utils/api';
import {
  formatCurrency,
  formatAcos,
  formatRoas,
  formatNumber,
  formatPercentage,
  cn,
  getStatusBadge,
} from '@/utils/helpers';

export default function HierarchicalCampaignManager() {
  const [activeTab, setActiveTab] = useState<TabType>('campaigns');
  const [dateRange, setDateRange] = useState<DateRange>({
    type: 'last_7_days',
    days: 7,
  });
  const [selectedCampaign, setSelectedCampaign] = useState<{ id: number; name: string } | null>(null);
  const [selectedAdGroup, setSelectedAdGroup] = useState<{ id: number; name: string } | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [portfolioFilter, setPortfolioFilter] = useState<number | undefined>(undefined);
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [inventoryStatuses, setInventoryStatuses] = useState<Record<string, any>>({});
  const [showPortfolioModal, setShowPortfolioModal] = useState(false);
  const [showColumnModal, setShowColumnModal] = useState(false);
  
  const queryClient = useQueryClient();
  const days = dateRange.days || 7;

  // Fetch trends for master chart
  const { data: trends } = useQuery({
    queryKey: ['trends', days],
    queryFn: () => fetchTrends(days),
    enabled: activeTab === 'campaigns',
  });

  // Breadcrumbs
  const breadcrumbs = useMemo(() => {
    const crumbs = [];
    if (selectedCampaign) {
      crumbs.push({ type: 'campaigns' as TabType, id: selectedCampaign.id, name: selectedCampaign.name });
    }
    if (selectedAdGroup) {
      crumbs.push({ type: 'ad_groups' as TabType, id: selectedAdGroup.id, name: selectedAdGroup.name });
    }
    return crumbs;
  }, [selectedCampaign, selectedAdGroup]);

  // Queries based on active tab
  const { data: portfolios, isLoading: portfoliosLoading } = useQuery({
    queryKey: ['portfolios', days],
    queryFn: () => fetchPortfolios(days),
    enabled: activeTab === 'portfolios',
  });

  const { data: campaigns, isLoading: campaignsLoading } = useQuery({
    queryKey: ['campaigns', days, portfolioFilter],
    queryFn: () => fetchCampaigns(days, portfolioFilter),
    enabled: activeTab === 'campaigns' || activeTab === 'ad_groups' || activeTab === 'ads' || activeTab === 'keywords' || activeTab === 'targeting' || activeTab === 'search_terms' || activeTab === 'placements',
  });

  const { data: adGroups, isLoading: adGroupsLoading } = useQuery({
    queryKey: ['ad-groups', selectedCampaign?.id, days],
    queryFn: () => fetchAdGroups(selectedCampaign?.id, days),
    enabled: activeTab === 'ad_groups' && selectedCampaign !== null,
  });

  const { data: keywords, isLoading: keywordsLoading } = useQuery({
    queryKey: ['keywords', selectedAdGroup?.id, days],
    queryFn: () => fetchKeywords({ ad_group_id: selectedAdGroup?.id, days }),
    enabled: activeTab === 'keywords' && selectedAdGroup !== null,
  });

  const { data: targeting, isLoading: targetingLoading } = useQuery({
    queryKey: ['targeting', selectedAdGroup?.id, days],
    queryFn: () => fetchProductTargeting(selectedCampaign?.id, selectedAdGroup?.id, days),
    enabled: activeTab === 'targeting' && selectedAdGroup !== null,
  });

  const { data: searchTerms, isLoading: searchTermsLoading } = useQuery({
    queryKey: ['search-terms', selectedAdGroup?.id, days],
    queryFn: () => fetchSearchTerms(selectedCampaign?.id, selectedAdGroup?.id, days),
    enabled: activeTab === 'search_terms' && selectedAdGroup !== null,
  });

  const { data: placements, isLoading: placementsLoading } = useQuery({
    queryKey: ['placements', selectedCampaign?.id, days],
    queryFn: () => fetchPlacements(selectedCampaign?.id, selectedAdGroup?.id, days),
    enabled: activeTab === 'placements' && selectedCampaign !== null,
  });

  const actionMutation = useMutation({
    mutationFn: ({ entityId, action }: { entityId: number; action: { action_type: string; new_value: number } }) =>
      applyCampaignAction(entityId, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['ad-groups'] });
    },
  });

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    // Reset selections when switching tabs
    if (tab === 'campaigns') {
      setSelectedCampaign(null);
      setSelectedAdGroup(null);
    } else if (tab === 'ad_groups' && !selectedCampaign) {
      // If switching to ad_groups without a selected campaign, stay on campaigns
      setActiveTab('campaigns');
    }
  };

  const handleBreadcrumbClick = (item: { type: TabType; id?: number; name?: string }) => {
    if (item.type === 'campaigns') {
      setSelectedCampaign(null);
      setSelectedAdGroup(null);
      setActiveTab('campaigns');
    } else if (item.type === 'ad_groups' && item.id) {
      const campaign = campaigns?.find(c => c.campaign_id === item.id);
      if (campaign) {
        setSelectedCampaign({ id: campaign.campaign_id, name: campaign.campaign_name });
        setSelectedAdGroup(null);
        setActiveTab('ad_groups');
      }
    }
  };

  const handleCampaignClick = (campaign: Campaign) => {
    setSelectedCampaign({ id: campaign.campaign_id, name: campaign.campaign_name });
    setSelectedAdGroup(null);
    setActiveTab('ad_groups');
  };

  const handleAdGroupClick = (adGroup: { ad_group_id: number; ad_group_name: string }) => {
    setSelectedAdGroup({ id: adGroup.ad_group_id, name: adGroup.ad_group_name });
    setActiveTab('keywords');
  };

  // Render content based on active tab
  const renderTabContent = () => {
    const isLoading = 
      (activeTab === 'portfolios' && portfoliosLoading) ||
      (activeTab === 'campaigns' && campaignsLoading) ||
      (activeTab === 'ad_groups' && adGroupsLoading) ||
      (activeTab === 'keywords' && keywordsLoading) ||
      (activeTab === 'targeting' && targetingLoading) ||
      (activeTab === 'search_terms' && searchTermsLoading) ||
      (activeTab === 'placements' && placementsLoading);

    if (isLoading) {
      return (
        <div className="card p-8 text-center">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mx-auto" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mx-auto" />
          </div>
        </div>
      );
    }

    switch (activeTab) {
      case 'portfolios':
        return renderPortfolios();
      case 'campaigns':
        return renderCampaigns();
      case 'ad_groups':
        if (!selectedCampaign) {
          return (
            <div className="card p-8 text-center text-gray-500">
              <Target className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Select a campaign to view ad groups</p>
            </div>
          );
        }
        return renderAdGroups();
      case 'keywords':
        if (!selectedAdGroup) {
          return (
            <div className="card p-8 text-center text-gray-500">
              <Filter className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Select an ad group to view keywords</p>
            </div>
          );
        }
        return renderKeywords();
      case 'targeting':
        if (!selectedAdGroup) {
          return (
            <div className="card p-8 text-center text-gray-500">
              <Filter className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Select an ad group to view product targeting</p>
            </div>
          );
        }
        return renderTargeting();
      case 'search_terms':
        if (!selectedAdGroup) {
          return (
            <div className="card p-8 text-center text-gray-500">
              <Filter className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Select an ad group to view search terms</p>
            </div>
          );
        }
        return renderSearchTerms();
      case 'placements':
        if (!selectedCampaign) {
          return (
            <div className="card p-8 text-center text-gray-500">
              <Filter className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Select a campaign to view placements</p>
            </div>
          );
        }
        return renderPlacements();
      default:
        return null;
    }
  };

  const renderPortfolios = () => {
    const filtered = portfolios?.filter(p => {
      if (statusFilter === 'all') return true;
      return p.status?.toLowerCase() === statusFilter.toLowerCase();
    }) || [];

    return (
      <DataTable
        data={filtered}
        columns={[
          {
            key: 'portfolio_name',
            header: 'Portfolio Name',
            sortable: true,
            render: (value: unknown, row: any) => (
              <div>
                <p className="font-medium text-gray-900 dark:text-white">{row.portfolio_name}</p>
              </div>
            ),
          },
          {
            key: 'status',
            header: 'Status',
            sortable: true,
            render: (value: unknown, row: any) => (
              <span className={cn('badge', getStatusBadge(row.status))}>
                {row.status}
              </span>
            ),
          },
          {
            key: 'campaign_count',
            header: 'Campaigns',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => formatNumber(value as number),
          },
          {
            key: 'total_spend',
            header: 'Spend',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'total_sales',
            header: 'Sales',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono text-green-400">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'acos',
            header: 'ACOS',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => {
              const acos = value as number | null;
              const color = acos === null ? 'text-gray-400' :
                acos < 9 ? 'text-green-400' :
                acos < 15 ? 'text-yellow-400' :
                'text-red-400';
              return <span className={cn('font-mono', color)}>{formatAcos(acos)}</span>;
            },
          },
        ]}
        keyField="portfolio_id"
        loading={portfoliosLoading}
        emptyMessage="No portfolios found"
      />
    );
  };

  const renderCampaigns = () => {
    const filtered = campaigns?.filter(c => {
      if (statusFilter === 'all') return true;
      return c.status?.toLowerCase() === statusFilter.toLowerCase();
    }) || [];

    return (
      <DataTable
        data={filtered}
        showToolbar={true}
        toolbarLeft={
          <>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="select text-sm"
              >
                <option value="all">All Status</option>
                <option value="enabled">Enabled</option>
                <option value="paused">Paused</option>
                <option value="archived">Archived</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={portfolioFilter || ''}
                onChange={(e) => setPortfolioFilter(e.target.value ? parseInt(e.target.value) : undefined)}
                className="select text-sm"
              >
                <option value="">All Portfolios</option>
                {portfolios?.map((p: Portfolio) => (
                  <option key={p.portfolio_id} value={p.portfolio_id.toString()}>
                    {p.portfolio_name}
                  </option>
                ))}
              </select>
            </div>
            {selectedRows.size > 0 && (
              <div className="flex items-center gap-2 ml-4 pl-4 border-l border-gray-200 dark:border-gray-700">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {selectedRows.size} selected
                </span>
                <button
                  onClick={() => setShowPortfolioModal(true)}
                  className="btn btn-sm btn-secondary"
                >
                  <Package className="w-4 h-4" />
                  Add to Portfolio
                </button>
              </div>
            )}
          </>
        }
        toolbarRight={
          <>
            <DateRangePicker value={dateRange} onChange={setDateRange} />
            <button
              className="btn btn-sm btn-secondary"
              title="Settings"
            >
              <Settings className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                exportDashboardToPDF('campaign-manager-content', `campaign-manager-${new Date().toISOString().split('T')[0]}.pdf`)
                  .catch(err => console.error('PDF export failed:', err));
              }}
              className="btn btn-sm btn-secondary"
            >
              <FileDown className="w-4 h-4" />
              Export
            </button>
          </>
        }
        columnModalOpen={showColumnModal}
        onColumnModalClose={() => setShowColumnModal(false)}
        onColumnsClick={() => setShowColumnModal(true)}
        columns={[
          {
            key: 'campaign_name',
            header: 'Campaign Name',
            sortable: true,
            render: (value: unknown, row: Campaign) => (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleCampaignClick(row)}
                  className="text-left hover:text-amazon-orange transition-colors"
                >
                  <p className="font-medium text-gray-900 dark:text-white">{row.campaign_name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-gray-400">{row.campaign_type}</span>
                    {row.sb_ad_type && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300">
                        {row.sb_ad_type.replace(/_/g, ' ')}
                      </span>
                    )}
                    {row.sd_targeting_type && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300">
                        {row.sd_targeting_type}
                      </span>
                    )}
                    {row.portfolio_name && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                        {row.portfolio_name}
                      </span>
                    )}
                  </div>
                </button>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </div>
            ),
          },
          {
            key: 'status',
            header: 'Status',
            sortable: true,
            render: (value: unknown, row: Campaign) => (
              <span className={cn('badge', getStatusBadge(row.status))}>
                {row.status}
              </span>
            ),
          },
          {
            key: 'spend',
            header: 'Spend',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'sales',
            header: 'Sales',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono text-green-400">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'acos',
            header: 'ACOS',
            sortable: true,
            className: 'text-right',
            render: (value: unknown, row: Campaign) => {
              const acos = row.acos;
              const color = acos === null ? 'text-gray-400' :
                acos < 9 ? 'text-green-400' :
                acos < 15 ? 'text-yellow-400' :
                'text-red-400';
              return <span className={cn('font-mono', color)}>{formatAcos(acos)}</span>;
            },
          },
          {
            key: 'roas',
            header: 'ROAS',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono">{formatRoas(value as number)}</span>
            ),
          },
          {
            key: 'orders',
            header: 'Orders',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => formatNumber(value as number),
          },
          {
            key: 'actions',
            header: 'Actions',
            render: (value: unknown, row: Campaign) => (
              <div className="flex items-center gap-2">
                {!row.portfolio_id && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowPortfolioModal(true);
                      setSelectedRows(new Set([row.campaign_id]));
                    }}
                    className="btn btn-sm btn-secondary"
                    title="Add to Portfolio"
                  >
                    <Package className="w-3 h-3" />
                  </button>
                )}
              </div>
            ),
          },
        ]}
        keyField="campaign_id"
        loading={campaignsLoading}
        enableSelection
        selectedRows={selectedRows as unknown as Set<string | number>}
        onSelectRow={(id) => {
          const newSelection = new Set(selectedRows);
          if (newSelection.has(id as number)) {
            newSelection.delete(id as number);
          } else {
            newSelection.add(id as number);
          }
          setSelectedRows(newSelection);
        }}
        emptyMessage="No campaigns found"
      />
    );
  };

  const renderAdGroups = () => {
    const filtered = adGroups?.filter(ag => {
      if (statusFilter === 'all') return true;
      return ag.status?.toLowerCase() === statusFilter.toLowerCase();
    }) || [];

    return (
      <DataTable
        data={filtered}
        columns={[
          {
            key: 'ad_group_name',
            header: 'Ad Group Name',
            sortable: true,
            render: (value: unknown, row: any) => (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleAdGroupClick(row)}
                  className="text-left hover:text-amazon-orange transition-colors"
                >
                  <p className="font-medium text-gray-900 dark:text-white">{row.ad_group_name}</p>
                </button>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </div>
            ),
          },
          {
            key: 'status',
            header: 'Status',
            sortable: true,
            render: (value: unknown, row: any) => (
              <span className={cn('badge', getStatusBadge(row.status))}>
                {row.status}
              </span>
            ),
          },
          {
            key: 'spend',
            header: 'Spend',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'sales',
            header: 'Sales',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono text-green-400">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'acos',
            header: 'ACOS',
            sortable: true,
            className: 'text-right',
            render: (value: unknown, row: any) => {
              const acos = row.acos;
              const color = acos === null ? 'text-gray-400' :
                acos < 9 ? 'text-green-400' :
                acos < 15 ? 'text-yellow-400' :
                'text-red-400';
              return <span className={cn('font-mono', color)}>{formatAcos(acos)}</span>;
            },
          },
          {
            key: 'orders',
            header: 'Orders',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => formatNumber(value as number),
          },
        ]}
        keyField="ad_group_id"
        loading={adGroupsLoading}
        emptyMessage="No ad groups found"
      />
    );
  };

  const renderKeywords = () => {
    const filtered = keywords?.filter(k => {
      if (statusFilter === 'all') return true;
      return k.state?.toLowerCase() === statusFilter.toLowerCase();
    }) || [];

    return (
      <DataTable
        data={filtered}
        columns={[
          {
            key: 'keyword_text',
            header: 'Keyword',
            sortable: true,
            render: (value: unknown) => (
              <span className="font-medium text-gray-900 dark:text-white">{value as string}</span>
            ),
          },
          {
            key: 'match_type',
            header: 'Match Type',
            sortable: true,
            render: (value: unknown) => (
              <span className="badge badge-info">{value as string}</span>
            ),
          },
          {
            key: 'bid',
            header: 'Bid',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'spend',
            header: 'Spend',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'sales',
            header: 'Sales',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono text-green-400">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'acos',
            header: 'ACOS',
            sortable: true,
            className: 'text-right',
            render: (value: unknown, row: any) => {
              const acos = row.acos;
              const color = acos === null ? 'text-gray-400' :
                acos < 9 ? 'text-green-400' :
                acos < 15 ? 'text-yellow-400' :
                'text-red-400';
              return <span className={cn('font-mono', color)}>{formatAcos(acos)}</span>;
            },
          },
          {
            key: 'orders',
            header: 'Orders',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => formatNumber(value as number),
          },
        ]}
        keyField="keyword_id"
        loading={keywordsLoading}
        emptyMessage="No keywords found"
      />
    );
  };

  const renderTargeting = () => {
    return (
      <DataTable
        data={targeting || []}
        columns={[
          {
            key: 'target_value',
            header: 'Target',
            sortable: true,
            render: (value: unknown, row: any) => (
              <div>
                <p className="font-medium text-gray-900 dark:text-white">{value as string}</p>
                <p className="text-xs text-gray-400">{row.target_type}</p>
              </div>
            ),
          },
          {
            key: 'bid',
            header: 'Bid',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'spend',
            header: 'Spend',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'sales',
            header: 'Sales',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono text-green-400">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'acos',
            header: 'ACOS',
            sortable: true,
            className: 'text-right',
            render: (value: unknown, row: any) => {
              const acos = row.acos;
              const color = acos === null ? 'text-gray-400' :
                acos < 9 ? 'text-green-400' :
                acos < 15 ? 'text-yellow-400' :
                'text-red-400';
              return <span className={cn('font-mono', color)}>{formatAcos(acos)}</span>;
            },
          },
        ]}
        keyField="target_id"
        loading={targetingLoading}
        emptyMessage="No product targeting found"
      />
    );
  };

  const handleAddAsKeyword = async (searchTerm: SearchTerm) => {
    try {
      await addSearchTermAsKeyword(
        searchTerm.search_term,
        searchTerm.campaign_id,
        searchTerm.ad_group_id,
        'PHRASE' // Default match type
      );
      queryClient.invalidateQueries({ queryKey: ['search-terms'] });
      queryClient.invalidateQueries({ queryKey: ['keywords'] });
    } catch (error) {
      console.error('Failed to add search term as keyword:', error);
    }
  };

  const handleAddAsNegative = async (searchTerm: SearchTerm) => {
    try {
      await addSearchTermAsNegative(
        searchTerm.search_term,
        searchTerm.campaign_id,
        searchTerm.ad_group_id,
        'negative_phrase' // Default match type
      );
      queryClient.invalidateQueries({ queryKey: ['search-terms'] });
    } catch (error) {
      console.error('Failed to add search term as negative:', error);
    }
  };

  const renderSearchTerms = () => {
    return (
      <DataTable
        data={searchTerms || []}
        columns={[
          {
            key: 'search_term',
            header: 'Search Term',
            sortable: true,
            render: (value: unknown) => (
              <span className="font-medium text-gray-900 dark:text-white">{value as string}</span>
            ),
          },
          {
            key: 'impressions',
            header: 'Impressions',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => formatNumber(value as number),
          },
          {
            key: 'clicks',
            header: 'Clicks',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => formatNumber(value as number),
          },
          {
            key: 'spend',
            header: 'Spend',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'sales',
            header: 'Sales',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono text-green-400">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'orders',
            header: 'Orders',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => formatNumber(value as number),
          },
          {
            key: 'harvest_action',
            header: 'Action',
            render: (value: unknown, row: any) => {
              const term = row as SearchTerm;
              if (term.harvest_action === 'add_keyword') {
                return (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAddAsKeyword(term);
                    }}
                    className="btn btn-sm btn-success"
                  >
                    Add as Keyword
                  </button>
                );
              } else if (term.harvest_action === 'add_negative') {
                return (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAddAsNegative(term);
                    }}
                    className="btn btn-sm btn-danger"
                  >
                    Add as Negative
                  </button>
                );
              }
              return null;
            },
          },
        ]}
        keyField="search_term"
        loading={searchTermsLoading}
        emptyMessage="No search terms found"
      />
    );
  };

  const renderPlacements = () => {
    return (
      <DataTable
        data={placements || []}
        columns={[
          {
            key: 'placement',
            header: 'Placement',
            sortable: true,
            render: (value: unknown) => (
              <span className="font-medium text-gray-900 dark:text-white">{value as string}</span>
            ),
          },
          {
            key: 'impressions',
            header: 'Impressions',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => formatNumber(value as number),
          },
          {
            key: 'clicks',
            header: 'Clicks',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => formatNumber(value as number),
          },
          {
            key: 'spend',
            header: 'Spend',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'sales',
            header: 'Sales',
            sortable: true,
            className: 'text-right',
            render: (value: unknown) => (
              <span className="font-mono text-green-400">{formatCurrency(value as number)}</span>
            ),
          },
          {
            key: 'acos',
            header: 'ACOS',
            sortable: true,
            className: 'text-right',
            render: (value: unknown, row: any) => {
              const acos = row.acos;
              const color = acos === null ? 'text-gray-400' :
                acos < 9 ? 'text-green-400' :
                acos < 15 ? 'text-yellow-400' :
                'text-red-400';
              return <span className={cn('font-mono', color)}>{formatAcos(acos)}</span>;
            },
          },
        ]}
        keyField="placement"
        loading={placementsLoading}
        emptyMessage="No placement data found"
      />
    );
  };

  return (
    <div id="campaign-manager-content" className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Campaign Manager</h1>
          <p className="text-gray-400 mt-1">
            Hierarchical view of your advertising structure
          </p>
        </div>
        <div className="flex items-center gap-3">
          <DateRangePicker value={dateRange} onChange={setDateRange} />
          <button
            onClick={() => queryClient.invalidateQueries()}
            className="btn btn-secondary"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Hierarchical Tabs */}
      <HierarchicalTabs
        activeTab={activeTab}
        onTabChange={handleTabChange}
        breadcrumbs={breadcrumbs}
        onBreadcrumbClick={handleBreadcrumbClick}
      />

      {/* Portfolio Modal */}
      {showPortfolioModal && (
        <PortfolioModal
          portfolios={portfolios || []}
          onClose={() => setShowPortfolioModal(false)}
          onSelect={async (portfolioId: number) => {
            try {
              if (selectedRows.size === 1) {
                const campaignId = Array.from(selectedRows)[0];
                await addCampaignToPortfolio(campaignId, portfolioId);
              } else {
                await bulkAddCampaignsToPortfolio(Array.from(selectedRows), portfolioId);
              }
              queryClient.invalidateQueries({ queryKey: ['campaigns'] });
              setShowPortfolioModal(false);
              setSelectedRows(new Set());
            } catch (error) {
              console.error('Failed to add campaign to portfolio:', error);
            }
          }}
        />
      )}

      {/* Master Performance Chart (shown for campaigns tab) */}
      {activeTab === 'campaigns' && trends && trends.length > 0 && (
        <MasterPerformanceChart
          data={trends.map(t => ({
            date: t.date,
            spend: t.spend,
            sales: t.sales,
            acos: t.acos,
            roas: t.roas,
          }))}
          height={400}
        />
      )}

      {/* Tab Content */}
      {renderTabContent()}
    </div>
  );
}

// Portfolio Modal Component
function PortfolioModal({
  portfolios,
  onClose,
  onSelect,
}: {
  portfolios: Portfolio[];
  onClose: () => void;
  onSelect: (portfolioId: number) => void;
}) {
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<number | null>(null);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="card p-6 max-w-md w-full">
        <h2 className="text-xl font-bold mb-4">Add Campaign to Portfolio</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Select Portfolio</label>
            <select
              value={selectedPortfolioId || ''}
              onChange={(e) => setSelectedPortfolioId(e.target.value ? parseInt(e.target.value) : null)}
              className="select w-full"
            >
              <option value="">Choose a portfolio...</option>
              {portfolios.map((p) => (
                <option key={p.portfolio_id} value={p.portfolio_id.toString()}>
                  {p.portfolio_name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button
              onClick={() => {
                if (selectedPortfolioId) {
                  onSelect(selectedPortfolioId);
                }
              }}
              disabled={!selectedPortfolioId}
              className="btn btn-primary"
            >
              Add
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

