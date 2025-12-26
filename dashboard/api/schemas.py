"""
Pydantic schemas for API request/response validation
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class DateRangeRequest(BaseModel):
    """Date range filter for queries"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    days: int = Field(default=7, ge=1, le=90)


class ActionRequest(BaseModel):
    """Request for applying an action to an entity"""
    entity_type: str = Field(..., description="Entity type: campaign, ad_group, keyword")
    entity_id: int = Field(..., description="Entity ID")
    action_type: str = Field(..., description="Action type: bid, budget, pause, enable")
    old_value: Optional[float] = Field(None, description="Previous value")
    new_value: float = Field(..., description="New value to set")
    reason: Optional[str] = Field(None, description="Reason for the action")


class BulkActionRequest(BaseModel):
    """Request for bulk actions"""
    actions: List[ActionRequest]


class StrategyConfigRequest(BaseModel):
    """Strategy configuration update request"""
    strategy: str = Field(..., description="Strategy: launch, growth, profit, liquidate")
    target_acos: float = Field(..., ge=0.01, le=1.0, description="Target ACOS (0.01-1.0)")
    max_bid_cap: float = Field(..., ge=0.02, le=100.0, description="Maximum bid cap")
    ai_mode: str = Field(..., description="AI mode: autonomous, human_review, warm_up")
    enable_dayparting: bool = Field(default=False)
    enable_inventory_protection: bool = Field(default=False)
    enable_brand_defense: bool = Field(default=False)


class RecommendationActionRequest(BaseModel):
    """Request for recommendation approval/rejection"""
    recommendation_id: str
    action: str = Field(..., description="Action: approve, reject, modify, schedule")
    modified_value: Optional[float] = None
    scheduled_time: Optional[datetime] = None
    reason: Optional[str] = None


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class OverviewMetricsResponse(BaseModel):
    """Overview metrics response"""
    spend: float
    sales: float
    acos: float
    roas: float
    orders: int
    impressions: int
    clicks: int
    ctr: float
    cvr: float
    cpc: float
    ai_activity_count: int
    account_health_score: float


class TrendDataPointResponse(BaseModel):
    """Single trend data point"""
    date: str
    spend: float
    sales: float
    acos: float
    roas: float


class AlertResponse(BaseModel):
    """Alert response"""
    id: str
    type: str
    severity: str  # critical, high, medium, low
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    entity_name: Optional[str] = None
    created_at: str


class CampaignResponse(BaseModel):
    """Campaign data response"""
    campaign_id: int
    campaign_name: str
    campaign_type: str
    status: str
    spend: float
    sales: float
    acos: Optional[float]
    roas: Optional[float]
    orders: int
    budget: float
    impressions: int
    clicks: int
    ctr: float
    cvr: float
    ai_recommendation: Optional[str] = None


class KeywordResponse(BaseModel):
    """Keyword data response"""
    keyword_id: int
    keyword_text: str
    match_type: str
    campaign_id: int
    ad_group_id: int
    bid: float
    spend: float
    sales: float
    acos: Optional[float]
    roas: Optional[float]
    orders: int
    impressions: int
    clicks: int
    ctr: float
    cvr: float
    ai_suggested_bid: Optional[float] = None
    confidence_score: Optional[float] = None
    reason: Optional[str] = None


class RecommendationResponse(BaseModel):
    """AI recommendation response"""
    id: str
    entity_type: str
    entity_id: int
    entity_name: str
    recommendation_type: str
    current_value: float
    recommended_value: float
    adjustment_percentage: float
    priority: str  # critical, high, medium, low
    confidence: float
    reason: str
    estimated_impact: Optional[str] = None
    created_at: str
    status: str = "pending"


class RuleResponse(BaseModel):
    """Rule information response"""
    id: str
    name: str
    description: str
    logic: str
    is_active: bool
    trigger_frequency: str
    last_execution: Optional[str]
    last_result: Optional[str]


class NegativeCandidateResponse(BaseModel):
    """Negative keyword candidate response"""
    keyword_id: int
    keyword_text: str
    search_term: Optional[str] = None
    match_type: str
    spend: float
    clicks: int
    orders: int
    severity: str
    confidence: float
    reason: str
    suggested_action: str


class ChangeLogResponse(BaseModel):
    """Change log entry response"""
    id: int
    timestamp: str
    entity_type: str
    entity_id: int
    entity_name: str
    action: str
    old_value: float
    new_value: float
    reason: str
    triggered_by: str
    status: str


class StrategyConfigResponse(BaseModel):
    """Strategy configuration response"""
    strategy: str
    target_acos: float
    max_bid_cap: float
    ai_mode: str
    enable_dayparting: bool
    enable_inventory_protection: bool
    enable_brand_defense: bool


class ActionResultResponse(BaseModel):
    """Generic action result response"""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class BulkActionResultResponse(BaseModel):
    """Bulk action result response"""
    status: str
    total_count: int
    success_count: int
    failed_count: int
    results: List[ActionResultResponse]


# ============================================================================
# DASHBOARD-SPECIFIC SCHEMAS
# ============================================================================

class DashboardSummaryResponse(BaseModel):
    """Dashboard summary for quick overview"""
    total_campaigns: int
    active_campaigns: int
    total_spend: float
    total_sales: float
    overall_acos: float
    overall_roas: float
    pending_recommendations: int
    critical_alerts: int
    ai_health_status: str


class PerformanceComparisonResponse(BaseModel):
    """Performance comparison between periods"""
    current_period: Dict[str, float]
    previous_period: Dict[str, float]
    change_percentage: Dict[str, float]
    trend_direction: Dict[str, str]  # up, down, neutral


class DaypartingData(BaseModel):
    """Dayparting heatmap data"""
    hour: int
    day_of_week: int  # 0 = Monday, 6 = Sunday
    value: float
    metric: str  # acos, ctr, cvr, conversion_rate


class InventoryHealthResponse(BaseModel):
    """Inventory health status"""
    asin: str
    product_name: str
    days_of_supply: int
    current_inventory: int
    ad_status: str
    recommended_action: Optional[str] = None

