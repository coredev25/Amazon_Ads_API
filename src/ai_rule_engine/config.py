"""
Configuration module for AI Rule Engine
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import json


@dataclass
class RuleConfig:
    """Configuration for AI Rule Engine rules and limits"""
    
    # ACOS Rule Configuration
    acos_target: float = 0.09  # Target ACOS (9%)
    acos_tolerance: float = 0.05  # ±5% tolerance
    acos_bid_adjustment_factor: float = 0.1  # 10% bid adjustment per rule violation
    # ACOS Threshold Definitions (Granular Range-Specific Actions)
    acos_high_threshold: float = 0.40  # High ACOS threshold (40%+) - reduce bids aggressively
    acos_medium_high_threshold: float = 0.35  # Medium-high ACOS (35-40%) - reduce bids moderately
    acos_low_threshold: float = 0.25  # Low ACOS threshold (<25%) - can increase bids
    # Granular ACOS Tiers (stored as % of target ACOS; 1.0 == 100% of target)
    acos_tier_very_high: float = 2.0  # 200%+ of target (Critical)
    acos_tier_high: float = 1.35  # 135-200% of target (Severe Overspend lower bound)
    acos_tier_medium_high: float = 1.20  # 120-135% of target (Moderately High)
    acos_tier_medium: float = 1.19  # Upper bound for 100-119% of target (Slightly Above Target)
    acos_tier_target: float = 1.0  # Target ACOS (100% of target)
    acos_tier_good: float = 0.85  # 70-85% of target (Optimal upper band)
    acos_tier_low: float = 0.70  # 70% of target (Optimal lower band)
    acos_tier_very_low: float = 0.45  # 45% of target (Ultra Profitable upper band)
    acos_tier_excellent: float = 0.30  # 30% of target (Ultra Profitable floor)
    
    # ROAS Rule Configuration  
    roas_target: float = 11.11  # Target ROAS (11.11:1)
    roas_tolerance: float = 0.5  # ±0.5 tolerance
    roas_bid_adjustment_factor: float = 0.15  # 15% bid adjustment per rule violation
    
    # CTR Rule Configuration
    ctr_minimum: float = 0.5  # Minimum CTR (0.5%)
    ctr_target: float = 0.50  # Target CTR (0.50%)
    ctr_bid_adjustment_factor: float = 0.2  # 20% bid adjustment per rule violation
    
    # Bid Limits
    bid_floor: float = 0.02  # Minimum bid ($0.02)
    bid_cap: float = 4.52  # Maximum bid ($4.52)
    bid_max_adjustment: float = 0.5  # Maximum 50% adjustment per cycle
    
    # Budget Configuration
    budget_min_daily: float = 1.0  # Minimum daily budget ($1.00)
    budget_max_daily: float = 1000.0  # Maximum daily budget ($1000.00)
    budget_adjustment_factor: float = 0.2  # 20% budget adjustment per cycle
    
    # Performance Thresholds
    min_impressions: int = 100  # Minimum impressions for rule evaluation
    min_clicks: int = 5  # Minimum clicks for rule evaluation
    min_conversions: int = 1  # Minimum conversions for rule evaluation
    
    # Lookback Periods
    performance_lookback_days: int = 7  # Days to look back for performance data
    trend_analysis_days: int = 14  # Days for trend analysis
    # Bid Optimization Time Frames (14-day default per client requirements)
    bid_optimization_lookback_days: int = 14  # Primary lookback window for bid decisions (enforced 14 days)
    bid_optimization_short_window: int = 7  # Short-term window for trend analysis
    bid_optimization_medium_window: int = 14  # Medium-term window for trend analysis
    bid_optimization_long_window: int = 30  # Long-term window for trend analysis
    previous_period_lookback_days: int = 14  # Days to look back for previous period comparison
    
    # Negative Keyword Rules
    negative_keyword_ctr_threshold: float = 0.1  # CTR below 0.1% triggers negative keyword
    negative_keyword_impression_threshold: int = 1000  # Min 1000 impressions before considering negative
    
    # Safety Limits
    max_daily_adjustments: int = 3  # Maximum adjustments per day per entity
    cooldown_hours: int = 6  # Hours between adjustments for same entity
    
    # Re-entry Control & Oscillation Prevention (New)
    bid_change_cooldown_days: int = 3  # Days to wait before re-adjusting same entity (reduced from 7)
    min_bid_change_threshold: float = 0.05  # Minimum 5% change to trigger adjustment
    acos_stability_window: int = 1  # Number of check cycles to confirm stable trend (act immediately, not after 3 cycles)
    acos_hysteresis_lower: float = 0.25  # Lower bound for ACOS hysteresis (25% - tighter band)
    acos_hysteresis_upper: float = 0.35  # Upper bound for ACOS hysteresis (35% - tighter band)
    historical_smoothing_weight_recent: float = 0.7  # Weight for recent 7 days
    historical_smoothing_weight_older: float = 0.3  # Weight for older 7 days
    # Performance Smoothing Configuration
    enable_performance_smoothing: bool = True  # Enable smoothing for performance metrics
    smoothing_method: str = 'exponential'  # 'exponential', 'weighted_moving_average', 'simple_moving_average'
    exponential_smoothing_alpha: float = 0.3  # Alpha for exponential smoothing (0-1, lower = more smoothing)
    moving_average_window: int = 7  # Window size for moving averages
    min_data_points_for_smoothing: int = 3  # Minimum data points required for smoothing
    enable_re_entry_control: bool = True  # Enable re-entry control system
    enable_oscillation_detection: bool = True  # Enable bid oscillation detection
    oscillation_lookback_days: int = 14  # Days to look back for oscillation detection
    oscillation_direction_change_threshold: int = 3  # Min direction changes to flag oscillation
    
    # Intelligence Engine Configuration
    high_performer_roas: float = 5.0  # ROAS threshold for high performers
    long_tail_min_words: int = 3  # Minimum words for long-tail keywords
    target_impression_share: float = 0.5  # Target impression share
    
    # Seasonality Configuration
    seasonal_boost_factor: float = 1.5  # Seasonal boost multiplier
    
    # Profit Engine Configuration
    target_profit_margin: float = 0.30  # Target profit margin (30%)
    min_profit_threshold: float = 0.15  # Minimum acceptable profit margin (15%)
    
    # Negative Keyword Manager Configuration (Legacy - deprecated)
    negative_zero_conversion_threshold: int = 500  # Impressions before flagging zero conversions
    negative_high_cost_threshold: float = 50.0  # Cost threshold for zero-conversion keywords
    
    # Smart Negative Keyword Manager Configuration (New)
    negative_short_window_days: int = 7  # Short lookback window
    negative_medium_window_days: int = 14  # Medium lookback window  
    negative_long_window_days: int = 30  # Long lookback window
    negative_consecutive_failures: int = 3  # Consecutive zero-conversion windows required
    attribution_delay_days: int = 14  # Attribution delay consideration
    negative_min_cost_threshold: float = 100.0  # Minimum cost before marking negative
    negative_critical_cost_threshold: float = 200.0  # Critical cost threshold
    negative_min_impressions: int = 2000  # Minimum impressions (conservative)
    use_dynamic_thresholds: bool = True  # Use portfolio-based dynamic thresholds
    negative_percentile_threshold: int = 25  # Bottom percentile for CTR comparison
    use_temporary_holds: bool = True  # Use temporary holds instead of permanent negatives
    temporary_hold_days: int = 30  # Days for temporary holds
    negative_decision_cooldown_days: int = 14  # Cooldown between decisions
    enable_negative_re_evaluation: bool = True  # Enable forgiveness logic
    re_evaluation_interval_days: int = 60  # Days between re-evaluations
    min_conversion_probability: float = 0.2  # Minimum conversion probability threshold
    product_price_tier: str = 'mid'  # Product price tier: 'low', 'mid', 'premium'
    # Bid cap overrides (per product/category)
    product_bid_caps: Dict[str, float] = field(default_factory=dict)
    category_bid_caps: Dict[str, float] = field(default_factory=dict)
    
    # Bid Optimization Weights
    weight_performance: float = 0.40  # Weight for performance metrics
    weight_intelligence: float = 0.30  # Weight for intelligence signals
    weight_seasonality: float = 0.15  # Weight for seasonal factors
    weight_profit: float = 0.15  # Weight for profit optimization
    
    # Budget Optimization
    aggressive_scale_roas: float = 5.0  # ROAS threshold for aggressive budget scaling
    
    # Spend/Clicks Safeguard Configuration
    enable_spend_safeguard: bool = True  # Enable spend spike detection
    enable_clicks_safeguard: bool = True  # Enable clicks spike detection
    spend_spike_threshold: float = 2.0  # 200% increase triggers safeguard (2.0 = 200%)
    clicks_spike_threshold: float = 3.0  # 300% increase triggers safeguard (3.0 = 300%)
    spend_safeguard_lookback_days: int = 3  # Days to compare for spike detection
    safeguard_action: str = 'reduce_bid'  # 'reduce_bid', 'pause', 'alert' - action on spike detection
    safeguard_bid_reduction_factor: float = 0.5  # Reduce bid by 50% when safeguard triggers
    min_spend_for_safeguard: float = 10.0  # Minimum spend required to trigger safeguard ($10)
    min_clicks_for_safeguard: int = 10  # Minimum clicks required to trigger safeguard
    # Comprehensive Safety Veto Configuration (#19)
    enable_comprehensive_safety_veto: bool = True  # Enable comprehensive safety-first veto layer
    spend_spike_veto_threshold: float = 2.0  # 200% spend increase in last 3 days triggers veto
    spend_spike_veto_lookback_days: int = 3  # Days to check for spend spike
    spend_spike_veto_conversion_check: bool = True  # Check if conversions unchanged during spike
    account_daily_limit: float = 10000.0  # Maximum daily account spend limit ($10,000)
    account_daily_limit_action: str = 'pause'  # 'pause', 'reduce_bid', 'alert'
    account_daily_limit_reduction_factor: float = 0.5  # Reduce bids by 50% if limit exceeded
    
    # Order-Based Scaling Configuration
    enable_order_based_scaling: bool = True  # Enable conversion count tier logic
    order_tier_1: int = 1  # 1 conversion - minimal adjustment
    order_tier_2_3: int = 3  # 2-3 conversions - moderate adjustment
    order_tier_4_plus: int = 4  # 4+ conversions - aggressive scaling
    order_tier_1_adjustment: float = 0.05  # 5% max adjustment for 1 conversion
    order_tier_2_3_adjustment: float = 0.15  # 15% max adjustment for 2-3 conversions
    order_tier_4_plus_adjustment: float = 0.30  # 30% max adjustment for 4+ conversions
    
    # Spend-Based No Sale Logic (Tiered)
    enable_spend_no_sale_logic: bool = True  # Enable spend-tiered no-sale logic
    no_sale_spend_tier_1: float = 10.0  # $10-15 threshold
    no_sale_spend_tier_2: float = 15.0  # $16-30 threshold
    no_sale_spend_tier_3: float = 30.0  # >$30 threshold
    no_sale_reduction_tier_1: float = 0.15  # 15% bid reduction at $10-15
    no_sale_reduction_tier_2: float = 0.25  # 25% bid reduction at $16-30
    no_sale_reduction_tier_3: float = 0.35  # 35% bid reduction at >$30
    
    # CTR Combined Logic Configuration
    ctr_critical_threshold: float = 0.2  # CTR < 0.2% triggers combined logic
    enable_ctr_combined_logic: bool = True  # Enable CTR combined with spend/order logic
    ctr_low_spend_threshold: float = 10.0  # Spend threshold for CTR+Spend logic ($10)
    ctr_low_spend_reduction: float = 0.20  # -20% reduction for CTR <0.2% & Spend >$10
    ctr_low_order_threshold: int = 3  # Order threshold for CTR+Order logic
    # Impressions/Clicks Logic
    enable_impressions_clicks_logic: bool = True  # Enable impressions >500 & clicks <3 rule
    impressions_high_threshold: int = 500  # Impressions > 500
    clicks_low_threshold: int = 3  # Clicks < 3
    impressions_clicks_adjustment: float = 0.075  # +5-10% adjustment (using 7.5% average)
    
    # ACOS Trend Comparison (Previous vs Current 14 Days)
    enable_acos_trend_comparison: bool = True  # Compare current vs previous 14-day periods
    acos_trend_decline_threshold: float = 0.30  # 30% increase triggers -10% adjustment
    acos_trend_improvement_threshold: float = 0.30  # 30% decrease triggers +10% adjustment
    acos_trend_decline_adjustment: float = -0.10  # -10% when ACOS ↑ >30%
    acos_trend_improvement_adjustment: float = 0.10  # +10% when ACOS ↓ >30%
    skip_on_acos_decline: bool = False  # Don't skip, apply adjustment instead
    
    # Low Data Zone Configuration
    enable_low_data_zone: bool = True  # Enable low data zone handling
    low_data_spend_threshold: float = 5.0  # Spend < $5 = low data zone
    low_data_clicks_threshold: int = 10  # Clicks < 10 = low data zone
    low_data_zone_adjustment_limit: float = 0.0  # 0% adjustment in low data zone (hold)
    
    # New Keyword Logic (<14 days old)
    enable_new_keyword_logic: bool = True  # Enable special logic for new keywords
    new_keyword_age_days: int = 14  # Keywords <14 days old are considered "new"
    new_keyword_adjustment_limit: float = 0.15  # Max 15% adjustment for new keywords
    new_keyword_cooldown_days: int = 7  # Cooldown period for new keywords
    
    # Learning Loop Configuration
    learning_success_threshold: float = 0.10  # 10% improvement = success
    learning_failure_threshold: float = -0.05  # -5% decline = failure
    learning_evaluation_days: int = 7  # Days to evaluate outcomes
    min_training_samples: int = 100  # Minimum samples for ML training
    min_spend_for_label: float = 5.0  # Minimum spend to keep label
    min_clicks_for_label: int = 5  # Minimum clicks to keep label
    learning_policy_holdout_pct: float = 0.1  # 10% traffic in control/holdout
    enable_probability_calibration: bool = True  # Use calibrated probabilities for ML
    
    # Warm-Up Mode Configuration (Cold Start Fix)
    warm_up_mode_threshold: int = 100  # Skip AI prediction if training samples < this threshold
    enable_warm_up_mode: bool = True  # Enable warm-up mode to use math-based ACOS tiers when insufficient training data
    
    # Model Retraining Validation Thresholds (#16)
    min_test_auc_improvement: float = 0.02  # 2% improvement required
    min_test_accuracy_improvement: float = 0.01  # 1% improvement required
    min_test_auc: float = 0.60  # Minimum AUC to promote
    min_test_accuracy: float = 0.55  # Minimum accuracy to promote
    max_model_versions: int = 5  # Maximum model versions to keep for rollback
    
    # Hierarchical Model Configuration (#18)
    enable_hierarchical_models: bool = False  # Enable cross-ASIN transfer learning
    
    # Advanced Models Configuration (#26)
    # CRITICAL: LSTM models disabled due to time-series data gaps (missing days break sequence assumptions)
    # Stick to Random Forest/Gradient Boosting models which are robust to missing days
    enable_time_series_models: bool = False  # DISABLED: Enable LSTM/RNN time-series models
    time_series_sequence_length: int = 14  # Days of history for time-series input
    use_gpu: bool = False  # Use GPU for time-series models if available
    enable_causal_inference: bool = False  # Enable causal inference models
    
    # Multi-Armed Bandits Configuration (#27)
    enable_multi_armed_bandits: bool = False  # Enable MAB for exploration vs exploitation
    bandit_algorithm: str = 'thompson_sampling'  # 'thompson_sampling' or 'ucb'
    bandit_alpha_prior: float = 1.0  # Beta prior alpha for Thompson Sampling
    bandit_beta_prior: float = 1.0  # Beta prior beta for Thompson Sampling
    ucb_exploration_constant: float = 2.0  # Exploration constant for UCB
    enable_counterfactual_evaluation: bool = False  # Enable counterfactual evaluation
    
    # Portfolio Learning Configuration (#28)
    enable_portfolio_learning: bool = False  # Enable cross-account learning
    enable_differential_privacy: bool = True  # Enable differential privacy for portfolio data
    differential_privacy_epsilon: float = 1.0  # Privacy budget (epsilon)
    min_accounts_for_pooling: int = 3  # Minimum accounts required for pooling
    privacy_salt: str = 'default_salt_change_in_production'  # Salt for anonymization
    
    # Explainability Configuration (#29)
    enable_explainability: bool = False  # Enable SHAP-based explainability
    explainability_top_k_features: int = 5  # Number of top features to show in explanations
    
    # Simulator Configuration (#30)
    enable_simulator: bool = False  # Enable historical simulation sandbox
    simulation_lookback_days: int = 30  # Days to look back for simulation
    
    # Engine Feature Flags
    enable_intelligence_engines: bool = True
    enable_learning_loop: bool = True
    enable_advanced_bid_optimization: bool = True
    enable_profit_optimization: bool = True
    enable_telemetry: bool = True
    telemetry_exporter: str = 'prometheus'  # prometheus|statsd|noop
    
    @classmethod
    def from_file(cls, config_path: str) -> 'RuleConfig':
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return cls(**config_data)
        except FileNotFoundError:
            print(f"Config file {config_path} not found, using defaults")
            return cls()
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            return cls()
    
    def to_file(self, config_path: str) -> None:
        """Save configuration to JSON file"""
        config_dict = {
            'acos_target': self.acos_target,
            'acos_tolerance': self.acos_tolerance,
            'acos_bid_adjustment_factor': self.acos_bid_adjustment_factor,
            'acos_high_threshold': self.acos_high_threshold,
            'acos_medium_high_threshold': self.acos_medium_high_threshold,
            'acos_low_threshold': self.acos_low_threshold,
            'acos_tier_very_high': self.acos_tier_very_high,
            'acos_tier_high': self.acos_tier_high,
            'acos_tier_medium_high': self.acos_tier_medium_high,
            'acos_tier_medium': self.acos_tier_medium,
            'acos_tier_target': self.acos_tier_target,
            'acos_tier_good': self.acos_tier_good,
            'acos_tier_low': self.acos_tier_low,
            'acos_tier_very_low': self.acos_tier_very_low,
            'acos_tier_excellent': self.acos_tier_excellent,
            'roas_target': self.roas_target,
            'roas_tolerance': self.roas_tolerance,
            'roas_bid_adjustment_factor': self.roas_bid_adjustment_factor,
            'ctr_minimum': self.ctr_minimum,
            'ctr_target': self.ctr_target,
            'ctr_bid_adjustment_factor': self.ctr_bid_adjustment_factor,
            'bid_floor': self.bid_floor,
            'bid_cap': self.bid_cap,
            'bid_max_adjustment': self.bid_max_adjustment,
            'budget_min_daily': self.budget_min_daily,
            'budget_max_daily': self.budget_max_daily,
            'budget_adjustment_factor': self.budget_adjustment_factor,
            'min_impressions': self.min_impressions,
            'min_clicks': self.min_clicks,
            'min_conversions': self.min_conversions,
            'performance_lookback_days': self.performance_lookback_days,
            'trend_analysis_days': self.trend_analysis_days,
            'bid_optimization_lookback_days': self.bid_optimization_lookback_days,
            'bid_optimization_short_window': self.bid_optimization_short_window,
            'bid_optimization_medium_window': self.bid_optimization_medium_window,
            'bid_optimization_long_window': self.bid_optimization_long_window,
            'previous_period_lookback_days': self.previous_period_lookback_days,
            'negative_keyword_ctr_threshold': self.negative_keyword_ctr_threshold,
            'negative_keyword_impression_threshold': self.negative_keyword_impression_threshold,
            'max_daily_adjustments': self.max_daily_adjustments,
            'cooldown_hours': self.cooldown_hours,
            # Re-entry Control
            'bid_change_cooldown_days': self.bid_change_cooldown_days,
            'min_bid_change_threshold': self.min_bid_change_threshold,
            'acos_stability_window': self.acos_stability_window,
            'acos_hysteresis_lower': self.acos_hysteresis_lower,
            'acos_hysteresis_upper': self.acos_hysteresis_upper,
            'historical_smoothing_weight_recent': self.historical_smoothing_weight_recent,
            'historical_smoothing_weight_older': self.historical_smoothing_weight_older,
            'enable_performance_smoothing': self.enable_performance_smoothing,
            'smoothing_method': self.smoothing_method,
            'exponential_smoothing_alpha': self.exponential_smoothing_alpha,
            'moving_average_window': self.moving_average_window,
            'min_data_points_for_smoothing': self.min_data_points_for_smoothing,
            'enable_re_entry_control': self.enable_re_entry_control,
            'enable_oscillation_detection': self.enable_oscillation_detection,
            'oscillation_lookback_days': self.oscillation_lookback_days,
            'oscillation_direction_change_threshold': self.oscillation_direction_change_threshold,
            # Intelligence Engines
            'high_performer_roas': self.high_performer_roas,
            'long_tail_min_words': self.long_tail_min_words,
            'target_impression_share': self.target_impression_share,
            'seasonal_boost_factor': self.seasonal_boost_factor,
            'target_profit_margin': self.target_profit_margin,
            'min_profit_threshold': self.min_profit_threshold,
            'negative_zero_conversion_threshold': self.negative_zero_conversion_threshold,
            'negative_high_cost_threshold': self.negative_high_cost_threshold,
            # Smart Negative Keyword Manager
            'negative_short_window_days': self.negative_short_window_days,
            'negative_medium_window_days': self.negative_medium_window_days,
            'negative_long_window_days': self.negative_long_window_days,
            'negative_consecutive_failures': self.negative_consecutive_failures,
            'attribution_delay_days': self.attribution_delay_days,
            'negative_min_cost_threshold': self.negative_min_cost_threshold,
            'negative_critical_cost_threshold': self.negative_critical_cost_threshold,
            'negative_min_impressions': self.negative_min_impressions,
            'use_dynamic_thresholds': self.use_dynamic_thresholds,
            'negative_percentile_threshold': self.negative_percentile_threshold,
            'use_temporary_holds': self.use_temporary_holds,
            'temporary_hold_days': self.temporary_hold_days,
            'negative_decision_cooldown_days': self.negative_decision_cooldown_days,
            'enable_negative_re_evaluation': self.enable_negative_re_evaluation,
            're_evaluation_interval_days': self.re_evaluation_interval_days,
            'min_conversion_probability': self.min_conversion_probability,
            'product_price_tier': self.product_price_tier,
            # Bid Optimization
            'weight_performance': self.weight_performance,
            'weight_intelligence': self.weight_intelligence,
            'weight_seasonality': self.weight_seasonality,
            'weight_profit': self.weight_profit,
            'aggressive_scale_roas': self.aggressive_scale_roas,
            # Spend/Clicks Safeguard
            'enable_spend_safeguard': self.enable_spend_safeguard,
            'enable_clicks_safeguard': self.enable_clicks_safeguard,
            'spend_spike_threshold': self.spend_spike_threshold,
            'clicks_spike_threshold': self.clicks_spike_threshold,
            'spend_safeguard_lookback_days': self.spend_safeguard_lookback_days,
            'safeguard_action': self.safeguard_action,
            'safeguard_bid_reduction_factor': self.safeguard_bid_reduction_factor,
            'min_spend_for_safeguard': self.min_spend_for_safeguard,
            'min_clicks_for_safeguard': self.min_clicks_for_safeguard,
            # Order-Based Scaling
            'enable_order_based_scaling': self.enable_order_based_scaling,
            'order_tier_1': self.order_tier_1,
            'order_tier_2_3': self.order_tier_2_3,
            'order_tier_4_plus': self.order_tier_4_plus,
            'order_tier_1_adjustment': self.order_tier_1_adjustment,
            'order_tier_2_3_adjustment': self.order_tier_2_3_adjustment,
            'order_tier_4_plus_adjustment': self.order_tier_4_plus_adjustment,
            # Spend-Based No Sale Logic
            'enable_spend_no_sale_logic': self.enable_spend_no_sale_logic,
            'no_sale_spend_tier_1': self.no_sale_spend_tier_1,
            'no_sale_spend_tier_2': self.no_sale_spend_tier_2,
            'no_sale_spend_tier_3': self.no_sale_spend_tier_3,
            'no_sale_reduction_tier_1': self.no_sale_reduction_tier_1,
            'no_sale_reduction_tier_2': self.no_sale_reduction_tier_2,
            'no_sale_reduction_tier_3': self.no_sale_reduction_tier_3,
            # CTR Combined Logic
            'ctr_critical_threshold': self.ctr_critical_threshold,
            'enable_ctr_combined_logic': self.enable_ctr_combined_logic,
            'ctr_low_spend_threshold': self.ctr_low_spend_threshold,
            'ctr_low_spend_reduction': self.ctr_low_spend_reduction,
            'ctr_low_order_threshold': self.ctr_low_order_threshold,
            'enable_impressions_clicks_logic': self.enable_impressions_clicks_logic,
            'impressions_high_threshold': self.impressions_high_threshold,
            'clicks_low_threshold': self.clicks_low_threshold,
            'impressions_clicks_adjustment': self.impressions_clicks_adjustment,
            # ACOS Trend Comparison
            'enable_acos_trend_comparison': self.enable_acos_trend_comparison,
            'acos_trend_decline_threshold': self.acos_trend_decline_threshold,
            'acos_trend_improvement_threshold': self.acos_trend_improvement_threshold,
            'acos_trend_decline_adjustment': self.acos_trend_decline_adjustment,
            'acos_trend_improvement_adjustment': self.acos_trend_improvement_adjustment,
            'skip_on_acos_decline': self.skip_on_acos_decline,
            # Low Data Zone
            'enable_low_data_zone': self.enable_low_data_zone,
            'low_data_spend_threshold': self.low_data_spend_threshold,
            'low_data_clicks_threshold': self.low_data_clicks_threshold,
            'low_data_zone_adjustment_limit': self.low_data_zone_adjustment_limit,
            # New Keyword Logic
            'enable_new_keyword_logic': self.enable_new_keyword_logic,
            'new_keyword_age_days': self.new_keyword_age_days,
            'new_keyword_adjustment_limit': self.new_keyword_adjustment_limit,
            'new_keyword_cooldown_days': self.new_keyword_cooldown_days,
            # Learning Loop
            'learning_success_threshold': self.learning_success_threshold,
            'learning_failure_threshold': self.learning_failure_threshold,
            'learning_evaluation_days': self.learning_evaluation_days,
            'min_training_samples': self.min_training_samples,
            'warm_up_mode_threshold': self.warm_up_mode_threshold,
            'enable_warm_up_mode': self.enable_warm_up_mode,
            # Feature Flags
            'enable_intelligence_engines': self.enable_intelligence_engines,
            'enable_learning_loop': self.enable_learning_loop,
            'enable_advanced_bid_optimization': self.enable_advanced_bid_optimization,
            'enable_profit_optimization': self.enable_profit_optimization
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def validate(self) -> bool:
        """Validate configuration values"""
        errors = []
        
        # Basic metric targets
        if self.acos_target <= 0 or self.acos_target > 1:
            errors.append("ACOS target must be between 0 and 1")
        
        if self.roas_target <= 0:
            errors.append("ROAS target must be positive")
        
        if self.ctr_minimum < 0 or self.ctr_target < 0:
            errors.append("CTR values must be non-negative")
        
        # Bid limits
        if self.bid_floor <= 0 or self.bid_cap <= 0 or self.bid_floor >= self.bid_cap:
            errors.append("Bid floor must be positive and less than bid cap")
        
        if self.bid_max_adjustment <= 0 or self.bid_max_adjustment > 1:
            errors.append("Bid max adjustment must be between 0 and 1")
        
        # Budget limits
        if self.budget_min_daily <= 0 or self.budget_max_daily <= 0 or self.budget_min_daily >= self.budget_max_daily:
            errors.append("Budget min must be positive and less than budget max")
        
        # Performance thresholds
        if self.min_impressions < 0:
            errors.append("Minimum impressions must be non-negative")
        
        if self.min_clicks < 0:
            errors.append("Minimum clicks must be non-negative")
        
        if self.min_conversions < 0:
            errors.append("Minimum conversions must be non-negative")
        
        # Lookback periods
        if self.performance_lookback_days < 1:
            errors.append("Performance lookback days must be at least 1")
        
        if self.bid_optimization_lookback_days < 1:
            errors.append("Bid optimization lookback days must be at least 1")
        
        if self.trend_analysis_days < 1:
            errors.append("Trend analysis days must be at least 1")
        
        # Re-entry control parameters
        if self.bid_change_cooldown_days < 0:
            errors.append("Bid change cooldown days must be non-negative")
        
        if self.min_bid_change_threshold < 0 or self.min_bid_change_threshold > 1:
            errors.append("Min bid change threshold must be between 0 and 1")
        
        if self.acos_hysteresis_lower < 0 or self.acos_hysteresis_upper < 0:
            errors.append("ACOS hysteresis values must be non-negative")
        
        if self.acos_hysteresis_lower >= self.acos_hysteresis_upper:
            errors.append("ACOS hysteresis lower must be less than upper")
        
        # Negative keyword thresholds
        if self.negative_keyword_ctr_threshold < 0:
            errors.append("Negative keyword CTR threshold must be non-negative")
        
        if self.negative_keyword_impression_threshold < 0:
            errors.append("Negative keyword impression threshold must be non-negative")
        
        if self.negative_min_cost_threshold < 0:
            errors.append("Negative min cost threshold must be non-negative")
        
        # Learning loop parameters
        if self.min_training_samples < 1:
            errors.append("Min training samples must be at least 1")
        
        if self.learning_evaluation_days < 1:
            errors.append("Learning evaluation days must be at least 1")
        
        if self.warm_up_mode_threshold < 0:
            errors.append("Warm-up mode threshold must be non-negative")
        
        # Safety limits
        if self.max_daily_adjustments < 0:
            errors.append("Max daily adjustments must be non-negative")
        
        if self.cooldown_hours < 0:
            errors.append("Cooldown hours must be non-negative")
        
        # Safety veto parameters
        if self.spend_spike_veto_threshold < 1:
            errors.append("Spend spike veto threshold must be >= 1 (100%)")
        
        if self.spend_spike_veto_lookback_days < 1:
            errors.append("Spend spike veto lookback days must be at least 1")
        
        if self.account_daily_limit <= 0:
            errors.append("Account daily limit must be positive")
        
        # Bid optimization weights
        weight_sum = (self.weight_performance + self.weight_intelligence + 
                     self.weight_seasonality + self.weight_profit)
        if abs(weight_sum - 1.0) > 0.01:  # Allow small floating point errors
            errors.append(f"Bid optimization weights must sum to 1.0 (currently {weight_sum:.2f})")
        
        # Order-based scaling
        if self.enable_order_based_scaling:
            if self.order_tier_1 < 1:
                errors.append("Order tier 1 must be at least 1")
            if self.order_tier_2_3 < self.order_tier_1:
                errors.append("Order tier 2-3 must be >= order tier 1")
            if self.order_tier_4_plus < self.order_tier_2_3:
                errors.append("Order tier 4+ must be >= order tier 2-3")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        return True
