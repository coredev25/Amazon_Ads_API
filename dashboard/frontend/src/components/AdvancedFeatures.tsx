'use client';

import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, AlertCircle, DollarSign } from 'lucide-react';
import { cn } from '@/utils/helpers';

interface FinancialMetricsProps {
  campaignId: string;
  date?: string;
}

interface FinancialData {
  spend: number;
  revenue: number;
  cogs: number;
  gross_profit: number;
  net_profit: number;
  acos: number;
  tacos: number;
  break_even_acos: number;
  roi: number;
  profit_margin: number;
}

export function FinancialMetricsCard({ campaignId, date }: FinancialMetricsProps) {
  const [metrics, setMetrics] = useState<FinancialData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch(`/api/financial-metrics/campaign/${campaignId}?date=${date || '2025-01-22'}`);
        if (response.ok) {
          const data = await response.json();
          setMetrics(data);
        } else {
          setError('Failed to load metrics');
        }
      } catch (err) {
        setError('Error loading metrics');
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [campaignId, date]);

  if (loading) return <div className="p-4">Loading financial metrics...</div>;
  if (error || !metrics) return <div className="p-4 text-red-600">{error || 'No data'}</div>;

  const isPositiveProfit = metrics.net_profit > 0;
  const isGoodAcos = metrics.acos < metrics.break_even_acos;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 p-4">
      {/* Revenue */}
      <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
        <div className="text-sm text-gray-600 mb-1">Revenue</div>
        <div className="text-2xl font-bold text-blue-600">${metrics.revenue.toFixed(2)}</div>
      </div>

      {/* Spend */}
      <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
        <div className="text-sm text-gray-600 mb-1">Spend</div>
        <div className="text-2xl font-bold text-orange-600">${metrics.spend.toFixed(2)}</div>
      </div>

      {/* Net Profit */}
      <div className={cn('p-4 rounded-lg border', isPositiveProfit ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200')}>
        <div className="text-sm text-gray-600 mb-1">Net Profit</div>
        <div className={cn('text-2xl font-bold flex items-center gap-1', isPositiveProfit ? 'text-green-600' : 'text-red-600')}>
          ${metrics.net_profit.toFixed(2)}
          {isPositiveProfit ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
        </div>
      </div>

      {/* ACoS */}
      <div className={cn('p-4 rounded-lg border', isGoodAcos ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200')}>
        <div className="text-sm text-gray-600 mb-1">ACoS</div>
        <div className={cn('text-2xl font-bold', isGoodAcos ? 'text-green-600' : 'text-yellow-600')}>
          {metrics.acos.toFixed(1)}%
        </div>
        <div className="text-xs text-gray-500 mt-1">Break-even: {metrics.break_even_acos.toFixed(1)}%</div>
      </div>

      {/* ROI */}
      <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
        <div className="text-sm text-gray-600 mb-1">ROI</div>
        <div className="text-2xl font-bold text-purple-600">{metrics.roi.toFixed(1)}%</div>
        <div className="text-xs text-gray-500 mt-1">Margin: {metrics.profit_margin.toFixed(1)}%</div>
      </div>
    </div>
  );
}

interface SearchTermHarvestProps {
  campaignId: string;
  harvestType: 'positive' | 'negative';
}

export function SearchTermHarvest({ campaignId, harvestType }: SearchTermHarvestProps) {
  const [terms, setTerms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    const fetchTerms = async () => {
      try {
        const endpoint = harvestType === 'positive' 
          ? `/api/search-terms/positive-harvest?campaign_id=${campaignId}`
          : `/api/search-terms/negative-harvest?campaign_id=${campaignId}`;
        
        const response = await fetch(endpoint);
        if (response.ok) {
          const data = await response.json();
          setTerms(data.search_terms);
        }
      } catch (error) {
        console.error('Error fetching search terms:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTerms();
  }, [campaignId, harvestType]);

  const handleApplyHarvest = async (term: any) => {
    try {
      setApplying(true);
      const response = await fetch('/api/search-terms/apply-harvest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          search_term: term.search_term,
          campaign_id: term.campaign_id,
          ad_group_id: term.ad_group_id,
          clicks: term.clicks,
          conversions: term.conversions,
          spend: term.spend,
          acos: term.acos,
          keyword_type: term.keyword_type,
          harvest_type: harvestType,
          status: 'pending'
        })
      });

      if (response.ok) {
        setTerms(terms.filter(t => t.search_term !== term.search_term));
      }
    } catch (error) {
      console.error('Error applying harvest:', error);
    } finally {
      setApplying(false);
    }
  };

  if (loading) return <div className="p-4">Loading search terms...</div>;

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold mb-4">
        {harvestType === 'positive' ? 'Positive Keywords to Add' : 'Negative Keywords to Add'} ({terms.length})
      </h3>
      
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {terms.map((term, idx) => (
          <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex-1">
              <div className="font-medium">{term.search_term}</div>
              <div className="text-sm text-gray-600">
                {harvestType === 'positive' 
                  ? `${term.conversions} orders • ${term.acos.toFixed(1)}% ACoS`
                  : `${term.clicks} clicks • ${term.spend.toFixed(2)} spend`
                }
              </div>
            </div>
            <button
              onClick={() => handleApplyHarvest(term)}
              disabled={applying}
              className="px-3 py-1 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {harvestType === 'positive' ? 'Add' : 'Add Negative'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

interface ChangeHistoryProps {
  entityType?: string;
  entityId?: string;
  limit?: number;
}

export function ChangeHistory({ entityType, entityId, limit = 50 }: ChangeHistoryProps) {
  const [changes, setChanges] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        let url = '/api/changes/history?limit=' + limit;
        if (entityType) url += '&entity_type=' + entityType;
        if (entityId) url += '&entity_id=' + entityId;

        const response = await fetch(url);
        if (response.ok) {
          const data = await response.json();
          setChanges(data.changes);
        }
      } catch (error) {
        console.error('Error fetching change history:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [entityType, entityId, limit]);

  if (loading) return <div className="p-4">Loading change history...</div>;

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold mb-4">Change History</h3>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {changes.map((change, idx) => (
          <div key={idx} className="p-3 bg-gray-50 rounded-lg border border-gray-200 text-sm">
            <div className="flex justify-between items-start mb-1">
              <span className="font-medium">{change.entity_name}</span>
              <span className={cn(
                'px-2 py-1 rounded text-xs',
                change.change_type === 'ai' ? 'bg-purple-100 text-purple-700' :
                change.change_type === 'manual' ? 'bg-blue-100 text-blue-700' :
                'bg-gray-100 text-gray-700'
              )}>
                {change.change_type.toUpperCase()}
              </span>
            </div>
            <div className="text-gray-600">
              {change.old_value} → {change.new_value}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {new Date(change.created_at).toLocaleString()} by {change.user_id}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface EventAnnotationProps {
  startDate: string;
  endDate: string;
  onEventCreated?: () => void;
}

export function EventAnnotationPanel({ startDate, endDate, onEventCreated }: EventAnnotationProps) {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const response = await fetch(`/api/events/annotations?start_date=${startDate}&end_date=${endDate}`);
        if (response.ok) {
          const data = await response.json();
          setEvents(data.events);
        }
      } catch (error) {
        console.error('Error fetching events:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
  }, [startDate, endDate]);

  if (loading) return <div className="p-4">Loading events...</div>;

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Event Annotations</h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700"
        >
          Add Event
        </button>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {events.map((event, idx) => (
          <div key={idx} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex justify-between items-start mb-1">
              <span className="font-medium">{event.title}</span>
              <span className={cn(
                'px-2 py-1 rounded text-xs',
                event.impact === 'positive' ? 'bg-green-100 text-green-700' :
                event.impact === 'negative' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-700'
              )}>
                {event.impact}
              </span>
            </div>
            <div className="text-sm text-gray-600">{event.description}</div>
            <div className="text-xs text-gray-500 mt-1">{event.date}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
