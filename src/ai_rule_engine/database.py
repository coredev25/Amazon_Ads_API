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
                ELSE NULL 
            END as roas_7d,
            CASE 
                WHEN attributed_sales_7d > 0 THEN (cost / attributed_sales_7d)
                ELSE NULL 
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
                ELSE NULL 
            END as roas_7d,
            CASE 
                WHEN attributed_sales_7d > 0 THEN (cost / attributed_sales_7d)
                ELSE NULL 
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
                ELSE NULL 
            END as roas_7d,
            CASE 
                WHEN attributed_sales_7d > 0 THEN (cost / attributed_sales_7d)
                ELSE NULL 
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
                ELSE NULL 
            END as avg_roas,
            CASE 
                WHEN SUM(cp.attributed_sales_7d) > 0 THEN (SUM(cp.cost) / SUM(cp.attributed_sales_7d))
                ELSE NULL 
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
        ORDER BY total_cost DESC
        """
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, (start_date,))
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
                ELSE NULL 
            END as avg_roas,
            CASE 
                WHEN SUM(agp.attributed_sales_7d) > 0 THEN (SUM(agp.cost) / SUM(agp.attributed_sales_7d))
                ELSE NULL 
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
                ELSE NULL 
            END as avg_roas,
            CASE 
                WHEN SUM(kp.attributed_sales_7d) > 0 THEN (SUM(kp.cost) / SUM(kp.attributed_sales_7d))
                ELSE NULL 
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
    
    # ============================================================================
    # RE-ENTRY CONTROL & BID CHANGE TRACKING METHODS
    # ============================================================================
    
    def get_last_bid_change(self, entity_type: str, entity_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the last bid change for an entity
        
        Args:
            entity_type: Type of entity (keyword, ad_group, campaign)
            entity_id: Entity ID
            
        Returns:
            Last bid change record or None
        """
        query = """
        SELECT 
            id,
            entity_type,
            entity_id,
            entity_name,
            change_date,
            old_bid,
            new_bid,
            change_amount,
            change_percentage,
            reason,
            acos_at_change,
            roas_at_change,
            ctr_at_change,
            metadata
        FROM bid_change_history
        WHERE entity_type = %s AND entity_id = %s
        ORDER BY change_date DESC
        LIMIT 1
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (entity_type, entity_id))
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Error fetching last bid change: {e}")
            return None
    
    def get_bid_change_history(self, entity_type: str, entity_id: int, 
                               days_back: int = 14) -> List[Dict[str, Any]]:
        """
        Get bid change history for an entity
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            days_back: Days to look back
            
        Returns:
            List of bid changes
        """
        query = """
        SELECT 
            id,
            entity_type,
            entity_id,
            entity_name,
            change_date,
            old_bid,
            new_bid,
            change_amount,
            change_percentage,
            reason,
            acos_at_change,
            roas_at_change,
            ctr_at_change,
            metadata
        FROM bid_change_history
        WHERE entity_type = %s 
            AND entity_id = %s
            AND change_date >= %s
        ORDER BY change_date DESC
        """
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (entity_type, entity_id, start_date))
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error fetching bid change history: {e}")
            return []
    
    def save_bid_change(self, change_record: Dict[str, Any]) -> Optional[int]:
        """
        Save a bid change record to the database
        
        Args:
            change_record: Bid change record dictionary
            
        Returns:
            Inserted change ID if successful, None otherwise
        """
        query = """
        INSERT INTO bid_change_history (
            entity_type, entity_id, entity_name, change_date,
            old_bid, new_bid, change_amount, change_percentage,
            reason, triggered_by, acos_at_change, roas_at_change,
            ctr_at_change, conversions_at_change, metadata
        ) VALUES (
            %(entity_type)s, %(entity_id)s, %(entity_name)s, %(change_date)s,
            %(old_bid)s, %(new_bid)s, %(change_amount)s, %(change_percentage)s,
            %(reason)s, %(triggered_by)s, %(acos_at_change)s, %(roas_at_change)s,
            %(ctr_at_change)s, %(conversions_at_change)s, %(metadata)s
        )
        RETURNING id
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, change_record)
                    change_id_row = cursor.fetchone()
                    conn.commit()
                    if change_id_row:
                        change_id = change_id_row[0]
                        self.logger.info(f"Bid change saved: ID {change_id}")
                        return change_id
                    self.logger.error("Bid change insert returned no ID")
                    return None
        except Exception as e:
            self.logger.error(f"Error saving bid change: {e}")
            return None
    
    def get_acos_history(self, entity_type: str, entity_id: int, 
                        days_back: int = 14) -> List[Dict[str, Any]]:
        """
        Get ACOS history for an entity from performance data
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            days_back: Days to look back
            
        Returns:
            List of ACOS values by date
        """
        # Determine which table to query based on entity type
        if entity_type == 'keyword':
            table = 'keyword_performance'
            id_column = 'keyword_id'
        elif entity_type == 'ad_group':
            table = 'ad_group_performance'
            id_column = 'ad_group_id'
        elif entity_type == 'campaign':
            table = 'campaign_performance'
            id_column = 'campaign_id'
        else:
            self.logger.error(f"Invalid entity type: {entity_type}")
            return []
        
        query = f"""
        SELECT 
            report_date as check_date,
            CASE 
                WHEN attributed_sales_7d > 0 THEN (cost / attributed_sales_7d)
                ELSE NULL 
            END as acos_value,
            cost,
            attributed_sales_7d as sales
        FROM {table}
        WHERE {id_column} = %s
            AND report_date >= %s
            AND cost > 0
        ORDER BY report_date DESC
        """
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (entity_id, start_date))
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error fetching ACOS history: {e}")
            return []
    
    def save_acos_trend(self, entity_type: str, entity_id: int, 
                       acos_value: float, trend_window_days: int,
                       is_stable: bool, variance: Optional[float] = None) -> bool:
        """
        Save ACOS trend tracking data
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            acos_value: Current ACOS value
            trend_window_days: Window size for trend calculation
            is_stable: Whether the trend is stable
            variance: Variance value
            
        Returns:
            True if successful
        """
        query = """
        INSERT INTO acos_trend_tracking (
            entity_type, entity_id, check_date, acos_value,
            trend_window_days, is_stable, variance
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (entity_id, entity_type, check_date, trend_window_days)
        DO UPDATE SET 
            acos_value = EXCLUDED.acos_value,
            is_stable = EXCLUDED.is_stable,
            variance = EXCLUDED.variance
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (
                        entity_type, entity_id, datetime.now(), acos_value,
                        trend_window_days, is_stable, variance
                    ))
                    conn.commit()
                    return True
        except Exception as e:
            self.logger.error(f"Error saving ACOS trend: {e}")
            return False
    
    def check_bid_lock(self, entity_type: str, entity_id: int) -> Optional[Dict[str, Any]]:
        """
        Check if entity has an active bid adjustment lock
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            
        Returns:
            Lock record if active, None otherwise
        """
        query = """
        SELECT 
            id,
            entity_type,
            entity_id,
            locked_until,
            lock_reason,
            last_change_id
        FROM bid_adjustment_locks
        WHERE entity_type = %s 
            AND entity_id = %s
            AND locked_until > %s
        ORDER BY locked_until DESC
        LIMIT 1
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (entity_type, entity_id, datetime.now()))
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Error checking bid lock: {e}")
            return None
    
    def create_bid_lock(self, entity_type: str, entity_id: int, 
                       lock_days: int, reason: str, 
                       change_id: Optional[int] = None) -> bool:
        """
        Create a bid adjustment lock for an entity
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            lock_days: Number of days to lock
            reason: Reason for lock
            change_id: ID of associated bid change
            
        Returns:
            True if successful
        """
        query = """
        INSERT INTO bid_adjustment_locks (
            entity_type, entity_id, locked_until, lock_reason, last_change_id
        ) VALUES (
            %s, %s, %s, %s, %s
        )
        ON CONFLICT (entity_id, entity_type)
        DO UPDATE SET 
            locked_until = EXCLUDED.locked_until,
            lock_reason = EXCLUDED.lock_reason,
            last_change_id = EXCLUDED.last_change_id
        WHERE bid_adjustment_locks.locked_until < EXCLUDED.locked_until
        """
        
        locked_until = datetime.now() + timedelta(days=lock_days)
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (entity_type, entity_id, locked_until, reason, change_id))
                    conn.commit()
                    self.logger.info(f"Bid lock created for {entity_type} {entity_id} until {locked_until}")
                    return True
        except Exception as e:
            self.logger.error(f"Error creating bid lock: {e}")
            return False
    
    def get_oscillating_entities(self) -> List[Dict[str, Any]]:
        """
        Get entities that are experiencing bid oscillation
        
        Returns:
            List of oscillating entities
        """
        query = """
        SELECT 
            entity_type,
            entity_id,
            entity_name,
            direction_changes,
            last_change_date,
            is_oscillating
        FROM bid_oscillation_detection
        WHERE is_oscillating = TRUE
        ORDER BY direction_changes DESC
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query)
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error fetching oscillating entities: {e}")
            return []

    def get_bid_constraint(self, constraint_type: str, constraint_key: str) -> Optional[Dict[str, Any]]:
        """
        Fetch bid constraint override for given type/key (e.g., ASIN or category)
        """
        query = """
        SELECT bid_cap, bid_floor
        FROM bid_constraints
        WHERE constraint_type = %s AND constraint_key = %s
        LIMIT 1
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (constraint_type, constraint_key))
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Error fetching bid constraint for {constraint_type}:{constraint_key}: {e}")
            return None

    def get_entity_performance_range(self, entity_type: str, entity_id: int,
                                     start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Retrieve raw performance rows for an entity between two dates.
        Used by evaluation pipeline for outcome analysis.
        """
        table_map = {
            'campaign': ('campaign_performance', 'campaign_id'),
            'ad_group': ('ad_group_performance', 'ad_group_id'),
            'keyword': ('keyword_performance', 'keyword_id')
        }
        if entity_type not in table_map:
            self.logger.error(f"Unsupported entity type for performance range: {entity_type}")
            return []
        table, column = table_map[entity_type]
        query = f"""
        SELECT
            report_date,
            impressions,
            clicks,
            cost,
            attributed_conversions_7d,
            attributed_sales_7d
        FROM {table}
        WHERE {column} = %s
          AND report_date BETWEEN %s AND %s
        ORDER BY report_date ASC
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (entity_id, start_date, end_date))
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error fetching performance range for {entity_type} {entity_id}: {e}")
            return []

    def create_model_training_run(self, model_version: int, status: str,
                                  metrics: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        Persist a model training run record for observability/versioning.
        """
        query = """
        INSERT INTO model_training_runs (
            model_version, status, train_accuracy, test_accuracy,
            train_auc, test_auc, brier_score, promoted, started_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        ) RETURNING id
        """
        metrics = metrics or {}
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (
                        model_version,
                        status,
                        metrics.get('train_accuracy'),
                        metrics.get('test_accuracy'),
                        metrics.get('train_auc'),
                        metrics.get('test_auc'),
                        metrics.get('brier_score'),
                        metrics.get('promoted', False)
                    ))
                    run_id = cursor.fetchone()[0]
                    conn.commit()
                    return run_id
        except Exception as e:
            self.logger.error(f"Error creating model training run: {e}")
            return None

    def update_model_training_run(self, run_id: int, status: str,
                                  metrics: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update status/metrics for an existing training run.
        """
        metrics = metrics or {}
        query = """
        UPDATE model_training_runs
        SET status = %s,
            train_accuracy = COALESCE(%s, train_accuracy),
            test_accuracy = COALESCE(%s, test_accuracy),
            train_auc = COALESCE(%s, train_auc),
            test_auc = COALESCE(%s, test_auc),
            brier_score = COALESCE(%s, brier_score),
            promoted = COALESCE(%s, promoted),
            completed_at = CASE
                WHEN %s IN ('success','failed') THEN CURRENT_TIMESTAMP
                ELSE completed_at
            END
        WHERE id = %s
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (
                        status,
                        metrics.get('train_accuracy'),
                        metrics.get('test_accuracy'),
                        metrics.get('train_auc'),
                        metrics.get('test_auc'),
                        metrics.get('brier_score'),
                        metrics.get('promoted'),
                        status,
                        run_id
                    ))
                    conn.commit()
                    return True
        except Exception as e:
            self.logger.error(f"Error updating model training run {run_id}: {e}")
            return False
    
    def get_latest_model_training_run(self) -> Optional[Dict[str, Any]]:
        """Return most recent training run for retraining heuristics (#16)."""
        query = """
        SELECT *
        FROM model_training_runs
        ORDER BY started_at DESC
        LIMIT 1
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query)
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Error fetching latest model training run: {e}")
            return None
    
    # ============================================================================
    # LEARNING LOOP & RECOMMENDATION TRACKING METHODS (FIX #1, #2, #14)
    # ============================================================================
    
    def save_recommendation(self, tracking_data: Dict[str, Any]) -> bool:
        """
        FIX #1: Save recommendation tracking data to database
        
        Args:
            tracking_data: Recommendation tracking dictionary
            
        Returns:
            True if successful
        """
        query = """
        INSERT INTO recommendation_tracking (
            recommendation_id, entity_type, entity_id, adjustment_type,
            recommended_value, current_value, intelligence_signals,
            strategy_id, policy_variant, created_at, applied, metadata
        ) VALUES (
            %(recommendation_id)s, %(entity_type)s, %(entity_id)s, %(adjustment_type)s,
            %(recommended_value)s, %(current_value)s, %(intelligence_signals)s,
            %(strategy_id)s, %(policy_variant)s, %(timestamp)s, %(applied)s, %(metadata)s
        )
        ON CONFLICT (recommendation_id) DO UPDATE SET
            applied = EXCLUDED.applied,
            applied_at = CASE WHEN EXCLUDED.applied THEN CURRENT_TIMESTAMP ELSE recommendation_tracking.applied_at END
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, tracking_data)
                    conn.commit()
                    return True
        except Exception as e:
            self.logger.error(f"Error saving recommendation: {e}")
            return False
    
    def get_tracked_recommendation(self, recommendation_id: str) -> Optional[Dict[str, Any]]:
        """
        FIX #2: Get tracked recommendation from database
        
        Args:
            recommendation_id: Recommendation ID
            
        Returns:
            Tracking data dictionary or None
        """
        query = """
        SELECT 
            recommendation_id, entity_type, entity_id, adjustment_type,
            recommended_value, current_value, intelligence_signals,
            strategy_id, policy_variant,
            created_at, applied, applied_at, metadata
        FROM recommendation_tracking
        WHERE recommendation_id = %s
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (recommendation_id,))
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Error fetching tracked recommendation: {e}")
            return None
    
    def save_learning_outcome(self, outcome: 'PerformanceOutcome', 
                            intelligence_signals: Optional[Dict[str, Any]] = None) -> bool:
        """
        FIX #14: Save learning outcome to database for long-term training
        
        Args:
            outcome: PerformanceOutcome object
            intelligence_signals: Optional intelligence signals
            
        Returns:
            True if successful
        """
        # Prepare features for ML (simplified version)
        features = {
            'before_acos': outcome.before_metrics.get('acos'),
            'before_roas': outcome.before_metrics.get('roas'),
            'before_ctr': outcome.before_metrics.get('ctr'),
            'before_conversions': outcome.before_metrics.get('conversions'),
            'before_spend': outcome.before_metrics.get('spend'),
            'before_sales': outcome.before_metrics.get('sales'),
            'adjustment_type': outcome.adjustment_type,
            'recommended_value': outcome.recommended_value,
            'applied_value': outcome.applied_value,
            'intelligence_signals': intelligence_signals
        }
        
        query = """
        INSERT INTO learning_outcomes (
            recommendation_id, entity_type, entity_id, adjustment_type,
            recommended_value, applied_value, before_metrics, after_metrics,
            outcome, improvement_percentage, label, strategy_id, policy_variant,
            is_holdout, features, timestamp
        ) VALUES (
            %(recommendation_id)s, %(entity_type)s, %(entity_id)s, %(adjustment_type)s,
            %(recommended_value)s, %(applied_value)s, %(before_metrics)s, %(after_metrics)s,
            %(outcome)s, %(improvement_percentage)s, %(label)s, %(strategy_id)s,
            %(policy_variant)s, %(is_holdout)s, %(features)s, %(timestamp)s
        )
        """
        
        try:
            import json
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, {
                        'recommendation_id': outcome.recommendation_id,
                        'entity_type': outcome.entity_type,
                        'entity_id': outcome.entity_id,
                        'adjustment_type': outcome.adjustment_type,
                        'recommended_value': outcome.recommended_value,
                        'applied_value': outcome.applied_value,
                        'before_metrics': json.dumps(outcome.before_metrics),
                        'after_metrics': json.dumps(outcome.after_metrics),
                        'outcome': outcome.outcome,
                        'improvement_percentage': outcome.improvement_percentage,
                        'label': 1 if outcome.outcome == 'success' else 0,
                        'strategy_id': getattr(outcome, 'strategy_id', None),
                        'policy_variant': getattr(outcome, 'policy_variant', None),
                        'is_holdout': getattr(outcome, 'is_holdout', False),
                        'features': json.dumps(features),
                        'timestamp': outcome.timestamp
                    })
                    conn.commit()
                    return True
        except Exception as e:
            self.logger.error(f"Error saving learning outcome: {e}")
            return False
    
    def get_bid_changes_for_evaluation(self, min_age_days: int = 14) -> List[Dict[str, Any]]:
        """
        Get bid changes that are ready for evaluation (≥14 days old)
        
        Args:
            min_age_days: Minimum age in days
            
        Returns:
            List of bid changes ready for evaluation
        """
        query = """
        SELECT 
            id, entity_type, entity_id, change_date,
            old_bid, new_bid, performance_before, performance_after,
            outcome_score, outcome_label, evaluated_at
        FROM bid_change_history
        WHERE evaluated_at IS NULL
            AND change_date <= %s
            AND performance_before IS NOT NULL
        ORDER BY change_date ASC
        """
        
        cutoff_date = datetime.now() - timedelta(days=min_age_days)
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, (cutoff_date,))
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error fetching bid changes for evaluation: {e}")
            return []
    
    def update_bid_change_outcome(self, change_id: int, outcome_score: float,
                                 outcome_label: str, performance_after: Dict[str, float]) -> bool:
        """
        Update bid change with outcome evaluation results
        
        Args:
            change_id: Bid change ID
            outcome_score: Outcome score
            outcome_label: Outcome label ('success', 'failure', 'neutral')
            performance_after: Performance metrics after change
            
        Returns:
            True if successful
        """
        query = """
        UPDATE bid_change_history
        SET outcome_score = %s,
            outcome_label = %s,
            performance_after = %s,
            evaluated_at = %s
        WHERE id = %s
        """
        
        try:
            import json
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (
                        outcome_score,
                        outcome_label,
                        json.dumps(performance_after),
                        datetime.now(),
                        change_id
                    ))
                    conn.commit()
                    return True
        except Exception as e:
            self.logger.error(f"Error updating bid change outcome: {e}")
            return False