/**
 * API Client for Amazon PPC AI Dashboard
 * Updated to support full AI Rule Engine control and database integration
 */

import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors (redirect to login)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// ============================================================================
// TYPES
// ============================================================================

export interface MetricComparison {
  value: number;
  change_percentage: number;
  direction: 'up' | 'down' | 'neutral';
}

export interface OverviewMetrics {
  spend: number;
  sales: number;
  acos: number;
  roas: number;
  orders: number;
  impressions: number;
  clicks: number;
  ctr: number;
  cvr: number;
  cpc: number;
  ai_activity_count: number;
  account_health_score: number;
  pending_recommendations: number;
  applied_today: number;
  spend_comparison?: MetricComparison;
  sales_comparison?: MetricComparison;
  acos_comparison?: MetricComparison;
  roas_comparison?: MetricComparison;
}

export interface TrendDataPoint extends Record<string, string | number> {
  date: string;
  spend: number;
  sales: number;
  acos: number;
  roas: number;
}

export interface Alert {
  id: string;
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  entity_type?: string;
  entity_id?: number;
  entity_name?: string;
  created_at: string;
}

export interface Campaign extends Record<string, unknown> {
  campaign_id: number;
  campaign_name: string;
  campaign_type: string;
  status: string;
  spend: number;
  sales: number;
  acos: number | null;
  roas: number | null;
  orders: number;
  budget: number;
  impressions: number;
  clicks: number;
  ctr: number;
  cvr: number;
  ai_recommendation: string | null;
}

export interface Keyword extends Record<string, unknown> {
  keyword_id: number;
  keyword_text: string;
  match_type: string;
  campaign_id: number;
  ad_group_id: number;
  bid: number;
  state: string;
  spend: number;
  sales: number;
  acos: number | null;
  roas: number | null;
  orders: number;
  impressions: number;
  clicks: number;
  ctr: number;
  cvr: number;
  ai_suggested_bid: number | null;
  confidence_score: number | null;
  reason: string | null;
  is_locked: boolean;
  lock_reason: string | null;
}

export interface Recommendation extends Record<string, unknown> {
  id: string;
  entity_type: string;
  entity_id: number;
  entity_name: string;
  recommendation_type: string;
  current_value: number;
  recommended_value: number;
  adjustment_percentage: number;
  priority: 'critical' | 'high' | 'medium' | 'low';
  confidence: number;
  reason: string;
  estimated_impact: string | null;
  intelligence_signals?: Record<string, unknown>;
  created_at: string;
  status: string;
}

export interface Rule {
  id: string;
  name: string;
  description: string;
  logic: string;
  is_active: boolean;
  trigger_frequency: string;
  last_execution: string | null;
  last_result: string | null;
  parameters?: Record<string, unknown>;
}

export interface NegativeCandidate extends Record<string, unknown> {
  keyword_id: number;
  keyword_text: string;
  search_term?: string;
  match_type: string;
  campaign_id: number;
  ad_group_id: number;
  spend: number;
  clicks: number;
  impressions: number;
  orders: number;
  severity: string;
  confidence: number;
  reason: string;
  suggested_action: string;
  status: string;
}

export interface ChangeLogEntry extends Record<string, unknown> {
  id: number;
  timestamp: string;
  entity_type: string;
  entity_id: number;
  entity_name: string;
  action: string;
  old_value: number;
  new_value: number;
  change_percentage: number;
  reason: string;
  triggered_by: string;
  status: string;
  outcome_label?: string;
  outcome_score?: number;
}

export interface StrategyConfig {
  strategy: string;
  target_acos: number;
  max_bid_cap: number;
  min_bid_floor: number;
  ai_mode: string;
  enable_dayparting: boolean;
  enable_inventory_protection: boolean;
  enable_brand_defense: boolean;
}

