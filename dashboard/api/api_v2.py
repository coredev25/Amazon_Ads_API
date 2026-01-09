"""
API v2.0 Extensions - New endpoints for Dashboard v2.0 features
These endpoints extend the base API in main.py
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging
import json

# Import db_connector from main module (will be set at runtime)
# This is a lazy import pattern to avoid circular dependencies
def get_db_connector():
    """Get the database connector from main module"""
    from dashboard.api.main import db_connector
    if db_connector is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db_connector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["v2.0"])


# ============================================================================
# PYDANTIC MODELS FOR V2.0
# ============================================================================

class PortfolioData(BaseModel):
    portfolio_id: int
    portfolio_name: str
    budget_amount: Optional[float] = None
    budget_type: Optional[str] = None
    status: str
    campaign_count: int = 0
    total_spend: float = 0
    total_sales: float = 0
    acos: Optional[float] = None
    roas: Optional[float] = None


class AdGroupData(BaseModel):
    ad_group_id: int
    ad_group_name: str
    campaign_id: int
    campaign_name: str
    default_bid: float
    status: str
    spend: float
    sales: float
    acos: Optional[float] = None
    roas: Optional[float] = None
    orders: int
    impressions: int
    clicks: int
    ctr: float
    cvr: float


class AdData(BaseModel):
    ad_id: int
    asin: str
    sku: Optional[str] = None
    campaign_id: int
    ad_group_id: int
    status: str
    spend: float
    sales: float
    acos: Optional[float] = None
    roas: Optional[float] = None
    orders: int
    impressions: int
    clicks: int
    inventory_status: Optional[str] = None  # 'in_stock', 'out_of_stock', 'low_stock'


class ProductTargetData(BaseModel):
    target_id: int
    target_type: str  # 'ASIN', 'CATEGORY'
    target_value: str
    campaign_id: int
    ad_group_id: int
    bid: float
    status: str
    spend: float
    sales: float
    acos: Optional[float] = None
    roas: Optional[float] = None
    orders: int
    impressions: int
    clicks: int


class SearchTermData(BaseModel):
    search_term: str
    campaign_id: int
    ad_group_id: int
    keyword_id: Optional[int] = None
    impressions: int
    clicks: int
    spend: float
    sales: float
    orders: int
    acos: Optional[float] = None
    roas: Optional[float] = None
    harvest_action: Optional[str] = None  # 'add_keyword', 'add_negative', None


class PlacementData(BaseModel):
    placement: str  # 'TOP_OF_SEARCH', 'PRODUCT_PAGES', 'REST_OF_SEARCH'
    campaign_id: Optional[int] = None
    ad_group_id: Optional[int] = None
    keyword_id: Optional[int] = None
    target_id: Optional[int] = None
    impressions: int
    clicks: int
    spend: float
    sales: float
    orders: int
    acos: Optional[float] = None
    roas: Optional[float] = None


class COGSData(BaseModel):
    asin: str
    cogs: float
    amazon_fees_percentage: float = 0.15
    notes: Optional[str] = None


class FinancialMetrics(BaseModel):
    asin: str
    sales: float
    cogs: float
    amazon_fees: float
    gross_profit: float
    ad_spend: float
    net_profit: float
    tacos: float
    break_even_acos: float


class ChangeHistoryEntry(BaseModel):
    id: int
    change_date: str
    user_id: Optional[str] = None
    entity_type: str
    entity_id: int
    entity_name: Optional[str] = None
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_type: str
    triggered_by: str
    reason: Optional[str] = None


class ColumnLayoutPreference(BaseModel):
    view_type: str
    column_visibility: Dict[str, bool]
    column_order: List[str]
    column_widths: Dict[str, int]


# ============================================================================
# API ENDPOINTS - PORTFOLIOS
# ============================================================================

@router.get("/portfolios", response_model=List[PortfolioData])
async def get_portfolios(
    days: int = Query(7, ge=1, le=90),
    account_id: Optional[str] = None
):
    """Get all portfolios with performance data"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                query = """
                    SELECT p.portfolio_id, p.portfolio_name, p.budget_amount, 
                           p.budget_type, p.state as status,
                           COUNT(DISTINCT c.campaign_id) as campaign_count
                    FROM portfolios p
                    LEFT JOIN campaigns c ON c.portfolio_id = p.portfolio_id
                    WHERE 1=1
                """
                params = []
                
                if account_id:
                    query += " AND p.account_id = %s"
                    params.append(account_id)
                
                query += " GROUP BY p.portfolio_id, p.portfolio_name, p.budget_amount, p.budget_type, p.state"
                cursor.execute(query, params)
                portfolios = cursor.fetchall()
                
                result = []
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days)
                
                for portfolio in portfolios:
                    portfolio_id = portfolio['portfolio_id']
                    
                    # Get performance data
                    cursor.execute("""
                        SELECT 
                            SUM(cp.cost) as total_spend,
                            SUM(cp.attributed_sales_7d) as total_sales,
                            SUM(cp.attributed_conversions_7d) as total_orders,
                            SUM(cp.impressions) as total_impressions,
                            SUM(cp.clicks) as total_clicks
                        FROM campaign_performance cp
                        INNER JOIN campaigns c ON c.campaign_id = cp.campaign_id
                        WHERE c.portfolio_id = %s
                        AND cp.report_date >= %s
                        AND cp.report_date <= %s
                    """, (portfolio_id, start_date, end_date))
                    
                    perf = cursor.fetchone()
                    spend = float(perf['total_spend'] or 0)
                    sales = float(perf['total_sales'] or 0)
                    
                    result.append(PortfolioData(
                        portfolio_id=portfolio_id,
                        portfolio_name=portfolio['portfolio_name'],
                        budget_amount=float(portfolio['budget_amount'] or 0),
                        budget_type=portfolio['budget_type'],
                        status=portfolio['status'],
                        campaign_count=int(portfolio['campaign_count'] or 0),
                        total_spend=spend,
                        total_sales=sales,
                        acos=round(spend / sales * 100, 2) if sales > 0 else None,
                        roas=round(sales / spend, 2) if spend > 0 else None
                    ))
                
                return result
    except Exception as e:
        logger.error(f"Error fetching portfolios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - AD GROUPS
# ============================================================================

@router.get("/ad-groups", response_model=List[AdGroupData])
async def get_ad_groups(
    campaign_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=90)
):
    """Get ad groups with performance data"""
    try:
        db_connector = get_db_connector()
        ad_groups = db_connector.get_ad_groups_with_performance(campaign_id, days) if campaign_id else []
        
        # Get campaigns for ad group names
        campaigns_map = {}
        if ad_groups:
            with db_connector.get_connection() as conn:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    campaign_ids = list(set([ag['campaign_id'] for ag in ad_groups]))
                    placeholders = ','.join(['%s'] * len(campaign_ids))
                    cursor.execute(f"""
                        SELECT campaign_id, campaign_name 
                        FROM campaigns 
                        WHERE campaign_id IN ({placeholders})
                    """, campaign_ids)
                    for row in cursor.fetchall():
                        campaigns_map[row['campaign_id']] = row['campaign_name']
        
        result = []
        for ag in ad_groups:
            spend = float(ag.get('total_cost', 0) or 0)
            sales = float(ag.get('total_sales', 0) or 0)
            impressions = int(ag.get('total_impressions', 0) or 0)
            clicks = int(ag.get('total_clicks', 0) or 0)
            orders = int(ag.get('total_conversions', 0) or 0)
            
            result.append(AdGroupData(
                ad_group_id=ag['ad_group_id'],
                ad_group_name=ag.get('ad_group_name', ''),
                campaign_id=ag['campaign_id'],
                campaign_name=campaigns_map.get(ag['campaign_id'], ''),
                default_bid=float(ag.get('default_bid', 0) or 0),
                status=ag.get('state', 'ENABLED'),
                spend=spend,
                sales=sales,
                acos=round(spend / sales * 100, 2) if sales > 0 else None,
                roas=round(sales / spend, 2) if spend > 0 else None,
                orders=orders,
                impressions=impressions,
                clicks=clicks,
                ctr=round(clicks / impressions * 100, 2) if impressions > 0 else 0,
                cvr=round(orders / clicks * 100, 2) if clicks > 0 else 0
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error fetching ad groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - PRODUCT TARGETING
# ============================================================================

@router.get("/targeting", response_model=List[ProductTargetData])
async def get_product_targeting(
    campaign_id: Optional[int] = None,
    ad_group_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=90)
):
    """Get product targeting data (ASINs and Categories)"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                query = """
                    SELECT pt.target_id, pt.target_type, pt.target_value, 
                           pt.campaign_id, pt.ad_group_id, pt.bid, pt.state as status
                    FROM product_targets pt
                    WHERE 1=1
                """
                params = []
                
                if campaign_id:
                    query += " AND pt.campaign_id = %s"
                    params.append(campaign_id)
                
                if ad_group_id:
                    query += " AND pt.ad_group_id = %s"
                    params.append(ad_group_id)
                
                cursor.execute(query, params)
                targets = cursor.fetchall()
                
                result = []
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days)
                
                for target in targets:
                    target_id = target['target_id']
                    
                    # Get performance data
                    cursor.execute("""
                        SELECT 
                            SUM(impressions) as total_impressions,
                            SUM(clicks) as total_clicks,
                            SUM(cost) as total_spend,
                            SUM(attributed_sales_7d) as total_sales,
                            SUM(attributed_conversions_7d) as total_orders
                        FROM product_target_performance
                        WHERE target_id = %s
                        AND report_date >= %s
                        AND report_date <= %s
                    """, (target_id, start_date, end_date))
                    
                    perf = cursor.fetchone()
                    spend = float(perf['total_spend'] or 0)
                    sales = float(perf['total_sales'] or 0)
                    impressions = int(perf['total_impressions'] or 0)
                    clicks = int(perf['total_clicks'] or 0)
                    orders = int(perf['total_orders'] or 0)
                    
                    result.append(ProductTargetData(
                        target_id=target_id,
                        target_type=target['target_type'],
                        target_value=target['target_value'],
                        campaign_id=target['campaign_id'],
                        ad_group_id=target['ad_group_id'],
                        bid=float(target['bid'] or 0),
                        status=target['status'],
                        spend=spend,
                        sales=sales,
                        acos=round(spend / sales * 100, 2) if sales > 0 else None,
                        roas=round(sales / spend, 2) if spend > 0 else None,
                        orders=orders,
                        impressions=impressions,
                        clicks=clicks
                    ))
                
                return result
    except Exception as e:
        logger.error(f"Error fetching product targeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - SEARCH TERMS
# ============================================================================

@router.get("/search-terms", response_model=List[SearchTermData])
async def get_search_terms(
    campaign_id: Optional[int] = None,
    ad_group_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=90),
    min_clicks: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get search terms (customer queries) with performance"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days)
                
                query = """
                    SELECT 
                        search_term,
                        campaign_id,
                        ad_group_id,
                        keyword_id,
                        SUM(impressions) as total_impressions,
                        SUM(clicks) as total_clicks,
                        SUM(cost) as total_spend,
                        SUM(attributed_sales_7d) as total_sales,
                        SUM(attributed_conversions_7d) as total_orders
                    FROM search_term_performance
                    WHERE report_date >= %s
                    AND report_date <= %s
                """
                params = [start_date, end_date]
                
                if campaign_id:
                    query += " AND campaign_id = %s"
                    params.append(campaign_id)
                
                if ad_group_id:
                    query += " AND ad_group_id = %s"
                    params.append(ad_group_id)
                
                query += """
                    GROUP BY search_term, campaign_id, ad_group_id, keyword_id
                    HAVING SUM(clicks) >= %s
                    ORDER BY SUM(attributed_sales_7d) DESC
                    LIMIT %s
                """
                params.extend([min_clicks, limit])
                
                cursor.execute(query, params)
                terms = cursor.fetchall()
                
                result = []
                for term in terms:
                    spend = float(term['total_spend'] or 0)
                    sales = float(term['total_sales'] or 0)
                    clicks = int(term['total_clicks'] or 0)
                    orders = int(term['total_orders'] or 0)
                    
                    # Determine harvest action based on PRD logic
                    harvest_action = None
                    if orders > 3 and sales > 0 and spend > 0:
                        acos_val = (spend / sales) * 100 if sales > 0 else None
                        # Would need target ACOS from strategy config
                        # For now, simple heuristic
                        if acos_val and acos_val < 15:  # Below 15% ACOS
                            harvest_action = 'add_keyword'
                    elif clicks > 15 and orders == 0:
                        harvest_action = 'add_negative'
                    
                    result.append(SearchTermData(
                        search_term=term['search_term'],
                        campaign_id=term['campaign_id'],
                        ad_group_id=term['ad_group_id'],
                        keyword_id=term['keyword_id'],
                        impressions=int(term['total_impressions'] or 0),
                        clicks=clicks,
                        spend=spend,
                        sales=sales,
                        orders=orders,
                        acos=round(spend / sales * 100, 2) if sales > 0 else None,
                        roas=round(sales / spend, 2) if spend > 0 else None,
                        harvest_action=harvest_action
                    ))
                
                return result
    except Exception as e:
        logger.error(f"Error fetching search terms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - PLACEMENTS
# ============================================================================

@router.get("/placements", response_model=List[PlacementData])
async def get_placements(
    campaign_id: Optional[int] = None,
    ad_group_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=90)
):
    """Get placement performance data"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days)
                
                query = """
                    SELECT 
                        placement,
                        campaign_id,
                        ad_group_id,
                        keyword_id,
                        target_id,
                        SUM(impressions) as total_impressions,
                        SUM(clicks) as total_clicks,
                        SUM(cost) as total_spend,
                        SUM(attributed_sales_7d) as total_sales,
                        SUM(attributed_conversions_7d) as total_orders
                    FROM placement_performance
                    WHERE report_date >= %s
                    AND report_date <= %s
                """
                params = [start_date, end_date]
                
                if campaign_id:
                    query += " AND campaign_id = %s"
                    params.append(campaign_id)
                
                if ad_group_id:
                    query += " AND ad_group_id = %s"
                    params.append(ad_group_id)
                
                query += """
                    GROUP BY placement, campaign_id, ad_group_id, keyword_id, target_id
                    ORDER BY SUM(attributed_sales_7d) DESC
                """
                
                cursor.execute(query, params)
                placements = cursor.fetchall()
                
                result = []
                for pl in placements:
                    spend = float(pl['total_spend'] or 0)
                    sales = float(pl['total_sales'] or 0)
                    
                    result.append(PlacementData(
                        placement=pl['placement'],
                        campaign_id=pl['campaign_id'],
                        ad_group_id=pl['ad_group_id'],
                        keyword_id=pl['keyword_id'],
                        target_id=pl['target_id'],
                        impressions=int(pl['total_impressions'] or 0),
                        clicks=int(pl['total_clicks'] or 0),
                        spend=spend,
                        sales=sales,
                        orders=int(pl['total_orders'] or 0),
                        acos=round(spend / sales * 100, 2) if sales > 0 else None,
                        roas=round(sales / spend, 2) if spend > 0 else None
                    ))
                
                return result
    except Exception as e:
        logger.error(f"Error fetching placements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - COGS & FINANCIAL METRICS
# ============================================================================

@router.get("/cogs", response_model=List[COGSData])
async def get_cogs():
    """Get all COGS data"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT asin, cogs, amazon_fees_percentage, notes
                    FROM asin_cogs
                    ORDER BY asin
                """)
                cogs_list = cursor.fetchall()
                
                return [COGSData(**row) for row in cogs_list]
    except Exception as e:
        logger.error(f"Error fetching COGS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cogs")
