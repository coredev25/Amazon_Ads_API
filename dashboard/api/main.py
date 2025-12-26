"""
FastAPI Main Application for Amazon Vendor Central PPC AI Dashboard
Provides REST API endpoints for the React frontend to interact with the AI Rule Engine
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import logging
import json

# Load environment variables from .env file in project root
# Get project root directory (3 levels up from dashboard/api/main.py)
project_root = Path(__file__).parent.parent.parent

try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logging.info(f"Loaded environment variables from {env_path}")
    else:
        logging.warning(f".env file not found at {env_path}")
except ImportError:
    logging.warning("python-dotenv not installed, using system environment variables only")

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.ai_rule_engine.config import RuleConfig
from src.ai_rule_engine.database import DatabaseConnector
from src.ai_rule_engine.rule_engine import AIRuleEngine

# Import authentication module
from dashboard.api import auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
db_connector: Optional[DatabaseConnector] = None
ai_engine: Optional[AIRuleEngine] = None
rule_config: Optional[RuleConfig] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global db_connector, ai_engine, rule_config
    
    # Initialize database connection
    try:
        # Check if DB_PASSWORD is set
        if not os.getenv('DB_PASSWORD'):
            error_msg = (
                "DB_PASSWORD environment variable is required. "
                f"Please check your .env file at: {project_root / '.env'}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        db_connector = DatabaseConnector()
        rule_config = RuleConfig()
        ai_engine = AIRuleEngine(rule_config, db_connector)
        logger.info("Dashboard API initialized successfully")
    except ValueError as e:
        # Re-raise ValueError with clear message
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize dashboard API: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Dashboard API shutting down")


app = FastAPI(
    title="Amazon Vendor Central PPC AI Dashboard API",
    description="REST API for the PPC AI Dashboard - connects React frontend to AI Rule Engine",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class DateRangeParams(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    days: int = 7


class MetricComparison(BaseModel):
    """Comparison data for a metric"""
    value: float
    change_percentage: float
    direction: str  # 'up', 'down', 'neutral'


class OverviewMetrics(BaseModel):
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
    pending_recommendations: int = 0
    applied_today: int = 0
    # Comparison data
    spend_comparison: Optional[MetricComparison] = None
    sales_comparison: Optional[MetricComparison] = None
    acos_comparison: Optional[MetricComparison] = None
    roas_comparison: Optional[MetricComparison] = None


class TrendDataPoint(BaseModel):
    date: str
    spend: float
    sales: float
    acos: float
    roas: float


class Alert(BaseModel):
    id: str
    type: str
    severity: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    entity_name: Optional[str] = None
    created_at: str


class CampaignData(BaseModel):
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


class KeywordData(BaseModel):
    keyword_id: int
    keyword_text: str
    match_type: str
    campaign_id: int
    ad_group_id: int
    bid: float
    state: str
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
    is_locked: bool = False
    lock_reason: Optional[str] = None


class RecommendationData(BaseModel):
    id: str
    entity_type: str
    entity_id: int
    entity_name: str
    recommendation_type: str
    current_value: float
    recommended_value: float
    adjustment_percentage: float
    priority: str
    confidence: float
    reason: str
    estimated_impact: Optional[str] = None
    intelligence_signals: Optional[Dict[str, Any]] = None
    created_at: str
    status: str = "pending"


class RuleData(BaseModel):
    id: str
    name: str
    description: str
    logic: str
    is_active: bool
    trigger_frequency: str
    last_execution: Optional[str]
    last_result: Optional[str]
    parameters: Optional[Dict[str, Any]] = None


class StrategyConfig(BaseModel):
    strategy: str = Field(..., description="Strategy: 'launch', 'growth', 'profit', 'liquidate'")
    target_acos: float = Field(..., ge=0.01, le=1.0, description="Target ACOS (0.01-1.0)")
    max_bid_cap: float = Field(..., ge=0.02, le=100.0, description="Maximum bid cap")
    min_bid_floor: float = Field(default=0.02, ge=0.02, le=10.0, description="Minimum bid floor")
    ai_mode: str = Field(..., description="AI mode: 'autonomous', 'human_review', 'warm_up'")
    enable_dayparting: bool = False
    enable_inventory_protection: bool = False
    enable_brand_defense: bool = False


class AIControlConfig(BaseModel):
    """Comprehensive AI Rule Engine control configuration"""
    # Core Settings
    target_acos: float = Field(0.09, ge=0.01, le=1.0)
    acos_tolerance: float = Field(0.05, ge=0.01, le=0.5)
    roas_target: float = Field(11.11, ge=1.0, le=50.0)
    
    # Bid Limits
    bid_floor: float = Field(0.02, ge=0.02, le=1.0)
    bid_cap: float = Field(4.52, ge=0.5, le=100.0)
    bid_max_adjustment: float = Field(0.5, ge=0.1, le=1.0)
    
    # Re-entry Control
    enable_re_entry_control: bool = True
    bid_change_cooldown_days: int = Field(3, ge=1, le=14)
    min_bid_change_threshold: float = Field(0.05, ge=0.01, le=0.5)
    
    # Oscillation Prevention
    enable_oscillation_detection: bool = True
    oscillation_lookback_days: int = Field(14, ge=7, le=30)
    oscillation_direction_change_threshold: int = Field(3, ge=2, le=10)
    
    # Safety Controls
    enable_spend_safeguard: bool = True
    spend_spike_threshold: float = Field(2.0, ge=1.5, le=5.0)
    enable_comprehensive_safety_veto: bool = True
    account_daily_limit: float = Field(10000.0, ge=100.0, le=1000000.0)
    
    # Order-Based Scaling
    enable_order_based_scaling: bool = True
    order_tier_1_adjustment: float = Field(0.05, ge=0.01, le=0.2)
    order_tier_2_3_adjustment: float = Field(0.15, ge=0.05, le=0.3)
    order_tier_4_plus_adjustment: float = Field(0.30, ge=0.1, le=0.5)
    
    # Spend No-Sale Logic
    enable_spend_no_sale_logic: bool = True
    no_sale_reduction_tier_1: float = Field(0.15, ge=0.05, le=0.3)
    no_sale_reduction_tier_2: float = Field(0.25, ge=0.1, le=0.4)
    no_sale_reduction_tier_3: float = Field(0.35, ge=0.15, le=0.5)
    
    # Performance Thresholds
    min_impressions: int = Field(100, ge=10, le=1000)
    min_clicks: int = Field(5, ge=1, le=50)
    min_conversions: int = Field(1, ge=0, le=10)
    
    # Learning Loop
    enable_learning_loop: bool = True
    learning_success_threshold: float = Field(0.10, ge=0.01, le=0.5)
    learning_failure_threshold: float = Field(-0.05, ge=-0.5, le=0)
    min_training_samples: int = Field(100, ge=10, le=1000)
    
    # Feature Flags
    enable_warm_up_mode: bool = True
    enable_intelligence_engines: bool = True
    enable_advanced_bid_optimization: bool = True


class ActionRequest(BaseModel):
    entity_type: str
    entity_id: int
    action_type: str
    old_value: Optional[float] = None
    new_value: float
    reason: Optional[str] = None


class BulkActionRequest(BaseModel):
    actions: List[ActionRequest]


class NegativeCandidateData(BaseModel):
    keyword_id: int
    keyword_text: str
    search_term: Optional[str] = None
    match_type: str
    campaign_id: int
    ad_group_id: int
    spend: float
    clicks: int
    impressions: int
    orders: int
    severity: str
    confidence: float
    reason: str
    suggested_action: str
    status: str = "pending"


class ChangeLogEntry(BaseModel):
    id: int
    timestamp: str
    entity_type: str
    entity_id: int
    entity_name: str
    action: str
    old_value: float
    new_value: float
    change_percentage: float
    reason: str
    triggered_by: str
    status: str
    outcome_label: Optional[str] = None
    outcome_score: Optional[float] = None


class BidLockData(BaseModel):
    entity_type: str
    entity_id: int
    entity_name: Optional[str] = None
    locked_until: str
    lock_reason: str
    last_change_id: Optional[int] = None


class OscillationData(BaseModel):
    entity_type: str
    entity_id: int
    entity_name: Optional[str] = None
    direction_changes: int
    is_oscillating: bool
    last_change_date: Optional[str] = None


class SearchResult(BaseModel):
    type: str  # 'campaign', 'keyword', 'ad_group'
    id: int
    name: str
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    ad_group_id: Optional[int] = None
    ad_group_name: Optional[str] = None
    match_score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total: int


class LearningOutcomeData(BaseModel):
    id: int
    recommendation_id: str
    entity_type: str
    entity_id: int
    adjustment_type: str
    recommended_value: float
    applied_value: float
    outcome: str
    improvement_percentage: float
    timestamp: str


class ModelTrainingStatus(BaseModel):
    model_version: int
    status: str
    train_accuracy: Optional[float] = None
    test_accuracy: Optional[float] = None
    train_auc: Optional[float] = None
    test_auc: Optional[float] = None
    promoted: bool = False
    completed_at: Optional[str] = None


# ============================================================================
# API ENDPOINTS - OVERVIEW / COMMAND CENTER
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/signup", response_model=auth.UserResponse)
async def signup(user_data: auth.UserSignup):
    """
    Register a new user
    
    Process:
    1. User provides email, username, and password
    2. Server validates input (Pydantic models handle validation)
    3. Server checks if username/email already exists
    4. Server hashes the password using bcrypt
    5. Server stores user data in database with hashed password (NOT plain text)
    6. Returns user data (password_hash is never returned to client)
    """
    try:
        logger.info(f"Signup request for username: {user_data.username}, email: {user_data.email}")
        user = auth.create_user(db_connector, user_data)
        logger.info(f"User signup successful: {user_data.username}")
        return auth.UserResponse(
            id=user['id'],
            email=user['email'],
            username=user['username'],
            role=user['role'],
            is_active=user['is_active'],
            is_verified=user['is_verified'],
            last_login=None,
            created_at=user['created_at'].isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during signup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login", response_model=auth.Token)
async def login(credentials: auth.UserLogin):
    """
    Login and get access token
    
    Process:
    1. User provides username/email and password (plain text)
    2. Server retrieves user from database by username OR email
    3. Server gets stored password_hash from database
    4. Server verifies provided password against stored hash using bcrypt verify
       - bcrypt extracts salt from stored hash
       - bcrypt hashes provided password with that salt
       - bcrypt compares result with stored hash
    5. If passwords match:
       - Check if account is active
       - Update last_login timestamp
       - Generate JWT token
       - Return token to client
    6. If passwords don't match:
       - Return 401 error: "Incorrect username/email or password"
    """
    try:
        logger.info(f"Login attempt for username/email: {credentials.username}")
        user = auth.authenticate_user(db_connector, credentials.username, credentials.password)
        
        if not user:
            logger.warning(f"Login failed: Invalid credentials for username/email: {credentials.username}")
            raise HTTPException(
                status_code=401,
                detail="Incorrect username/email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        logger.info(f"Login successful for username/email: {credentials.username}, generating token")
        access_token = auth.create_access_token(
            data={"sub": str(user['id']), "username": user['username'], "role": user['role']}
        )
        
        return auth.Token(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user['id'],
                "email": user['email'],
                "username": user['username'],
                "role": user['role'],
                "is_verified": user['is_verified']
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/me", response_model=auth.UserResponse)
async def get_current_user_info(credentials: HTTPAuthorizationCredentials = Depends(auth.security)):
    """Get current user information"""
    try:
        user = auth.get_current_user(credentials, db_connector)
        return auth.UserResponse(
            id=user['id'],
            email=user['email'],
            username=user['username'],
            role=user['role'],
            is_active=user['is_active'],
            is_verified=user['is_verified'],
            last_login=user['last_login'].isoformat() if user['last_login'] else None,
            created_at=user['created_at'].isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/change-password")
async def change_user_password(
    password_data: auth.PasswordChange,
    credentials: HTTPAuthorizationCredentials = Depends(auth.security)
):
    """Change current user's password"""
    try:
        user = auth.get_current_user(credentials, db_connector)
        auth.change_password(
            db_connector,
            user['id'],
            password_data.current_password,
            password_data.new_password
        )
        return {"status": "success", "message": "Password changed successfully"}
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/logout")
async def logout():
    """Logout (client-side token removal)"""
    return {"status": "success", "message": "Logged out successfully"}


