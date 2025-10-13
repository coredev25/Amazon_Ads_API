"""
Database connector for AI Rule Engine
"""

import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging


class DatabaseConnector:
    """Database connector for retrieving Amazon Ads performance data"""
    
    def __init__(self, connection_string: str = None):
        """
        Initialize database connector
        
        Args:
            connection_string: PostgreSQL connection string (optional, will use env vars if not provided)
        """
        if connection_string:
            self.connection_string = connection_string
        else:
            # Build connection string from individual environment variables
            import os
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'amazon_ads')
            db_user = os.getenv('DB_USER', 'postgres')
            db_password = os.getenv('DB_PASSWORD')
            
            if not db_password:
                raise ValueError("DB_PASSWORD environment variable is required")
            
            self.connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        self.logger = logging.getLogger(__name__)
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)
    
    def get_campaign_performance(self, campaign_id: int, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Get campaign performance data for the last N days
        
        Args:
            campaign_id: Campaign ID
            days_back: Number of days to look back
            
        Returns:
            List of performance records
        """
        query = """
        SELECT 
            report_date,
            impressions,
            clicks,
            cost,
            attributed_conversions_1d,
            attributed_conversions_7d,
            attributed_sales_1d,
            attributed_sales_7d,
            CASE 
                WHEN cost > 0 THEN (attributed_sales_7d / cost)
                ELSE 0 
            END as roas_7d,
            CASE 
                WHEN attributed_sales_7d > 0 THEN (cost / attributed_sales_7d)
                ELSE 0 
            END as acos_7d,
            CASE 
                WHEN impressions > 0 THEN (clicks::float / impressions * 100)
                ELSE 0 
            END as ctr
        FROM campaign_performance 
        WHERE campaign_id = %s 
        AND report_date >= %s
        ORDER BY report_date DESC
        """
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (campaign_id, start_date))
                return cursor.fetchall()
    
    def get_ad_group_performance(self, ad_group_id: int, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Get ad group performance data for the last N days
        
        Args:
            ad_group_id: Ad Group ID
            days_back: Number of days to look back
            
        Returns:
            List of performance records
        """
        query = """
        SELECT 
            report_date,
            impressions,
            clicks,
            cost,
            attributed_conversions_1d,
            attributed_conversions_7d,
            attributed_sales_1d,
            attributed_sales_7d,
            CASE 
                WHEN cost > 0 THEN (attributed_sales_7d / cost)
                ELSE 0 
            END as roas_7d,
            CASE 
                WHEN attributed_sales_7d > 0 THEN (cost / attributed_sales_7d)
                ELSE 0 
            END as acos_7d,
            CASE 
                WHEN impressions > 0 THEN (clicks::float / impressions * 100)
                ELSE 0 
            END as ctr
        FROM ad_group_performance 
        WHERE ad_group_id = %s 
        AND report_date >= %s
        ORDER BY report_date DESC
        """
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (ad_group_id, start_date))
                return cursor.fetchall()
    
    def get_keyword_performance(self, keyword_id: int, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Get keyword performance data for the last N days
        
        Args:
            keyword_id: Keyword ID
            days_back: Number of days to look back
            
        Returns:
            List of performance records
        """
        query = """
        SELECT 
            report_date,
            impressions,
            clicks,
            cost,
            attributed_conversions_1d,
            attributed_conversions_7d,
            attributed_sales_1d,
            attributed_sales_7d,
            CASE 
                WHEN cost > 0 THEN (attributed_sales_7d / cost)
                ELSE 0 
            END as roas_7d,
            CASE 
                WHEN attributed_sales_7d > 0 THEN (cost / attributed_sales_7d)
                ELSE 0 
            END as acos_7d,
            CASE 
                WHEN impressions > 0 THEN (clicks::float / impressions * 100)
                ELSE 0 
            END as ctr
        FROM keyword_performance 
        WHERE keyword_id = %s 
        AND report_date >= %s
        ORDER BY report_date DESC
        """
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (keyword_id, start_date))
                return cursor.fetchall()
    
    def get_campaigns_with_performance(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Get all campaigns with their performance data
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of campaigns with aggregated performance
        """
        query = """
        SELECT 
            c.campaign_id,
            c.campaign_name,
            c.campaign_status,
            c.budget_amount,
            c.budget_type,
            COALESCE(SUM(cp.impressions), 0) as total_impressions,
            COALESCE(SUM(cp.clicks), 0) as total_clicks,
            COALESCE(SUM(cp.cost), 0) as total_cost,
            COALESCE(SUM(cp.attributed_conversions_7d), 0) as total_conversions,
            COALESCE(SUM(cp.attributed_sales_7d), 0) as total_sales,
            CASE 
                WHEN SUM(cp.cost) > 0 THEN (SUM(cp.attributed_sales_7d) / SUM(cp.cost))
                ELSE 0 
            END as avg_roas,
            CASE 
                WHEN SUM(cp.attributed_sales_7d) > 0 THEN (SUM(cp.cost) / SUM(cp.attributed_sales_7d))
                ELSE 0 
            END as avg_acos,
            CASE 
                WHEN SUM(cp.impressions) > 0 THEN (SUM(cp.clicks)::float / SUM(cp.impressions) * 100)
                ELSE 0 
            END as avg_ctr
        FROM campaigns c
        LEFT JOIN campaign_performance cp ON c.campaign_id = cp.campaign_id 
            AND cp.report_date >= %s
        WHERE c.campaign_status = 'enabled'
        GROUP BY c.campaign_id, c.campaign_name, c.campaign_status, c.budget_amount, c.budget_type
        HAVING SUM(cp.impressions) >= %s
        ORDER BY total_cost DESC
        """
        
        start_date = datetime.now() - timedelta(days=days_back)
        min_impressions = 100  # Minimum impressions threshold
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (start_date, min_impressions))
                return cursor.fetchall()
    
    def get_ad_groups_with_performance(self, campaign_id: int, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Get ad groups for a campaign with their performance data
        
        Args:
            campaign_id: Campaign ID
            days_back: Number of days to look back
            
        Returns:
            List of ad groups with aggregated performance
        """
        query = """
        SELECT 
            ag.ad_group_id,
            ag.ad_group_name,
            ag.default_bid,
            ag.state,
            COALESCE(SUM(agp.impressions), 0) as total_impressions,
            COALESCE(SUM(agp.clicks), 0) as total_clicks,
            COALESCE(SUM(agp.cost), 0) as total_cost,
            COALESCE(SUM(agp.attributed_conversions_7d), 0) as total_conversions,
            COALESCE(SUM(agp.attributed_sales_7d), 0) as total_sales,
            CASE 
                WHEN SUM(agp.cost) > 0 THEN (SUM(agp.attributed_sales_7d) / SUM(agp.cost))
                ELSE 0 
            END as avg_roas,
            CASE 
                WHEN SUM(agp.attributed_sales_7d) > 0 THEN (SUM(agp.cost) / SUM(agp.attributed_sales_7d))
                ELSE 0 
            END as avg_acos,
            CASE 
                WHEN SUM(agp.impressions) > 0 THEN (SUM(agp.clicks)::float / SUM(agp.impressions) * 100)
                ELSE 0 
            END as avg_ctr
        FROM ad_groups ag
        LEFT JOIN ad_group_performance agp ON ag.ad_group_id = agp.ad_group_id 
            AND agp.report_date >= %s
        WHERE ag.campaign_id = %s AND ag.state = 'enabled'
        GROUP BY ag.ad_group_id, ag.ad_group_name, ag.default_bid, ag.state
        HAVING SUM(agp.impressions) >= %s
        ORDER BY total_cost DESC
        """
        
        start_date = datetime.now() - timedelta(days=days_back)
        min_impressions = 50  # Minimum impressions threshold for ad groups
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (start_date, campaign_id, min_impressions))
                return cursor.fetchall()
    
    def get_keywords_with_performance(self, ad_group_id: int, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Get keywords for an ad group with their performance data
        
        Args:
            ad_group_id: Ad Group ID
            days_back: Number of days to look back
            
        Returns:
            List of keywords with aggregated performance
        """
        query = """
        SELECT 
            k.keyword_id,
            k.keyword_text,
            k.match_type,
            k.bid,
            k.state,
            COALESCE(SUM(kp.impressions), 0) as total_impressions,
            COALESCE(SUM(kp.clicks), 0) as total_clicks,
            COALESCE(SUM(kp.cost), 0) as total_cost,
            COALESCE(SUM(kp.attributed_conversions_7d), 0) as total_conversions,
            COALESCE(SUM(kp.attributed_sales_7d), 0) as total_sales,
            CASE 
                WHEN SUM(kp.cost) > 0 THEN (SUM(kp.attributed_sales_7d) / SUM(kp.cost))
                ELSE 0 
            END as avg_roas,
            CASE 
                WHEN SUM(kp.attributed_sales_7d) > 0 THEN (SUM(kp.cost) / SUM(kp.attributed_sales_7d))
                ELSE 0 
            END as avg_acos,
            CASE 
                WHEN SUM(kp.impressions) > 0 THEN (SUM(kp.clicks)::float / SUM(kp.impressions) * 100)
                ELSE 0 
            END as avg_ctr
        FROM keywords k
        LEFT JOIN keyword_performance kp ON k.keyword_id = kp.keyword_id 
            AND kp.report_date >= %s
        WHERE k.ad_group_id = %s AND k.state = 'enabled'
        GROUP BY k.keyword_id, k.keyword_text, k.match_type, k.bid, k.state
        HAVING SUM(kp.impressions) >= %s
        ORDER BY total_cost DESC
        """
        
        start_date = datetime.now() - timedelta(days=days_back)
        min_impressions = 10  # Minimum impressions threshold for keywords
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (start_date, ad_group_id, min_impressions))
                return cursor.fetchall()
    
    def get_recent_adjustments(self, entity_type: str, entity_id: int, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent adjustments for an entity to enforce cooldown periods
        
        Args:
            entity_type: 'campaign', 'ad_group', or 'keyword'
            entity_id: Entity ID
            hours_back: Hours to look back for adjustments
            
        Returns:
            List of recent adjustments
        """
        # This would require an adjustments_log table to track changes
        # For now, return empty list
        return []
    
    def log_adjustment(self, entity_type: str, entity_id: int, adjustment_type: str, 
                      old_value: float, new_value: float, reason: str) -> None:
        """
        Log an adjustment for tracking and cooldown enforcement
        
        Args:
            entity_type: Type of entity adjusted
            entity_id: ID of entity adjusted
            adjustment_type: Type of adjustment (bid, budget, etc.)
            old_value: Previous value
            new_value: New value
            reason: Reason for adjustment
        """
        # This would require an adjustments_log table
        # For now, just log to console
        self.logger.info(f"Adjustment logged: {entity_type} {entity_id} - {adjustment_type} "
                        f"from {old_value} to {new_value} - {reason}")