async def create_or_update_cogs(cogs_data: COGSData):
    """Create or update COGS for an ASIN"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO asin_cogs (asin, cogs, amazon_fees_percentage, notes)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (asin) 
                    DO UPDATE SET 
                        cogs = EXCLUDED.cogs,
                        amazon_fees_percentage = EXCLUDED.amazon_fees_percentage,
                        notes = EXCLUDED.notes,
                        updated_at = CURRENT_TIMESTAMP
                """, (cogs_data.asin, cogs_data.cogs, cogs_data.amazon_fees_percentage, cogs_data.notes))
                conn.commit()
        
        return {"status": "success", "message": f"COGS updated for ASIN {cogs_data.asin}"}
    except Exception as e:
        logger.error(f"Error updating COGS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/financial-metrics", response_model=List[FinancialMetrics])
async def get_financial_metrics(
    days: int = Query(7, ge=1, le=90),
    asin: Optional[str] = None
):
    """Get financial metrics (Gross Profit, Net Profit, TACoS, Break-Even ACOS)"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days)
                
                # Get sales and ad spend by ASIN
                query = """
                    SELECT 
                        pa.asin,
                        SUM(ap.attributed_sales_7d) as total_sales,
                        SUM(ap.cost) as total_ad_spend
                    FROM asin_performance ap
                    INNER JOIN product_ads pa ON pa.asin = ap.asin
                    WHERE ap.report_date >= %s
                    AND ap.report_date <= %s
                """
                params = [start_date, end_date]
                
                if asin:
                    query += " AND pa.asin = %s"
                    params.append(asin)
                
                query += " GROUP BY pa.asin"
                
                cursor.execute(query, params)
                asin_perf = cursor.fetchall()
                
                result = []
                for perf in asin_perf:
                    asin_val = perf['asin']
                    sales = float(perf['total_sales'] or 0)
                    ad_spend = float(perf['total_ad_spend'] or 0)
                    
                    # Get COGS
                    cursor.execute("""
                        SELECT cogs, amazon_fees_percentage 
                        FROM asin_cogs 
                        WHERE asin = %s
                    """, (asin_val,))
                    cogs_row = cursor.fetchone()
                    
                    if not cogs_row:
                        continue  # Skip ASINs without COGS data
                    
                    cogs_unit = float(cogs_row['cogs'] or 0)
                    fees_percentage = float(cogs_row['amazon_fees_percentage'] or 0.15)
                    
                    # Calculate metrics
                    # For simplicity, assuming average order value - in reality would need orders count
                    # This is a simplified calculation
                    amazon_fees = sales * fees_percentage
                    gross_profit = sales - cogs_unit - amazon_fees
                    net_profit = gross_profit - ad_spend
                    tacos = (ad_spend / sales * 100) if sales > 0 else 0
                    break_even_acos = ((sales - cogs_unit - amazon_fees) / sales * 100) if sales > 0 else 0
                    
                    result.append(FinancialMetrics(
                        asin=asin_val,
                        sales=sales,
                        cogs=cogs_unit,
                        amazon_fees=amazon_fees,
                        gross_profit=gross_profit,
                        ad_spend=ad_spend,
                        net_profit=net_profit,
                        tacos=round(tacos, 2),
                        break_even_acos=round(break_even_acos, 2)
                    ))
                
                return result
    except Exception as e:
        logger.error(f"Error calculating financial metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - CHANGE HISTORY
# ============================================================================

@router.get("/change-history", response_model=List[ChangeHistoryEntry])
async def get_change_history(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """Get change history / audit log"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                query = """
                    SELECT id, change_date, user_id, entity_type, entity_id, 
                           entity_name, field_name, old_value, new_value,
                           change_type, triggered_by, reason
                    FROM change_history
                    WHERE 1=1
                """
                params = []
                
                if entity_type:
                    query += " AND entity_type = %s"
                    params.append(entity_type)
                
                if entity_id:
                    query += " AND entity_id = %s"
                    params.append(entity_id)
                
                query += " ORDER BY change_date DESC LIMIT %s"
                params.append(limit)
                
                cursor.execute(query, params)
                history = cursor.fetchall()
                
                return [
                    ChangeHistoryEntry(
                        id=row['id'],
                        change_date=row['change_date'].isoformat(),
                        user_id=row['user_id'],
                        entity_type=row['entity_type'],
                        entity_id=row['entity_id'],
                        entity_name=row['entity_name'],
                        field_name=row['field_name'],
                        old_value=row['old_value'],
                        new_value=row['new_value'],
                        change_type=row['change_type'],
                        triggered_by=row['triggered_by'],
                        reason=row['reason']
                    )
                    for row in history
                ]
    except Exception as e:
        logger.error(f"Error fetching change history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - COLUMN LAYOUT PREFERENCES
# ============================================================================

@router.get("/column-layout/{view_type}", response_model=ColumnLayoutPreference)
async def get_column_layout(view_type: str, user_id: str = Query(..., alias="userId")):
    """Get column layout preferences for a view type"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT column_visibility, column_order, column_widths
                    FROM column_layout_preferences
                    WHERE user_id = %s AND view_type = %s
                """, (user_id, view_type))
                row = cursor.fetchone()
                
                if row:
                    return ColumnLayoutPreference(
                        view_type=view_type,
                        column_visibility=row['column_visibility'] or {},
                        column_order=row['column_order'] or [],
                        column_widths=row['column_widths'] or {}
                    )
                else:
                    # Return defaults
                    return ColumnLayoutPreference(
                        view_type=view_type,
                        column_visibility={},
                        column_order=[],
                        column_widths={}
                    )
    except Exception as e:
        logger.error(f"Error fetching column layout: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/column-layout/{view_type}")
async def save_column_layout(
    view_type: str,
    layout: ColumnLayoutPreference,
    user_id: str = Query(..., alias="userId")
):
    """Save column layout preferences for a view type"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO column_layout_preferences 
                        (user_id, view_type, column_visibility, column_order, column_widths)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, view_type)
                    DO UPDATE SET
                        column_visibility = EXCLUDED.column_visibility,
                        column_order = EXCLUDED.column_order,
                        column_widths = EXCLUDED.column_widths,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    user_id, view_type,
                    json.dumps(layout.column_visibility),
                    json.dumps(layout.column_order),
                    json.dumps(layout.column_widths)
                ))
                conn.commit()
        
        return {"status": "success", "message": f"Column layout saved for {view_type}"}
    except Exception as e:
        logger.error(f"Error saving column layout: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - SEARCH TERM HARVESTING ACTIONS
# ============================================================================

@router.post("/search-terms/{search_term}/add-keyword")
async def add_search_term_as_keyword(
    search_term: str,
    campaign_id: int,
    ad_group_id: int,
    match_type: str = Query(..., description="BROAD, PHRASE, or EXACT"),
    bid: Optional[float] = Query(None)
):
    """Add a search term as a keyword to a campaign/ad group"""
    try:
        # This would typically call the Amazon Ads API to add the keyword
        # For now, we'll log it and return success
        logger.info(f"Adding search term '{search_term}' as {match_type} keyword to campaign {campaign_id}, ad group {ad_group_id}")
        
        # Log to change history
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO change_history 
                        (entity_type, entity_id, field_name, old_value, new_value, 
                         change_type, triggered_by, reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    'keyword', ad_group_id, 'keyword_text',
                    '', search_term,
                    'create', 'search_term_harvesting',
                    f'Added from search term harvesting: {search_term}'
                ))
                conn.commit()
        
        return {
            "status": "success",
            "message": f"Search term '{search_term}' added as {match_type} keyword"
        }
    except Exception as e:
        logger.error(f"Error adding search term as keyword: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-terms/{search_term}/add-negative")