@app.get("/api/overview/metrics", response_model=OverviewMetrics)
async def get_overview_metrics(days: int = Query(7, ge=1, le=90)):
    """Get overview metrics for the Command Center"""
    try:
        # Get current period metrics
        campaigns = db_connector.get_campaigns_with_performance(days)
        
        # Aggregate metrics for current period
        total_spend = sum(float(c.get('total_cost', 0) or 0) for c in campaigns)
        total_sales = sum(float(c.get('total_sales', 0) or 0) for c in campaigns)
        total_impressions = sum(int(c.get('total_impressions', 0) or 0) for c in campaigns)
        total_clicks = sum(int(c.get('total_clicks', 0) or 0) for c in campaigns)
        total_orders = sum(int(c.get('total_conversions', 0) or 0) for c in campaigns)
        
        acos = (total_spend / total_sales * 100) if total_sales > 0 else 0
        roas = (total_sales / total_spend) if total_spend > 0 else 0
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        cvr = (total_orders / total_clicks * 100) if total_clicks > 0 else 0
        cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
        
        # Get previous period metrics for comparison (days*2 to days ago)
        prev_start_date = datetime.now() - timedelta(days=days * 2)
        prev_end_date = datetime.now() - timedelta(days=days)
        
        prev_total_spend = 0
        prev_total_sales = 0
        prev_total_impressions = 0
        prev_total_clicks = 0
        prev_total_orders = 0
        
        try:
            with db_connector.get_connection() as conn:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT 
                            COALESCE(SUM(cp.impressions), 0) as total_impressions,
                            COALESCE(SUM(cp.clicks), 0) as total_clicks,
                            COALESCE(SUM(cp.cost), 0) as total_cost,
                            COALESCE(SUM(cp.attributed_conversions_7d), 0) as total_conversions,
                            COALESCE(SUM(cp.attributed_sales_7d), 0) as total_sales
                        FROM campaign_performance cp
                        INNER JOIN campaigns c ON cp.campaign_id = c.campaign_id
                        WHERE c.campaign_status = 'ENABLED'
                            AND cp.report_date >= %s 
                            AND cp.report_date < %s
                    """, (prev_start_date, prev_end_date))
                    result = cursor.fetchone()
                    if result:
                        prev_total_impressions = int(result['total_impressions'] or 0)
                        prev_total_clicks = int(result['total_clicks'] or 0)
                        prev_total_spend = float(result['total_cost'] or 0)
                        prev_total_orders = int(result['total_conversions'] or 0)
                        prev_total_sales = float(result['total_sales'] or 0)
        except Exception as e:
            logger.warning(f"Could not get previous period metrics: {e}")
        
        prev_acos = (prev_total_spend / prev_total_sales * 100) if prev_total_sales > 0 else 0
        prev_roas = (prev_total_sales / prev_total_spend) if prev_total_spend > 0 else 0
        
        # Calculate comparison percentages
        def calculate_comparison(current: float, previous: float, inverted: bool = False) -> Optional[MetricComparison]:
            """Calculate comparison between current and previous period
            
            Args:
                current: Current period value
                previous: Previous period value
                inverted: If True, lower values are better (e.g., ACOS)
            """
            if previous == 0:
                if current == 0:
                    return None
                return MetricComparison(value=current, change_percentage=0.0, direction='neutral')
            
            change_pct = ((current - previous) / previous) * 100
            if abs(change_pct) < 0.01:  # Less than 0.01% change is considered neutral
                direction = 'neutral'
            elif inverted:
                # For inverted metrics (like ACOS), lower is better
                # So if change_pct < 0 (current < previous), that's "up" (good)
                direction = 'down' if change_pct > 0 else 'up'
            else:
                # For normal metrics, higher is better
                direction = 'up' if change_pct > 0 else 'down'
            
            return MetricComparison(value=current, change_percentage=round(abs(change_pct), 1), direction=direction)
        
        spend_comp = calculate_comparison(total_spend, prev_total_spend)
        sales_comp = calculate_comparison(total_sales, prev_total_sales)
        acos_comp = calculate_comparison(acos, prev_acos, inverted=True)  # For ACOS, down is good
        roas_comp = calculate_comparison(roas, prev_roas)
        
        # Get AI activity count (recommendations in last 24h)
        ai_activity = len(ai_engine.recent_adjustments) if hasattr(ai_engine, 'recent_adjustments') else 0
        
        # Get pending recommendations count
        pending_recs = 0
        applied_today = 0
        try:
            with db_connector.get_connection() as conn:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT 
                            COUNT(*) FILTER (WHERE applied = FALSE) as pending,
                            COUNT(*) FILTER (WHERE applied = TRUE AND applied_at >= CURRENT_DATE) as applied_today
                        FROM recommendation_tracking
                        WHERE created_at >= %s
                    """, (datetime.now() - timedelta(days=7),))
                    result = cursor.fetchone()
                    if result:
                        pending_recs = result['pending'] or 0
                        applied_today = result['applied_today'] or 0
        except Exception as e:
            logger.warning(f"Could not get recommendation counts: {e}")
        
        # Calculate account health score (0-100)
        health_score = _calculate_account_health_score(acos, roas, ctr, cvr, total_orders)
        
        return OverviewMetrics(
            spend=round(total_spend, 2),
            sales=round(total_sales, 2),
            acos=round(acos, 2),
            roas=round(roas, 2),
            orders=total_orders,
            impressions=total_impressions,
            clicks=total_clicks,
            ctr=round(ctr, 2),
            cvr=round(cvr, 2),
            cpc=round(cpc, 2),
            ai_activity_count=ai_activity,
            account_health_score=round(health_score, 1),
            pending_recommendations=pending_recs,
            applied_today=applied_today,
            spend_comparison=spend_comp,
            sales_comparison=sales_comp,
            acos_comparison=acos_comp,
            roas_comparison=roas_comp
        )
    except Exception as e:
        logger.error(f"Error fetching overview metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/overview/trends", response_model=List[TrendDataPoint])
