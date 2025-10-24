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
    
    # Intelligence Engine Configuration
    high_performer_roas: float = 5.0  # ROAS threshold for high performers
    long_tail_min_words: int = 3  # Minimum words for long-tail keywords
    target_impression_share: float = 0.5  # Target impression share
    
    # Seasonality Configuration
    seasonal_boost_factor: float = 1.5  # Seasonal boost multiplier
    
    # Profit Engine Configuration
    target_profit_margin: float = 0.30  # Target profit margin (30%)
    min_profit_threshold: float = 0.15  # Minimum acceptable profit margin (15%)
    
    # Negative Keyword Manager Configuration
    negative_zero_conversion_threshold: int = 500  # Impressions before flagging zero conversions
    negative_high_cost_threshold: float = 50.0  # Cost threshold for zero-conversion keywords
    
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
            # Intelligence Engines
            'high_performer_roas': self.high_performer_roas,
            'long_tail_min_words': self.long_tail_min_words,
            'target_impression_share': self.target_impression_share,
            'seasonal_boost_factor': self.seasonal_boost_factor,
            'target_profit_margin': self.target_profit_margin,
            'min_profit_threshold': self.min_profit_threshold,
            'negative_zero_conversion_threshold': self.negative_zero_conversion_threshold,
            'negative_high_cost_threshold': self.negative_high_cost_threshold,
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
