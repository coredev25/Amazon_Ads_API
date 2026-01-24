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
  FileText,
  Target,
  Settings,
  ChevronDown,
} from 'lucide-react';
import SmartGrid from '@/components/SmartGrid';
import HierarchicalTabs, { type TabType } from '@/components/HierarchicalTabs';
import DateRangePicker, { type DateRange } from '@/components/DateRangePicker';
import MasterPerformanceChart, { type EventAnnotation } from '@/components/MasterPerformanceChart';
import InventoryBadge from '@/components/InventoryBadge';
import {
  fetchCampaigns,
  fetchPortfolios,
  fetchAdGroups,
  fetchAds,
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
  fetchEventAnnotations,
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
    queryKey: ['trends', days, dateRange.startDate, dateRange.endDate],
    queryFn: () => {
      if (dateRange.type === 'custom' && dateRange.startDate && dateRange.endDate) {
        return fetchTrends(undefined, dateRange.startDate, dateRange.endDate);
      }
      return fetchTrends(days);
    },
    enabled: activeTab === 'campaigns',
  });

  // Fetch event annotations for chart
  const { data: eventAnnotations = [] } = useQuery<EventAnnotation[]>({
    queryKey: ['eventAnnotations', days, dateRange.startDate, dateRange.endDate],
    queryFn: () => {
      if (dateRange.type === 'custom' && dateRange.startDate && dateRange.endDate) {
        return fetchEventAnnotations(undefined, dateRange.startDate, dateRange.endDate);
      }
      return fetchEventAnnotations(days);
    },
    enabled: activeTab === 'campaigns',
  });

  // Calculate previous period data for comparison
  const previousPeriodData = useMemo(() => {
    if (!trends || trends.length === 0) return undefined;
    
    const periodLength = trends.length;
    const previousStartDate = new Date(trends[0].date);
    previousStartDate.setDate(previousStartDate.getDate() - periodLength);
    
    // For now, return undefined - this would need to fetch actual previous period data
    // In a real implementation, you'd fetch trends for the previous period
    return undefined;
  }, [trends]);

  // Breadcrumbs - Show "All Campaigns > [Campaign Name] > Ad Groups" format
  const breadcrumbs = useMemo(() => {
    const crumbs = [];
    if (selectedCampaign && activeTab !== 'campaigns' && activeTab !== 'portfolios') {
      crumbs.push({ type: 'campaigns' as TabType, id: selectedCampaign.id, name: selectedCampaign.name });
    }
    if (selectedAdGroup && (activeTab === 'keywords' || activeTab === 'targeting' || activeTab === 'search_terms' || activeTab === 'ads')) {
      crumbs.push({ type: 'ad_groups' as TabType, id: selectedAdGroup.id, name: selectedAdGroup.name });
    }
    return crumbs;
  }, [selectedCampaign, selectedAdGroup, activeTab]);

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

  const { data: ads, isLoading: adsLoading } = useQuery({
    queryKey: ['ads', selectedCampaign?.id, selectedAdGroup?.id, days],
    queryFn: () => fetchAds(selectedCampaign?.id, selectedAdGroup?.id, days),
    enabled: activeTab === 'ads' && (selectedCampaign !== null || selectedAdGroup !== null),
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

  const filteredPortfolios = useMemo(() => {
    return portfolios?.filter(p => {
      if (statusFilter === 'all') return true;
      return p.status?.toLowerCase() === statusFilter.toLowerCase();
    }) || [];
  }, [portfolios, statusFilter]);

  const filteredCampaigns = useMemo(() => {
    return campaigns?.filter(c => {
      if (statusFilter === 'all') return true;
      return c.status?.toLowerCase() === statusFilter.toLowerCase();
    }) || [];
  }, [campaigns, statusFilter]);

  const filteredAdGroups = useMemo(() => {
    return adGroups?.filter(ag => {
      if (statusFilter === 'all') return true;
      return ag.status?.toLowerCase() === statusFilter.toLowerCase();
    }) || [];
  }, [adGroups, statusFilter]);

  const filteredAds = useMemo(() => {
    return ads?.filter(ad => {
      if (statusFilter === 'all') return true;
      return ad.status?.toLowerCase() === statusFilter.toLowerCase();
    }) || [];
  }, [ads, statusFilter]);

  const filteredKeywords = useMemo(() => {
    return keywords?.filter(k => {
      if (statusFilter === 'all') return true;
      return k.state?.toLowerCase() === statusFilter.toLowerCase();
    }) || [];
  }, [keywords, statusFilter]);

  const actionMutation = useMutation({
    mutationFn: ({
      entityId,
      action,
    }: {
      entityId: number;
      action: { action_type: string; new_value: number; old_value?: number; reason?: string };
    }) => applyCampaignAction(entityId, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['ad-groups'] });
    },
  });

  const handleTabChange = (tab: TabType) => {
    // Allow navigation to top-level tabs (portfolios, campaigns) - reset selections
    if (tab === 'portfolios' || tab === 'campaigns') {
      setSelectedCampaign(null);
      setSelectedAdGroup(null);
      setActiveTab(tab);
    } 
    // For drill-down tabs, require proper context
    else if (tab === 'ad_groups' && !selectedCampaign) {
      // If switching to ad_groups without a selected campaign, stay on campaigns
      setActiveTab('campaigns');
    } else if ((tab === 'ads' || tab === 'keywords' || tab === 'targeting' || tab === 'search_terms') && !selectedAdGroup && !selectedCampaign) {
      // If switching to child tabs without context, go back to campaigns
      setActiveTab('campaigns');
    } else if (tab === 'placements' && !selectedCampaign) {
      // Placements require a campaign
      setActiveTab('campaigns');
    } else {
      // Valid navigation - allow it
      setActiveTab(tab);
    }
  };

  const handleBreadcrumbClick = (item: { type: TabType; id?: number; name?: string }) => {
    if (item.type === 'campaigns' && !item.id) {
      // "All Campaigns" clicked - reset everything
      setSelectedCampaign(null);
      setSelectedAdGroup(null);
      setActiveTab('campaigns');
    } else if (item.type === 'campaigns' && item.id) {
      // Campaign name clicked - go to ad groups for that campaign
      const campaign = campaigns?.find(c => c.campaign_id === item.id);
      if (campaign) {
        setSelectedCampaign({ id: campaign.campaign_id, name: campaign.campaign_name });
        setSelectedAdGroup(null);
        setActiveTab('ad_groups');
      }
    } else if (item.type === 'ad_groups' && item.id) {
      // Ad group name clicked - go to keywords for that ad group
      const adGroup = adGroups?.find(ag => ag.ad_group_id === item.id);
      if (adGroup) {
        setSelectedAdGroup({ id: adGroup.ad_group_id, name: adGroup.ad_group_name });
        setActiveTab('keywords');
      }
    }
  };

  const handleCampaignClick = (campaign: Campaign, e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    // Auto-switch to Ad Groups tab and filter to show only ad groups within that campaign
    setSelectedCampaign({ id: campaign.campaign_id, name: campaign.campaign_name });
    setSelectedAdGroup(null);
    setActiveTab('ad_groups');
  };

  const handleAdGroupClick = (adGroup: { ad_group_id: number; ad_group_name: string }) => {
    setSelectedAdGroup({ id: adGroup.ad_group_id, name: adGroup.ad_group_name });
    setActiveTab('keywords');
  };

  function formatCsvValue(value: unknown) {
    if (value === null || value === undefined) return '';
    const stringValue = String(value);
    if (stringValue.includes('"') || stringValue.includes(',') || stringValue.includes('\n')) {
      return `"${stringValue.replace(/"/g, '""')}"`;
    }
    return stringValue;
  }

  function downloadCsv(filename: string, rows: Record<string, unknown>[]) {
    if (!rows.length) return;
    const headers = Object.keys(rows[0]);
    const lines = [
      headers.map(formatCsvValue).join(','),
      ...rows.map(row => headers.map(key => formatCsvValue(row[key])).join(',')),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }

  const handleExportCsv = () => {
    const today = new Date().toISOString().split('T')[0];
    const payload = (() => {
      switch (activeTab) {
        case 'portfolios':
          return {
            filename: `portfolios-${today}.csv`,
            rows: filteredPortfolios.map(p => ({
              portfolio_name: p.portfolio_name,
              status: p.status,
              campaign_count: p.campaign_count,
              total_spend: p.total_spend,
              total_sales: p.total_sales,
              acos: p.acos,
            })),
          };
        case 'campaigns':
          return {
            filename: `campaigns-${today}.csv`,
            rows: filteredCampaigns.map(c => ({
              campaign_name: c.campaign_name,
              status: c.status,
              spend: c.spend,
              sales: c.sales,
              acos: c.acos,
              roas: c.roas,
              orders: c.orders,
              campaign_type: c.campaign_type,
              portfolio_name: c.portfolio_name,
            })),
          };
        case 'ad_groups':
          return {
            filename: `ad-groups-${today}.csv`,
            rows: filteredAdGroups.map(ag => ({
              ad_group_name: ag.ad_group_name,
              status: ag.status,
              spend: ag.spend,
              sales: ag.sales,
              acos: ag.acos,
              orders: ag.orders,
            })),
          };
        case 'ads':
          return {
            filename: `ads-${today}.csv`,
            rows: filteredAds.map(ad => ({
              asin: ad.asin,
              sku: ad.sku,
              status: ad.status,
              impressions: ad.impressions,
              clicks: ad.clicks,
              spend: ad.spend,
              sales: ad.sales,
              acos: ad.acos,
              roas: ad.roas,
              orders: ad.orders,
            })),
          };
        case 'keywords':
          return {
            filename: `keywords-${today}.csv`,
            rows: filteredKeywords.map(k => ({
              keyword_text: k.keyword_text,
              match_type: k.match_type,
              bid: k.bid,
              spend: k.spend,
              sales: k.sales,
              acos: k.acos,
              orders: k.orders,
            })),
          };
        case 'targeting':
          return {
            filename: `targeting-${today}.csv`,
            rows: (targeting || []).map(t => ({
              target_value: t.target_value,
              target_type: t.target_type,
              bid: t.bid,
              spend: t.spend,
              sales: t.sales,
              acos: t.acos,
            })),
          };
        case 'search_terms':
          return {
            filename: `search-terms-${today}.csv`,
            rows: (searchTerms || []).map(t => ({
              search_term: t.search_term,
              impressions: t.impressions,
              clicks: t.clicks,
              spend: t.spend,
              sales: t.sales,
              orders: t.orders,
              harvest_action: t.harvest_action,
            })),
          };
        case 'placements':
          return {
            filename: `placements-${today}.csv`,
            rows: (placements || []).map(p => ({
              placement: p.placement,
              impressions: p.impressions,
              clicks: p.clicks,
              spend: p.spend,
              sales: p.sales,
              acos: p.acos,
            })),
          };
        default:
          return { filename: `export-${today}.csv`, rows: [] };
      }
    })();
    downloadCsv(payload.filename, payload.rows);
  };

  // Render content based on active tab
  const renderTabContent = () => {
    const isLoading = 
      (activeTab === 'portfolios' && portfoliosLoading) ||
      (activeTab === 'campaigns' && campaignsLoading) ||
      (activeTab === 'ad_groups' && adGroupsLoading) ||
      (activeTab === 'ads' && adsLoading) ||
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
      case 'ads':
        if (!selectedCampaign && !selectedAdGroup) {
          return (
            <div className="card p-8 text-center text-gray-500">
              <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Select a campaign or ad group to view ads</p>
            </div>
          );
        }
        return renderAds();
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
    return (
      <SmartGrid
        data={filteredPortfolios}
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
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
      />
    );
  };

  const renderCampaigns = () => {
    return (
      <div className="space-y-4">
        {/* Toolbar */}
        <div className="card p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
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
            </div>
            <div className="flex items-center gap-2">
              <DateRangePicker value={dateRange} onChange={setDateRange} />
              <button
                className="btn btn-sm btn-secondary"
                title="Settings"
              >
                <Settings className="w-4 h-4" />
              </button>
              <button
                onClick={() => {
                  handleExportCsv();
                }}
                className="btn btn-sm btn-secondary"
              >
                <FileDown className="w-4 h-4" />
                Export CSV
              </button>
            </div>
          </div>
        </div>
        <SmartGrid
          data={filteredCampaigns}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          statusFilterOptions={[
            { value: 'all', label: 'All Status' },
            { value: 'enabled', label: 'Enabled' },
            { value: 'paused', label: 'Paused' },
            { value: 'archived', label: 'Archived' },
          ]}
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
          onSelectAllRows={(ids, select) => {
            const newSelection = new Set(selectedRows);
            if (select) {
              // Select all provided IDs
              ids.forEach(id => newSelection.add(id as number));
            } else {
              // Deselect all provided IDs
              ids.forEach(id => newSelection.delete(id as number));
            }
            setSelectedRows(newSelection);
          }}
          onBulkAction={async (action, ids, params) => {
            if (action === 'move_to_portfolio' && params?.portfolioId) {
              await bulkAddCampaignsToPortfolio(ids.map(id => Number(id)), params.portfolioId);
            } else if (action === 'pause' || action === 'enable' || action === 'archive') {
              // Bulk status changes - implement based on your API requirements
              console.log(`Bulk ${action} action for ${ids.length} campaigns`);
            }
            queryClient.invalidateQueries({ queryKey: ['campaigns'] });
          }}
        columns={[
          {
            key: 'campaign_name',
            header: 'Campaign Name',
            sortable: true,
            render: (value: unknown, row: Campaign) => (
              <div className="flex items-center gap-2">
                <button
                  onClick={(e) => handleCampaignClick(row, e)}
                  className="text-left hover:text-amazon-orange transition-colors flex-1"
                  type="button"
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
                {String(row.status || '').toLowerCase() === 'enabled' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      actionMutation.mutate({
                        entityId: row.campaign_id,
                        action: { action_type: 'pause', new_value: 0, reason: 'Manual pause from dashboard' },
                      });
                    }}
                    className="btn btn-sm btn-secondary"
                    title="Pause Campaign"
                  >
                    <Pause className="w-3 h-3" />
                  </button>
                )}
                {String(row.status || '').toLowerCase() !== 'enabled' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      actionMutation.mutate({
                        entityId: row.campaign_id,
                        action: { action_type: 'enable', new_value: 1, reason: 'Manual enable from dashboard' },
                      });
                    }}
                    className="btn btn-sm btn-secondary"
                    title="Enable Campaign"
                  >
                    <Play className="w-3 h-3" />
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowPortfolioModal(true);
                    setSelectedRows(new Set([row.campaign_id]));
                  }}
                  className="btn btn-sm btn-secondary"
                  title={row.portfolio_id ? 'Move to Portfolio' : 'Add to Portfolio'}
                >
                  <Package className="w-3 h-3" />
                </button>
              </div>
            ),
          },
        ]}
        keyField="campaign_id"
        loading={campaignsLoading}
        emptyMessage="No campaigns found"
        />
      </div>
    );
  };

  const renderAdGroups = () => {
    return (
      <SmartGrid
        data={filteredAdGroups}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
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

  const renderAds = () => {
    return (
      <SmartGrid
        data={filteredAds}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        columns={[
          {
            key: 'asin',
            header: 'ASIN',
            sortable: true,
            render: (value: unknown, row: any) => (
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900 dark:text-white">{value as string}</span>
                {row.inventory_status && (
                  <InventoryBadge inventoryStatus={row.inventory_status} />
                )}
              </div>
            ),
          },
          {
            key: 'sku',
            header: 'SKU',
            sortable: true,
            render: (value: unknown) => (
              <span className="text-gray-600 dark:text-gray-400">{value as string || '-'}</span>
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
        ]}
        keyField="ad_id"
        loading={adsLoading}
        emptyMessage="No ads found"
      />
    );
  };

  const renderKeywords = () => {
    return (
      <SmartGrid
        data={filteredKeywords}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
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
      <SmartGrid
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
      <SmartGrid
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
      <SmartGrid
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
            spend: typeof t.spend === 'number' ? t.spend : parseFloat(String(t.spend)) || 0,
            sales: typeof t.sales === 'number' ? t.sales : parseFloat(String(t.sales)) || 0,
            acos: typeof t.acos === 'number' ? t.acos : parseFloat(String(t.acos)) || 0,
            roas: typeof t.roas === 'number' ? t.roas : parseFloat(String(t.roas)) || 0,
            impressions: typeof t.impressions === 'number' ? t.impressions : parseInt(String(t.impressions)) || undefined,
            clicks: typeof t.clicks === 'number' ? t.clicks : parseInt(String(t.clicks)) || undefined,
            cpc: typeof t.cpc === 'number' ? t.cpc : parseFloat(String(t.cpc)) || undefined,
            ctr: typeof t.ctr === 'number' ? t.ctr : parseFloat(String(t.ctr)) || undefined,
          }))}
          previousPeriodData={previousPeriodData}
          eventAnnotations={eventAnnotations}
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