async def get_overview_trends(days: int = Query(30, ge=7, le=90)):
    """Get trend data for charts"""
    try:
        # Get daily performance data
        query = """
        SELECT 
            report_date,
            SUM(cost) as spend,
            SUM(attributed_sales_7d) as sales
        FROM campaign_performance
        WHERE report_date >= %s
        GROUP BY report_date
        ORDER BY report_date ASC
        """
        
        start_date = datetime.now() - timedelta(days=days)
        
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (start_date,))
                rows = cursor.fetchall()
        
        trends = []
        for row in rows:
            spend = float(row['spend'] or 0)
            sales = float(row['sales'] or 0)
            acos = (spend / sales * 100) if sales > 0 else 0
            roas = (sales / spend) if spend > 0 else 0
            
            trends.append(TrendDataPoint(
                date=row['report_date'].strftime('%Y-%m-%d'),
                spend=round(spend, 2),
                sales=round(sales, 2),
                acos=round(acos, 2),
                roas=round(roas, 2)
            ))
        
        return trends
    except Exception as e:
        logger.error(f"Error fetching trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/overview/alerts", response_model=List[Alert])
async def get_alerts(limit: int = Query(10, ge=1, le=50)):
    """Get active alerts for the dashboard"""
    try:
        alerts = []
        
        # Get alerts from alert_history table
        try:
            with db_connector.get_connection() as conn:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, alert_type, entity_type, entity_id, entity_name, 
                               severity, message, triggered_at
                        FROM alert_history
                        WHERE is_dismissed = FALSE
                        ORDER BY 
                            CASE severity 
                                WHEN 'critical' THEN 0 
                                WHEN 'high' THEN 1 
                                WHEN 'medium' THEN 2 
                                ELSE 3 
                            END,
                            triggered_at DESC
                        LIMIT %s
                    """, (limit,))
                    db_alerts = cursor.fetchall()
                    
                    for row in db_alerts:
                        alerts.append(Alert(
                            id=str(row['id']),
                            type=row['alert_type'],
                            severity=row['severity'],
                            message=row['message'],
                            entity_type=row['entity_type'],
                            entity_id=row['entity_id'],
                            entity_name=row['entity_name'],
                            created_at=row['triggered_at'].isoformat()
                        ))
        except Exception as e:
            logger.warning(f"Could not get alerts from database: {e}")
        
        # Generate real-time alerts from campaign data if needed
        if len(alerts) < limit:
            campaigns = db_connector.get_campaigns_with_performance(7)
            for campaign in campaigns:
                if len(alerts) >= limit:
                    break
                    
                budget = float(campaign.get('budget_amount', 0) or 0)
                spend = float(campaign.get('total_cost', 0) or 0)
                
                if budget > 0 and spend >= budget * 0.9:
                    alert_id = f"budget_{campaign['campaign_id']}"
                    if not any(a.id == alert_id for a in alerts):
                        alerts.append(Alert(
                            id=alert_id,
                            type="budget_depletion",
                            severity="high",
                            message=f"Campaign '{campaign['campaign_name']}' is near budget limit ({(spend/budget*100):.1f}% used)",
                            entity_type="campaign",
                            entity_id=campaign['campaign_id'],
                            entity_name=campaign['campaign_name'],
                            created_at=datetime.now().isoformat()
                        ))
                
                # Check for ACOS spikes
                acos = float(campaign.get('avg_acos', 0) or 0)
                if acos > rule_config.acos_target * 2:
                    alert_id = f"acos_{campaign['campaign_id']}"
                    if not any(a.id == alert_id for a in alerts):
                        alerts.append(Alert(
                            id=alert_id,
                            type="acos_spike",
                            severity="critical" if acos > rule_config.acos_target * 3 else "high",
                            message=f"Campaign '{campaign['campaign_name']}' has high ACOS ({acos*100:.1f}%)",
                            entity_type="campaign",
                            entity_id=campaign['campaign_id'],
                            entity_name=campaign['campaign_name'],
                            created_at=datetime.now().isoformat()
                        ))
        
        # Get oscillating entities
        try:
            oscillating = db_connector.get_oscillating_entities()
            for entity in oscillating:
                if len(alerts) >= limit:
                    break
                alert_id = f"oscillation_{entity['entity_type']}_{entity['entity_id']}"
                if not any(a.id == alert_id for a in alerts):
                    alerts.append(Alert(
                        id=alert_id,
                        type="bid_oscillation",
                        severity="medium",
                        message=f"{entity.get('entity_name', f'{entity['entity_type']} {entity['entity_id']}')} is experiencing bid oscillation ({entity['direction_changes']} changes)",
                        entity_type=entity['entity_type'],
                        entity_id=entity['entity_id'],
                        entity_name=entity.get('entity_name'),
                        created_at=datetime.now().isoformat()
                    ))
        except Exception as e:
            logger.warning(f"Could not get oscillating entities: {e}")
        
        return alerts[:limit]
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - CAMPAIGN MANAGEMENT
# ============================================================================

@app.get("/api/campaigns", response_model=List[CampaignData])
async def get_campaigns(days: int = Query(7, ge=1, le=90)):
    """Get all campaigns with performance data"""
    try:
        campaigns = db_connector.get_campaigns_with_performance(days)
        
        result = []
        for campaign in campaigns:
            spend = float(campaign.get('total_cost', 0) or 0)
            sales = float(campaign.get('total_sales', 0) or 0)
            impressions = int(campaign.get('total_impressions', 0) or 0)
            clicks = int(campaign.get('total_clicks', 0) or 0)
            orders = int(campaign.get('total_conversions', 0) or 0)
            
            result.append(CampaignData(
                campaign_id=campaign['campaign_id'],
                campaign_name=campaign['campaign_name'],
                campaign_type=campaign.get('targeting_type', 'SP'),
                status=campaign.get('campaign_status', 'ENABLED'),
                spend=round(spend, 2),
                sales=round(sales, 2),
                acos=round(spend / sales * 100, 2) if sales > 0 else None,
                roas=round(sales / spend, 2) if spend > 0 else None,
                orders=orders,
                budget=float(campaign.get('budget_amount', 0) or 0),
                impressions=impressions,
                clicks=clicks,
                ctr=round(clicks / impressions * 100, 2) if impressions > 0 else 0,
                cvr=round(orders / clicks * 100, 2) if clicks > 0 else 0,
                ai_recommendation=_get_campaign_ai_signal(campaign)
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error fetching campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/campaigns/{campaign_id}")
async def get_campaign_details(campaign_id: int, days: int = Query(7, ge=1, le=90)):
    """Get detailed campaign information"""
    try:
        performance = db_connector.get_campaign_performance(campaign_id, days)
        ad_groups = db_connector.get_ad_groups_with_performance(campaign_id, days)
        
        # Get recent bid changes for this campaign
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, entity_type, entity_id, entity_name, change_date, 
                           old_bid, new_bid, change_percentage, reason, triggered_by,
                           outcome_label, outcome_score
                    FROM bid_change_history
                    WHERE entity_type = 'campaign' AND entity_id = %s
                    ORDER BY change_date DESC
                    LIMIT 20
                """, (campaign_id,))
                bid_history = cursor.fetchall()
        
        return {
            "campaign_id": campaign_id,
            "performance_history": performance,
            "ad_groups": ad_groups,
            "bid_history": bid_history
        }
    except Exception as e:
        logger.error(f"Error fetching campaign details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/campaigns/{campaign_id}/action")
