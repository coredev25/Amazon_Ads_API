-- ============================================================================
-- DATABASE SCHEMA ADDITIONS FOR AMAZON PPC AI DASHBOARD v2.0
-- Run this after the main schema.sql to add new v2.0 features
-- ============================================================================

BEGIN;

-- ============================================================================
-- PORTFOLIOS & CAMPAIGN TYPES
-- ============================================================================

-- Table for Portfolios
CREATE TABLE IF NOT EXISTS portfolios (
    id SERIAL PRIMARY KEY,
    portfolio_id BIGINT UNIQUE NOT NULL,
    portfolio_name VARCHAR(255) NOT NULL,
    budget_amount DECIMAL(10, 2),
    budget_type VARCHAR(50), -- DAILY, LIFETIME
    state VARCHAR(50), -- ENABLED, PAUSED, ARCHIVED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add portfolio_id to campaigns table
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS portfolio_id BIGINT;
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS campaign_type VARCHAR(50) DEFAULT 'SP'; -- SP, SB, SD
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS sb_ad_type VARCHAR(50); -- PRODUCT_COLLECTION, STORE_SPOTLIGHT, VIDEO
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS sd_targeting_type VARCHAR(50); -- CONTEXTUAL, AUDIENCES

-- ============================================================================
-- PRODUCT TARGETING
-- ============================================================================

-- Table for Product Targeting (ASINs and Categories)
CREATE TABLE IF NOT EXISTS product_targets (
    id SERIAL PRIMARY KEY,
    target_id BIGINT UNIQUE NOT NULL,
    campaign_id BIGINT NOT NULL,
    ad_group_id BIGINT NOT NULL,
    target_type VARCHAR(50) NOT NULL, -- ASIN, CATEGORY
    target_value TEXT NOT NULL, -- ASIN or Category ID
    bid DECIMAL(10, 2),
    state VARCHAR(50), -- ENABLED, PAUSED, ARCHIVED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for product targeting performance
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

-- ============================================================================
-- PLACEMENTS
-- ============================================================================

-- Table for placement performance (Top of Search, Product Pages, etc.)
CREATE TABLE IF NOT EXISTS placement_performance (
    id SERIAL PRIMARY KEY,
    campaign_id BIGINT,
    ad_group_id BIGINT,
    keyword_id BIGINT,
    target_id BIGINT, -- for product targets
    placement VARCHAR(50) NOT NULL, -- TOP_OF_SEARCH, PRODUCT_PAGES, REST_OF_SEARCH
    report_date DATE NOT NULL,
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    cost DECIMAL(10, 2) DEFAULT 0,
    attributed_conversions_7d INT DEFAULT 0,
    attributed_sales_7d DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, ad_group_id, COALESCE(keyword_id, -1), COALESCE(target_id, -1), placement, report_date)
);

-- ============================================================================
-- FINANCIAL METRICS (COGS & PROFITABILITY)
-- ============================================================================

-- Table for COGS (Cost of Goods Sold) per ASIN
CREATE TABLE IF NOT EXISTS asin_cogs (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(20) NOT NULL UNIQUE,
    cogs DECIMAL(10, 2) NOT NULL,
    amazon_fees_percentage DECIMAL(5, 4) DEFAULT 0.15, -- Default 15% referral fee
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SEARCH TERMS (Customer Queries)
-- ============================================================================

-- Note: search_term_performance table already exists in main schema
-- We'll enhance it here if needed

-- ============================================================================
-- CHANGE HISTORY / AUDIT LOG
-- ============================================================================

-- Comprehensive change history table for all entity changes
CREATE TABLE IF NOT EXISTS change_history (
    id SERIAL PRIMARY KEY,
    change_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(100),
    entity_type VARCHAR(50) NOT NULL, -- portfolio, campaign, ad_group, ad, keyword, target
    entity_id BIGINT NOT NULL,
    entity_name VARCHAR(255),
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_type VARCHAR(50) NOT NULL, -- create, update, delete, status_change
    triggered_by VARCHAR(100), -- 'manual', 'ai_rule_engine', 'bulk_action', etc.
    reason TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- COLUMN LAYOUT PREFERENCES (Smart Grid)
-- ============================================================================

-- Table for user column layout preferences per view type
CREATE TABLE IF NOT EXISTS column_layout_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    view_type VARCHAR(50) NOT NULL, -- portfolios, campaigns, ad_groups, ads, keywords, targets, search_terms, placements
    column_visibility JSONB DEFAULT '{}', -- {column_key: true/false}
    column_order JSONB DEFAULT '[]', -- [column_key1, column_key2, ...]
    column_widths JSONB DEFAULT '{}', -- {column_key: width_px}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, view_type)
);

-- ============================================================================
-- MULTI-ACCOUNT SUPPORT
-- ============================================================================

-- Table for multiple Amazon Seller Accounts
CREATE TABLE IF NOT EXISTS amazon_accounts (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(100) UNIQUE NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    marketplace_id VARCHAR(50),
    region VARCHAR(50), -- US, EU, JP, etc.
    is_active BOOLEAN DEFAULT TRUE,
    profile_id BIGINT, -- Amazon Ads Profile ID
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link users to accounts (many-to-many relationship)
CREATE TABLE IF NOT EXISTS user_account_mappings (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    account_id VARCHAR(100) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, account_id)
);

-- Add account_id to relevant tables
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS account_id VARCHAR(100);
ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS account_id VARCHAR(100);

-- ============================================================================
-- ORGANIC RANK TRACKING
-- ============================================================================

-- Table for tracking organic rank positions for keywords
CREATE TABLE IF NOT EXISTS organic_rank_tracking (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(20) NOT NULL,
    keyword_text TEXT NOT NULL,
    rank_position INT,
    rank_date DATE NOT NULL,
    page_number INT,
    ad_rank_position INT, -- Ad rank for comparison
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asin, keyword_text, rank_date)
);

