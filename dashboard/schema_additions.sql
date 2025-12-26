-- ============================================================================
-- DASHBOARD-SPECIFIC DATABASE SCHEMA ADDITIONS
-- Run this after the main schema.sql to add dashboard functionality
-- ============================================================================

-- Table for storing dashboard user preferences
CREATE TABLE IF NOT EXISTS dashboard_user_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL UNIQUE,
    default_date_range INT DEFAULT 7,
    dark_mode BOOLEAN DEFAULT TRUE,
    auto_refresh_enabled BOOLEAN DEFAULT TRUE,
    auto_refresh_interval_seconds INT DEFAULT 60,
    saved_filters JSONB DEFAULT '{}',
    notification_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing saved views/filters
CREATE TABLE IF NOT EXISTS dashboard_saved_views (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    view_name VARCHAR(255) NOT NULL,
    view_type VARCHAR(50) NOT NULL, -- 'campaigns', 'keywords', 'recommendations'
    filters JSONB NOT NULL,
    column_visibility JSONB DEFAULT '{}',
    sort_config JSONB DEFAULT '{}',
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing approved/rejected recommendation history
CREATE TABLE IF NOT EXISTS recommendation_actions (
    id SERIAL PRIMARY KEY,
    recommendation_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    action_taken VARCHAR(50) NOT NULL, -- 'approved', 'rejected', 'modified', 'scheduled'
    original_value DECIMAL(10, 2),
    recommended_value DECIMAL(10, 2),
    final_value DECIMAL(10, 2),
    user_id VARCHAR(100),
    reason TEXT,
    scheduled_time TIMESTAMP,
    executed_at TIMESTAMP,
    execution_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'executed', 'failed', 'cancelled'
    api_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for dashboard analytics (tracking dashboard usage)
CREATE TABLE IF NOT EXISTS dashboard_analytics (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    session_id VARCHAR(255),
    page_viewed VARCHAR(100),
    action_type VARCHAR(100),
    action_details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing strategy configurations per portfolio/campaign
CREATE TABLE IF NOT EXISTS strategy_configurations (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL, -- 'account', 'portfolio', 'campaign'
    entity_id BIGINT,
    strategy VARCHAR(50) NOT NULL, -- 'launch', 'growth', 'profit', 'liquidate'
    target_acos DECIMAL(5, 4) NOT NULL,
    max_bid_cap DECIMAL(10, 2),
    min_bid_floor DECIMAL(10, 2),
    ai_mode VARCHAR(50) DEFAULT 'human_review', -- 'autonomous', 'human_review', 'warm_up'
    enable_dayparting BOOLEAN DEFAULT FALSE,
    enable_inventory_protection BOOLEAN DEFAULT FALSE,
    enable_brand_defense BOOLEAN DEFAULT FALSE,
    custom_rules JSONB DEFAULT '{}',
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id)
);

-- Table for storing alert configurations and history
CREATE TABLE IF NOT EXISTS alert_configurations (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id BIGINT,
    threshold_type VARCHAR(50), -- 'above', 'below', 'change_percent'
    threshold_value DECIMAL(10, 4),
    comparison_period_days INT DEFAULT 1,
    severity VARCHAR(50) DEFAULT 'medium',
    is_active BOOLEAN DEFAULT TRUE,
    notification_channels JSONB DEFAULT '["dashboard"]', -- 'dashboard', 'email', 'slack'
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_history (
    id SERIAL PRIMARY KEY,
    alert_config_id INT REFERENCES alert_configurations(id),
    alert_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id BIGINT,
    entity_name VARCHAR(255),
    severity VARCHAR(50),
    message TEXT NOT NULL,
    metric_value DECIMAL(10, 4),
    threshold_value DECIMAL(10, 4),
    is_read BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    dismissed_at TIMESTAMP
);

-- Table for dayparting configurations
CREATE TABLE IF NOT EXISTS dayparting_config (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    day_of_week INT NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6), -- 0 = Monday
    hour_of_day INT NOT NULL CHECK (hour_of_day >= 0 AND hour_of_day <= 23),
    bid_multiplier DECIMAL(5, 2) DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id, day_of_week, hour_of_day)
);

-- Table for inventory health data (Vendor Central specific)
CREATE TABLE IF NOT EXISTS inventory_health (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(20) NOT NULL,
    product_name VARCHAR(500),
    sku VARCHAR(100),
    current_inventory INT DEFAULT 0,
    weekly_velocity INT DEFAULT 0,
    days_of_supply INT,
    restock_date DATE,
    ad_status VARCHAR(50) DEFAULT 'active', -- 'active', 'paused_low_inventory', 'paused_out_of_stock'
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asin)
);