async def apply_campaign_action(campaign_id: int, action: ActionRequest, background_tasks: BackgroundTasks):
    """Apply an action to a campaign (pause, enable, budget change)"""
    try:
        # Log the action
        db_connector.log_adjustment(
            entity_type='campaign',
            entity_id=campaign_id,
            adjustment_type=action.action_type,
            old_value=action.old_value or 0,
            new_value=action.new_value,
            reason=action.reason or "Manual action from dashboard"
        )
        
        # Create a lock to prevent AI from overwriting
        if action.action_type in ['bid', 'budget']:
            db_connector.create_bid_lock(
                entity_type='campaign',
                entity_id=campaign_id,
                lock_days=rule_config.bid_change_cooldown_days,
                reason=f"Manual {action.action_type} change from dashboard"
            )
        
        return {"status": "success", "message": f"Action {action.action_type} applied to campaign {campaign_id}"}
    except Exception as e:
        logger.error(f"Error applying campaign action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - KEYWORDS / TARGETING
# ============================================================================

@app.get("/api/keywords", response_model=List[KeywordData])
async def get_keywords(
    campaign_id: Optional[int] = None,
    ad_group_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get keywords with performance data"""
    try:
        all_keywords = []
        
        # Get campaigns to iterate through
        if campaign_id:
            campaign_ids = [campaign_id]
        else:
            campaigns = db_connector.get_campaigns_with_performance(days)
            campaign_ids = [c['campaign_id'] for c in campaigns]
        
        # Get bid locks for lookup
        bid_locks = {}
        try:
            with db_connector.get_connection() as conn:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT entity_id, locked_until, lock_reason 
                        FROM bid_adjustment_locks 
                        WHERE entity_type = 'keyword' AND locked_until > NOW()
                    """)
                    for row in cursor.fetchall():
                        bid_locks[row['entity_id']] = {
                            'locked_until': row['locked_until'],
                            'lock_reason': row['lock_reason']
                        }
        except Exception as e:
            logger.warning(f"Could not get bid locks: {e}")
        
        for cid in campaign_ids:
            ad_groups = db_connector.get_ad_groups_with_performance(cid, days)
            
            for ag in ad_groups:
                if ad_group_id and ag['ad_group_id'] != ad_group_id:
                    continue
                    
                keywords = db_connector.get_keywords_with_performance(ag['ad_group_id'], days)
                
                for kw in keywords:
                    spend = float(kw.get('total_cost', 0) or 0)
                    sales = float(kw.get('total_sales', 0) or 0)
                    impressions = int(kw.get('total_impressions', 0) or 0)
                    clicks = int(kw.get('total_clicks', 0) or 0)
                    orders = int(kw.get('total_conversions', 0) or 0)
                    
                    # Get AI suggested bid if available
                    ai_bid = None
                    confidence = None
                    reason = None
                    
                    # Check for recent bid change recommendations
                    last_change = db_connector.get_last_bid_change('keyword', kw['keyword_id'])
                    if last_change:
                        ai_bid = float(last_change.get('new_bid', 0))
                        reason = last_change.get('reason', '')
                    
                    # Check if locked
                    is_locked = kw['keyword_id'] in bid_locks
                    lock_reason = bid_locks.get(kw['keyword_id'], {}).get('lock_reason')
                    
                    all_keywords.append(KeywordData(
                        keyword_id=kw['keyword_id'],
                        keyword_text=kw['keyword_text'],
                        match_type=kw.get('match_type', 'BROAD'),
                        campaign_id=cid,
                        ad_group_id=ag['ad_group_id'],
                        bid=float(kw.get('bid', 0) or 0),
                        state=kw.get('state', 'ENABLED'),
                        spend=round(spend, 2),
                        sales=round(sales, 2),
                        acos=round(spend / sales * 100, 2) if sales > 0 else None,
                        roas=round(sales / spend, 2) if spend > 0 else None,
                        orders=orders,
                        impressions=impressions,
                        clicks=clicks,
                        ctr=round(clicks / impressions * 100, 2) if impressions > 0 else 0,
                        cvr=round(orders / clicks * 100, 2) if clicks > 0 else 0,
                        ai_suggested_bid=ai_bid,
                        confidence_score=confidence,
                        reason=reason,
                        is_locked=is_locked,
                        lock_reason=lock_reason
                    ))
            
            if len(all_keywords) >= limit:
                break
        
        return all_keywords[:limit]
    except Exception as e:
        logger.error(f"Error fetching keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/keywords/{keyword_id}/bid")
async def update_keyword_bid(keyword_id: int, action: ActionRequest):
    """Update keyword bid"""
    try:
        # Save the bid change
        change_record = {
            'entity_type': 'keyword',
            'entity_id': keyword_id,
            'entity_name': f"Keyword {keyword_id}",
            'change_date': datetime.now(),
            'old_bid': action.old_value or 0,
            'new_bid': action.new_value,
            'change_amount': action.new_value - (action.old_value or 0),
            'change_percentage': ((action.new_value - (action.old_value or 0)) / action.old_value * 100) if action.old_value else 0,
            'reason': action.reason or "Manual bid update from dashboard",
            'triggered_by': 'dashboard_manual',
            'acos_at_change': None,
            'roas_at_change': None,
            'ctr_at_change': None,
            'conversions_at_change': None,
            'metadata': '{}',
        }
        
        change_id = db_connector.save_bid_change(change_record)
        
        # Create a lock to prevent AI from overwriting
        db_connector.create_bid_lock(
            entity_type='keyword',
            entity_id=keyword_id,
            lock_days=rule_config.bid_change_cooldown_days,
            reason="Manual bid change from dashboard",
            change_id=change_id
        )
        
        return {"status": "success", "message": f"Bid updated for keyword {keyword_id}", "change_id": change_id}
    except Exception as e:
        logger.error(f"Error updating keyword bid: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/keywords/{keyword_id}/lock")
async def lock_keyword_bid(keyword_id: int, days: int = Query(3, ge=1, le=30), reason: str = None):
    """Lock a keyword from AI bid changes"""
    try:
        db_connector.create_bid_lock(
            entity_type='keyword',
            entity_id=keyword_id,
            lock_days=days,
            reason=reason or "Manual lock from dashboard"
        )
        return {"status": "success", "message": f"Keyword {keyword_id} locked for {days} days"}
    except Exception as e:
        logger.error(f"Error locking keyword: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/keywords/{keyword_id}/lock")
async def unlock_keyword_bid(keyword_id: int):
    """Remove lock from a keyword"""
    try:
        with db_connector.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM bid_adjustment_locks 
                    WHERE entity_type = 'keyword' AND entity_id = %s
                """, (keyword_id,))
                conn.commit()
        return {"status": "success", "message": f"Keyword {keyword_id} unlocked"}
    except Exception as e:
        logger.error(f"Error unlocking keyword: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - SEARCH
# ============================================================================

@app.get("/api/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results")
):
    """
    Search across campaigns, keywords, and ad groups
    
    Searches for:
    - Campaign names
    - Keyword text
    - Ad group names
    """
    try:
        if not q or len(q.strip()) == 0:
            return SearchResponse(query=q, results=[], total=0)
        
        query = q.strip().lower()
        results: List[SearchResult] = []
        
        # Search campaigns
        try:
            campaigns = db_connector.get_campaigns_with_performance(30)
            for campaign in campaigns:
                campaign_name = campaign.get('campaign_name', '').lower()
                if query in campaign_name:
                    # Calculate match score (exact match = 1.0, partial = 0.5)
                    match_score = 1.0 if campaign_name == query else 0.5
                    results.append(SearchResult(
                        type='campaign',
                        id=campaign['campaign_id'],
                        name=campaign.get('campaign_name', ''),
                        campaign_id=campaign['campaign_id'],
                        campaign_name=campaign.get('campaign_name', ''),
                        match_score=match_score
                    ))
        except Exception as e:
            logger.warning(f"Error searching campaigns: {e}")
        
        # Search keywords and ad groups
        try:
            all_campaigns = db_connector.get_campaigns_with_performance(30)
            for campaign in all_campaigns:
                campaign_id = campaign['campaign_id']
                campaign_name = campaign.get('campaign_name', '')
                
                # Get ad groups for this campaign
                ad_groups = db_connector.get_ad_groups_with_performance(campaign_id, 30)
                for ad_group in ad_groups:
                    ad_group_id = ad_group['ad_group_id']
                    ad_group_name = ad_group.get('ad_group_name', '').lower()
                    
                    # Check if ad group name matches
                    if query in ad_group_name:
                        match_score = 1.0 if ad_group_name == query else 0.5
                        results.append(SearchResult(
                            type='ad_group',
                            id=ad_group_id,
                            name=ad_group.get('ad_group_name', ''),
                            campaign_id=campaign_id,
                            campaign_name=campaign_name,
                            ad_group_id=ad_group_id,
                            ad_group_name=ad_group.get('ad_group_name', ''),
                            match_score=match_score
                        ))
                    
                    # Search keywords in this ad group
                    keywords = db_connector.get_keywords_with_performance(ad_group_id, 30)
                    for keyword in keywords:
                        keyword_text = keyword.get('keyword_text', '').lower()
                        if query in keyword_text:
                            match_score = 1.0 if keyword_text == query else 0.5
                            results.append(SearchResult(
                                type='keyword',
                                id=keyword['keyword_id'],
                                name=keyword.get('keyword_text', ''),
                                campaign_id=campaign_id,
                                campaign_name=campaign_name,
                                ad_group_id=ad_group_id,
                                ad_group_name=ad_group.get('ad_group_name', ''),
                                match_score=match_score
                            ))
        except Exception as e:
            logger.warning(f"Error searching keywords/ad groups: {e}")
        
        # Sort by match score (highest first) and limit results
        results.sort(key=lambda x: x.match_score, reverse=True)
        results = results[:limit]
        
        return SearchResponse(
            query=q,
            results=results,
            total=len(results)
        )
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - AI RECOMMENDATIONS
# ============================================================================

@app.get("/api/recommendations", response_model=List[RecommendationData])
async def get_recommendations(
    recommendation_type: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200)
):
    """Get AI recommendations"""
    try:
        # Get recommendations from database
        recommendations = []
        try:
            with db_connector.get_connection() as conn:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    query = """
                        SELECT recommendation_id, entity_type, entity_id, adjustment_type,
                               recommended_value, current_value, intelligence_signals,
                               strategy_id, created_at, applied, metadata
                        FROM recommendation_tracking
                        WHERE applied = FALSE
                    """
                    params = []
                    
                    if recommendation_type:
                        query += " AND adjustment_type = %s"
                        params.append(recommendation_type)
                    
                    query += " ORDER BY created_at DESC LIMIT %s"
                    params.append(limit)
                    
                    cursor.execute(query, params)
                    db_recs = cursor.fetchall()
                    
                    for rec in db_recs:
                        # Determine priority based on intelligence signals
                        signals = rec.get('intelligence_signals') or {}
                        if isinstance(signals, str):
                            try:
                                signals = json.loads(signals)
                            except:
                                signals = {}
                        
                        # Calculate priority
                        adjustment_pct = abs(((rec['recommended_value'] - rec['current_value']) / rec['current_value'] * 100) if rec['current_value'] else 0)
                        if adjustment_pct > 30:
                            rec_priority = 'critical'
                        elif adjustment_pct > 20:
                            rec_priority = 'high'
                        elif adjustment_pct > 10:
                            rec_priority = 'medium'
                        else:
                            rec_priority = 'low'
                        
                        if priority and rec_priority != priority:
                            continue
                        
                        # Get entity name
                        entity_name = f"{rec['entity_type']} {rec['entity_id']}"
                        try:
                            if rec['entity_type'] == 'keyword':
                                cursor.execute("SELECT keyword_text FROM keywords WHERE keyword_id = %s", (rec['entity_id'],))
                                kw = cursor.fetchone()
                                if kw:
                                    entity_name = kw['keyword_text']
                            elif rec['entity_type'] == 'campaign':
                                cursor.execute("SELECT campaign_name FROM campaigns WHERE campaign_id = %s", (rec['entity_id'],))
                                c = cursor.fetchone()
                                if c:
                                    entity_name = c['campaign_name']
                        except:
                            pass
                        
                        # Build reason from signals
                        reason = _build_recommendation_reason(signals, rec['adjustment_type'])
                        
                        recommendations.append(RecommendationData(
                            id=rec['recommendation_id'],
                            entity_type=rec['entity_type'],
                            entity_id=rec['entity_id'],
                            entity_name=entity_name,
                            recommendation_type=rec['adjustment_type'],
                            current_value=rec['current_value'],
                            recommended_value=rec['recommended_value'],
                            adjustment_percentage=adjustment_pct if rec['recommended_value'] > rec['current_value'] else -adjustment_pct,
                            priority=rec_priority,
                            confidence=signals.get('confidence', 0.7),
                            reason=reason,
                            estimated_impact=_calculate_estimated_impact_str(rec),
                            intelligence_signals=signals,
                            created_at=rec['created_at'].isoformat(),
                            status="pending"
                        ))
        except Exception as e:
            logger.warning(f"Could not get recommendations from database: {e}")
        
        # If no recommendations in database, run analysis
        if not recommendations:
            try:
                recs = ai_engine.analyze_campaigns()
                for rec in recs[:limit]:
                    if recommendation_type and rec.adjustment_type != recommendation_type:
                        continue
                    if priority and rec.priority != priority:
                        continue
                    
                    impact = _calculate_estimated_impact(rec)
                    
                    recommendations.append(RecommendationData(
                        id=f"{rec.entity_type}_{rec.entity_id}_{rec.created_at.timestamp()}",
                        entity_type=rec.entity_type,
                        entity_id=rec.entity_id,
                        entity_name=rec.entity_name,
                        recommendation_type=rec.adjustment_type,
                        current_value=rec.current_value,
                        recommended_value=rec.recommended_value,
                        adjustment_percentage=rec.adjustment_percentage,
                        priority=rec.priority,
                        confidence=rec.confidence,
                        reason=rec.reason,
                        estimated_impact=impact,
                        created_at=rec.created_at.isoformat(),
                        status="pending"
                    ))
            except Exception as e:
                logger.warning(f"Could not run AI analysis: {e}")
        
        return recommendations[:limit]
    except Exception as e:
        logger.error(f"Error fetching recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recommendations/{recommendation_id}/approve")
async def approve_recommendation(recommendation_id: str, background_tasks: BackgroundTasks):
    """Approve an AI recommendation"""
    try:
        # Update recommendation status in database
        with db_connector.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE recommendation_tracking 
                    SET applied = TRUE, applied_at = NOW()
                    WHERE recommendation_id = %s
                """, (recommendation_id,))
                conn.commit()
        
        # Log the approval in recommendation_actions
        try:
            with db_connector.get_connection() as conn:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Get recommendation details
                    cursor.execute("""
                        SELECT entity_type, entity_id, current_value, recommended_value
                        FROM recommendation_tracking
                        WHERE recommendation_id = %s
                    """, (recommendation_id,))
                    rec = cursor.fetchone()
                    
                    if rec:
                        cursor.execute("""
                            INSERT INTO recommendation_actions 
                            (recommendation_id, entity_type, entity_id, action_taken, 
                             original_value, recommended_value, final_value, execution_status)
                            VALUES (%s, %s, %s, 'approved', %s, %s, %s, 'pending')
                        """, (recommendation_id, rec['entity_type'], rec['entity_id'],
                              rec['current_value'], rec['recommended_value'], rec['recommended_value']))
                        conn.commit()
        except Exception as e:
            logger.warning(f"Could not log recommendation action: {e}")
        
        logger.info(f"Recommendation approved: {recommendation_id}")
        
        return {"status": "success", "message": f"Recommendation {recommendation_id} approved and scheduled for execution"}
    except Exception as e:
        logger.error(f"Error approving recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recommendations/{recommendation_id}/reject")
