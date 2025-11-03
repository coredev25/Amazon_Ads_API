-- Amazon Ads Database Schema

-- Table for storing campaigns
CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id BIGINT UNIQUE NOT NULL,
    campaign_name VARCHAR(255),
    campaign_status VARCHAR(50),
    targeting_type VARCHAR(50),
    start_date DATE,
    end_date DATE,
    budget_amount DECIMAL(10, 2),
    budget_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing ad groups
CREATE TABLE IF NOT EXISTS ad_groups (
    id SERIAL PRIMARY KEY,
    ad_group_id BIGINT UNIQUE NOT NULL,
    ad_group_name VARCHAR(255),
    campaign_id BIGINT NOT NULL,
    default_bid DECIMAL(10, 2),
    state VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE
);

-- Table for storing keywords
CREATE TABLE IF NOT EXISTS keywords (
    id SERIAL PRIMARY KEY,
    keyword_id BIGINT UNIQUE NOT NULL,
    keyword_text TEXT,
    match_type VARCHAR(50),
    campaign_id BIGINT NOT NULL,
    ad_group_id BIGINT NOT NULL,
    bid DECIMAL(10, 2),
    state VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE
);

-- Table for campaign performance data
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
    UNIQUE(campaign_id, report_date),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE
);

-- Table for ad group performance data
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
    UNIQUE(ad_group_id, report_date),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE
);

-- Table for keyword performance data
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
    UNIQUE(keyword_id, report_date),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES keywords(keyword_id) ON DELETE CASCADE
);

-- Table for sync logs
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

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_campaigns_campaign_id ON campaigns(campaign_id);
CREATE INDEX IF NOT EXISTS idx_ad_groups_campaign_id ON ad_groups(campaign_id);
CREATE INDEX IF NOT EXISTS idx_ad_groups_ad_group_id ON ad_groups(ad_group_id);
CREATE INDEX IF NOT EXISTS idx_keywords_campaign_id ON keywords(campaign_id);
CREATE INDEX IF NOT EXISTS idx_keywords_ad_group_id ON keywords(ad_group_id);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword_id ON keywords(keyword_id);
CREATE INDEX IF NOT EXISTS idx_campaign_perf_date ON campaign_performance(report_date);
CREATE INDEX IF NOT EXISTS idx_ad_group_perf_date ON ad_group_performance(report_date);
CREATE INDEX IF NOT EXISTS idx_keyword_perf_date ON keyword_performance(report_date);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables
CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ad_groups_updated_at BEFORE UPDATE ON ad_groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_keywords_updated_at BEFORE UPDATE ON keywords
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_campaign_performance_updated_at BEFORE UPDATE ON campaign_performance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ad_group_performance_updated_at BEFORE UPDATE ON ad_group_performance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_keyword_performance_updated_at BEFORE UPDATE ON keyword_performance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- AI RULE ENGINE TABLES
-- ============================================================================

-- Table for tracking bid changes (Re-entry Control System)
CREATE TABLE IF NOT EXISTS bid_change_history (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL, -- 'campaign', 'ad_group', 'keyword'
    entity_id BIGINT NOT NULL,
    entity_name VARCHAR(255),
    change_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    old_bid DECIMAL(10, 2) NOT NULL,
    new_bid DECIMAL(10, 2) NOT NULL,
    change_amount DECIMAL(10, 2) NOT NULL,
    change_percentage DECIMAL(10, 2) NOT NULL,
    reason TEXT,
    triggered_by VARCHAR(100), -- 'ai_rule_engine', 'manual', etc.
    acos_at_change DECIMAL(10, 4),
    roas_at_change DECIMAL(10, 4),
    ctr_at_change DECIMAL(10, 4),
    conversions_at_change INT,
    metadata JSONB, -- Additional context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for tracking ACOS trends over time
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

-- Table for bid adjustment locks (cooldown periods)
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

-- Table for detecting bid oscillation
CREATE TABLE IF NOT EXISTS bid_oscillation_detection (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    entity_name VARCHAR(255),
    direction_changes INT DEFAULT 0, -- Number of direction changes
    last_change_date TIMESTAMP,
    is_oscillating BOOLEAN DEFAULT FALSE,
    detection_window_days INT DEFAULT 14,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_id, entity_type)
);