export interface SearchResult {
  type: 'campaign' | 'keyword' | 'ad_group';
  id: number;
  name: string;
  campaign_id?: number;
  campaign_name?: string;
  ad_group_id?: number;
  ad_group_name?: string;
  match_score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export interface AIControlConfig {
  // Core Settings
  target_acos: number;
  acos_tolerance: number;
  roas_target: number;
  
  // Bid Limits
  bid_floor: number;
  bid_cap: number;
  bid_max_adjustment: number;
  
  // Re-entry Control
  enable_re_entry_control: boolean;
  bid_change_cooldown_days: number;
  min_bid_change_threshold: number;
  
  // Oscillation Prevention
  enable_oscillation_detection: boolean;
  oscillation_lookback_days: number;
  oscillation_direction_change_threshold: number;
  
  // Safety Controls
  enable_spend_safeguard: boolean;
  spend_spike_threshold: number;
  enable_comprehensive_safety_veto: boolean;
  account_daily_limit: number;
  
  // Order-Based Scaling
  enable_order_based_scaling: boolean;
  order_tier_1_adjustment: number;
  order_tier_2_3_adjustment: number;
  order_tier_4_plus_adjustment: number;
  
  // Spend No-Sale Logic
  enable_spend_no_sale_logic: boolean;
  no_sale_reduction_tier_1: number;
  no_sale_reduction_tier_2: number;
  no_sale_reduction_tier_3: number;
  
  // Performance Thresholds
  min_impressions: number;
  min_clicks: number;
  min_conversions: number;
  
  // Learning Loop
  enable_learning_loop: boolean;
  learning_success_threshold: number;
  learning_failure_threshold: number;
  min_training_samples: number;
  
  // Feature Flags
  enable_warm_up_mode: boolean;
  enable_intelligence_engines: boolean;
  enable_advanced_bid_optimization: boolean;
}

export interface BidLock {
  entity_type: string;
  entity_id: number;
  entity_name?: string;
  locked_until: string;
  lock_reason: string;
  last_change_id?: number;
}

export interface Oscillation {
  entity_type: string;
  entity_id: number;
  entity_name?: string;
  direction_changes: number;
  is_oscillating: boolean;
  last_change_date?: string;
}

export interface LearningOutcome {
  id: number;
  recommendation_id: string;
  entity_type: string;
  entity_id: number;
  adjustment_type: string;
  recommended_value: number;
  applied_value: number;
  outcome: string;
  improvement_percentage: number;
  timestamp: string;
}

export interface ModelTrainingStatus {
  model_version: number;
  status: string;
  train_accuracy?: number;
  test_accuracy?: number;
  train_auc?: number;
  test_auc?: number;
  promoted: boolean;
  completed_at?: string;
}

export interface LearningStats {
  total_outcomes: number;
  successes: number;
  failures: number;
  neutrals: number;
  success_rate: number;
  avg_improvement: number;
  recent_training_runs: ModelTrainingStatus[];
}

export interface EngineRun {
  start_time: string;
  end_time?: string;
  status: string;
  duration_seconds?: number;
  recommendations_count?: number;
  error?: string;
  campaigns?: number[];
  sync?: boolean;
  dry_run?: boolean;
  elapsed_seconds?: number;
}

export interface EngineStatus {
  is_running: boolean;
  last_run: EngineRun | null;
  current_run: EngineRun | null;
}

export interface EngineHistory {
  history: EngineRun[];
  total_runs: number;
}

// ============================================================================
// API FUNCTIONS - OVERVIEW / COMMAND CENTER
// ============================================================================

export const fetchOverviewMetrics = async (days: number = 7): Promise<OverviewMetrics> => {
  const response = await api.get(`/api/overview/metrics?days=${days}`);
  return response.data;
};

export const fetchTrends = async (days: number = 30): Promise<TrendDataPoint[]> => {
  const response = await api.get(`/api/overview/trends?days=${days}`);
  return response.data;
};

export const fetchAlerts = async (limit: number = 10): Promise<Alert[]> => {
  const response = await api.get(`/api/overview/alerts?limit=${limit}`);
  return response.data;
};

// ============================================================================
// API FUNCTIONS - CAMPAIGNS
// ============================================================================

export const fetchCampaigns = async (days: number = 7): Promise<Campaign[]> => {
  const response = await api.get(`/api/campaigns?days=${days}`);
  return response.data;
};

export const fetchCampaignDetails = async (campaignId: number, days: number = 7) => {
  const response = await api.get(`/api/campaigns/${campaignId}?days=${days}`);
  return response.data;
};

export const applyCampaignAction = async (campaignId: number, action: {
  action_type: string;
  old_value?: number;
  new_value: number;
  reason?: string;
}) => {
  const response = await api.post(`/api/campaigns/${campaignId}/action`, {
    entity_type: 'campaign',
    entity_id: campaignId,
    ...action,
  });
  return response.data;
};

// ============================================================================
// API FUNCTIONS - KEYWORDS
// ============================================================================

export const fetchKeywords = async (params: {
  campaign_id?: number;
  ad_group_id?: number;
  days?: number;
  limit?: number;
}): Promise<Keyword[]> => {
  const queryParams = new URLSearchParams();
  if (params.campaign_id) queryParams.append('campaign_id', params.campaign_id.toString());
  if (params.ad_group_id) queryParams.append('ad_group_id', params.ad_group_id.toString());
  if (params.days) queryParams.append('days', params.days.toString());
  if (params.limit) queryParams.append('limit', params.limit.toString());
  
  const response = await api.get(`/api/keywords?${queryParams.toString()}`);
  return response.data;
};

export const updateKeywordBid = async (keywordId: number, action: {
  old_value?: number;
  new_value: number;
  reason?: string;
}) => {
  const response = await api.post(`/api/keywords/${keywordId}/bid`, {
    entity_type: 'keyword',
    entity_id: keywordId,
    action_type: 'bid',
    ...action,
  });
  return response.data;
};

export const lockKeywordBid = async (keywordId: number, days: number = 3, reason?: string) => {
  const params = new URLSearchParams();
  params.append('days', days.toString());
  if (reason) params.append('reason', reason);
  
  const response = await api.post(`/api/keywords/${keywordId}/lock?${params.toString()}`);
  return response.data;
};

export const unlockKeywordBid = async (keywordId: number) => {
  const response = await api.delete(`/api/keywords/${keywordId}/lock`);
  return response.data;
};

// ============================================================================
// API FUNCTIONS - RECOMMENDATIONS
// ============================================================================

export const fetchRecommendations = async (params?: {
  recommendation_type?: string;
  priority?: string;
  limit?: number;
}): Promise<Recommendation[]> => {
  const queryParams = new URLSearchParams();
  if (params?.recommendation_type) queryParams.append('recommendation_type', params.recommendation_type);
  if (params?.priority) queryParams.append('priority', params.priority);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  
  const response = await api.get(`/api/recommendations?${queryParams.toString()}`);
  return response.data;
};

export const approveRecommendation = async (recommendationId: string) => {
  const response = await api.post(`/api/recommendations/${recommendationId}/approve`);
  return response.data;
};

export const rejectRecommendation = async (recommendationId: string, reason?: string) => {
  const response = await api.post(`/api/recommendations/${recommendationId}/reject`, { reason });
  return response.data;
};

export const bulkApproveRecommendations = async (recommendationIds: string[]) => {
  const response = await api.post('/api/recommendations/bulk-approve', recommendationIds);
  return response.data;
};

// ============================================================================
// API FUNCTIONS - RULES
// ============================================================================

export const fetchRules = async (): Promise<Rule[]> => {
  const response = await api.get('/api/rules');
  return response.data;
};

export const fetchRuleDetails = async (ruleId: string) => {
  const response = await api.get(`/api/rules/${ruleId}`);
  return response.data;
};

// ============================================================================
// API FUNCTIONS - NEGATIVE KEYWORDS
// ============================================================================

export const fetchNegativeCandidates = async (params?: {
  campaign_id?: number;
  limit?: number;
}): Promise<NegativeCandidate[]> => {
  const queryParams = new URLSearchParams();
  if (params?.campaign_id) queryParams.append('campaign_id', params.campaign_id.toString());
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  
  const response = await api.get(`/api/negatives/candidates?${queryParams.toString()}`);
  return response.data;
};

export const approveNegativeKeyword = async (keywordId: number, matchType: string = 'negative_exact') => {
  const response = await api.post(`/api/negatives/${keywordId}/approve?match_type=${matchType}`);
  return response.data;
};

export const rejectNegativeKeyword = async (keywordId: number, reason?: string) => {
  const params = reason ? `?reason=${encodeURIComponent(reason)}` : '';
  const response = await api.post(`/api/negatives/${keywordId}/reject${params}`);
  return response.data;
};

export const holdNegativeKeyword = async (keywordId: number, days: number = 30) => {
  const response = await api.post(`/api/negatives/${keywordId}/hold?days=${days}`);
  return response.data;
};

// ============================================================================
// API FUNCTIONS - CHANGE LOG
// ============================================================================

export const fetchChangeLog = async (params?: {
  entity_type?: string;
  entity_id?: number;
  days?: number;
  limit?: number;
}): Promise<ChangeLogEntry[]> => {
  const queryParams = new URLSearchParams();
  if (params?.entity_type) queryParams.append('entity_type', params.entity_type);
  if (params?.entity_id) queryParams.append('entity_id', params.entity_id.toString());
  if (params?.days) queryParams.append('days', params.days.toString());
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  
  const response = await api.get(`/api/changelog?${queryParams.toString()}`);
  return response.data;
};

export const revertChange = async (changeId: number) => {
  const response = await api.post(`/api/changelog/${changeId}/revert`);
  return response.data;
};

// ============================================================================
// API FUNCTIONS - BID LOCKS & OSCILLATIONS
// ============================================================================

export const fetchBidLocks = async (entityType?: string): Promise<BidLock[]> => {
  const params = entityType ? `?entity_type=${entityType}` : '';
  const response = await api.get(`/api/bid-locks${params}`);
  return response.data;
};

export const fetchOscillations = async (): Promise<Oscillation[]> => {
  const response = await api.get('/api/oscillations');
  return response.data;
};

// ============================================================================
// API FUNCTIONS - LEARNING LOOP
// ============================================================================

export const fetchLearningOutcomes = async (params?: {
  days?: number;
  limit?: number;
}): Promise<LearningOutcome[]> => {
  const queryParams = new URLSearchParams();
  if (params?.days) queryParams.append('days', params.days.toString());
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  
  const response = await api.get(`/api/learning/outcomes?${queryParams.toString()}`);
  return response.data;
};

export const fetchLearningStats = async (days: number = 30): Promise<LearningStats> => {
  const response = await api.get(`/api/learning/stats?days=${days}`);
  return response.data;
};

// ============================================================================
// API FUNCTIONS - STRATEGY CONFIGURATION
// ============================================================================

export const fetchStrategyConfig = async (): Promise<StrategyConfig> => {
  const response = await api.get('/api/config/strategy');
  return response.data;
};

export const updateStrategyConfig = async (config: Partial<StrategyConfig>) => {
  const response = await api.post('/api/config/strategy', config);
  return response.data;
};

// ============================================================================
// API FUNCTIONS - AI CONTROL (COMPREHENSIVE)
// ============================================================================

export const fetchAIControlConfig = async (): Promise<AIControlConfig> => {
  const response = await api.get('/api/config/ai-control');
  return response.data;
};

export const updateAIControlConfig = async (config: Partial<AIControlConfig>) => {
  const response = await api.post('/api/config/ai-control', config);
  return response.data;
};

// ============================================================================
// API FUNCTIONS - ENGINE EXECUTION CONTROL
// ============================================================================

export const fetchEngineStatus = async (): Promise<EngineStatus> => {
  const response = await api.get('/api/engine/status');
  return response.data;
};

export const triggerEngineExecution = async (params?: {
  campaigns?: number[];
  sync?: boolean;
  dry_run?: boolean;
}) => {
  const response = await api.post('/api/engine/trigger', params || {});
  return response.data;
};

export const fetchEngineHistory = async (limit: number = 10): Promise<EngineHistory> => {
  const response = await api.get(`/api/engine/history?limit=${limit}`);
  return response.data;
};

// ============================================================================
// API FUNCTIONS - SEARCH
// ============================================================================

export const search = async (query: string, limit: number = 20): Promise<SearchResponse> => {
  const response = await api.get('/api/search', {
    params: { q: query, limit },
  });
  return response.data;
};

export default api;