async def reject_recommendation(recommendation_id: str, reason: Optional[str] = None):
    """Reject an AI recommendation"""
    try:
        # Log the rejection in recommendation_actions
        try:
            with db_connector.get_connection() as conn:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT entity_type, entity_id, current_value, recommended_value
                        FROM recommendation_tracking
                        WHERE recommendation_id = %s
                    """, (recommendation_id,))
                    rec = cursor.fetchone()
                    
                    if rec:
                        cursor.execute("""
                            INSERT INTO recommendation_actions 
                            (recommendation_id, entity_type, entity_id, action_taken, 
                             original_value, recommended_value, reason, execution_status)
                            VALUES (%s, %s, %s, 'rejected', %s, %s, %s, 'cancelled')
                        """, (recommendation_id, rec['entity_type'], rec['entity_id'],
                              rec['current_value'], rec['recommended_value'], reason))
                        conn.commit()
        except Exception as e:
            logger.warning(f"Could not log recommendation rejection: {e}")
        
        logger.info(f"Recommendation rejected: {recommendation_id}, reason: {reason}")
        return {"status": "success", "message": f"Recommendation {recommendation_id} rejected"}
    except Exception as e:
        logger.error(f"Error rejecting recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recommendations/bulk-approve")
async def bulk_approve_recommendations(recommendation_ids: List[str]):
    """Bulk approve multiple recommendations"""
    try:
        approved = []
        for rec_id in recommendation_ids:
            try:
                with db_connector.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE recommendation_tracking 
                            SET applied = TRUE, applied_at = NOW()
                            WHERE recommendation_id = %s
                        """, (rec_id,))
                        conn.commit()
                approved.append(rec_id)
            except Exception as e:
                logger.warning(f"Failed to approve {rec_id}: {e}")
        
        return {"status": "success", "approved_count": len(approved), "approved_ids": approved}
    except Exception as e:
        logger.error(f"Error bulk approving recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - RULE ENGINE VISIBILITY
# ============================================================================

@app.get("/api/rules", response_model=List[RuleData])
async def get_rules():
    """Get all active rules with their configuration"""
    try:
        rule_docs = ai_engine.get_rule_documentation()
        
        rules = []
        for rule_name, rule_info in rule_docs.items():
            if rule_name in ['bid_limits', 'safety_limits']:
                continue
            
            # Get parameters from config
            parameters = {}
            if 'acos' in rule_name.lower():
                parameters = {
                    'target_acos': rule_config.acos_target,
                    'tolerance': rule_config.acos_tolerance,
                    'high_threshold': rule_config.acos_high_threshold,
                    'low_threshold': rule_config.acos_low_threshold
                }
            elif 'roas' in rule_name.lower():
                parameters = {
                    'target_roas': rule_config.roas_target,
                    'tolerance': rule_config.roas_tolerance
                }
            
            rules.append(RuleData(
                id=rule_name,
                name=rule_name.replace('_', ' ').title(),
                description=rule_info.get('description', ''),
                logic=str(rule_info.get('triggers', [])),
                is_active=True,
                trigger_frequency="Daily",
                last_execution=datetime.now().isoformat(),
                last_result="Success",
                parameters=parameters
            ))
        
        return rules
    except Exception as e:
        logger.error(f"Error fetching rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rules/{rule_id}")
async def get_rule_details(rule_id: str):
    """Get detailed rule information"""
    try:
        rule_docs = ai_engine.get_rule_documentation()
        
        if rule_id not in rule_docs:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
        
        return {
            "id": rule_id,
            "name": rule_id.replace('_', ' ').title(),
            **rule_docs[rule_id]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching rule details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - NEGATIVE KEYWORDS / WASTE ANALYZER
# ============================================================================

@app.get("/api/negatives/candidates", response_model=List[NegativeCandidateData])
async def get_negative_candidates(campaign_id: Optional[int] = None, limit: int = Query(50, ge=1, le=200)):
    """Get negative keyword candidates"""
    try:
        all_candidates = []
        
        # Try to get from database first
        try:
            with db_connector.get_connection() as conn:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    query = """
                        SELECT nkc.keyword_id, nkc.keyword_text, nkc.match_type,
                               nkc.campaign_id, nkc.ad_group_id, nkc.severity,
                               nkc.confidence, nkc.reason, nkc.suggested_action,
                               nkc.cost_at_identification as spend,
                               nkc.clicks_at_identification as clicks,
                               nkc.impressions_at_identification as impressions,
                               nkc.conversions_at_identification as orders,
                               nkc.status
                        FROM negative_keyword_candidates nkc
                        WHERE nkc.status = 'pending'
                    """
                    params = []
                    
                    if campaign_id:
                        query += " AND nkc.campaign_id = %s"
                        params.append(campaign_id)
                    
                    query += " ORDER BY nkc.confidence DESC, nkc.cost_at_identification DESC LIMIT %s"
                    params.append(limit)
                    
                    cursor.execute(query, params)
                    db_candidates = cursor.fetchall()
                    
                    for c in db_candidates:
                        all_candidates.append(NegativeCandidateData(
                            keyword_id=c['keyword_id'],
                            keyword_text=c['keyword_text'],
                            match_type=c['match_type'],
                            campaign_id=c['campaign_id'],
                            ad_group_id=c['ad_group_id'],
                            spend=float(c.get('spend', 0) or 0),
                            clicks=int(c.get('clicks', 0) or 0),
                            impressions=int(c.get('impressions', 0) or 0),
                            orders=int(c.get('orders', 0) or 0),
                            severity=c['severity'],
                            confidence=float(c['confidence']),
                            reason=c['reason'],
                            suggested_action=c.get('suggested_action', 'negative_exact'),
                            status=c['status']
                        ))
        except Exception as e:
            logger.warning(f"Could not get negative candidates from database: {e}")
        
        # If no candidates in database, run analysis
        if not all_candidates:
            if campaign_id:
                campaign_ids = [campaign_id]
            else:
                campaigns = db_connector.get_campaigns_with_performance(14)
                campaign_ids = [c['campaign_id'] for c in campaigns]
            
            for cid in campaign_ids:
                try:
                    candidates = ai_engine.get_negative_keyword_candidates(cid)
                    
                    for candidate in candidates:
                        all_candidates.append(NegativeCandidateData(
                            keyword_id=candidate['keyword_id'],
                            keyword_text=candidate['keyword_text'],
                            match_type=candidate.get('match_type', 'BROAD'),
                            campaign_id=cid,
                            ad_group_id=candidate.get('ad_group_id', 0),
                            spend=float(candidate.get('cost', 0) or 0),
                            clicks=int(candidate.get('clicks', 0) or 0),
                            impressions=int(candidate.get('impressions', 0) or 0),
                            orders=int(candidate.get('orders', 0) or 0),
                            severity=candidate['severity'],
                            confidence=candidate['confidence'],
                            reason=candidate['reason'],
                            suggested_action=candidate.get('suggested_match_type', 'negative_exact'),
                            status='pending'
                        ))
                except Exception as e:
                    logger.warning(f"Could not analyze campaign {cid}: {e}")
                
                if len(all_candidates) >= limit:
                    break
        
        return all_candidates[:limit]
    except Exception as e:
        logger.error(f"Error fetching negative candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/negatives/{keyword_id}/approve")
async def approve_negative_keyword(keyword_id: int, match_type: str = "negative_exact"):
    """Approve a negative keyword candidate"""
    try:
        with db_connector.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE negative_keyword_candidates
                    SET status = 'applied', applied_date = NOW(), suggested_match_type = %s
                    WHERE keyword_id = %s
                """, (match_type, keyword_id))
                conn.commit()
        
        logger.info(f"Negative keyword approved: {keyword_id} as {match_type}")
        return {"status": "success", "message": f"Keyword {keyword_id} marked as negative ({match_type})"}
    except Exception as e:
        logger.error(f"Error approving negative keyword: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/negatives/{keyword_id}/reject")
async def reject_negative_keyword(keyword_id: int, reason: str = None):
    """Reject a negative keyword candidate"""
    try:
        with db_connector.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE negative_keyword_candidates
                    SET status = 'rejected'
                    WHERE keyword_id = %s
                """, (keyword_id,))
                conn.commit()
        
        logger.info(f"Negative keyword rejected: {keyword_id}, reason: {reason}")
        return {"status": "success", "message": f"Keyword {keyword_id} rejected"}
    except Exception as e:
        logger.error(f"Error rejecting negative keyword: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/negatives/{keyword_id}/hold")
async def hold_negative_keyword(keyword_id: int, days: int = 30):
    """Put a negative keyword candidate on temporary hold"""
    try:
        hold_expiry = datetime.now() + timedelta(days=days)
        with db_connector.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE negative_keyword_candidates
                    SET is_temporary_hold = TRUE, hold_expiry_date = %s
                    WHERE keyword_id = %s
                """, (hold_expiry, keyword_id))
                conn.commit()
        
        logger.info(f"Negative keyword put on hold: {keyword_id} for {days} days")
        return {"status": "success", "message": f"Keyword {keyword_id} put on {days}-day hold"}
    except Exception as e:
        logger.error(f"Error holding negative keyword: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - AUDIT LOG / TRANSPARENCY
# ============================================================================

@app.get("/api/changelog", response_model=List[ChangeLogEntry])
async def get_change_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(100, ge=1, le=500)
):
    """Get change history for audit trail"""
    try:
        query = """
        SELECT 
            id, entity_type, entity_id, entity_name,
            change_date, old_bid, new_bid, change_percentage, 
            reason, triggered_by, outcome_label, outcome_score
        FROM bid_change_history
        WHERE change_date >= %s
        """
        params = [datetime.now() - timedelta(days=days)]
        
        if entity_type:
            query += " AND entity_type = %s"
            params.append(entity_type)
        
        if entity_id:
            query += " AND entity_id = %s"
            params.append(entity_id)
        
        query += " ORDER BY change_date DESC LIMIT %s"
        params.append(limit)
        
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
        
        result = []
        for row in rows:
            result.append(ChangeLogEntry(
                id=row['id'],
                timestamp=row['change_date'].isoformat(),
                entity_type=row['entity_type'],
                entity_id=row['entity_id'],
                entity_name=row['entity_name'] or f"{row['entity_type']} {row['entity_id']}",
                action="bid_change",
                old_value=float(row['old_bid']),
                new_value=float(row['new_bid']),
                change_percentage=float(row.get('change_percentage', 0) or 0),
                reason=row['reason'] or "",
                triggered_by=row['triggered_by'] or "ai_rule_engine",
                status="success",
                outcome_label=row.get('outcome_label'),
                outcome_score=float(row['outcome_score']) if row.get('outcome_score') else None
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error fetching change log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/changelog/{change_id}/revert")
async def revert_change(change_id: int):
    """Revert a previous change"""
    try:
        # Get the original change
        query = """
        SELECT entity_type, entity_id, old_bid, new_bid
        FROM bid_change_history
        WHERE id = %s
        """
        
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (change_id,))
                row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Change {change_id} not found")
        
        # Create a revert change record
        revert_record = {
            'entity_type': row['entity_type'],
            'entity_id': row['entity_id'],
            'entity_name': f"Revert of change {change_id}",
            'change_date': datetime.now(),
            'old_bid': row['new_bid'],
            'new_bid': row['old_bid'],
            'change_amount': float(row['old_bid']) - float(row['new_bid']),
            'change_percentage': 0,
            'reason': f"Revert of change {change_id}",
            'triggered_by': 'dashboard_revert',
            'acos_at_change': None,
            'roas_at_change': None,
            'ctr_at_change': None,
            'conversions_at_change': None,
            'metadata': '{}'
        }
        
        db_connector.save_bid_change(revert_record)
        
        return {"status": "success", "message": f"Change {change_id} reverted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reverting change: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - BID LOCKS & OSCILLATION MONITORING
# ============================================================================

@app.get("/api/bid-locks", response_model=List[BidLockData])
async def get_bid_locks(entity_type: Optional[str] = None):
    """Get all active bid locks"""
    try:
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                query = """
                    SELECT bal.entity_type, bal.entity_id, bal.locked_until, bal.lock_reason, bal.last_change_id
                    FROM bid_adjustment_locks bal
                    WHERE bal.locked_until > NOW()
                """
                params = []
                
                if entity_type:
                    query += " AND bal.entity_type = %s"
                    params.append(entity_type)
                
                query += " ORDER BY bal.locked_until DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                result = []
                for row in rows:
                    result.append(BidLockData(
                        entity_type=row['entity_type'],
                        entity_id=row['entity_id'],
                        locked_until=row['locked_until'].isoformat(),
                        lock_reason=row['lock_reason'] or "",
                        last_change_id=row['last_change_id']
                    ))
                
                return result
    except Exception as e:
        logger.error(f"Error fetching bid locks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/oscillations", response_model=List[OscillationData])
async def get_oscillations():
    """Get entities with bid oscillation detected"""
    try:
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT entity_type, entity_id, entity_name, direction_changes, 
                           is_oscillating, last_change_date
                    FROM bid_oscillation_detection
                    WHERE is_oscillating = TRUE
                    ORDER BY direction_changes DESC
                """)
                rows = cursor.fetchall()
                
                result = []
                for row in rows:
                    result.append(OscillationData(
                        entity_type=row['entity_type'],
                        entity_id=row['entity_id'],
                        entity_name=row.get('entity_name'),
                        direction_changes=row['direction_changes'],
                        is_oscillating=row['is_oscillating'],
                        last_change_date=row['last_change_date'].isoformat() if row['last_change_date'] else None
                    ))
                
                return result
    except Exception as e:
        logger.error(f"Error fetching oscillations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - LEARNING OUTCOMES
# ============================================================================

@app.get("/api/learning/outcomes", response_model=List[LearningOutcomeData])
async def get_learning_outcomes(
    days: int = Query(30, ge=7, le=90),
    limit: int = Query(100, ge=1, le=500)
):
    """Get learning outcomes for recommendations"""
    try:
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, recommendation_id, entity_type, entity_id, adjustment_type,
                           recommended_value, applied_value, outcome, improvement_percentage, timestamp
                    FROM learning_outcomes
                    WHERE timestamp >= %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (datetime.now() - timedelta(days=days), limit))
                rows = cursor.fetchall()
                
                result = []
                for row in rows:
                    result.append(LearningOutcomeData(
                        id=row['id'],
                        recommendation_id=row['recommendation_id'],
                        entity_type=row['entity_type'],
                        entity_id=row['entity_id'],
                        adjustment_type=row['adjustment_type'],
                        recommended_value=row['recommended_value'],
                        applied_value=row['applied_value'],
                        outcome=row['outcome'],
                        improvement_percentage=row['improvement_percentage'],
                        timestamp=row['timestamp'].isoformat()
                    ))
                
                return result
    except Exception as e:
        logger.error(f"Error fetching learning outcomes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/learning/stats")
