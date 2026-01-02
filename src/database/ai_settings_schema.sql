-- ============================================================================
-- AI RULE ENGINE SETTINGS & CONTROL TABLE
-- Stores AI control and configuration settings in database
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_rule_engine_settings (
    id SERIAL PRIMARY KEY,
    setting_name VARCHAR(100) UNIQUE NOT NULL,
    setting_value JSONB NOT NULL,
    value_type VARCHAR(50) NOT NULL, -- 'number', 'string', 'boolean', 'object', 'array'
    category VARCHAR(50) NOT NULL, -- 'acos', 'roas', 'ctr', 'bid', 'budget', 'learning', 'optimization', 'general'
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_ai_settings_name ON ai_rule_engine_settings(setting_name);
CREATE INDEX IF NOT EXISTS idx_ai_settings_category ON ai_rule_engine_settings(category);
CREATE INDEX IF NOT EXISTS idx_ai_settings_active ON ai_rule_engine_settings(is_active);

-- Trigger to update updated_at timestamp
DROP TRIGGER IF EXISTS update_ai_settings_updated_at ON ai_rule_engine_settings;
CREATE TRIGGER update_ai_settings_updated_at BEFORE UPDATE ON ai_rule_engine_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- AI CONTROL SETTINGS TABLE
-- Stores high-level AI control flags and operational settings
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_control_settings (
    id SERIAL PRIMARY KEY,
    control_key VARCHAR(100) UNIQUE NOT NULL,
    control_value BOOLEAN NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL, -- 'feature', 'operation', 'safety'
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_ai_control_key ON ai_control_settings(control_key);
CREATE INDEX IF NOT EXISTS idx_ai_control_category ON ai_control_settings(category);
CREATE INDEX IF NOT EXISTS idx_ai_control_active ON ai_control_settings(is_active);

-- Trigger to update updated_at timestamp
DROP TRIGGER IF EXISTS update_ai_control_updated_at ON ai_control_settings;
CREATE TRIGGER update_ai_control_updated_at BEFORE UPDATE ON ai_control_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- DEFAULT AI CONTROL SETTINGS
-- Initialize with default feature flags
-- ============================================================================

INSERT INTO ai_control_settings (control_key, control_value, description, category) VALUES
('enable_learning_loop', true, 'Enable machine learning feedback loop', 'feature'),
('enable_advanced_bid_optimization', true, 'Enable advanced bid optimization engine', 'feature'),
('enable_intelligence_engines', true, 'Enable intelligence engines (seasonality, profit, etc.)', 'feature'),
('enable_re_entry_control', true, 'Enable re-entry control to prevent oscillation', 'feature'),
('enable_oscillation_detection', true, 'Enable bid oscillation detection', 'safety'),
('enable_profit_optimization', true, 'Enable profit-based optimization', 'feature'),
('enable_telemetry', true, 'Enable telemetry and metrics collection', 'operation')
ON CONFLICT (control_key) DO NOTHING;