-- Table for ASIN-level performance aggregation
CREATE TABLE IF NOT EXISTS asin_performance (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(20) NOT NULL,
    report_date DATE NOT NULL,
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(10, 2) DEFAULT 0,
    attributed_sales_7d DECIMAL(10, 2) DEFAULT 0,
    attributed_conversions_7d INT DEFAULT 0,
    organic_sales DECIMAL(10, 2) DEFAULT 0,
    total_sales DECIMAL(10, 2) DEFAULT 0,
    ppc_dependency_score DECIMAL(5, 4), -- 0-1, how dependent on PPC
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asin, report_date)
);

-- Table for search term harvesting candidates
CREATE TABLE IF NOT EXISTS search_term_harvesting (
    id SERIAL PRIMARY KEY,
    search_term TEXT NOT NULL,
    source_campaign_id BIGINT,
    source_ad_group_id BIGINT,
    suggested_campaign_id BIGINT,
    suggested_ad_group_id BIGINT,
    suggested_match_type VARCHAR(50),
    total_impressions BIGINT DEFAULT 0,
    total_clicks BIGINT DEFAULT 0,
    total_cost DECIMAL(10, 2) DEFAULT 0,
    total_sales DECIMAL(10, 2) DEFAULT 0,
    total_orders INT DEFAULT 0,
    acos DECIMAL(10, 4),
    roas DECIMAL(10, 4),
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'promoted', 'rejected', 'ignored'
    promoted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for dashboard tables
CREATE INDEX IF NOT EXISTS idx_dashboard_user_prefs ON dashboard_user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_saved_views_user ON dashboard_saved_views(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_actions_rec ON recommendation_actions(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_actions_entity ON recommendation_actions(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_analytics_timestamp ON dashboard_analytics(timestamp);
CREATE INDEX IF NOT EXISTS idx_strategy_config_entity ON strategy_configurations(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_triggered ON alert_history(triggered_at);
CREATE INDEX IF NOT EXISTS idx_alert_history_unread ON alert_history(is_read, is_dismissed);
CREATE INDEX IF NOT EXISTS idx_dayparting_config_entity ON dayparting_config(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_inventory_health_asin ON inventory_health(asin);
CREATE INDEX IF NOT EXISTS idx_asin_performance_date ON asin_performance(report_date);
CREATE INDEX IF NOT EXISTS idx_search_term_harvesting_status ON search_term_harvesting(status);

-- Apply updated_at triggers to new tables
DROP TRIGGER IF EXISTS update_dashboard_user_prefs_updated_at ON dashboard_user_preferences;
CREATE TRIGGER update_dashboard_user_prefs_updated_at BEFORE UPDATE ON dashboard_user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_dashboard_saved_views_updated_at ON dashboard_saved_views;
CREATE TRIGGER update_dashboard_saved_views_updated_at BEFORE UPDATE ON dashboard_saved_views
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_strategy_configurations_updated_at ON strategy_configurations;
CREATE TRIGGER update_strategy_configurations_updated_at BEFORE UPDATE ON strategy_configurations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_alert_configurations_updated_at ON alert_configurations;
CREATE TRIGGER update_alert_configurations_updated_at BEFORE UPDATE ON alert_configurations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_dayparting_config_updated_at ON dayparting_config;
CREATE TRIGGER update_dayparting_config_updated_at BEFORE UPDATE ON dayparting_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_asin_performance_updated_at ON asin_performance;
CREATE TRIGGER update_asin_performance_updated_at BEFORE UPDATE ON asin_performance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_search_term_harvesting_updated_at ON search_term_harvesting;
CREATE TRIGGER update_search_term_harvesting_updated_at BEFORE UPDATE ON search_term_harvesting
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default strategy configuration for account-level
INSERT INTO strategy_configurations (entity_type, entity_id, strategy, target_acos, max_bid_cap, ai_mode)
VALUES ('account', NULL, 'growth', 0.09, 4.52, 'human_review')
ON CONFLICT (entity_type, entity_id) DO NOTHING;