async def get_learning_stats(days: int = Query(30, ge=7, le=90)):
    """Get learning loop statistics"""
    try:
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE outcome = 'success') as successes,
                        COUNT(*) FILTER (WHERE outcome = 'failure') as failures,
                        COUNT(*) FILTER (WHERE outcome = 'neutral') as neutrals,
                        AVG(improvement_percentage) as avg_improvement
                    FROM learning_outcomes
                    WHERE timestamp >= %s
                """, (datetime.now() - timedelta(days=days),))
                stats = cursor.fetchone()
                
                # Get model training status
                cursor.execute("""
                    SELECT model_version, status, train_accuracy, test_accuracy,
                           train_auc, test_auc, promoted, completed_at
                    FROM model_training_runs
                    ORDER BY id DESC
                    LIMIT 5
                """)
                training_runs = cursor.fetchall()
                
                return {
                    "total_outcomes": stats['total'] or 0,
                    "successes": stats['successes'] or 0,
                    "failures": stats['failures'] or 0,
                    "neutrals": stats['neutrals'] or 0,
                    "success_rate": (stats['successes'] / stats['total'] * 100) if stats['total'] else 0,
                    "avg_improvement": float(stats['avg_improvement'] or 0),
                    "recent_training_runs": [
                        ModelTrainingStatus(
                            model_version=r['model_version'],
                            status=r['status'],
                            train_accuracy=r['train_accuracy'],
                            test_accuracy=r['test_accuracy'],
                            train_auc=r['train_auc'],
                            test_auc=r['test_auc'],
                            promoted=r['promoted'],
                            completed_at=r['completed_at'].isoformat() if r['completed_at'] else None
                        ) for r in training_runs
                    ]
                }
    except Exception as e:
        logger.error(f"Error fetching learning stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - STRATEGY CONFIGURATION
# ============================================================================

@app.get("/api/config/strategy")
async def get_strategy_config():
    """Get current strategy configuration"""
    try:
        # Map target ACOS to strategy
        acos = rule_config.acos_target
        if acos <= 0.05:
            strategy = "profit"
        elif acos <= 0.10:
            strategy = "growth"
        elif acos <= 0.15:
            strategy = "launch"
        else:
            strategy = "liquidate"
        
        # Determine AI mode
        if rule_config.enable_warm_up_mode:
            ai_mode = "warm_up"
        else:
            ai_mode = "autonomous"  # Default is autonomous
        
        return StrategyConfig(
            strategy=strategy,
            target_acos=rule_config.acos_target,
            max_bid_cap=rule_config.bid_cap,
            min_bid_floor=rule_config.bid_floor,
            ai_mode=ai_mode,
            enable_dayparting=False,  # Would need to check config
            enable_inventory_protection=rule_config.enable_spend_safeguard,
            enable_brand_defense=False  # Would need to add to config
        )
    except Exception as e:
        logger.error(f"Error fetching strategy config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/strategy")
async def update_strategy_config(config: StrategyConfig):
    """Update strategy configuration"""
    try:
        global rule_config, ai_engine
        
        # Update configuration
        rule_config.acos_target = config.target_acos
        rule_config.bid_cap = config.max_bid_cap
        rule_config.bid_floor = config.min_bid_floor
        
        # Update AI mode
        if config.ai_mode == "warm_up":
            rule_config.enable_warm_up_mode = True
        else:
            rule_config.enable_warm_up_mode = False
        
        # Update database configuration
        try:
            with db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO strategy_configurations 
                        (entity_type, entity_id, strategy, target_acos, max_bid_cap, min_bid_floor, ai_mode,
                         enable_dayparting, enable_inventory_protection, enable_brand_defense)
                        VALUES ('account', NULL, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (entity_type, entity_id) 
                        DO UPDATE SET 
                            strategy = EXCLUDED.strategy,
                            target_acos = EXCLUDED.target_acos,
                            max_bid_cap = EXCLUDED.max_bid_cap,
                            min_bid_floor = EXCLUDED.min_bid_floor,
                            ai_mode = EXCLUDED.ai_mode,
                            enable_dayparting = EXCLUDED.enable_dayparting,
                            enable_inventory_protection = EXCLUDED.enable_inventory_protection,
                            enable_brand_defense = EXCLUDED.enable_brand_defense,
                            updated_at = NOW()
                    """, (config.strategy, config.target_acos, config.max_bid_cap, config.min_bid_floor,
                          config.ai_mode, config.enable_dayparting, config.enable_inventory_protection,
                          config.enable_brand_defense))
                    conn.commit()
        except Exception as e:
            logger.warning(f"Could not save strategy to database: {e}")
        
        # Reinitialize AI engine with new config
        ai_engine = AIRuleEngine(rule_config, db_connector)
        
        logger.info(f"Strategy config updated: {config}")
        
        return {"status": "success", "message": "Strategy configuration updated"}
    except Exception as e:
        logger.error(f"Error updating strategy config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - AI CONTROL (COMPREHENSIVE)
# ============================================================================

@app.get("/api/config/ai-control", response_model=AIControlConfig)
async def get_ai_control_config():
    """Get comprehensive AI Rule Engine control configuration"""
    try:
        return AIControlConfig(
            # Core Settings
            target_acos=rule_config.acos_target,
            acos_tolerance=rule_config.acos_tolerance,
            roas_target=rule_config.roas_target,
            
            # Bid Limits
            bid_floor=rule_config.bid_floor,
            bid_cap=rule_config.bid_cap,
            bid_max_adjustment=rule_config.bid_max_adjustment,
            
            # Re-entry Control
            enable_re_entry_control=rule_config.enable_re_entry_control,
            bid_change_cooldown_days=rule_config.bid_change_cooldown_days,
            min_bid_change_threshold=rule_config.min_bid_change_threshold,
            
            # Oscillation Prevention
            enable_oscillation_detection=rule_config.enable_oscillation_detection,
            oscillation_lookback_days=rule_config.oscillation_lookback_days,
            oscillation_direction_change_threshold=rule_config.oscillation_direction_change_threshold,
            
            # Safety Controls
            enable_spend_safeguard=rule_config.enable_spend_safeguard,
            spend_spike_threshold=rule_config.spend_spike_threshold,
            enable_comprehensive_safety_veto=rule_config.enable_comprehensive_safety_veto,
            account_daily_limit=rule_config.account_daily_limit,
            
            # Order-Based Scaling
            enable_order_based_scaling=rule_config.enable_order_based_scaling,
            order_tier_1_adjustment=rule_config.order_tier_1_adjustment,
            order_tier_2_3_adjustment=rule_config.order_tier_2_3_adjustment,
            order_tier_4_plus_adjustment=rule_config.order_tier_4_plus_adjustment,
            
            # Spend No-Sale Logic
            enable_spend_no_sale_logic=rule_config.enable_spend_no_sale_logic,
            no_sale_reduction_tier_1=rule_config.no_sale_reduction_tier_1,
            no_sale_reduction_tier_2=rule_config.no_sale_reduction_tier_2,
            no_sale_reduction_tier_3=rule_config.no_sale_reduction_tier_3,
            
            # Performance Thresholds
            min_impressions=rule_config.min_impressions,
            min_clicks=rule_config.min_clicks,
            min_conversions=rule_config.min_conversions,
            
            # Learning Loop
            enable_learning_loop=rule_config.enable_learning_loop,
            learning_success_threshold=rule_config.learning_success_threshold,
            learning_failure_threshold=rule_config.learning_failure_threshold,
            min_training_samples=rule_config.min_training_samples,
            
            # Feature Flags
            enable_warm_up_mode=rule_config.enable_warm_up_mode,
            enable_intelligence_engines=rule_config.enable_intelligence_engines,
            enable_advanced_bid_optimization=rule_config.enable_advanced_bid_optimization,
        )
    except Exception as e:
        logger.error(f"Error fetching AI control config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/ai-control")
async def update_ai_control_config(config: AIControlConfig):
    """Update comprehensive AI Rule Engine control configuration"""
    try:
        global rule_config, ai_engine
        
        # Update all configuration fields
        rule_config.acos_target = config.target_acos
        rule_config.acos_tolerance = config.acos_tolerance
        rule_config.roas_target = config.roas_target
        
        rule_config.bid_floor = config.bid_floor
        rule_config.bid_cap = config.bid_cap
        rule_config.bid_max_adjustment = config.bid_max_adjustment
        
        rule_config.enable_re_entry_control = config.enable_re_entry_control
        rule_config.bid_change_cooldown_days = config.bid_change_cooldown_days
        rule_config.min_bid_change_threshold = config.min_bid_change_threshold
        
        rule_config.enable_oscillation_detection = config.enable_oscillation_detection
        rule_config.oscillation_lookback_days = config.oscillation_lookback_days
        rule_config.oscillation_direction_change_threshold = config.oscillation_direction_change_threshold
        
        rule_config.enable_spend_safeguard = config.enable_spend_safeguard
        rule_config.spend_spike_threshold = config.spend_spike_threshold
        rule_config.enable_comprehensive_safety_veto = config.enable_comprehensive_safety_veto
        rule_config.account_daily_limit = config.account_daily_limit
        
        rule_config.enable_order_based_scaling = config.enable_order_based_scaling
        rule_config.order_tier_1_adjustment = config.order_tier_1_adjustment
        rule_config.order_tier_2_3_adjustment = config.order_tier_2_3_adjustment
        rule_config.order_tier_4_plus_adjustment = config.order_tier_4_plus_adjustment
        
        rule_config.enable_spend_no_sale_logic = config.enable_spend_no_sale_logic
        rule_config.no_sale_reduction_tier_1 = config.no_sale_reduction_tier_1
        rule_config.no_sale_reduction_tier_2 = config.no_sale_reduction_tier_2
        rule_config.no_sale_reduction_tier_3 = config.no_sale_reduction_tier_3
        
        rule_config.min_impressions = config.min_impressions
        rule_config.min_clicks = config.min_clicks
        rule_config.min_conversions = config.min_conversions
        
        rule_config.enable_learning_loop = config.enable_learning_loop
        rule_config.learning_success_threshold = config.learning_success_threshold
        rule_config.learning_failure_threshold = config.learning_failure_threshold
        rule_config.min_training_samples = config.min_training_samples
        
        rule_config.enable_warm_up_mode = config.enable_warm_up_mode
        rule_config.enable_intelligence_engines = config.enable_intelligence_engines
        rule_config.enable_advanced_bid_optimization = config.enable_advanced_bid_optimization
        
        # Validate configuration
        rule_config.validate()
        
        # Reinitialize AI engine with new config
        ai_engine = AIRuleEngine(rule_config, db_connector)
        
        logger.info(f"AI control config updated")
        
        return {"status": "success", "message": "AI control configuration updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating AI control config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _calculate_account_health_score(acos: float, roas: float, ctr: float, cvr: float, orders: int) -> float:
    """Calculate account health score (0-100)"""
    score = 100.0
    
    # ACOS penalty (higher ACOS = lower score)
    if acos > 0:
        target_acos = rule_config.acos_target * 100
        if acos > target_acos * 2:
            score -= 30
        elif acos > target_acos * 1.5:
            score -= 20
        elif acos > target_acos:
            score -= 10
    
    # ROAS bonus/penalty
    if roas >= 5:
        score += 10
    elif roas < 1:
        score -= 20
    elif roas < 2:
        score -= 10
    
    # CTR consideration
    if ctr < 0.2:
        score -= 10
    elif ctr > 0.5:
        score += 5
    
    # CVR consideration
    if cvr < 5:
        score -= 10
    elif cvr > 15:
        score += 10
    
    # Volume consideration
    if orders < 10:
        score -= 5
    elif orders > 100:
        score += 5
    
    return max(0, min(100, score))


def _get_campaign_ai_signal(campaign: Dict[str, Any]) -> Optional[str]:
    """Get AI recommendation signal for a campaign"""
    spend = float(campaign.get('total_cost', 0) or 0)
    sales = float(campaign.get('total_sales', 0) or 0)
    budget = float(campaign.get('budget_amount', 0) or 0)
    
    if budget > 0 and spend >= budget * 0.9:
        return "budget_constrained"
    
    if sales > 0:
        acos = spend / sales
        if acos > rule_config.acos_target * 2:
            return "wasted_spend"
        elif acos < rule_config.acos_target * 0.5:
            return "scaling_opportunity"
    
    return None


def _calculate_estimated_impact(rec) -> str:
    """Calculate estimated impact of a recommendation"""
    if rec.adjustment_type == 'bid':
        if rec.adjustment_percentage < 0:
            return f"Spend ↓ ~{abs(rec.adjustment_percentage):.0f}%"
        else:
            return f"Sales ↑ ~{rec.adjustment_percentage:.0f}%"
    elif rec.adjustment_type == 'budget':
        if rec.adjustment_percentage > 0:
            return f"Opportunity ↑ ~{rec.adjustment_percentage:.0f}%"
        else:
            return f"Waste ↓ ~{abs(rec.adjustment_percentage):.0f}%"
    return "Impact TBD"


def _calculate_estimated_impact_str(rec: dict) -> str:
    """Calculate estimated impact from recommendation dict"""
    current = rec.get('current_value', 0)
    recommended = rec.get('recommended_value', 0)
    adjustment_type = rec.get('adjustment_type', 'bid')
    
    if current > 0:
        pct = ((recommended - current) / current) * 100
        if adjustment_type == 'bid':
            if pct < 0:
                return f"Spend ↓ ~{abs(pct):.0f}%"
            else:
                return f"Sales ↑ ~{pct:.0f}%"
    return "Impact TBD"


def _build_recommendation_reason(signals: dict, adjustment_type: str) -> str:
    """Build human-readable reason from intelligence signals"""
    reasons = []
    
    if signals.get('acos_tier'):
        tier = signals['acos_tier']
        if 'high' in tier.lower():
            reasons.append(f"ACOS in high tier ({tier})")
        elif 'low' in tier.lower():
            reasons.append(f"ACOS performing well ({tier})")
    
    if signals.get('conversion_tier'):
        reasons.append(f"Conversions: {signals['conversion_tier']}")
    
    if signals.get('ctr_status'):
        reasons.append(f"CTR: {signals['ctr_status']}")
    
    if signals.get('spend_status'):
        reasons.append(f"Spend: {signals['spend_status']}")
    
    if not reasons:
        return f"AI-optimized {adjustment_type} recommendation based on performance analysis"
    
    return "; ".join(reasons)


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