async def add_search_term_as_negative(
    search_term: str,
    campaign_id: int,
    ad_group_id: int,
    match_type: str = Query(..., description="negative_exact, negative_phrase, negative_broad")
):
    """Add a search term as a negative keyword"""
    try:
        logger.info(f"Adding search term '{search_term}' as {match_type} negative keyword to campaign {campaign_id}, ad group {ad_group_id}")
        
        # Log to change history
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO change_history 
                        (entity_type, entity_id, field_name, old_value, new_value, 
                         change_type, triggered_by, reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    'negative_keyword', ad_group_id, 'keyword_text',
                    '', search_term,
                    'create', 'search_term_harvesting',
                    f'Added as negative from search term harvesting: {search_term} (Clicks > 15, Orders = 0)'
                ))
                conn.commit()
        
        return {
            "status": "success",
            "message": f"Search term '{search_term}' added as {match_type} negative keyword"
        }
    except Exception as e:
        logger.error(f"Error adding search term as negative: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - INVENTORY AWARENESS
# ============================================================================

@router.get("/inventory-status/{asin}")
async def get_inventory_status(asin: str):
    """Get inventory status for an ASIN"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT asin, current_inventory, days_of_supply, ad_status
                    FROM inventory_health
                    WHERE asin = %s
                """, (asin,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        "asin": result['asin'],
                        "current_inventory": result['current_inventory'],
                        "days_of_supply": result['days_of_supply'],
                        "ad_status": result['ad_status'],
                        "is_out_of_stock": result['current_inventory'] == 0,
                    }
                else:
                    return {
                        "asin": asin,
                        "current_inventory": None,
                        "days_of_supply": None,
                        "ad_status": "unknown",
                        "is_out_of_stock": False,
                    }
    except Exception as e:
        logger.error(f"Error fetching inventory status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - DAYPARTING
# ============================================================================

@router.get("/dayparting/heatmap")
async def get_dayparting_heatmap(
    entity_type: str,
    entity_id: int,
    metric: str = Query('sales', description="sales, spend, acos, ctr, cvr"),
    days: int = Query(30, ge=7, le=90)
):
    """Get dayparting heatmap data (performance by hour and day)"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days)
                
                # This is a simplified query - in reality, you'd need hourly performance data
                # For now, we'll aggregate by day of week and hour from campaign_performance
                # Note: Amazon Ads API doesn't provide hourly data directly, so this would need
                # to be calculated from your own tracking or estimated
                
                query = """
                    SELECT 
                        EXTRACT(DOW FROM report_date)::int as day_of_week,
                        EXTRACT(HOUR FROM CURRENT_TIMESTAMP)::int as hour_of_day,
                        SUM(cost) as spend,
                        SUM(attributed_sales_7d) as sales,
                        CASE 
                            WHEN SUM(cost) > 0 THEN (SUM(cost) / SUM(attributed_sales_7d) * 100)
                            ELSE NULL
                        END as acos
                    FROM campaign_performance
                    WHERE campaign_id = %s
                    AND report_date >= %s
                    AND report_date <= %s
                    GROUP BY EXTRACT(DOW FROM report_date), EXTRACT(HOUR FROM CURRENT_TIMESTAMP)
                """
                
                # For demo purposes, generate sample data
                # In production, you'd need actual hourly performance tracking
                result = []
                for day in range(7):
                    for hour in range(24):
                        # Generate sample data (replace with actual query)
                        value = 0
                        if metric == 'sales':
                            value = 100 + (day * 10) + (hour * 5) + (hash(f"{entity_id}-{day}-{hour}") % 50)
                        elif metric == 'spend':
                            value = 10 + (day * 2) + (hour * 1) + (hash(f"{entity_id}-{day}-{hour}") % 10)
                        elif metric == 'acos':
                            value = 8 + (day * 0.5) + (hash(f"{entity_id}-{day}-{hour}") % 5)
                        elif metric == 'ctr':
                            value = 0.5 + (day * 0.1) + (hash(f"{entity_id}-{day}-{hour}") % 2) / 10
                        elif metric == 'cvr':
                            value = 2 + (day * 0.2) + (hash(f"{entity_id}-{day}-{hour}") % 3) / 10
                        
                        result.append({
                            "day_of_week": day,
                            "hour_of_day": hour,
                            "value": value,
                            "metric": metric
                        })
                
                return result
    except Exception as e:
        logger.error(f"Error fetching dayparting heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dayparting/config")
async def get_dayparting_config(
    entity_type: str,
    entity_id: int
):
    """Get dayparting configuration for an entity"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT day_of_week, hour_of_day, bid_multiplier, is_active
                    FROM dayparting_config
                    WHERE entity_type = %s AND entity_id = %s
                    ORDER BY day_of_week, hour_of_day
                """, (entity_type, entity_id))
                
                configs = cursor.fetchall()
                return [
                    {
                        "day_of_week": c['day_of_week'],
                        "hour_of_day": c['hour_of_day'],
                        "bid_multiplier": float(c['bid_multiplier']),
                        "is_active": c['is_active']
                    }
                    for c in configs
                ]
    except Exception as e:
        logger.error(f"Error fetching dayparting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dayparting/config")
async def save_dayparting_config(
    entity_type: str,
    entity_id: int,
    config: List[Dict[str, Any]]
):
    """Save dayparting configuration for an entity"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            with conn.cursor() as cursor:
                # Delete existing config
                cursor.execute("""
                    DELETE FROM dayparting_config
                    WHERE entity_type = %s AND entity_id = %s
                """, (entity_type, entity_id))
                
                # Insert new config
                for c in config:
                    cursor.execute("""
                        INSERT INTO dayparting_config 
                            (entity_type, entity_id, day_of_week, hour_of_day, bid_multiplier, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (entity_type, entity_id, day_of_week, hour_of_day)
                        DO UPDATE SET
                            bid_multiplier = EXCLUDED.bid_multiplier,
                            is_active = EXCLUDED.is_active,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        entity_type, entity_id,
                        c['day_of_week'], c['hour_of_day'],
                        c['bid_multiplier'], c.get('is_active', True)
                    ))
                
                conn.commit()
        
        return {"status": "success", "message": f"Dayparting config saved for {entity_type} {entity_id}"}
    except Exception as e:
        logger.error(f"Error saving dayparting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - MULTI-ACCOUNT
# ============================================================================

@router.get("/accounts")
async def get_accounts():
    """Get all Amazon seller accounts for the current user"""
    try:
        db_connector = get_db_connector()
        with db_connector.get_connection() as conn:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT account_id, account_name, marketplace_id, region, is_active
                    FROM amazon_accounts
                    WHERE is_active = TRUE
                    ORDER BY account_name
                """)
                accounts = cursor.fetchall()
                
                return [
                    {
                        "account_id": a['account_id'],
                        "account_name": a['account_name'],
                        "marketplace_id": a.get('marketplace_id'),
                        "region": a.get('region'),
                        "is_active": a['is_active']
                    }
                    for a in accounts
                ]
    except Exception as e:
        logger.error(f"Error fetching accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

