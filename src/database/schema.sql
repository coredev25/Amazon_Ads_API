-- ============================================================================
-- AMAZON ADS COMPLETE DATABASE SCHEMA
-- Consolidated from:
--  - src/database/schema.sql
--  - src/database/ai_settings_schema.sql
--  - dashboard/auth_schema.sql
--  - dashboard/schema_additions.sql
--  - dashboard/schema_additions_v2.sql
-- Version: Consolidated 2.0
-- ============================================================================

-- Run this script in a PostgreSQL database to create all required tables,
-- indexes, triggers, and default configuration for the Amazon Ads API project.

BEGIN;

-- ============================================================================
-- UTILITY: trigger function for updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================================================
-- CORE ADVERTISING TABLES
-- (deduplicated and normalized)
-- ============================================================================

CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id BIGINT UNIQUE NOT NULL,
    campaign_name VARCHAR(255),
    campaign_status VARCHAR(50),  -- ENABLED, PAUSED, ARCHIVED
    targeting_type VARCHAR(50),    -- MANUAL, AUTO
    start_date DATE,
    end_date DATE,
    budget_amount DECIMAL(10, 2),
    budget_type VARCHAR(50),       -- DAILY, LIFETIME
    portfolio_id BIGINT,
    campaign_type VARCHAR(50) DEFAULT 'SP', -- SP, SB, SD
    sb_ad_type VARCHAR(50), -- PRODUCT_COLLECTION, STORE_SPOTLIGHT, VIDEO
    sd_targeting_type VARCHAR(50), -- CONTEXTUAL, AUDIENCES
    account_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ad_groups (
    id SERIAL PRIMARY KEY,
    ad_group_id BIGINT UNIQUE NOT NULL,
    ad_group_name VARCHAR(255),
    campaign_id BIGINT NOT NULL,
    default_bid DECIMAL(10, 2),
    state VARCHAR(50),  -- ENABLED, PAUSED, ARCHIVED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS keywords (
    id SERIAL PRIMARY KEY,
    keyword_id BIGINT UNIQUE NOT NULL,
    keyword_text TEXT,
    match_type VARCHAR(50),  -- BROAD, PHRASE, EXACT
    campaign_id BIGINT NOT NULL,
    ad_group_id BIGINT NOT NULL,
    bid DECIMAL(10, 2),
    state VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_ads (
    id SERIAL PRIMARY KEY,
    ad_id BIGINT UNIQUE NOT NULL,
    campaign_id BIGINT NOT NULL,
    ad_group_id BIGINT NOT NULL,
    asin VARCHAR(20),
    sku VARCHAR(100),
    state VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance tables
CREATE TABLE IF NOT EXISTS campaign_performance (
    id SERIAL PRIMARY KEY,
    campaign_id BIGINT NOT NULL,
    report_date DATE NOT NULL,
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(10, 2) DEFAULT 0,
    attributed_conversions_1d INT DEFAULT 0,
    attributed_conversions_7d INT DEFAULT 0,
    attributed_conversions_14d INT DEFAULT 0,
    attributed_conversions_30d INT DEFAULT 0,
    attributed_sales_1d DECIMAL(10, 2) DEFAULT 0,
    attributed_sales_7d DECIMAL(10, 2) DEFAULT 0,
    attributed_sales_14d DECIMAL(10, 2) DEFAULT 0,
    attributed_sales_30d DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, report_date)
);

CREATE TABLE IF NOT EXISTS ad_group_performance (
    id SERIAL PRIMARY KEY,
    campaign_id BIGINT NOT NULL,
    ad_group_id BIGINT NOT NULL,
    report_date DATE NOT NULL,
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(10, 2) DEFAULT 0,
    attributed_conversions_1d INT DEFAULT 0,
    attributed_conversions_7d INT DEFAULT 0,
    attributed_sales_1d DECIMAL(10, 2) DEFAULT 0,
    attributed_sales_7d DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ad_group_id, report_date)
);

CREATE TABLE IF NOT EXISTS keyword_performance (
    id SERIAL PRIMARY KEY,
    campaign_id BIGINT NOT NULL,
    ad_group_id BIGINT NOT NULL,
    keyword_id BIGINT NOT NULL,
    report_date DATE NOT NULL,
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(10, 2) DEFAULT 0,
    attributed_conversions_1d INT DEFAULT 0,
    attributed_conversions_7d INT DEFAULT 0,
    attributed_sales_1d DECIMAL(10, 2) DEFAULT 0,
    attributed_sales_7d DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(keyword_id, report_date)
);

CREATE TABLE IF NOT EXISTS sync_logs (
    id SERIAL PRIMARY KEY,
    sync_type VARCHAR(50) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(50) NOT NULL,
    records_processed INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- AI RULE ENGINE / LEARNING LOOP / ML TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS bid_change_history (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    entity_name VARCHAR(255),
    change_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    old_bid DECIMAL(10, 2) NOT NULL,
    new_bid DECIMAL(10, 2) NOT NULL,
    change_amount DECIMAL(10, 2) NOT NULL,
    change_percentage DECIMAL(10, 2) NOT NULL,
    reason TEXT,
    triggered_by VARCHAR(100),
    acos_at_change DECIMAL(10, 4),
    roas_at_change DECIMAL(10, 4),
    ctr_at_change DECIMAL(10, 4),
    conversions_at_change INT,
    metadata JSONB,
    performance_before JSONB,
    performance_after JSONB,
    outcome_score DECIMAL(10, 4),
    outcome_label VARCHAR(20),
    evaluated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS acos_trend_tracking (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    check_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acos_value DECIMAL(10, 4) NOT NULL,
    trend_window_days INT NOT NULL,
    is_stable BOOLEAN DEFAULT FALSE,
    variance DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_id, entity_type, check_date, trend_window_days)
);

CREATE TABLE IF NOT EXISTS bid_adjustment_locks (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    locked_until TIMESTAMP NOT NULL,
    lock_reason TEXT,
    last_change_id INT REFERENCES bid_change_history(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_id, entity_type)
);

CREATE TABLE IF NOT EXISTS bid_constraints (
    id SERIAL PRIMARY KEY,
    constraint_type VARCHAR(50) NOT NULL,
    constraint_key TEXT NOT NULL,
    bid_cap DECIMAL(10, 2),
    bid_floor DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(constraint_type, constraint_key)
);

CREATE TABLE IF NOT EXISTS bid_oscillation_detection (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    entity_name VARCHAR(255),
    direction_changes INT DEFAULT 0,
    last_change_date TIMESTAMP,
    is_oscillating BOOLEAN DEFAULT FALSE,
    detection_window_days INT DEFAULT 14,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_id, entity_type)
);

CREATE TABLE IF NOT EXISTS negative_keyword_candidates (
    id SERIAL PRIMARY KEY,
    keyword_id BIGINT NOT NULL,
    keyword_text TEXT NOT NULL,
    match_type VARCHAR(50),
    campaign_id BIGINT NOT NULL,
    ad_group_id BIGINT NOT NULL,
    identified_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    severity VARCHAR(50),
    confidence DECIMAL(5, 4),
    reason TEXT,
    cost_at_identification DECIMAL(10, 2),
    impressions_at_identification BIGINT,
    clicks_at_identification BIGINT,
    conversions_at_identification INT,
    consecutive_failures INT,
    lookback_windows_analyzed INT,
    conversion_probability DECIMAL(5, 4),
    suggested_action VARCHAR(50),
    suggested_match_type VARCHAR(50),
    is_temporary_hold BOOLEAN DEFAULT FALSE,
    hold_expiry_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    applied_date TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS negative_keyword_history (
    id SERIAL PRIMARY KEY,
    keyword_id BIGINT NOT NULL,
    keyword_text TEXT NOT NULL,
    match_type VARCHAR(50),
    campaign_id BIGINT NOT NULL,
    ad_group_id BIGINT NOT NULL,
    marked_negative_date TIMESTAMP NOT NULL,
    reason TEXT,
    cost_at_marking DECIMAL(10, 2),
    consecutive_zero_conversion_windows INT,
    can_be_reactivated BOOLEAN DEFAULT TRUE,
    re_evaluation_date TIMESTAMP,
    reactivated_date TIMESTAMP,
    reactivation_reason TEXT,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS search_term_performance (
    id SERIAL PRIMARY KEY,
    campaign_id BIGINT NOT NULL,
    ad_group_id BIGINT NOT NULL,
    keyword_id BIGINT,
    search_term TEXT NOT NULL,
    report_date DATE NOT NULL,
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(10, 2) DEFAULT 0,
    attributed_conversions_1d INT DEFAULT 0,
    attributed_conversions_7d INT DEFAULT 0,
    attributed_sales_1d DECIMAL(10, 2) DEFAULT 0,
    attributed_sales_7d DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(search_term, keyword_id, report_date)
);

CREATE TABLE IF NOT EXISTS ai_rule_execution_logs (
    id SERIAL PRIMARY KEY,
    execution_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    rule_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id BIGINT,
    entity_name VARCHAR(255),
    action_taken VARCHAR(100),
    old_value DECIMAL(10, 2),
    new_value DECIMAL(10, 2),
    reason TEXT,
    metrics_at_execution JSONB,
    status VARCHAR(50) DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_rule_config_overrides (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50),
    entity_id BIGINT,
    config_key VARCHAR(100) NOT NULL,
    config_value TEXT NOT NULL,
    value_type VARCHAR(50),
    reason TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(entity_type, entity_id, config_key)
);

CREATE TABLE IF NOT EXISTS recommendation_tracking (
    recommendation_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id BIGINT NOT NULL,
    adjustment_type TEXT NOT NULL,
    recommended_value FLOAT NOT NULL,
    current_value FLOAT NOT NULL,
    intelligence_signals JSONB,
    strategy_id TEXT,
    policy_variant TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMP,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS learning_outcomes (
    id SERIAL PRIMARY KEY,
    recommendation_id TEXT NOT NULL REFERENCES recommendation_tracking(recommendation_id),
    entity_type TEXT NOT NULL,
    entity_id BIGINT NOT NULL,
    adjustment_type TEXT NOT NULL,
    recommended_value FLOAT NOT NULL,
    applied_value FLOAT NOT NULL,
    before_metrics JSONB NOT NULL,
    after_metrics JSONB NOT NULL,
    outcome VARCHAR(20) NOT NULL,
    improvement_percentage FLOAT NOT NULL,
    label INT NOT NULL,
    strategy_id TEXT,
    policy_variant TEXT,
    is_holdout BOOLEAN DEFAULT FALSE,
    features JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_training_runs (
    id SERIAL PRIMARY KEY,
    model_version INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    train_accuracy FLOAT,
    test_accuracy FLOAT,
    train_auc FLOAT,
    test_auc FLOAT,
    brier_score FLOAT,
    promoted BOOLEAN DEFAULT FALSE,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS waste_patterns (
    id SERIAL PRIMARY KEY,
    pattern_text TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL,
    is_regex BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pattern_text, severity)
);

-- ============================================================================
-- DASHBOARD & UX TABLES
-- ============================================================================

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

CREATE TABLE IF NOT EXISTS dashboard_saved_views (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    view_name VARCHAR(255) NOT NULL,
    view_type VARCHAR(50) NOT NULL,
    filters JSONB NOT NULL,
    column_visibility JSONB DEFAULT '{}',
    sort_config JSONB DEFAULT '{}',
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recommendation_actions (
    id SERIAL PRIMARY KEY,
    recommendation_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    action_taken VARCHAR(50) NOT NULL,
    original_value DECIMAL(10, 2),
    recommended_value DECIMAL(10, 2),
    final_value DECIMAL(10, 2),
    user_id VARCHAR(100),
    reason TEXT,
    scheduled_time TIMESTAMP,
    executed_at TIMESTAMP,
    execution_status VARCHAR(50) DEFAULT 'pending',
    api_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dashboard_analytics (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    session_id VARCHAR(255),
    page_viewed VARCHAR(100),
    action_type VARCHAR(100),
    action_details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS strategy_configurations (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT,
    strategy VARCHAR(50) NOT NULL,
    target_acos DECIMAL(5, 4) NOT NULL,
    max_bid_cap DECIMAL(10, 2),
    min_bid_floor DECIMAL(10, 2),
    ai_mode VARCHAR(50) DEFAULT 'human_review',
    enable_dayparting BOOLEAN DEFAULT FALSE,
    enable_inventory_protection BOOLEAN DEFAULT FALSE,
    enable_brand_defense BOOLEAN DEFAULT FALSE,
    custom_rules JSONB DEFAULT '{}',
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS alert_configurations (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id BIGINT,
    threshold_type VARCHAR(50),
    threshold_value DECIMAL(10, 4),
    comparison_period_days INT DEFAULT 1,
    severity VARCHAR(50) DEFAULT 'medium',
    is_active BOOLEAN DEFAULT TRUE,
    notification_channels JSONB DEFAULT '["dashboard"]',
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_history (
    id SERIAL PRIMARY KEY,
    alert_config_id INT,
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

CREATE TABLE IF NOT EXISTS dayparting_config (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    day_of_week INT NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
    hour_of_day INT NOT NULL CHECK (hour_of_day >= 0 AND hour_of_day <= 23),
    bid_multiplier DECIMAL(5, 2) DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id, day_of_week, hour_of_day)
);

CREATE TABLE IF NOT EXISTS inventory_health (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(20) NOT NULL,
    product_name VARCHAR(500),
    sku VARCHAR(100),
    current_inventory INT DEFAULT 0,
    weekly_velocity INT DEFAULT 0,
    days_of_supply INT,
    restock_date DATE,
    ad_status VARCHAR(50) DEFAULT 'active',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asin)
);

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
    ppc_dependency_score DECIMAL(5, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asin, report_date)
);

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
    status VARCHAR(50) DEFAULT 'pending',
    promoted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- AUTHENTICATION & USER MANAGEMENT
-- (from dashboard/auth_schema.sql)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- DASHBOARD v2 ADDITIONS (portfolios, product targets, placements, accounts)
-- ============================================================================

CREATE TABLE IF NOT EXISTS portfolios (
    id SERIAL PRIMARY KEY,
    portfolio_id BIGINT UNIQUE NOT NULL,
    portfolio_name VARCHAR(255) NOT NULL,
    budget_amount DECIMAL(10, 2),
    budget_type VARCHAR(50),
    state VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_targets (
    id SERIAL PRIMARY KEY,
    target_id BIGINT UNIQUE NOT NULL,
    campaign_id BIGINT NOT NULL,
    ad_group_id BIGINT NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_value TEXT NOT NULL,
    bid DECIMAL(10, 2),
    state VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_target_performance (
    id SERIAL PRIMARY KEY,
    target_id BIGINT NOT NULL,
    campaign_id BIGINT NOT NULL,
    ad_group_id BIGINT NOT NULL,
    report_date DATE NOT NULL,
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(10, 2) DEFAULT 0,
    attributed_conversions_1d INT DEFAULT 0,
    attributed_conversions_7d INT DEFAULT 0,
    attributed_sales_1d DECIMAL(10, 2) DEFAULT 0,
    attributed_sales_7d DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(target_id, report_date)
);

CREATE TABLE IF NOT EXISTS placement_performance (
    id SERIAL PRIMARY KEY,
    campaign_id BIGINT,
    ad_group_id BIGINT,
    keyword_id BIGINT,
    target_id BIGINT,
    placement VARCHAR(50) NOT NULL,
    report_date DATE NOT NULL,
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(10, 2) DEFAULT 0,
    attributed_conversions_7d INT DEFAULT 0,
    attributed_sales_7d DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unique index that treats NULL keyword_id/target_id as -1 for uniqueness
CREATE UNIQUE INDEX IF NOT EXISTS idx_placement_perf_unique ON placement_performance
    (campaign_id, ad_group_id, COALESCE(keyword_id, -1), COALESCE(target_id, -1), placement, report_date);

CREATE TABLE IF NOT EXISTS asin_cogs (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(20) NOT NULL UNIQUE,
    cogs DECIMAL(10, 2) NOT NULL,
    amazon_fees_percentage DECIMAL(5, 4) DEFAULT 0.15,
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS change_history (
    id SERIAL PRIMARY KEY,
    change_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(100),
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    entity_name VARCHAR(255),
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_type VARCHAR(50) NOT NULL,
    triggered_by VARCHAR(100),
    reason TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS column_layout_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    view_type VARCHAR(50) NOT NULL,
    column_visibility JSONB DEFAULT '{}',
    column_order JSONB DEFAULT '[]',
    column_widths JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, view_type)
);

CREATE TABLE IF NOT EXISTS amazon_accounts (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(100) UNIQUE NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    marketplace_id VARCHAR(50),
    region VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    profile_id BIGINT,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_account_mappings (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    account_id VARCHAR(100) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, account_id)
);

CREATE TABLE IF NOT EXISTS organic_rank_tracking (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(20) NOT NULL,
    keyword_text TEXT NOT NULL,
    rank_position INT,
    rank_date DATE NOT NULL,
    page_number INT,
    ad_rank_position INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asin, keyword_text, rank_date)
);

-- ============================================================================
-- SETTINGS: AI rule engine settings & control
-- (from src/database/ai_settings_schema.sql)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_rule_engine_settings (
    id SERIAL PRIMARY KEY,
    setting_name VARCHAR(100) UNIQUE NOT NULL,
    setting_value JSONB NOT NULL,
    value_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_ai_settings_name ON ai_rule_engine_settings(setting_name);
CREATE INDEX IF NOT EXISTS idx_ai_settings_category ON ai_rule_engine_settings(category);
CREATE INDEX IF NOT EXISTS idx_ai_settings_active ON ai_rule_engine_settings(is_active);

CREATE TABLE IF NOT EXISTS ai_control_settings (
    id SERIAL PRIMARY KEY,
    control_key VARCHAR(100) UNIQUE NOT NULL,
    control_value BOOLEAN NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_ai_control_key ON ai_control_settings(control_key);
CREATE INDEX IF NOT EXISTS idx_ai_control_category ON ai_control_settings(category);
CREATE INDEX IF NOT EXISTS idx_ai_control_active ON ai_control_settings(is_active);

-- Default AI control flags
INSERT INTO ai_control_settings (control_key, control_value, description, category) VALUES
('enable_learning_loop', true, 'Enable machine learning feedback loop', 'feature'),
('enable_advanced_bid_optimization', true, 'Enable advanced bid optimization engine', 'feature'),
('enable_intelligence_engines', true, 'Enable intelligence engines (seasonality, profit, etc.)', 'feature'),
('enable_re_entry_control', true, 'Enable re-entry control to prevent oscillation', 'feature'),
('enable_oscillation_detection', true, 'Enable bid oscillation detection', 'safety'),
('enable_profit_optimization', true, 'Enable profit-based optimization', 'feature'),
('enable_telemetry', true, 'Enable telemetry and metrics collection', 'operation')
ON CONFLICT (control_key) DO NOTHING;

-- ============================================================================
-- FOREIGN KEY CONSTRAINTS (safely added with IF EXISTS / IF NOT EXISTS patterns)
-- ============================================================================

ALTER TABLE ad_groups DROP CONSTRAINT IF EXISTS ad_groups_campaign_id_fkey;
ALTER TABLE ad_groups ADD CONSTRAINT ad_groups_campaign_id_fkey 
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE keywords DROP CONSTRAINT IF EXISTS keywords_campaign_id_fkey;
ALTER TABLE keywords ADD CONSTRAINT keywords_campaign_id_fkey 
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE keywords DROP CONSTRAINT IF EXISTS keywords_ad_group_id_fkey;
ALTER TABLE keywords ADD CONSTRAINT keywords_ad_group_id_fkey 
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE;

ALTER TABLE campaign_performance DROP CONSTRAINT IF EXISTS campaign_performance_campaign_id_fkey;
ALTER TABLE campaign_performance ADD CONSTRAINT campaign_performance_campaign_id_fkey 
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE ad_group_performance DROP CONSTRAINT IF EXISTS ad_group_performance_campaign_id_fkey;
ALTER TABLE ad_group_performance ADD CONSTRAINT ad_group_performance_campaign_id_fkey 
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE ad_group_performance DROP CONSTRAINT IF EXISTS ad_group_performance_ad_group_id_fkey;
ALTER TABLE ad_group_performance ADD CONSTRAINT ad_group_performance_ad_group_id_fkey 
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE;

ALTER TABLE keyword_performance DROP CONSTRAINT IF EXISTS keyword_performance_campaign_id_fkey;
ALTER TABLE keyword_performance ADD CONSTRAINT keyword_performance_campaign_id_fkey 
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE keyword_performance DROP CONSTRAINT IF EXISTS keyword_performance_ad_group_id_fkey;
ALTER TABLE keyword_performance ADD CONSTRAINT keyword_performance_ad_group_id_fkey 
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE;

ALTER TABLE keyword_performance DROP CONSTRAINT IF EXISTS keyword_performance_keyword_id_fkey;
ALTER TABLE keyword_performance ADD CONSTRAINT keyword_performance_keyword_id_fkey 
    FOREIGN KEY (keyword_id) REFERENCES keywords(keyword_id) ON DELETE CASCADE;

ALTER TABLE product_ads DROP CONSTRAINT IF EXISTS product_ads_campaign_id_fkey;
ALTER TABLE product_ads ADD CONSTRAINT product_ads_campaign_id_fkey 
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE product_ads DROP CONSTRAINT IF EXISTS product_ads_ad_group_id_fkey;
ALTER TABLE product_ads ADD CONSTRAINT product_ads_ad_group_id_fkey 
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE;

ALTER TABLE negative_keyword_candidates DROP CONSTRAINT IF EXISTS negative_keyword_candidates_keyword_id_fkey;
ALTER TABLE negative_keyword_candidates ADD CONSTRAINT negative_keyword_candidates_keyword_id_fkey 
    FOREIGN KEY (keyword_id) REFERENCES keywords(keyword_id) ON DELETE CASCADE;

ALTER TABLE negative_keyword_candidates DROP CONSTRAINT IF EXISTS negative_keyword_candidates_campaign_id_fkey;
ALTER TABLE negative_keyword_candidates ADD CONSTRAINT negative_keyword_candidates_campaign_id_fkey 
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE negative_keyword_candidates DROP CONSTRAINT IF EXISTS negative_keyword_candidates_ad_group_id_fkey;
ALTER TABLE negative_keyword_candidates ADD CONSTRAINT negative_keyword_candidates_ad_group_id_fkey 
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE;

ALTER TABLE negative_keyword_history DROP CONSTRAINT IF EXISTS negative_keyword_history_campaign_id_fkey;
ALTER TABLE negative_keyword_history ADD CONSTRAINT negative_keyword_history_campaign_id_fkey 
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE negative_keyword_history DROP CONSTRAINT IF EXISTS negative_keyword_history_ad_group_id_fkey;
ALTER TABLE negative_keyword_history ADD CONSTRAINT negative_keyword_history_ad_group_id_fkey 
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE;

ALTER TABLE search_term_performance DROP CONSTRAINT IF EXISTS search_term_performance_campaign_id_fkey;
ALTER TABLE search_term_performance ADD CONSTRAINT search_term_performance_campaign_id_fkey 
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE search_term_performance DROP CONSTRAINT IF EXISTS search_term_performance_ad_group_id_fkey;
ALTER TABLE search_term_performance ADD CONSTRAINT search_term_performance_ad_group_id_fkey 
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE;

ALTER TABLE search_term_performance DROP CONSTRAINT IF EXISTS search_term_performance_keyword_id_fkey;
ALTER TABLE search_term_performance ADD CONSTRAINT search_term_performance_keyword_id_fkey 
    FOREIGN KEY (keyword_id) REFERENCES keywords(keyword_id) ON DELETE SET NULL;

ALTER TABLE alert_history DROP CONSTRAINT IF EXISTS alert_history_alert_config_id_fkey;
ALTER TABLE alert_history ADD CONSTRAINT alert_history_alert_config_id_fkey 
    FOREIGN KEY (alert_config_id) REFERENCES alert_configurations(id);

ALTER TABLE product_targets DROP CONSTRAINT IF EXISTS product_targets_campaign_id_fkey;
ALTER TABLE product_targets ADD CONSTRAINT product_targets_campaign_id_fkey 
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE product_targets DROP CONSTRAINT IF EXISTS product_targets_ad_group_id_fkey;
ALTER TABLE product_targets ADD CONSTRAINT product_targets_ad_group_id_fkey 
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE;

ALTER TABLE product_target_performance DROP CONSTRAINT IF EXISTS product_target_performance_target_id_fkey;
ALTER TABLE product_target_performance ADD CONSTRAINT product_target_performance_target_id_fkey 
    FOREIGN KEY (target_id) REFERENCES product_targets(target_id) ON DELETE CASCADE;

ALTER TABLE product_target_performance DROP CONSTRAINT IF EXISTS product_target_performance_campaign_id_fkey;
ALTER TABLE product_target_performance ADD CONSTRAINT product_target_performance_campaign_id_fkey 
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE product_target_performance DROP CONSTRAINT IF EXISTS product_target_performance_ad_group_id_fkey;
ALTER TABLE product_target_performance ADD CONSTRAINT product_target_performance_ad_group_id_fkey 
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE;

ALTER TABLE user_account_mappings DROP CONSTRAINT IF EXISTS user_account_mappings_account_id_fkey;
ALTER TABLE user_account_mappings ADD CONSTRAINT user_account_mappings_account_id_fkey 
    FOREIGN KEY (account_id) REFERENCES amazon_accounts(account_id) ON DELETE CASCADE;

-- ============================================================================
-- INDEXES (selected important indexes)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_sync_logs_type ON sync_logs(sync_type);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON sync_logs(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_campaign_id ON campaigns(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(campaign_status);
CREATE INDEX IF NOT EXISTS idx_ad_groups_campaign_id ON ad_groups(campaign_id);
CREATE INDEX IF NOT EXISTS idx_ad_groups_ad_group_id ON ad_groups(ad_group_id);
CREATE INDEX IF NOT EXISTS idx_keywords_campaign_id ON keywords(campaign_id);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword_id ON keywords(keyword_id);
CREATE INDEX IF NOT EXISTS idx_campaign_perf_date ON campaign_performance(report_date);
CREATE INDEX IF NOT EXISTS idx_ad_group_perf_ad_group_id ON ad_group_performance(ad_group_id);
CREATE INDEX IF NOT EXISTS idx_keyword_perf_keyword_id ON keyword_performance(keyword_id);
CREATE INDEX IF NOT EXISTS idx_product_ads_asin ON product_ads(asin);
CREATE INDEX IF NOT EXISTS idx_ai_rule_logs_date ON ai_rule_execution_logs(execution_date);
CREATE INDEX IF NOT EXISTS idx_ai_config_overrides_entity ON ai_rule_config_overrides(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_tracking_entity ON recommendation_tracking(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_waste_patterns_severity ON waste_patterns(severity);
CREATE INDEX IF NOT EXISTS idx_dashboard_user_prefs ON dashboard_user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_strategy_config_entity ON strategy_configurations(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_triggered ON alert_history(triggered_at);
CREATE INDEX IF NOT EXISTS idx_inventory_health_asin ON inventory_health(asin);
CREATE INDEX IF NOT EXISTS idx_asin_performance_date ON asin_performance(report_date);
CREATE INDEX IF NOT EXISTS idx_portfolios_portfolio_id ON portfolios(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_product_targets_target_type ON product_targets(target_type);
CREATE INDEX IF NOT EXISTS idx_amazon_accounts_account_id ON amazon_accounts(account_id);

-- ============================================================================
-- TRIGGERS: updated_at refreshers for tables that have updated_at column
-- (create or recreate the BEFORE UPDATE triggers)
-- ============================================================================

-- helper macro-style: list of tables to add triggers to
-- Note: If your DB has more tables with updated_at, add them here

DROP TRIGGER IF EXISTS update_campaigns_updated_at ON campaigns;
CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ad_groups_updated_at ON ad_groups;
CREATE TRIGGER update_ad_groups_updated_at BEFORE UPDATE ON ad_groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_keywords_updated_at ON keywords;
CREATE TRIGGER update_keywords_updated_at BEFORE UPDATE ON keywords
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_campaign_performance_updated_at ON campaign_performance;
CREATE TRIGGER update_campaign_performance_updated_at BEFORE UPDATE ON campaign_performance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ad_group_performance_updated_at ON ad_group_performance;
CREATE TRIGGER update_ad_group_performance_updated_at BEFORE UPDATE ON ad_group_performance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_keyword_performance_updated_at ON keyword_performance;
CREATE TRIGGER update_keyword_performance_updated_at BEFORE UPDATE ON keyword_performance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_product_ads_updated_at ON product_ads;
CREATE TRIGGER update_product_ads_updated_at BEFORE UPDATE ON product_ads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_negative_history_updated_at ON negative_keyword_history;
CREATE TRIGGER update_negative_history_updated_at BEFORE UPDATE ON negative_keyword_history
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ai_config_overrides_updated_at ON ai_rule_config_overrides;
CREATE TRIGGER update_ai_config_overrides_updated_at BEFORE UPDATE ON ai_rule_config_overrides
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_waste_patterns_updated_at ON waste_patterns;
CREATE TRIGGER update_waste_patterns_updated_at BEFORE UPDATE ON waste_patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_bid_constraints_updated_at ON bid_constraints;
CREATE TRIGGER update_bid_constraints_updated_at BEFORE UPDATE ON bid_constraints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_negative_keyword_candidates_updated_at ON negative_keyword_candidates;
CREATE TRIGGER update_negative_keyword_candidates_updated_at BEFORE UPDATE ON negative_keyword_candidates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_recommendation_tracking_updated_at ON recommendation_tracking;
CREATE TRIGGER update_recommendation_tracking_updated_at BEFORE UPDATE ON recommendation_tracking
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_learning_outcomes_updated_at ON learning_outcomes;
CREATE TRIGGER update_learning_outcomes_updated_at BEFORE UPDATE ON learning_outcomes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

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

-- TRIGGERS FOR V2 TABLES
DROP TRIGGER IF EXISTS update_portfolios_updated_at ON portfolios;
CREATE TRIGGER update_portfolios_updated_at BEFORE UPDATE ON portfolios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_product_targets_updated_at ON product_targets;
CREATE TRIGGER update_product_targets_updated_at BEFORE UPDATE ON product_targets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_product_target_performance_updated_at ON product_target_performance;
CREATE TRIGGER update_product_target_performance_updated_at BEFORE UPDATE ON product_target_performance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_placement_performance_updated_at ON placement_performance;
CREATE TRIGGER update_placement_performance_updated_at BEFORE UPDATE ON placement_performance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_asin_cogs_updated_at ON asin_cogs;
CREATE TRIGGER update_asin_cogs_updated_at BEFORE UPDATE ON asin_cogs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_column_layout_preferences_updated_at ON column_layout_preferences;
CREATE TRIGGER update_column_layout_preferences_updated_at BEFORE UPDATE ON column_layout_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_amazon_accounts_updated_at ON amazon_accounts;
CREATE TRIGGER update_amazon_accounts_updated_at BEFORE UPDATE ON amazon_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- DEFAULT DATA
-- ============================================================================

-- Insert default waste patterns (idempotent)
INSERT INTO waste_patterns (pattern_text, severity, description) VALUES
('\b(job|jobs|career|hiring|employment|recruiter)\b', 'critical', 'Job-related terms'),
('\b(porn|sex|adult|xxx)\b', 'critical', 'Adult content'),
('\b(illegal|scam|fake|counterfeit)\b', 'critical', 'Illegal/scam terms'),
('\b(repair|fix|broken|damaged)\b', 'high', 'Repair-related terms'),
('\b(used|refurbished|secondhand|pre-owned)\b', 'high', 'Used product terms'),
('\b(review|reviews|complaint|complaints|lawsuit)\b', 'high', 'Review/complaint terms'),
('\b(diy|how to|tutorial|instructions|guide)\b', 'medium', 'DIY/tutorial terms'),
('\b(free|freebie)\b', 'medium', 'Free product terms'),
('\b(for kids|for children|toy|toys)\b', 'medium', 'Children-related terms'),
('\b(cheap|cheapest|budget|affordable)\b', 'contextual', 'Budget/cheap terms'),
('\b(luxury|premium|expensive|high-end)\b', 'contextual', 'Luxury/premium terms'),
('\b(discount|sale|clearance|deal)\b', 'contextual', 'Discount/sale terms')
ON CONFLICT (pattern_text, severity) DO NOTHING;

-- Insert default strategy configuration for account-level
INSERT INTO strategy_configurations (entity_type, entity_id, strategy, target_acos, max_bid_cap, ai_mode)
VALUES ('account', NULL, 'growth', 0.09, 4.52, 'human_review')
ON CONFLICT (entity_type, entity_id) DO NOTHING;

COMMIT;

-- ============================================================================
-- Schema file creation complete
-- ============================================================================