-- Table for negative keyword candidates and history
CREATE TABLE IF NOT EXISTS negative_keyword_candidates (
    id SERIAL PRIMARY KEY,
    keyword_id BIGINT NOT NULL REFERENCES keywords(keyword_id) ON DELETE CASCADE,
    keyword_text TEXT NOT NULL,
    match_type VARCHAR(50),
    campaign_id BIGINT NOT NULL,
    ad_group_id BIGINT NOT NULL,
    identified_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    severity VARCHAR(50), -- 'low', 'medium', 'high', 'critical'
    confidence DECIMAL(5, 4), -- 0-1 confidence score
    reason TEXT,
    cost_at_identification DECIMAL(10, 2),
    impressions_at_identification BIGINT,
    clicks_at_identification BIGINT,
    conversions_at_identification INT,
    consecutive_failures INT,
    lookback_windows_analyzed INT,
    conversion_probability DECIMAL(5, 4),
    suggested_action VARCHAR(50), -- 'permanent_negative', 'temporary_hold', 'monitor'
    suggested_match_type VARCHAR(50), -- 'negative_exact', 'negative_phrase', 'negative_broad'
    is_temporary_hold BOOLEAN DEFAULT FALSE,
    hold_expiry_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'applied', 'rejected', 'expired'
    applied_date TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE
);

-- Table for negative keyword history and reactivation tracking
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
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'reactivated', 'permanently_blocked'
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE
);

-- Table for search term performance (for negative keyword analysis)
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
    UNIQUE(search_term, keyword_id, report_date),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    FOREIGN KEY (ad_group_id) REFERENCES ad_groups(ad_group_id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES keywords(keyword_id) ON DELETE SET NULL
);

-- Table for AI rule execution logs
CREATE TABLE IF NOT EXISTS ai_rule_execution_logs (
    id SERIAL PRIMARY KEY,
    execution_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    rule_type VARCHAR(100) NOT NULL, -- 'bid_optimization', 'negative_keywords', 'budget_adjustment'
    entity_type VARCHAR(50), -- 'campaign', 'ad_group', 'keyword'
    entity_id BIGINT,
    entity_name VARCHAR(255),
    action_taken VARCHAR(100),
    old_value DECIMAL(10, 2),
    new_value DECIMAL(10, 2),
    reason TEXT,
    metrics_at_execution JSONB, -- Store relevant metrics
    status VARCHAR(50) DEFAULT 'success', -- 'success', 'failed', 'skipped'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for AI rule engine configuration overrides
CREATE TABLE IF NOT EXISTS ai_rule_config_overrides (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50), -- 'campaign', 'ad_group', 'keyword', or NULL for global
    entity_id BIGINT, -- NULL for global config
    config_key VARCHAR(100) NOT NULL,
    config_value TEXT NOT NULL,
    value_type VARCHAR(50), -- 'string', 'number', 'boolean', 'json'
    reason TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(entity_type, entity_id, config_key)
);

-- Create indexes for AI rule engine tables
CREATE INDEX IF NOT EXISTS idx_bid_change_history_entity ON bid_change_history(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_bid_change_history_date ON bid_change_history(change_date);
CREATE INDEX IF NOT EXISTS idx_acos_trend_entity ON acos_trend_tracking(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_acos_trend_date ON acos_trend_tracking(check_date);
CREATE INDEX IF NOT EXISTS idx_bid_locks_entity ON bid_adjustment_locks(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_bid_locks_until ON bid_adjustment_locks(locked_until);
CREATE INDEX IF NOT EXISTS idx_bid_oscillation_entity ON bid_oscillation_detection(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_negative_candidates_keyword ON negative_keyword_candidates(keyword_id);
CREATE INDEX IF NOT EXISTS idx_negative_candidates_status ON negative_keyword_candidates(status);
CREATE INDEX IF NOT EXISTS idx_negative_history_keyword ON negative_keyword_history(keyword_id);
CREATE INDEX IF NOT EXISTS idx_negative_history_status ON negative_keyword_history(status);
CREATE INDEX IF NOT EXISTS idx_search_term_perf_date ON search_term_performance(report_date);
CREATE INDEX IF NOT EXISTS idx_search_term_perf_keyword ON search_term_performance(keyword_id);
CREATE INDEX IF NOT EXISTS idx_search_term_text ON search_term_performance(search_term);
CREATE INDEX IF NOT EXISTS idx_ai_rule_logs_date ON ai_rule_execution_logs(execution_date);
CREATE INDEX IF NOT EXISTS idx_ai_rule_logs_entity ON ai_rule_execution_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_ai_config_overrides_entity ON ai_rule_config_overrides(entity_type, entity_id);

-- Apply triggers to new tables
CREATE TRIGGER update_bid_oscillation_updated_at BEFORE UPDATE ON bid_oscillation_detection
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_negative_history_updated_at BEFORE UPDATE ON negative_keyword_history
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_search_term_performance_updated_at BEFORE UPDATE ON search_term_performance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_config_overrides_updated_at BEFORE UPDATE ON ai_rule_config_overrides
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

