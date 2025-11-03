"""
Configuration module for AI Rule Engine
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Optional
import json


@dataclass
class RuleConfig:
    """Configuration for AI Rule Engine rules and limits"""
    
    # ACOS Rule Configuration
    acos_target: float = 0.30  # Target ACOS (30%)
    acos_tolerance: float = 0.05  # ±5% tolerance
    acos_bid_adjustment_factor: float = 0.1  # 10% bid adjustment per rule violation
    
    # ROAS Rule Configuration  
    roas_target: float = 4.0  # Target ROAS (4:1)
    roas_tolerance: float = 0.5  # ±0.5 tolerance
    roas_bid_adjustment_factor: float = 0.15  # 15% bid adjustment per rule violation
    
    # CTR Rule Configuration
    ctr_minimum: float = 0.5  # Minimum CTR (0.5%)
    ctr_target: float = 2.0  # Target CTR (2.0%)
    ctr_bid_adjustment_factor: float = 0.2  # 20% bid adjustment per rule violation
    
    # Bid Limits
    bid_floor: float = 0.01  # Minimum bid ($0.01)
    bid_cap: float = 10.0  # Maximum bid ($10.00)
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
    
    # Bid Optimization Weights
    weight_performance: float = 0.40  # Weight for performance metrics
    weight_intelligence: float = 0.30  # Weight for intelligence signals
    weight_seasonality: float = 0.15  # Weight for seasonal factors
    weight_profit: float = 0.15  # Weight for profit optimization
    
    # Budget Optimization
    aggressive_scale_roas: float = 5.0  # ROAS threshold for aggressive budget scaling
    
    # Learning Loop Configuration
    learning_success_threshold: float = 0.10  # 10% improvement = success
    learning_failure_threshold: float = -0.05  # -5% decline = failure
    learning_evaluation_days: int = 7  # Days to evaluate outcomes
    min_training_samples: int = 100  # Minimum samples for ML training
    
    # Engine Feature Flags
    enable_intelligence_engines: bool = True
    enable_learning_loop: bool = True
    enable_advanced_bid_optimization: bool = True
    enable_profit_optimization: bool = True
    
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
            # Learning Loop
            'learning_success_threshold': self.learning_success_threshold,
            'learning_failure_threshold': self.learning_failure_threshold,
            'learning_evaluation_days': self.learning_evaluation_days,
            'min_training_samples': self.min_training_samples,
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
        
        if self.acos_target <= 0 or self.acos_target > 1:
            errors.append("ACOS target must be between 0 and 1")
        
        if self.roas_target <= 0:
            errors.append("ROAS target must be positive")
        
        if self.ctr_minimum < 0 or self.ctr_target < 0:
            errors.append("CTR values must be non-negative")
        
        if self.bid_floor <= 0 or self.bid_cap <= 0 or self.bid_floor >= self.bid_cap:
            errors.append("Bid floor must be positive and less than bid cap")
        
        if self.budget_min_daily <= 0 or self.budget_max_daily <= 0 or self.budget_min_daily >= self.budget_max_daily:
            errors.append("Budget min must be positive and less than budget max")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        return True
