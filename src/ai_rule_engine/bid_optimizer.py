"""
Bid Optimization Engine
Integrates all intelligence engines for intelligent bid adjustments
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from .re_entry_control import ReEntryController, BidChangeTracker


@dataclass
class BidOptimization:
    """Bid optimization recommendation"""
    entity_id: int
    entity_type: str
    entity_name: str
    current_bid: float
    recommended_bid: float
    adjustment_amount: float
    adjustment_percentage: float
    reason: str
    contributing_factors: List[str]
    confidence: float
    priority: str
    metadata: Dict[str, Any]


class BidOptimizationEngine:
    """
    Advanced bid optimization combining multiple intelligence signals
    """
    
    def __init__(self, config: Dict[str, Any], db_connector=None, model_trainer=None, learning_loop=None):
        self.config = config
        self.db = db_connector
        self.model_trainer = model_trainer  # For STEP 5: Predictive gating
        self.learning_loop = learning_loop  # For STEP 7: Campaign adaptivity
        self.logger = logging.getLogger(__name__)
        
        # Bid limits
        self.bid_floor = config.get('bid_floor', 0.02)
        self.bid_cap = config.get('bid_cap', 4.52)
        self.max_adjustment = config.get('bid_max_adjustment', 0.5)
        
        # Target metrics
        self.target_acos = config.get('acos_target', 0.09)
        self.target_roas = config.get('roas_target', 11.11)
        self.target_ctr = config.get('ctr_target', 0.50)
        
        # ACOS Threshold Definitions
        self.acos_high_threshold = config.get('acos_high_threshold', 0.40)
        self.acos_medium_high_threshold = config.get('acos_medium_high_threshold', 0.35)
        self.acos_low_threshold = config.get('acos_low_threshold', 0.25)
        
        # Granular ACOS Tiers (discrete tier logic)
        self.acos_tier_very_high = config.get('acos_tier_very_high', 0.50)
        self.acos_tier_high = config.get('acos_tier_high', 0.40)
        self.acos_tier_medium_high = config.get('acos_tier_medium_high', 0.35)
        self.acos_tier_medium = config.get('acos_tier_medium', 0.30)
        self.acos_tier_target = config.get('acos_tier_target', 0.09)
        self.acos_tier_good = config.get('acos_tier_good', 0.25)
        self.acos_tier_low = config.get('acos_tier_low', 0.20)
        self.acos_tier_very_low = config.get('acos_tier_very_low', 0.15)
        self.acos_tier_excellent = config.get('acos_tier_excellent', 0.10)
        
        # Time frame configuration (14-day default per client requirements)
        self.bid_optimization_lookback_days = config.get('bid_optimization_lookback_days', 14)
        self.bid_optimization_short_window = config.get('bid_optimization_short_window', 7)
        self.bid_optimization_medium_window = config.get('bid_optimization_medium_window', 14)
        self.bid_optimization_long_window = config.get('bid_optimization_long_window', 30)
        self.previous_period_lookback_days = config.get('previous_period_lookback_days', 14)
        
        # Smoothing configuration
        self.enable_performance_smoothing = config.get('enable_performance_smoothing', True)
        self.smoothing_method = config.get('smoothing_method', 'exponential')
        self.exponential_smoothing_alpha = config.get('exponential_smoothing_alpha', 0.3)
        self.moving_average_window = config.get('moving_average_window', 7)
        self.min_data_points_for_smoothing = config.get('min_data_points_for_smoothing', 3)
        
        # Spend/Clicks Safeguard configuration
        self.enable_spend_safeguard = config.get('enable_spend_safeguard', True)
        self.enable_clicks_safeguard = config.get('enable_clicks_safeguard', True)
        self.spend_spike_threshold = config.get('spend_spike_threshold', 2.0)  # 200% increase
        self.clicks_spike_threshold = config.get('clicks_spike_threshold', 3.0)  # 300% increase
        self.spend_safeguard_lookback_days = config.get('spend_safeguard_lookback_days', 3)
        self.safeguard_action = config.get('safeguard_action', 'reduce_bid')
        self.safeguard_bid_reduction_factor = config.get('safeguard_bid_reduction_factor', 0.5)
        self.min_spend_for_safeguard = config.get('min_spend_for_safeguard', 10.0)
        self.min_clicks_for_safeguard = config.get('min_clicks_for_safeguard', 10)
        
        # Order-Based Scaling Configuration
        self.enable_order_based_scaling = config.get('enable_order_based_scaling', True)
        self.order_tier_1 = config.get('order_tier_1', 1)
        self.order_tier_2_3 = config.get('order_tier_2_3', 3)
        self.order_tier_4_plus = config.get('order_tier_4_plus', 4)
        self.order_tier_1_adjustment = config.get('order_tier_1_adjustment', 0.05)
        self.order_tier_2_3_adjustment = config.get('order_tier_2_3_adjustment', 0.15)
        self.order_tier_4_plus_adjustment = config.get('order_tier_4_plus_adjustment', 0.30)
        
        # Spend-Based No Sale Logic (Tiered)
        self.enable_spend_no_sale_logic = config.get('enable_spend_no_sale_logic', True)
        self.no_sale_spend_tier_1 = config.get('no_sale_spend_tier_1', 10.0)
        self.no_sale_spend_tier_2 = config.get('no_sale_spend_tier_2', 15.0)
        self.no_sale_spend_tier_3 = config.get('no_sale_spend_tier_3', 30.0)
        self.no_sale_reduction_tier_1 = config.get('no_sale_reduction_tier_1', 0.15)
        self.no_sale_reduction_tier_2 = config.get('no_sale_reduction_tier_2', 0.25)
        self.no_sale_reduction_tier_3 = config.get('no_sale_reduction_tier_3', 0.35)
        
        # CTR Combined Logic Configuration
        # Note: CTR values are in percentage format (e.g., 0.2 = 0.2%, 2.0 = 2.0%)
        # current_ctr is calculated as (clicks/impressions * 100), so both are comparable
        self.ctr_critical_threshold = config.get('ctr_critical_threshold', 0.2)  # 0.2% in percentage format
        self.enable_ctr_combined_logic = config.get('enable_ctr_combined_logic', True)
        self.ctr_low_spend_threshold = config.get('ctr_low_spend_threshold', 10.0)
        self.ctr_low_spend_reduction = config.get('ctr_low_spend_reduction', 0.20)
        self.ctr_low_order_threshold = config.get('ctr_low_order_threshold', 3)
        
        # Impressions/Clicks Logic
        self.enable_impressions_clicks_logic = config.get('enable_impressions_clicks_logic', True)
        self.impressions_high_threshold = config.get('impressions_high_threshold', 500)
        self.clicks_low_threshold = config.get('clicks_low_threshold', 3)
        self.impressions_clicks_adjustment = config.get('impressions_clicks_adjustment', 0.075)
        
        # ACOS Trend Comparison
        self.enable_acos_trend_comparison = config.get('enable_acos_trend_comparison', True)
        self.acos_trend_decline_threshold = config.get('acos_trend_decline_threshold', 0.30)
        self.acos_trend_improvement_threshold = config.get('acos_trend_improvement_threshold', 0.30)
        self.acos_trend_decline_adjustment = config.get('acos_trend_decline_adjustment', -0.10)
        self.acos_trend_improvement_adjustment = config.get('acos_trend_improvement_adjustment', 0.10)
        self.skip_on_acos_decline = config.get('skip_on_acos_decline', False)
        
        # Low Data Zone Configuration
        self.enable_low_data_zone = config.get('enable_low_data_zone', True)
        self.low_data_spend_threshold = config.get('low_data_spend_threshold', 5.0)
        self.low_data_clicks_threshold = config.get('low_data_clicks_threshold', 10)
        self.low_data_zone_adjustment_limit = config.get('low_data_zone_adjustment_limit', 0.0)
        
        # New Keyword Logic
        self.enable_new_keyword_logic = config.get('enable_new_keyword_logic', True)
        self.new_keyword_age_days = config.get('new_keyword_age_days', 14)
        self.new_keyword_adjustment_limit = config.get('new_keyword_adjustment_limit', 0.15)
        self.new_keyword_cooldown_days = config.get('new_keyword_cooldown_days', 7)
        
        # Adjustment weights for different factors
        self.weights = {
            'performance': config.get('weight_performance', 0.40),
            'intelligence': config.get('weight_intelligence', 0.30),
            'seasonality': config.get('weight_seasonality', 0.15),
            'profit': config.get('weight_profit', 0.15)
        }
        
        # Initialize re-entry control
        self.enable_re_entry_control = config.get('enable_re_entry_control', True)
        if self.enable_re_entry_control:
            self.re_entry_controller = ReEntryController(config)
            self.bid_change_tracker = BidChangeTracker(self.logger)
            self.logger.info("Re-entry control enabled for bid optimizer")
        else:
            self.re_entry_controller = None
            self.bid_change_tracker = None
        
        # STEP 7: Campaign adaptivity configuration
        self.enable_campaign_adaptivity = config.get('enable_campaign_adaptivity', True)
        self.campaign_success_threshold_high = config.get('campaign_success_threshold_high', 0.70)  # >70% = increase aggressiveness
        self.campaign_success_threshold_low = config.get('campaign_success_threshold_low', 0.40)  # <40% = reduce aggressiveness
        self.adaptivity_adjustment_factor = config.get('adaptivity_adjustment_factor', 0.10)  # ±10% adjustment
    
    def calculate_optimal_bid(self, entity_data: Dict[str, Any],
                              performance_data: List[Dict[str, Any]],
                              intelligence_signals: List[Any]) -> Optional[BidOptimization]:
        """
        Calculate optimal bid based on multiple factors with re-entry control
        
        Args:
            entity_data: Entity information
            performance_data: Historical performance data
            intelligence_signals: Signals from intelligence engines
            
        Returns:
            BidOptimization recommendation or None
        """
        if not performance_data:
            return None
        
        current_bid = float(entity_data.get('bid', entity_data.get('default_bid', 0)))
        if current_bid == 0:
            return None
        
        # Extract entity info
        entity_id = entity_data.get('keyword_id', entity_data.get('ad_group_id', entity_data.get('campaign_id', 0)))
        entity_type = entity_data.get('entity_type', 'keyword')
        entity_name = entity_data.get('keyword_text', entity_data.get('ad_group_name', entity_data.get('campaign_name', 'Unknown')))
        
        # 1. TIME FRAME FILTERING: Filter performance data by specified lookback period
        filtered_performance_data = self._filter_performance_data_by_timeframe(
            performance_data, self.bid_optimization_lookback_days
        )
        
        if not filtered_performance_data:
            self.logger.debug(f"No performance data found for {entity_type} {entity_id} in last {self.bid_optimization_lookback_days} days")
            return None
        
        # 2. SPEND/CLICKS SAFEGUARD: Check for sudden spikes before making decisions
        safeguard_result = self._check_spend_clicks_safeguard(
            filtered_performance_data, current_bid, entity_id, entity_type
        )
        
        if safeguard_result['triggered']:
            self.logger.warning(
                f"Safeguard triggered for {entity_type} {entity_id}: {safeguard_result['reason']}"
            )
            if safeguard_result['action'] == 'reduce_bid':
                # Reduce bid by configured factor
                new_bid = current_bid * (1 - self.safeguard_bid_reduction_factor)
                new_bid = max(self.bid_floor, new_bid)
                actual_adjustment = new_bid - current_bid
                adjustment_percentage = (actual_adjustment / current_bid * 100) if current_bid > 0 else 0
                
                return BidOptimization(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    entity_name=entity_name,
                    current_bid=current_bid,
                    recommended_bid=new_bid,
                    adjustment_amount=actual_adjustment,
                    adjustment_percentage=adjustment_percentage,
                    reason=f"SAFEGUARD: {safeguard_result['reason']} - Reducing bid by {self.safeguard_bid_reduction_factor:.0%}",
                    contributing_factors=[safeguard_result['reason']],
                    confidence=1.0,  # High confidence in safeguard actions
                    priority='critical',
                    metadata={
                        'safeguard_triggered': True,
                        'safeguard_type': safeguard_result['type'],
                        'spike_percentage': safeguard_result.get('spike_percentage', 0)
                    }
                )
            elif safeguard_result['action'] == 'pause':
                # Return None to skip adjustment (pausing would be handled elsewhere)
                self.logger.warning(f"Safeguard recommends pausing {entity_type} {entity_id}")
                return None
        
        # 3. NEW KEYWORD CHECK: Skip keywords <14 days old
        if self.enable_new_keyword_logic and entity_type == 'keyword':
            keyword_age = self._get_keyword_age(entity_id)
            if keyword_age is not None and keyword_age < self.new_keyword_age_days:
                self.logger.info(
                    f"Skipping new keyword: {entity_name} (age: {keyword_age} days) - "
                    f"must be {self.new_keyword_age_days}+ days old for bid adjustments"
                )
                return None
        
        # 4. LOW DATA ZONE CHECK: Skip adjustments if low data (0% adjustment)
        low_data_result = self._check_low_data_zone(filtered_performance_data, entity_id, entity_type)
        if low_data_result.get('in_low_data_zone', False):
            self.logger.info(
                f"Low data zone detected for {entity_type} {entity_id}: {low_data_result['reason']} - "
                f"holding bid (0% adjustment)"
            )
            # Return immediately if in low data zone
            return None
        
        # 5. ACOS TREND COMPARISON: Compare current vs previous 14-day period
        trend_adjustment = 0.0
        if self.enable_acos_trend_comparison:
            trend_result = self._compare_acos_trend(performance_data, filtered_performance_data)
            if trend_result['should_skip']:
                self.logger.info(
                    f"Skipping bid adjustment for {entity_type} {entity_id}: "
                    f"ACOS declining ({trend_result['current_acos']:.2%} vs {trend_result['previous_acos']:.2%})"
                )
                return None
            # Apply trend-based adjustments
            if trend_result.get('trend_adjustment'):
                trend_adjustment = trend_result['trend_adjustment']
                self.logger.info(
                    f"ACOS trend adjustment for {entity_type} {entity_id}: "
                    f"{trend_result['trend']} ({trend_result['current_acos']:.2%} vs {trend_result['previous_acos']:.2%}) = {trend_adjustment:+.0%}"
                )
        
        # 6. SPEND-BASED NO SALE LOGIC: Check for no sales with tiered spend thresholds
        if self.enable_spend_no_sale_logic:
            no_sale_result = self._check_spend_no_sale(filtered_performance_data, entity_id, entity_type)
            if no_sale_result['triggered']:
                # Apply tiered reduction
                reduction_factor = no_sale_result['reduction_factor']
                new_bid = current_bid * (1 - reduction_factor)
                new_bid = max(self.bid_floor, new_bid)
                actual_adjustment = new_bid - current_bid
                adjustment_percentage = (actual_adjustment / current_bid * 100) if current_bid > 0 else 0
                
                return BidOptimization(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    entity_name=entity_name,
                    current_bid=current_bid,
                    recommended_bid=new_bid,
                    adjustment_amount=actual_adjustment,
                    adjustment_percentage=adjustment_percentage,
                    reason=f"NO SALE: {no_sale_result['reason']} - Reducing bid by {reduction_factor:.0%}",
                    contributing_factors=[no_sale_result['reason']],
                    confidence=0.9,
                    priority='high',
                    metadata={
                        'no_sale_triggered': True,
                        'spend': no_sale_result['spend'],
                        'tier': no_sale_result['tier']
                    }
                )
        
        # Calculate performance-based adjustment (with smoothing and all new logic)
        performance_adjustment = self._calculate_performance_adjustment(
            filtered_performance_data, low_data_result, entity_id, entity_type
        )
        
        # Add trend adjustment
        performance_adjustment += trend_adjustment
        
        # Calculate intelligence-based adjustment
        intelligence_adjustment = self._calculate_intelligence_adjustment(intelligence_signals)
        
        # Calculate seasonality adjustment
        seasonality_adjustment = self._calculate_seasonality_adjustment(intelligence_signals)
        
        # Calculate profit-based adjustment
        profit_adjustment = self._calculate_profit_adjustment(intelligence_signals)
        
        # Combine adjustments with weights
        total_adjustment = (
            performance_adjustment * self.weights['performance'] +
            intelligence_adjustment * self.weights['intelligence'] +
            seasonality_adjustment * self.weights['seasonality'] +
            profit_adjustment * self.weights['profit']
        )
        
        # STEP 7: Apply campaign-level adaptivity (adjust aggressiveness based on campaign success rate)
        if self.enable_campaign_adaptivity and self.learning_loop:
            try:
                # Get campaign ID from entity data
                campaign_id = entity_data.get('campaign_id')
                if campaign_id:
                    campaign_success_rate = self.learning_loop.get_campaign_success_rate(campaign_id, days=30)
                    
                    if campaign_success_rate > self.campaign_success_threshold_high:
                        # High success rate - increase aggressiveness (+10%)
                        total_adjustment = total_adjustment * (1 + self.adaptivity_adjustment_factor)
                        self.logger.info(
                            f"Campaign {campaign_id} high success rate ({campaign_success_rate:.1%}) - "
                            f"increasing aggressiveness by {self.adaptivity_adjustment_factor:.0%}"
                        )
                    elif campaign_success_rate < self.campaign_success_threshold_low:
                        # Low success rate - reduce aggressiveness (-10%)
                        total_adjustment = total_adjustment * (1 - self.adaptivity_adjustment_factor)
                        self.logger.info(
                            f"Campaign {campaign_id} low success rate ({campaign_success_rate:.1%}) - "
                            f"reducing aggressiveness by {self.adaptivity_adjustment_factor:.0%}"
                        )
            except Exception as e:
                self.logger.warning(f"Error in campaign adaptivity: {e}")
        
        # Apply adjustment to current bid
        adjustment_amount = current_bid * total_adjustment
        new_bid = current_bid + adjustment_amount
        
        # Apply bid limits
        new_bid = max(self.bid_floor, min(self.bid_cap, new_bid))
        
        # Apply max adjustment limit
        max_change = current_bid * self.max_adjustment
        if abs(new_bid - current_bid) > max_change:
            new_bid = current_bid + (max_change if new_bid > current_bid else -max_change)
        
        # Recalculate actual adjustment
        actual_adjustment = new_bid - current_bid
        adjustment_percentage = (actual_adjustment / current_bid * 100) if current_bid > 0 else 0
        
        # Skip if adjustment is too small
        if abs(adjustment_percentage) < 2.0:
            return None
        
        # RE-ENTRY CONTROL CHECK
        if self.enable_re_entry_control and self.db and self.re_entry_controller:
            # Get bid change history with defensive coding
            last_change = None
            bid_history = []
            acos_history = []
            
            try:
                if hasattr(self.db, 'get_last_bid_change'):
                    last_change = self.db.get_last_bid_change(entity_type, entity_id)
                    # Validate return structure
                    if last_change and not isinstance(last_change, dict):
                        self.logger.warning(f"get_last_bid_change returned unexpected type for {entity_type} {entity_id}")
                        last_change = None
            except Exception as e:
                self.logger.warning(f"Error getting last bid change for {entity_type} {entity_id}: {e}")
                last_change = None
            
            try:
                if hasattr(self.db, 'get_bid_change_history'):
                    bid_history = self.db.get_bid_change_history(
                        entity_type, entity_id, 
                        self.config.get('oscillation_lookback_days', 14)
                    )
                    if not isinstance(bid_history, list):
                        self.logger.warning(f"get_bid_change_history returned unexpected type for {entity_type} {entity_id}")
                        bid_history = []
            except Exception as e:
                self.logger.warning(f"Error getting bid change history for {entity_type} {entity_id}: {e}")
                bid_history = []
            
            try:
                if hasattr(self.db, 'get_acos_history'):
                    acos_history = self.db.get_acos_history(entity_type, entity_id, 14)
                    if not isinstance(acos_history, list):
                        self.logger.warning(f"get_acos_history returned unexpected type for {entity_type} {entity_id}")
                        acos_history = []
            except Exception as e:
                self.logger.warning(f"Error getting ACOS history for {entity_type} {entity_id}: {e}")
                acos_history = []
            
            # Check if bid adjustment is allowed
            try:
                re_entry_result = self.re_entry_controller.should_adjust_bid(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    current_bid=current_bid,
                    proposed_bid=new_bid,
                    last_change_date=last_change.get('change_date') if last_change and isinstance(last_change, dict) else None,
                    last_bid=last_change.get('new_bid') if last_change and isinstance(last_change, dict) else None,
                    acos_history=acos_history,
                    bid_change_history=bid_history
                )
            except Exception as e:
                self.logger.error(f"Error in re-entry control check for {entity_type} {entity_id}: {e}")
                # On error, allow the adjustment (fail open) but log the issue
                re_entry_result = type('obj', (object,), {'allowed': True, 'reason': 'Error in re-entry check, allowing adjustment'})()
            
            if not re_entry_result.allowed:
                self.logger.info(
                    f"Bid adjustment blocked for {entity_type} {entity_id}: {re_entry_result.reason}"
                )
                # Return None to skip this adjustment
                return None
            else:
                self.logger.debug(
                    f"Bid adjustment approved for {entity_type} {entity_id}: {re_entry_result.reason}"
                )
        
        # Build contributing factors
        contributing_factors = []
        if abs(performance_adjustment) > 0.02:
            contributing_factors.append(f"Performance metrics (ACOS/ROAS): {performance_adjustment:+.1%}")
        if abs(intelligence_adjustment) > 0.02:
            contributing_factors.append(f"Intelligence signals: {intelligence_adjustment:+.1%}")
        if abs(seasonality_adjustment) > 0.02:
            contributing_factors.append(f"Seasonal trends: {seasonality_adjustment:+.1%}")
        if abs(profit_adjustment) > 0.02:
            contributing_factors.append(f"Profit optimization: {profit_adjustment:+.1%}")
        
        # Calculate current metrics for prediction (reuse from performance calculation)
        total_conversions = sum(int(record.get('attributed_conversions_7d', 0)) for record in filtered_performance_data)
        total_spend = sum(float(record.get('cost', 0)) for record in filtered_performance_data)
        total_sales = sum(self._get_daily_sales(record) for record in filtered_performance_data)
        
        # Get current metrics (reuse smoothed or calculated values)
        if self.enable_performance_smoothing and len(filtered_performance_data) >= self.min_data_points_for_smoothing:
            smoothed_metrics = self._apply_smoothing(filtered_performance_data)
            current_acos = smoothed_metrics.get('acos', 0)
            current_roas = smoothed_metrics.get('roas', 0)
            current_ctr = smoothed_metrics.get('ctr', 0)
        else:
            current_acos = (total_spend / total_sales) if total_sales > 0 else 0
            current_roas = (total_sales / total_spend) if total_spend > 0 else 0
            total_impressions = sum(float(record.get('impressions', 0)) for record in filtered_performance_data)
            total_clicks = sum(float(record.get('clicks', 0)) for record in filtered_performance_data)
            current_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # STEP 5: Predict success probability before making adjustment
        prob_success = 0.5  # Default
        if self.model_trainer:
            try:
                # Prepare current metrics for prediction
                current_metrics_for_pred = {
                    'acos': current_acos,
                    'roas': current_roas,
                    'ctr': current_ctr,
                    'conversions': total_conversions,
                    'spend': total_spend,
                    'sales': total_sales,
                }
                
                # Summarize intelligence signals
                intelligence_summary = {}
                if intelligence_signals:
                    for signal in intelligence_signals:
                        if signal.engine_name == 'Seasonality':
                            intelligence_summary['seasonality_boost'] = signal.strength
                        elif signal.engine_name == 'Ranking':
                            intelligence_summary['rank_signal'] = signal.strength
                        elif signal.engine_name == 'Profit':
                            intelligence_summary['profit_margin'] = signal.strength
                
                prob_success = self.model_trainer.predict_success_probability(
                    current_metrics=current_metrics_for_pred,
                    proposed_adjustment=total_adjustment,
                    current_bid=current_bid,
                    entity_type=entity_type,
                    intelligence_signals=intelligence_summary if intelligence_summary else None
                )
                
                # Apply predictive gating: skip if probability < 0.5, reduce if 0.5-0.7, boost if >0.7
                if prob_success < 0.5:
                    self.logger.info(
                        f"Skipping bid adjustment for {entity_type} {entity_id}: "
                        f"low success probability ({prob_success:.2%})"
                    )
                    return None
                elif 0.5 <= prob_success < 0.7:
                    # Apply smaller adjustment (reduce by 30%)
                    total_adjustment = total_adjustment * 0.7
                    self.logger.info(
                        f"Reducing adjustment for {entity_type} {entity_id}: "
                        f"moderate success probability ({prob_success:.2%})"
                    )
                # else: prob_success >= 0.7, apply full or boosted adjustment
                
            except Exception as e:
                self.logger.warning(f"Error in success probability prediction: {e}")
        
        # Recalculate bid with potentially adjusted total_adjustment
        adjustment_amount = current_bid * total_adjustment
        new_bid = current_bid + adjustment_amount
        
        # Apply bid limits
        new_bid = max(self.bid_floor, min(self.bid_cap, new_bid))
        
        # Apply max adjustment limit
        max_change = current_bid * self.max_adjustment
        if abs(new_bid - current_bid) > max_change:
            new_bid = current_bid + (max_change if new_bid > current_bid else -max_change)
        
        # Recalculate actual adjustment
        actual_adjustment = new_bid - current_bid
        adjustment_percentage = (actual_adjustment / current_bid * 100) if current_bid > 0 else 0
        
        # Skip if adjustment is too small
        if abs(adjustment_percentage) < 2.0:
            return None
        
        # Calculate confidence
        confidence = self._calculate_confidence(performance_data, intelligence_signals)
        
        # Determine priority
        priority = self._determine_priority(adjustment_percentage, confidence)
        
        # Generate reason
        reason = self._generate_reason(
            performance_adjustment, intelligence_adjustment,
            seasonality_adjustment, profit_adjustment, adjustment_percentage
        )
        
        return BidOptimization(
            entity_id=entity_data.get('id', 0),
            entity_type=entity_data.get('entity_type', 'unknown'),
            entity_name=entity_data.get('name', 'Unknown'),
            current_bid=current_bid,
            recommended_bid=new_bid,
            adjustment_amount=actual_adjustment,
            adjustment_percentage=adjustment_percentage,
            reason=reason,
            contributing_factors=contributing_factors,
            confidence=confidence,
            priority=priority,
            metadata={
                'performance_adjustment': performance_adjustment,
                'intelligence_adjustment': intelligence_adjustment,
                'seasonality_adjustment': seasonality_adjustment,
                'profit_adjustment': profit_adjustment,
                'total_adjustment': total_adjustment,
                'signals_count': len(intelligence_signals),
                'predicted_success_probability': prob_success
            }
        )
    
    def _calculate_performance_adjustment(self, performance_data: List[Dict[str, Any]],
                                        low_data_result: Dict[str, Any] = None,
                                        entity_id: int = 0, entity_type: str = 'keyword') -> float:
        """
        Calculate bid adjustment based on performance metrics with smoothing,
        granular ACOS tiers, order-based scaling, and CTR combined logic
        """
        if not performance_data:
            return 0.0
        
        low_data_result = low_data_result or {'in_low_data_zone': False}
        
        # 3. SMOOTHING: Apply smoothing to performance metrics
        if self.enable_performance_smoothing and len(performance_data) >= self.min_data_points_for_smoothing:
            smoothed_metrics = self._apply_smoothing(performance_data)
            current_acos = smoothed_metrics.get('acos', 0)
            current_roas = smoothed_metrics.get('roas', 0)
            current_ctr = smoothed_metrics.get('ctr', 0)
        else:
            # Fallback to simple aggregation if smoothing not enabled or insufficient data
            total_cost = sum(float(record.get('cost', 0)) for record in performance_data)
            total_sales = sum(self._get_daily_sales(record) for record in performance_data)
            total_impressions = sum(float(record.get('impressions', 0)) for record in performance_data)
            total_clicks = sum(float(record.get('clicks', 0)) for record in performance_data)
            
            if total_cost == 0 or total_sales == 0:
                return 0.0
            
            current_acos = total_cost / total_sales if total_sales > 0 else 0
            current_roas = total_sales / total_cost if total_cost > 0 else 0
            current_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        if current_acos == 0 and current_roas == 0:
            return 0.0
        
        # Get conversion count for order-based scaling
        total_conversions = sum(int(record.get('attributed_conversions_7d', 0)) for record in performance_data)
        total_spend = sum(float(record.get('cost', 0)) for record in performance_data)
        
        adjustment = 0.0
        
        # CLIENT-SPECIFIC ACOS RANGE LOGIC WITH ORDER-BASED SCALING
        # All ranges are calculated as percentages of target ACOS for flexibility
        # This allows changing target ACOS without modifying all hardcoded ranges
        if current_acos > 0:
            # Calculate ACOS as percentage of target
            acos_ratio = current_acos / self.target_acos if self.target_acos > 0 else 0
            
            # Critical Overspend: >150% of target ACOS
            if acos_ratio >= 1.50:
                adjustment -= 0.30  # -30%
                self.logger.debug(f"Critical Overspend ({acos_ratio:.0%} of target): {current_acos:.2%} = -30%")
            
            # Severe Overspend: 135%-150% of target ACOS
            elif 1.35 <= acos_ratio < 1.50:
                adjustment -= 0.25  # -25%
                self.logger.debug(f"Severe Overspend ({acos_ratio:.0%} of target): {current_acos:.2%} = -25%")
            
            # Moderately High ACOS: 120%-135% of target ACOS
            elif 1.20 <= acos_ratio < 1.35:
                adjustment -= 0.15  # -15%
                self.logger.debug(f"Moderately High ACOS ({acos_ratio:.0%} of target): {current_acos:.2%} = -15%")
            
            # Slightly Above Target: 100%-120% of target ACOS
            elif 1.00 <= acos_ratio < 1.20:
                adjustment -= 0.05  # -5%
                self.logger.debug(f"Slightly Above Target ({acos_ratio:.0%} of target): {current_acos:.2%} = -5%")
            
            # At Target: 85%-100% of target ACOS (hold)
            elif 0.85 <= acos_ratio < 1.00:
                adjustment += 0.0  # Hold at target
                self.logger.debug(f"At Target ({acos_ratio:.0%} of target): {current_acos:.2%} = Hold")
            
            # Optimal Zone (Slightly Below Target): 70%-85% of target ACOS
            elif 0.70 <= acos_ratio < 0.85:
                if total_conversions == 1:
                    adjustment += 0.0  # Hold (0%)
                elif 2 <= total_conversions <= 3:
                    adjustment += 0.05  # +5%
                else:  # 4+ orders
                    adjustment += 0.10  # +10%
                self.logger.debug(f"Optimal Zone ({acos_ratio:.0%} of target): {current_acos:.2%} with {total_conversions} orders = {adjustment:+.0%}")
            
            # High Efficiency Zone: 45%-70% of target ACOS
            elif 0.45 <= acos_ratio < 0.70:
                if total_conversions == 1:
                    adjustment += 0.05  # +5%
                elif 2 <= total_conversions <= 3:
                    adjustment += 0.10  # +10%
                else:  # 4+ orders
                    adjustment += 0.20  # +20%
                self.logger.debug(f"High Efficiency Zone ({acos_ratio:.0%} of target): {current_acos:.2%} with {total_conversions} orders = {adjustment:+.0%}")
            
            # Ultra Profitable Zone: 30%-45% of target ACOS
            elif 0.30 <= acos_ratio < 0.45:
                if total_conversions == 1:
                    adjustment += 0.10  # +10%
                elif 2 <= total_conversions <= 3:
                    adjustment += 0.20  # +20%
                else:  # 4+ orders
                    adjustment += 0.30  # +30%
                self.logger.debug(f"Ultra Profitable Zone ({acos_ratio:.0%} of target): {current_acos:.2%} with {total_conversions} orders = {adjustment:+.0%}")
            
            # Very Low ACOS (<30% of target) - Extreme profitability
            else:  # acos_ratio < 0.30
                # For very low ACOS, use aggressive scaling
                if total_conversions == 1:
                    adjustment += 0.15  # +15%
                elif 2 <= total_conversions <= 3:
                    adjustment += 0.25  # +25%
                else:  # 4+ orders
                    adjustment += 0.35  # +35% (but capped at max adjustment)
                self.logger.debug(f"Very Low ACOS ({acos_ratio:.0%} of target): {current_acos:.2%} with {total_conversions} orders = {adjustment:+.0%}")
        
        # IMPRESSIONS >500 & CLICKS <3 -- +5-10%
        if self.enable_impressions_clicks_logic:
            total_impressions = sum(int(record.get('impressions', 0)) for record in performance_data)
            if total_impressions > self.impressions_high_threshold and total_clicks < self.clicks_low_threshold:
                adjustment += self.impressions_clicks_adjustment
                self.logger.debug(f"Impressions/Clicks rule: {total_impressions} impressions, {total_clicks} clicks = +{self.impressions_clicks_adjustment:.0%}")
        
        # CTR COMBINED LOGIC: CTR <0.2% & Spend >$10 -- -20%
        if self.enable_ctr_combined_logic and current_ctr < self.ctr_critical_threshold:
            if total_spend >= self.ctr_low_spend_threshold:
                # Low CTR + High Spend = reduce bid by -20%
                adjustment -= self.ctr_low_spend_reduction
                self.logger.debug(f"CTR+Spend combined: CTR {current_ctr:.2f}% with ${total_spend:.2f} spend = -{self.ctr_low_spend_reduction:.0%}")
            elif total_conversions < self.ctr_low_order_threshold:
                # Low CTR + Low Orders = reduce bid
                adjustment -= 0.10
                self.logger.debug(f"CTR+Order combined: CTR {current_ctr:.2f}% with {total_conversions} conversions = -10%")
        
        # ROAS-based adjustment
        if current_roas > 0:
            roas_deviation = (current_roas - self.target_roas) / self.target_roas
            # If ROAS too low, reduce bid (negative adjustment)
            # If ROAS too high, increase bid (positive adjustment)
            adjustment += roas_deviation * 0.15
        
        # CTR-based adjustment (only if not already handled by combined logic)
        if current_ctr > 0 and not (self.enable_ctr_combined_logic and current_ctr < self.ctr_critical_threshold):
            ctr_deviation = (current_ctr - self.target_ctr) / self.target_ctr
            # If CTR too low, might need to increase bid for visibility
            adjustment += ctr_deviation * 0.10
        
        # Apply low data zone limit
        if low_data_result.get('in_low_data_zone', False):
            adjustment = max(-self.low_data_zone_adjustment_limit, 
                           min(self.low_data_zone_adjustment_limit, adjustment))
            self.logger.debug(f"Low data zone: limiting adjustment to {self.low_data_zone_adjustment_limit:.0%}")
        
        # Cap adjustment (general limit)
        return max(-0.30, min(0.30, adjustment))
    
    def _filter_performance_data_by_timeframe(self, performance_data: List[Dict[str, Any]], 
                                             days: int) -> List[Dict[str, Any]]:
        """
        Filter performance data to only include records within the specified time frame
        
        Args:
            performance_data: List of performance records
            days: Number of days to look back
            
        Returns:
            Filtered list of performance records
            
        Raises:
            ValueError: If records are missing date fields and cannot be filtered
        """
        if not performance_data:
            return []
        
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_data = []
        records_without_date = []
        
        # Preferred date field names (in order of preference)
        date_field_names = ['report_date', 'date', 'reportDate', 'timestamp']
        
        for record in performance_data:
            record_date = None
            
            # Try each date field name
            for date_field in date_field_names:
                if date_field in record:
                    date_value = record[date_field]
                    
                    if isinstance(date_value, str):
                        # Try ISO format first
                        try:
                            record_date = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                            break
                        except:
                            try:
                                # Try common date formats
                                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d']:
                                    try:
                                        record_date = datetime.strptime(date_value, fmt)
                                        break
                                    except:
                                        continue
                                if record_date:
                                    break
                            except:
                                continue
                    elif isinstance(date_value, datetime):
                        record_date = date_value
                        break
            
            if record_date:
                if record_date >= cutoff_date:
                    filtered_data.append(record)
            else:
                records_without_date.append(record)
        
        # If we have records without dates, log warning
        if records_without_date:
            self.logger.warning(
                f"Found {len(records_without_date)} records without valid date fields. "
                f"These will be excluded from filtering. Expected date fields: {date_field_names}"
            )
        
        # If no records have dates and we have data, this is a critical issue
        if not filtered_data and performance_data and not records_without_date:
            # All records processed but none had valid dates - this shouldn't happen
            self.logger.error(
                f"All {len(performance_data)} records are missing valid date fields. "
                f"Cannot filter by timeframe. Returning empty list to prevent incorrect calculations."
            )
            return []
        
        return filtered_data
    
    def _apply_smoothing(self, performance_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Apply smoothing to performance metrics to reduce noise from daily fluctuations
        
        Args:
            performance_data: List of performance records (should be sorted by date, most recent first)
            
        Returns:
            Dictionary with smoothed metrics: {'acos', 'roas', 'ctr'}
        """
        if not performance_data:
            return {'acos': 0, 'roas': 0, 'ctr': 0}
        
        # Sort by date (most recent first) if date field exists
        sorted_data = sorted(
            performance_data,
            key=lambda x: self._get_record_date(x),
            reverse=True
        )
        
        if self.smoothing_method == 'exponential':
            return self._exponential_smoothing(sorted_data)
        elif self.smoothing_method == 'weighted_moving_average':
            return self._weighted_moving_average(sorted_data)
        elif self.smoothing_method == 'simple_moving_average':
            return self._simple_moving_average(sorted_data)
        else:
            # Default to exponential smoothing
            return self._exponential_smoothing(sorted_data)
    
    def _get_record_date(self, record: Dict[str, Any]) -> datetime:
        """Extract date from record, defaulting to now if not found"""
        for date_field in ['report_date', 'date', 'reportDate', 'timestamp']:
            if date_field in record:
                date_value = record[date_field]
                if isinstance(date_value, str):
                    try:
                        return datetime.strptime(date_value, '%Y-%m-%d')
                    except:
                        try:
                            return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                        except:
                            pass
                elif isinstance(date_value, datetime):
                    return date_value
        return datetime.now()
    
    def _get_daily_sales(self, record: Dict[str, Any]) -> float:
        """
        Extract daily sales from record, preferring daily field over 7-day aggregate
        
        Args:
            record: Performance record
            
        Returns:
            Daily sales amount (not 7-day rolling sum)
        """
        # Prefer daily sales field if available
        daily_sales = record.get('sales') or record.get('attributed_sales') or record.get('daily_sales')
        if daily_sales is not None:
            return float(daily_sales)
        
        # Fallback to 7-day aggregate only if daily is not available
        # Note: This assumes records are daily and 7d field represents that day's portion
        # If this is incorrect, the caller should ensure daily sales are provided
        return float(record.get('attributed_sales_7d', 0))
    
    def _exponential_smoothing(self, sorted_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Apply exponential smoothing to metrics"""
        if not sorted_data:
            return {'acos': 0, 'roas': 0, 'ctr': 0}
        
        # Initialize with first record
        first_record = sorted_data[0]
        total_cost = float(first_record.get('cost', 0))
        total_sales = self._get_daily_sales(first_record)
        total_impressions = float(first_record.get('impressions', 0))
        total_clicks = float(first_record.get('clicks', 0))
        
        # Apply exponential smoothing to subsequent records
        alpha = self.exponential_smoothing_alpha
        for record in sorted_data[1:]:
            cost = float(record.get('cost', 0))
            sales = self._get_daily_sales(record)
            impressions = float(record.get('impressions', 0))
            clicks = float(record.get('clicks', 0))
            
            total_cost = alpha * cost + (1 - alpha) * total_cost
            total_sales = alpha * sales + (1 - alpha) * total_sales
            total_impressions = alpha * impressions + (1 - alpha) * total_impressions
            total_clicks = alpha * clicks + (1 - alpha) * total_clicks
        
        # Calculate smoothed metrics
        acos = total_cost / total_sales if total_sales > 0 else 0
        roas = total_sales / total_cost if total_cost > 0 else 0
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        return {'acos': acos, 'roas': roas, 'ctr': ctr}
    
    def _weighted_moving_average(self, sorted_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Apply weighted moving average (more weight to recent data)"""
        window_size = min(self.moving_average_window, len(sorted_data))
        window_data = sorted_data[:window_size]
        
        # Calculate weights (more recent = higher weight)
        weights = []
        total_weight = 0
        for i in range(window_size):
            weight = window_size - i  # More recent = higher weight
            weights.append(weight)
            total_weight += weight
        
        # Calculate weighted averages
        weighted_cost = sum(float(r.get('cost', 0)) * weights[i] for i, r in enumerate(window_data))
        weighted_sales = sum(self._get_daily_sales(r) * weights[i] for i, r in enumerate(window_data))
        weighted_impressions = sum(float(r.get('impressions', 0)) * weights[i] for i, r in enumerate(window_data))
        weighted_clicks = sum(float(r.get('clicks', 0)) * weights[i] for i, r in enumerate(window_data))
        
        total_cost = weighted_cost / total_weight if total_weight > 0 else 0
        total_sales = weighted_sales / total_weight if total_weight > 0 else 0
        total_impressions = weighted_impressions / total_weight if total_weight > 0 else 0
        total_clicks = weighted_clicks / total_weight if total_weight > 0 else 0
        
        acos = total_cost / total_sales if total_sales > 0 else 0
        roas = total_sales / total_cost if total_cost > 0 else 0
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        return {'acos': acos, 'roas': roas, 'ctr': ctr}
    
    def _simple_moving_average(self, sorted_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Apply simple moving average"""
        window_size = min(self.moving_average_window, len(sorted_data))
        window_data = sorted_data[:window_size]
        
        total_cost = sum(float(r.get('cost', 0)) for r in window_data)
        total_sales = sum(self._get_daily_sales(r) for r in window_data)
        total_impressions = sum(float(r.get('impressions', 0)) for r in window_data)
        total_clicks = sum(float(r.get('clicks', 0)) for r in window_data)
        
        acos = total_cost / total_sales if total_sales > 0 else 0
        roas = total_sales / total_cost if total_cost > 0 else 0
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        return {'acos': acos, 'roas': roas, 'ctr': ctr}
    
    def _get_keyword_age(self, keyword_id: int) -> Optional[int]:
        """
        Get the age of a keyword in days based on creation date
        
        Uses abstracted DB method if available, otherwise falls back to direct query.
        
        Args:
            keyword_id: Keyword ID
            
        Returns:
            Age in days, or None if not found or error occurs
        """
        if not self.db:
            self.logger.debug(f"No DB connector available for keyword age check: {keyword_id}")
            return None
        
        try:
            # Try abstracted method first (if available)
            if hasattr(self.db, 'get_keyword_created_at'):
                created_at = self.db.get_keyword_created_at(keyword_id)
                if created_at:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    age_days = (datetime.now() - created_at).days
                    return age_days
                return None
            
            # Fallback to direct query (with schema flexibility)
            # Try common table/column names
            schema_config = self.config.get('db_schema', {})
            table_name = schema_config.get('keywords_table', 'keywords')
            id_column = schema_config.get('keyword_id_column', 'keyword_id')
            created_column = schema_config.get('created_at_column', 'created_at')
            
            query = f"SELECT {created_column} FROM {table_name} WHERE {id_column} = %s"
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (keyword_id,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        created_at = result[0]
                        if isinstance(created_at, str):
                            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        age_days = (datetime.now() - created_at).days
                        return age_days
        except AttributeError as e:
            self.logger.warning(f"DB method not available for keyword age check: {keyword_id}, error: {e}")
        except Exception as e:
            self.logger.warning(f"Error getting keyword age for {keyword_id}: {e}")
        
        return None
    
    def _check_low_data_zone(self, performance_data: List[Dict[str, Any]],
                            entity_id: int, entity_type: str) -> Dict[str, Any]:
        """
        Check if entity is in low data zone (Spend < $5 or Clicks < 10)
        
        Args:
            performance_data: Filtered performance data
            entity_id: Entity ID
            entity_type: Entity type
            
        Returns:
            Dictionary with low data zone result
        """
        result = {
            'in_low_data_zone': False,
            'reason': ''
        }
        
        if not self.enable_low_data_zone or not performance_data:
            return result
        
        total_spend = sum(float(record.get('cost', 0)) for record in performance_data)
        total_clicks = sum(int(record.get('clicks', 0)) for record in performance_data)
        
        if total_spend < self.low_data_spend_threshold:
            result['in_low_data_zone'] = True
            result['reason'] = f"Low spend: ${total_spend:.2f} < ${self.low_data_spend_threshold}"
            return result
        
        if total_clicks < self.low_data_clicks_threshold:
            result['in_low_data_zone'] = True
            result['reason'] = f"Low clicks: {total_clicks} < {self.low_data_clicks_threshold}"
            return result
        
        return result
    
    def _compare_acos_trend(self, all_performance_data: List[Dict[str, Any]],
                           current_period_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare ACOS trend: current 14-day period vs previous 14-day period
        
        Args:
            all_performance_data: All available performance data
            current_period_data: Current period data (14 days)
            
        Returns:
            Dictionary with trend comparison result
        """
        result = {
            'should_skip': False,
            'current_acos': 0,
            'previous_acos': 0,
            'trend': 'stable'
        }
        
        if not self.enable_acos_trend_comparison or not current_period_data:
            return result
        
        # Calculate current period ACOS
        current_cost = sum(float(r.get('cost', 0)) for r in current_period_data)
        current_sales = sum(float(r.get('attributed_sales_7d', 0)) for r in current_period_data)
        current_acos = current_cost / current_sales if current_sales > 0 else 0
        result['current_acos'] = current_acos
        
        if current_acos == 0:
            return result
        
        # Get previous period data (14-28 days ago)
        cutoff_current = datetime.now() - timedelta(days=self.bid_optimization_lookback_days)
        cutoff_previous_start = cutoff_current - timedelta(days=self.previous_period_lookback_days)
        
        previous_period_data = []
        for record in all_performance_data:
            record_date = self._get_record_date(record)
            if cutoff_previous_start <= record_date < cutoff_current:
                previous_period_data.append(record)
        
        if not previous_period_data:
            return result
        
        # Calculate previous period ACOS
        previous_cost = sum(float(r.get('cost', 0)) for r in previous_period_data)
        previous_sales = sum(float(r.get('attributed_sales_7d', 0)) for r in previous_period_data)
        previous_acos = previous_cost / previous_sales if previous_sales > 0 else 0
        result['previous_acos'] = previous_acos
        
        if previous_acos == 0:
            return result
        
        # Compare trends
        acos_change = (current_acos - previous_acos) / previous_acos if previous_acos > 0 else 0
        
        if acos_change >= self.acos_trend_decline_threshold:
            # ACOS ↑ >30% (getting worse) - apply -10% adjustment
            result['should_skip'] = self.skip_on_acos_decline
            result['trend'] = 'declining'
            result['trend_adjustment'] = self.acos_trend_decline_adjustment
            self.logger.info(
                f"ACOS trend declining: {current_acos:.2%} vs {previous_acos:.2%} "
                f"({acos_change:+.1%} change) = -10% adjustment"
            )
        elif acos_change <= -self.acos_trend_improvement_threshold:
            # ACOS ↓ >30% (improving) - apply +10% adjustment
            result['trend'] = 'improving'
            result['trend_adjustment'] = self.acos_trend_improvement_adjustment
            self.logger.info(
                f"ACOS trend improving: {current_acos:.2%} vs {previous_acos:.2%} "
                f"({acos_change:+.1%} change) = +10% adjustment"
            )
        else:
            # Stable
            result['trend'] = 'stable'
            result['trend_adjustment'] = 0.0
        
        return result
    
    def _check_spend_no_sale(self, performance_data: List[Dict[str, Any]],
                           entity_id: int, entity_type: str) -> Dict[str, Any]:
        """
        Check for no sales with tiered spend thresholds ($10, $15, $30)
        
        Args:
            performance_data: Filtered performance data
            entity_id: Entity ID
            entity_type: Entity type
            
        Returns:
            Dictionary with no sale result
        """
        result = {
            'triggered': False,
            'reason': '',
            'reduction_factor': 0.0,
            'spend': 0.0,
            'tier': None
        }
        
        if not self.enable_spend_no_sale_logic or not performance_data:
            return result
        
        total_spend = sum(float(record.get('cost', 0)) for record in performance_data)
        total_conversions = sum(int(record.get('attributed_conversions_7d', 0)) for record in performance_data)
        result['spend'] = total_spend
        
        # Check if there are no sales
        if total_conversions == 0:
            # Tier 3: >$30 spend with no sales - 35% reduction
            if total_spend > self.no_sale_spend_tier_3:
                result['triggered'] = True
                result['reduction_factor'] = self.no_sale_reduction_tier_3
                result['tier'] = 3
                result['reason'] = f"${total_spend:.2f} spent with no sales (Tier 3: >${self.no_sale_spend_tier_3})"
                self.logger.warning(
                    f"{entity_type} {entity_id}: Tier 3 no-sale - ${total_spend:.2f} spent, no conversions = -35%"
                )
                return result
            
            # Tier 2: $16-30 spend with no sales - 25% reduction
            elif self.no_sale_spend_tier_2 < total_spend <= self.no_sale_spend_tier_3:
                result['triggered'] = True
                result['reduction_factor'] = self.no_sale_reduction_tier_2
                result['tier'] = 2
                result['reason'] = f"${total_spend:.2f} spent with no sales (Tier 2: ${self.no_sale_spend_tier_2}-${self.no_sale_spend_tier_3})"
                self.logger.warning(
                    f"{entity_type} {entity_id}: Tier 2 no-sale - ${total_spend:.2f} spent, no conversions = -25%"
                )
                return result
            
            # Tier 1: $10-15 spend with no sales - 15% reduction
            elif self.no_sale_spend_tier_1 <= total_spend <= self.no_sale_spend_tier_2:
                result['triggered'] = True
                result['reduction_factor'] = self.no_sale_reduction_tier_1
                result['tier'] = 1
                result['reason'] = f"${total_spend:.2f} spent with no sales (Tier 1: ${self.no_sale_spend_tier_1}-${self.no_sale_spend_tier_2})"
                self.logger.info(
                    f"{entity_type} {entity_id}: Tier 1 no-sale - ${total_spend:.2f} spent, no conversions = -15%"
                )
                return result
        
        return result
    
    def _check_spend_clicks_safeguard(self, performance_data: List[Dict[str, Any]],
                                     current_bid: float, entity_id: int, entity_type: str) -> Dict[str, Any]:
        """
        Check for sudden spikes in spend or clicks that might indicate overspend
        
        Args:
            performance_data: Filtered performance data
            current_bid: Current bid amount
            entity_id: Entity ID
            entity_type: Entity type
            
        Returns:
            Dictionary with safeguard result: {'triggered': bool, 'reason': str, 'action': str, 'type': str}
        """
        result = {
            'triggered': False,
            'reason': '',
            'action': self.safeguard_action,
            'type': None,
            'spike_percentage': 0
        }
        
        if not performance_data or len(performance_data) < 2:
            return result
        
        # Sort by date (most recent first)
        sorted_data = sorted(
            performance_data,
            key=lambda x: self._get_record_date(x),
            reverse=True
        )
        
        # Get most recent day's data
        most_recent = sorted_data[0]
        recent_cost = float(most_recent.get('cost', 0))
        recent_clicks = float(most_recent.get('clicks', 0))
        
        # Calculate average from previous days (excluding most recent)
        lookback_days = min(self.spend_safeguard_lookback_days, len(sorted_data) - 1)
        if lookback_days == 0:
            return result
        
        previous_data = sorted_data[1:lookback_days + 1]
        avg_cost = sum(float(r.get('cost', 0)) for r in previous_data) / len(previous_data) if previous_data else 0
        avg_clicks = sum(float(r.get('clicks', 0)) for r in previous_data) / len(previous_data) if previous_data else 0
        
        # Check spend safeguard
        if self.enable_spend_safeguard and recent_cost >= self.min_spend_for_safeguard and avg_cost > 0:
            cost_increase_ratio = recent_cost / avg_cost if avg_cost > 0 else 0
            if cost_increase_ratio >= self.spend_spike_threshold:
                spike_percentage = (cost_increase_ratio - 1) * 100
                result['triggered'] = True
                result['reason'] = f"Spend spike detected: {recent_cost:.2f} vs avg {avg_cost:.2f} ({spike_percentage:.1f}% increase)"
                result['type'] = 'spend_spike'
                result['spike_percentage'] = spike_percentage
                self.logger.warning(
                    f"{entity_type} {entity_id}: Spend spike {spike_percentage:.1f}% "
                    f"(${recent_cost:.2f} vs ${avg_cost:.2f} avg)"
                )
                return result
        
        # Check clicks safeguard
        if self.enable_clicks_safeguard and recent_clicks >= self.min_clicks_for_safeguard and avg_clicks > 0:
            clicks_increase_ratio = recent_clicks / avg_clicks if avg_clicks > 0 else 0
            if clicks_increase_ratio >= self.clicks_spike_threshold:
                spike_percentage = (clicks_increase_ratio - 1) * 100
                result['triggered'] = True
                result['reason'] = f"Clicks spike detected: {recent_clicks:.0f} vs avg {avg_clicks:.0f} ({spike_percentage:.1f}% increase)"
                result['type'] = 'clicks_spike'
                result['spike_percentage'] = spike_percentage
                self.logger.warning(
                    f"{entity_type} {entity_id}: Clicks spike {spike_percentage:.1f}% "
                    f"({recent_clicks:.0f} vs {avg_clicks:.0f} avg)"
                )
                return result
        
        return result
    
    def _calculate_intelligence_adjustment(self, signals: List[Any]) -> float:
        """Calculate bid adjustment based on intelligence signals"""
        if not signals:
            return 0.0
        
        adjustment = 0.0
        
        for signal in signals:
            if signal.signal_type == 'opportunity':
                # Opportunities suggest increasing bids
                adjustment += signal.strength * 0.10
            elif signal.signal_type == 'warning':
                # Warnings suggest reducing bids
                adjustment -= signal.strength * 0.10
        
        # Cap adjustment
        return max(-0.20, min(0.20, adjustment))
    
    def _calculate_seasonality_adjustment(self, signals: List[Any]) -> float:
        """Calculate bid adjustment based on seasonal factors"""
        for signal in signals:
            if signal.engine_name == 'Seasonality' and signal.signal_type == 'optimization':
                boost_factor = signal.metadata.get('boost_factor', 1.0)
                return (boost_factor - 1.0) * 0.5  # Apply 50% of seasonal boost
        
        return 0.0
    
    def _calculate_profit_adjustment(self, signals: List[Any]) -> float:
        """Calculate bid adjustment based on profit optimization"""
        for signal in signals:
            if signal.engine_name == 'Profit':
                if signal.signal_type == 'opportunity':
                    # High profit margins - can afford to increase bids
                    return signal.strength * 0.15
                elif signal.signal_type == 'warning':
                    # Low profit margins - need to reduce bids
                    return -signal.strength * 0.15
        
        return 0.0
    
    def _calculate_confidence(self, performance_data: List[Dict[str, Any]],
                             signals: List[Any]) -> float:
        """Calculate confidence in the bid recommendation"""
        # Base confidence on data quantity
        data_confidence = min(1.0, len(performance_data) / 14.0)  # 14 days = 100% confidence
        
        # Factor in signal strength
        signal_confidence = 0.5  # Default
        if signals:
            avg_strength = sum(s.strength for s in signals) / len(signals)
            signal_confidence = avg_strength
        
        # Combine confidences
        return (data_confidence * 0.6 + signal_confidence * 0.4)
    
    def _determine_priority(self, adjustment_percentage: float, confidence: float) -> str:
        """Determine priority level for the bid optimization"""
        magnitude = abs(adjustment_percentage)
        
        if magnitude >= 30 and confidence >= 0.8:
            return 'critical'
        elif magnitude >= 20 and confidence >= 0.7:
            return 'high'
        elif magnitude >= 10 and confidence >= 0.6:
            return 'medium'
        else:
            return 'low'
    
    def _generate_reason(self, performance_adj: float, intelligence_adj: float,
                        seasonality_adj: float, profit_adj: float,
                        total_percentage: float) -> str:
        """Generate human-readable reason for the bid adjustment"""
        direction = "increase" if total_percentage > 0 else "decrease"
        
        reasons = []
        
        if abs(performance_adj) > 0.05:
            if performance_adj < 0:
                reasons.append("underperforming ACOS/ROAS metrics")
            else:
                reasons.append("strong ACOS/ROAS performance")
        
        if abs(intelligence_adj) > 0.05:
            if intelligence_adj < 0:
                reasons.append("intelligence warnings detected")
            else:
                reasons.append("growth opportunities identified")
        
        if abs(seasonality_adj) > 0.05:
            reasons.append("seasonal trends")
        
        if abs(profit_adj) > 0.05:
            if profit_adj < 0:
                reasons.append("profit margin constraints")
            else:
                reasons.append("profit margin opportunities")
        
        if not reasons:
            reasons.append("minor performance adjustments")
        
        return f"Recommend {direction} bid by {abs(total_percentage):.1f}% based on: {', '.join(reasons)}"
    
    def log_bid_change(self, bid_optimization: BidOptimization, 
                      current_metrics: Dict[str, Any],
                      performance_data: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        STEP 1: Log a bid change to the database with performance_before metrics
        
        Args:
            bid_optimization: BidOptimization object with recommendation
            current_metrics: Current performance metrics (ACOS, ROAS, CTR, conversions)
            performance_data: Optional performance data to calculate 14-day averages
            
        Returns:
            True if logged successfully
        """
        if not self.db or not self.bid_change_tracker:
            return False
        
        # Calculate 14-day performance averages for learning loop
        performance_before = None
        if performance_data:
            filtered_data = self._filter_performance_data_by_timeframe(
                performance_data, self.bid_optimization_lookback_days
            )
            if filtered_data:
                total_cost = sum(float(r.get('cost', 0)) for r in filtered_data)
                total_sales = sum(self._get_daily_sales(r) for r in filtered_data)
                total_impressions = sum(float(r.get('impressions', 0)) for r in filtered_data)
                total_clicks = sum(float(r.get('clicks', 0)) for r in filtered_data)
                total_conversions = sum(int(r.get('attributed_conversions_7d', 0)) for r in filtered_data)
                
                performance_before = {
                    'acos': (total_cost / total_sales) if total_sales > 0 else 0,
                    'roas': (total_sales / total_cost) if total_cost > 0 else 0,
                    'ctr': (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
                    'spend': total_cost,
                    'sales': total_sales,
                    'conversions': total_conversions,
                    'impressions': total_impressions,
                    'clicks': total_clicks
                }
        
        # Create change record
        change_record = self.bid_change_tracker.create_change_record(
            entity_type=bid_optimization.entity_type,
            entity_id=bid_optimization.entity_id,
            entity_name=bid_optimization.entity_name,
            old_bid=bid_optimization.current_bid,
            new_bid=bid_optimization.recommended_bid,
            reason=bid_optimization.reason,
            acos=current_metrics.get('acos'),
            roas=current_metrics.get('roas'),
            ctr=current_metrics.get('ctr'),
            conversions=current_metrics.get('conversions'),
            metadata={
                'confidence': bid_optimization.confidence,
                'priority': bid_optimization.priority,
                'contributing_factors': bid_optimization.contributing_factors,
                **bid_optimization.metadata
            }
        )
        
        # Add learning loop fields
        import json
        change_record['performance_before'] = json.dumps(performance_before) if performance_before else None
        change_record['performance_after'] = None  # Will be updated after 14 days
        change_record['outcome_score'] = None
        change_record['outcome_label'] = None
        change_record['evaluated_at'] = None
        
        # Save to database
        success = self.db.save_bid_change(change_record)
        
        # Create bid lock for cooldown period
        if success:
            cooldown_days = self.config.get('bid_change_cooldown_days', 3)
            self.db.create_bid_lock(
                entity_type=bid_optimization.entity_type,
                entity_id=bid_optimization.entity_id,
                lock_days=cooldown_days,
                reason=f"Cooldown after bid adjustment ({bid_optimization.adjustment_percentage:+.1f}%)"
            )
        
        return success


class BudgetOptimizationEngine:
    """
    Advanced budget optimization for campaigns
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.min_daily_budget = config.get('budget_min_daily', 1.0)
        self.max_daily_budget = config.get('budget_max_daily', 1000.0)
        self.target_roas = config.get('roas_target', 11.11)
        self.aggressive_scale_roas = config.get('aggressive_scale_roas', 5.0)
        
        # Smoothing configuration
        self.enable_performance_smoothing = config.get('enable_performance_smoothing', True)
        self.smoothing_method = config.get('smoothing_method', 'exponential')
        self.exponential_smoothing_alpha = config.get('exponential_smoothing_alpha', 0.3)
        self.moving_average_window = config.get('moving_average_window', 7)
    
    def _get_daily_sales(self, record: Dict[str, Any]) -> float:
        """
        Extract daily sales from record, preferring daily field over 7-day aggregate
        
        Args:
            record: Performance record
            
        Returns:
            Daily sales amount (not 7-day rolling sum)
        """
        # Prefer daily sales field if available
        daily_sales = record.get('sales') or record.get('attributed_sales') or record.get('daily_sales')
        if daily_sales is not None:
            return float(daily_sales)
        
        # Fallback to 7-day aggregate only if daily is not available
        return float(record.get('attributed_sales_7d', 0))
    
    def _apply_smoothing_for_budget(self, performance_data: List[Dict[str, Any]], 
                                    method: str = 'exponential') -> Dict[str, float]:
        """
        Apply smoothing to performance data for budget optimization
        Lightweight utility that doesn't require full BidOptimizationEngine instance
        
        Args:
            performance_data: List of performance records
            method: Smoothing method ('exponential', 'weighted_moving_average', 'simple_moving_average')
            
        Returns:
            Dictionary with smoothed metrics: {'acos', 'roas', 'ctr'}
        """
        if not performance_data:
            return {'acos': 0, 'roas': 0, 'ctr': 0}
        
        # Sort by date (most recent first)
        sorted_data = sorted(
            performance_data,
            key=lambda x: self._get_record_date(x),
            reverse=True
        )
        
        if method == 'exponential':
            return self._exponential_smoothing_budget(sorted_data)
        elif method == 'weighted_moving_average':
            return self._weighted_moving_average_budget(sorted_data)
        elif method == 'simple_moving_average':
            return self._simple_moving_average_budget(sorted_data)
        else:
            return self._exponential_smoothing_budget(sorted_data)
    
    def _get_record_date(self, record: Dict[str, Any]) -> datetime:
        """Extract date from record, defaulting to now if not found"""
        for date_field in ['report_date', 'date', 'reportDate', 'timestamp']:
            if date_field in record:
                date_value = record[date_field]
                if isinstance(date_value, str):
                    try:
                        return datetime.strptime(date_value, '%Y-%m-%d')
                    except:
                        try:
                            return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                        except:
                            pass
                elif isinstance(date_value, datetime):
                    return date_value
        return datetime.now()
    
    def _exponential_smoothing_budget(self, sorted_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Apply exponential smoothing to metrics"""
        if not sorted_data:
            return {'acos': 0, 'roas': 0, 'ctr': 0}
        
        first_record = sorted_data[0]
        total_cost = float(first_record.get('cost', 0))
        total_sales = self._get_daily_sales(first_record)
        total_impressions = float(first_record.get('impressions', 0))
        total_clicks = float(first_record.get('clicks', 0))
        
        alpha = self.exponential_smoothing_alpha
        for record in sorted_data[1:]:
            cost = float(record.get('cost', 0))
            sales = self._get_daily_sales(record)
            impressions = float(record.get('impressions', 0))
            clicks = float(record.get('clicks', 0))
            
            total_cost = alpha * cost + (1 - alpha) * total_cost
            total_sales = alpha * sales + (1 - alpha) * total_sales
            total_impressions = alpha * impressions + (1 - alpha) * total_impressions
            total_clicks = alpha * clicks + (1 - alpha) * total_clicks
        
        acos = total_cost / total_sales if total_sales > 0 else 0
        roas = total_sales / total_cost if total_cost > 0 else 0
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        return {'acos': acos, 'roas': roas, 'ctr': ctr}
    
    def _weighted_moving_average_budget(self, sorted_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Apply weighted moving average"""
        window_size = min(self.moving_average_window, len(sorted_data))
        window_data = sorted_data[:window_size]
        
        weights = []
        total_weight = 0
        for i in range(window_size):
            weight = window_size - i
            weights.append(weight)
            total_weight += weight
        
        weighted_cost = sum(float(r.get('cost', 0)) * weights[i] for i, r in enumerate(window_data))
        weighted_sales = sum(self._get_daily_sales(r) * weights[i] for i, r in enumerate(window_data))
        weighted_impressions = sum(float(r.get('impressions', 0)) * weights[i] for i, r in enumerate(window_data))
        weighted_clicks = sum(float(r.get('clicks', 0)) * weights[i] for i, r in enumerate(window_data))
        
        total_cost = weighted_cost / total_weight if total_weight > 0 else 0
        total_sales = weighted_sales / total_weight if total_weight > 0 else 0
        total_impressions = weighted_impressions / total_weight if total_weight > 0 else 0
        total_clicks = weighted_clicks / total_weight if total_weight > 0 else 0
        
        acos = total_cost / total_sales if total_sales > 0 else 0
        roas = total_sales / total_cost if total_cost > 0 else 0
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        return {'acos': acos, 'roas': roas, 'ctr': ctr}
    
    def _simple_moving_average_budget(self, sorted_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Apply simple moving average"""
        window_size = min(self.moving_average_window, len(sorted_data))
        window_data = sorted_data[:window_size]
        
        total_cost = sum(float(r.get('cost', 0)) for r in window_data)
        total_sales = sum(self._get_daily_sales(r) for r in window_data)
        total_impressions = sum(float(r.get('impressions', 0)) for r in window_data)
        total_clicks = sum(float(r.get('clicks', 0)) for r in window_data)
        
        acos = total_cost / total_sales if total_sales > 0 else 0
        roas = total_sales / total_cost if total_cost > 0 else 0
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        return {'acos': acos, 'roas': roas, 'ctr': ctr}
    
    def _filter_performance_data_by_timeframe(self, performance_data: List[Dict[str, Any]], 
                                             days: int) -> List[Dict[str, Any]]:
        """Filter performance data to only include records within the specified time frame"""
        if not performance_data:
            return []
        
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_data = []
        
        for record in performance_data:
            # Try different date field names
            record_date = None
            for date_field in ['report_date', 'date', 'reportDate', 'timestamp']:
                if date_field in record:
                    date_value = record[date_field]
                    if isinstance(date_value, str):
                        try:
                            record_date = datetime.strptime(date_value, '%Y-%m-%d')
                        except:
                            try:
                                record_date = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                            except:
                                pass
                    elif isinstance(date_value, datetime):
                        record_date = date_value
                    break
            
            if record_date and record_date >= cutoff_date:
                filtered_data.append(record)
        
        # If no date field found, assume all data is recent (backward compatibility)
        if not filtered_data and performance_data:
            self.logger.warning("No date field found in performance data, using all records")
            return performance_data
        
        return filtered_data
    
    def optimize_budget(self, campaign_data: Dict[str, Any],
                       performance_data: List[Dict[str, Any]],
                       budget_utilization: float) -> Optional[Dict[str, Any]]:
        """
        Optimize campaign budget based on performance and utilization
        
        Args:
            campaign_data: Campaign information
            performance_data: Historical performance data
            budget_utilization: Budget utilization rate (0.0 to 1.0)
            
        Returns:
            Budget optimization recommendation or None
        """
        if not performance_data:
            return None
        
        current_budget = float(campaign_data.get('budget_amount', 0))
        if current_budget == 0:
            return None
        
        # Filter by time frame (use same lookback as bid optimization)
        lookback_days = self.config.get('bid_optimization_lookback_days', 7)
        filtered_data = self._filter_performance_data_by_timeframe(performance_data, lookback_days)
        
        if not filtered_data:
            return None
        
        # Apply smoothing if enabled
        enable_smoothing = self.config.get('enable_performance_smoothing', True)
        smoothing_method = self.config.get('smoothing_method', 'exponential')
        min_data_points = self.config.get('min_data_points_for_smoothing', 3)
        
        if enable_smoothing and len(filtered_data) >= min_data_points:
            # Use smoothing utility directly without creating full optimizer instance
            smoothed_metrics = self._apply_smoothing_for_budget(filtered_data, smoothing_method)
            current_roas = smoothed_metrics.get('roas', 0)
            total_cost = sum(float(record.get('cost', 0)) for record in filtered_data)
        else:
            # Calculate performance metrics without smoothing
            total_cost = sum(float(record.get('cost', 0)) for record in filtered_data)
            total_sales = sum(float(record.get('attributed_sales_7d', 0)) for record in filtered_data)
            
            if total_cost == 0:
                return None
            
            current_roas = total_sales / total_cost if total_cost > 0 else 0
        
        # Determine budget adjustment strategy
        adjustment_factor = 0.0
        reason = ""
        priority = "low"
        
        # High ROAS + High utilization = Increase budget aggressively
        if current_roas >= self.aggressive_scale_roas and budget_utilization >= 0.9:
            adjustment_factor = 0.30  # 30% increase
            reason = f"Excellent ROAS ({current_roas:.2f}) with high budget utilization ({budget_utilization:.1%}) - scale aggressively"
            priority = "high"
        
        # Good ROAS + High utilization = Increase budget
        elif current_roas >= self.target_roas and budget_utilization >= 0.8:
            adjustment_factor = 0.20  # 20% increase
            reason = f"Strong ROAS ({current_roas:.2f}) with high budget utilization ({budget_utilization:.1%}) - scale moderately"
            priority = "medium"
        
        # Low utilization with good performance = No change
        elif current_roas >= self.target_roas and budget_utilization < 0.6:
            return None  # Budget is adequate
        
        # Poor ROAS = Decrease budget
        elif current_roas < self.target_roas * 0.7:
            adjustment_factor = -0.20  # 20% decrease
            reason = f"Below-target ROAS ({current_roas:.2f}) - reduce budget"
            priority = "medium"
        
        # No significant change needed
        else:
            return None
        
        # Calculate new budget
        adjustment_amount = current_budget * adjustment_factor
        new_budget = current_budget + adjustment_amount
        
        # Apply limits
        new_budget = max(self.min_daily_budget, min(self.max_daily_budget, new_budget))
        actual_adjustment = new_budget - current_budget
        adjustment_percentage = (actual_adjustment / current_budget * 100) if current_budget > 0 else 0
        
        # Skip if adjustment is too small
        if abs(adjustment_percentage) < 5.0:
            return None
        
        return {
            'campaign_id': campaign_data.get('id', 0),
            'campaign_name': campaign_data.get('name', 'Unknown'),
            'current_budget': current_budget,
            'recommended_budget': new_budget,
            'adjustment_amount': actual_adjustment,
            'adjustment_percentage': adjustment_percentage,
            'reason': reason,
            'priority': priority,
            'confidence': min(1.0, len(filtered_data) / 14.0),
            'metadata': {
                'current_roas': current_roas,
                'target_roas': self.target_roas,
                'budget_utilization': budget_utilization,
                'total_spend': total_cost
            }
        }