-- ============================================================================
-- FOREIGN KEYS
-- ============================================================================

-- Portfolio foreign keys
ALTER TABLE campaigns DROP CONSTRAINT IF EXISTS campaigns_portfolio_id_fkey;
ALTER TABLE campaigns ADD CONSTRAINT campaigns_portfolio_id_fkey 
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE SET NULL;

ALTER TABLE campaigns DROP CONSTRAINT IF EXISTS campaigns_account_id_fkey;
ALTER TABLE campaigns ADD CONSTRAINT campaigns_account_id_fkey 
    FOREIGN KEY (account_id) REFERENCES amazon_accounts(account_id) ON DELETE CASCADE;

ALTER TABLE portfolios DROP CONSTRAINT IF EXISTS portfolios_account_id_fkey;
ALTER TABLE portfolios ADD CONSTRAINT portfolios_account_id_fkey 
    FOREIGN KEY (account_id) REFERENCES amazon_accounts(account_id) ON DELETE CASCADE;

-- Product targeting foreign keys
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

-- User account mappings foreign key
ALTER TABLE user_account_mappings DROP CONSTRAINT IF EXISTS user_account_mappings_account_id_fkey;
ALTER TABLE user_account_mappings ADD CONSTRAINT user_account_mappings_account_id_fkey 
    FOREIGN KEY (account_id) REFERENCES amazon_accounts(account_id) ON DELETE CASCADE;

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_portfolios_portfolio_id ON portfolios(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_account_id ON portfolios(account_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_portfolio_id ON campaigns(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_campaign_type ON campaigns(campaign_type);
CREATE INDEX IF NOT EXISTS idx_campaigns_account_id ON campaigns(account_id);
CREATE INDEX IF NOT EXISTS idx_product_targets_campaign_id ON product_targets(campaign_id);
CREATE INDEX IF NOT EXISTS idx_product_targets_ad_group_id ON product_targets(ad_group_id);
CREATE INDEX IF NOT EXISTS idx_product_targets_target_type ON product_targets(target_type);
CREATE INDEX IF NOT EXISTS idx_product_target_perf_date ON product_target_performance(report_date);
CREATE INDEX IF NOT EXISTS idx_product_target_perf_target_id ON product_target_performance(target_id);
CREATE INDEX IF NOT EXISTS idx_placement_perf_date ON placement_performance(report_date);
CREATE INDEX IF NOT EXISTS idx_placement_perf_placement ON placement_performance(placement);
CREATE INDEX IF NOT EXISTS idx_asin_cogs_asin ON asin_cogs(asin);
CREATE INDEX IF NOT EXISTS idx_change_history_entity ON change_history(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_change_history_date ON change_history(change_date);
CREATE INDEX IF NOT EXISTS idx_change_history_user ON change_history(user_id);
CREATE INDEX IF NOT EXISTS idx_column_layout_user_view ON column_layout_preferences(user_id, view_type);
CREATE INDEX IF NOT EXISTS idx_amazon_accounts_account_id ON amazon_accounts(account_id);
CREATE INDEX IF NOT EXISTS idx_user_account_mappings_user ON user_account_mappings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_account_mappings_account ON user_account_mappings(account_id);
CREATE INDEX IF NOT EXISTS idx_organic_rank_asin_keyword ON organic_rank_tracking(asin, keyword_text);
CREATE INDEX IF NOT EXISTS idx_organic_rank_date ON organic_rank_tracking(rank_date);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

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

COMMIT;


