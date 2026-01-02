"""
Bid Optimization Engine
Integrates all intelligence engines for intelligent bid adjustments
"""

import logging
import random
import statistics
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from .re_entry_control import ReEntryController, BidChangeTracker
from .telemetry import TelemetryClient
from .utils.units import decimal_to_percentage


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


@dataclass
class AdjustmentProposal:
    """Represents an adjustment contribution from one subsystem."""
    source: str
    percentage: float
    priority: str = 'medium'
    confidence: float = 1.0
    veto: bool = False
    reason: Optional[str] = None


class BidOptimizationEngine:
    """
    Advanced bid optimization combining multiple intelligence signals
    """
    
    def __init__(self, config: Dict[str, Any], db_connector=None,
                 model_trainer=None, learning_loop=None,
                 telemetry: Optional[TelemetryClient] = None):
        self.config = config
        self.db = db_connector
        self.model_trainer = model_trainer  # For STEP 5: Predictive gating
        self.learning_loop = learning_loop  # For STEP 7: Campaign adaptivity
        self.logger = logging.getLogger(__name__)
        self.telemetry = telemetry or TelemetryClient(config)
        
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
        
        # Granular ACOS tiers expressed as % of the target ACOS (1.0 == 100% of target)
        tier_percentage_defaults = {
            'acos_tier_very_high': 2.00,     # 200%+ Critical Overspend
            'acos_tier_high': 1.35,          # 135%-200% Severe Overspend (lower bound)
            'acos_tier_medium_high': 1.20,   # 120%-135% Moderately High (lower bound)
            'acos_tier_medium': 1.19,        # 119% Slightly Above Target (upper bound)
            'acos_tier_target': 1.00,        # 100% Target
            'acos_tier_good': 0.85,          # 85% Target upper band
            'acos_tier_low': 0.70,           # 70% Target lower band
            'acos_tier_very_low': 0.45,      # 45% Ultra Profitable upper band
            'acos_tier_excellent': 0.30      # 30% Ultra Profitable floor
        }

        def resolve_acos_tier_percentage(key: str) -> float:
            pct_value = config.get(key, tier_percentage_defaults[key])
            # Safeguard: if someone passes an absolute ACOS (<=1) while target is very small,
            # allow opting out via `config['acos_tier_mode'] = 'absolute'`.
            mode = config.get('acos_tier_mode', 'percentage')
            if mode == 'absolute':
                return pct_value
            return self.target_acos * pct_value

        self.acos_tier_very_high = resolve_acos_tier_percentage('acos_tier_very_high')
        self.acos_tier_high = resolve_acos_tier_percentage('acos_tier_high')
        self.acos_tier_medium_high = resolve_acos_tier_percentage('acos_tier_medium_high')
        self.acos_tier_medium = resolve_acos_tier_percentage('acos_tier_medium')
        self.acos_tier_target = resolve_acos_tier_percentage('acos_tier_target')
        self.acos_tier_good = resolve_acos_tier_percentage('acos_tier_good')
        self.acos_tier_low = resolve_acos_tier_percentage('acos_tier_low')
        self.acos_tier_very_low = resolve_acos_tier_percentage('acos_tier_very_low')
        self.acos_tier_excellent = resolve_acos_tier_percentage('acos_tier_excellent')
        
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
        
        # Comprehensive Safety Veto Configuration (#19)
        self.enable_comprehensive_safety_veto = config.get('enable_comprehensive_safety_veto', True)
        self.spend_spike_veto_threshold = config.get('spend_spike_veto_threshold', 2.0)
        self.spend_spike_veto_lookback_days = config.get('spend_spike_veto_lookback_days', 3)
        self.spend_spike_veto_conversion_check = config.get('spend_spike_veto_conversion_check', True)
        self.account_daily_limit = config.get('account_daily_limit', 10000.0)
        self.account_daily_limit_action = config.get('account_daily_limit_action', 'pause')
        self.account_daily_limit_reduction_factor = config.get('account_daily_limit_reduction_factor', 0.5)
        
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
        self.strategy_id = config.get('strategy_id', 'ml_bid_optimizer_v1')
        self.policy_holdout_pct = config.get('learning_policy_holdout_pct', 0.1)
    
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
        entity_attributes = {
            'asin': entity_data.get('asin') or entity_data.get('product_asin'),
            'category': entity_data.get('category'),
            'price_tier': entity_data.get('price_tier', self.config.get('product_price_tier')),
            'fulfillment_type': entity_data.get('fulfillment_type'),
            'buy_box_share': entity_data.get('buy_box_share'),
            'competitor_density': entity_data.get('competitor_density')
        }
        proposals: List[AdjustmentProposal] = []
        
        # 1. TIME FRAME FILTERING: Filter performance data by specified lookback period
        filtered_performance_data = self._filter_performance_data_by_timeframe(
            performance_data, self.bid_optimization_lookback_days
        )
        
        if not filtered_performance_data:
            self.logger.debug(f"No performance data found for {entity_type} {entity_id} in last {self.bid_optimization_lookback_days} days")
            return None
        
        performance_snapshot = self._build_performance_snapshot(filtered_performance_data, entity_attributes)
        
        # 2. COMPREHENSIVE SAFETY VETO LAYER (#19): Check for catastrophic budget burns
        if self.enable_comprehensive_safety_veto:
            safety_veto_result = self._check_comprehensive_safety_veto(
                filtered_performance_data, entity_id, entity_type, entity_data
            )
            if safety_veto_result['veto']:
                self.logger.critical(
                    f"SAFETY VETO triggered for {entity_type} {entity_id}: {safety_veto_result['reason']}"
                )
                proposals.append(AdjustmentProposal(
                    source='safety_veto',
                    percentage=-safety_veto_result.get('reduction_factor', 0.5) if safety_veto_result.get('action') == 'reduce_bid' else 0.0,
                    priority='critical',
                    confidence=1.0,
                    veto=True,
                    reason=safety_veto_result['reason']
                ))
                # If pause action, return None immediately
                if safety_veto_result.get('action') == 'pause':
                    self.telemetry.increment('safety_veto_pause', labels={'entity_type': entity_type, 'reason': safety_veto_result.get('veto_type', 'unknown')})
                    return None
        
        # 2b. SPEND/CLICKS SAFEGUARD: Check for sudden spikes before making decisions
        safeguard_result = self._check_spend_clicks_safeguard(
            filtered_performance_data, current_bid, entity_id, entity_type
        )
        
        if safeguard_result['triggered']:
            self.logger.warning(
                f"Safeguard triggered for {entity_type} {entity_id}: {safeguard_result['reason']}"
            )
            if safeguard_result['action'] == 'reduce_bid':
                proposals.append(AdjustmentProposal(
                    source='safeguard_reduce',
                    percentage=-self.safeguard_bid_reduction_factor,
                    priority='critical',
                    confidence=1.0,
                    reason=safeguard_result['reason']
                ))
            elif safeguard_result['action'] == 'pause':
                self.logger.warning(f"Safeguard recommends pausing {entity_type} {entity_id}")
                proposals.append(AdjustmentProposal(
                    source='safeguard_pause',
                    percentage=0.0,
                    priority='critical',
                    confidence=1.0,
                    veto=True,
                    reason=safeguard_result['reason']
                ))
        
        # 3. NEW KEYWORD CHECK: Skip keywords <14 days old
        if self.enable_new_keyword_logic and entity_type == 'keyword':
            keyword_age = self._get_keyword_age(entity_id)
            if keyword_age is not None and keyword_age < self.new_keyword_age_days:
                self.logger.info(
                    f"Skipping new keyword: {entity_name} (age: {keyword_age} days) - "
                    f"must be {self.new_keyword_age_days}+ days old for bid adjustments"
                )
                proposals.append(AdjustmentProposal(
                    source='new_keyword_hold',
                    percentage=0.0,
                    priority='high',
                    confidence=1.0,
                    veto=True,
                    reason='Keyword younger than eligibility window'
                ))
        
        # 4. LOW DATA ZONE CHECK: Skip adjustments if low data (0% adjustment)
        low_data_result = self._check_low_data_zone(filtered_performance_data, entity_id, entity_type)
        if low_data_result.get('in_low_data_zone', False):
            self.logger.info(
                f"Low data zone detected for {entity_type} {entity_id}: {low_data_result['reason']} - "
                f"holding bid (0% adjustment)"
            )
            proposals.append(AdjustmentProposal(
                source='low_data_guard',
                percentage=0.0,
                priority='critical',
                confidence=1.0,
                veto=True,
                reason=low_data_result['reason']
            ))
            # Continue to collect veto for resolution (no immediate return)
        
        # 5. ACOS TREND COMPARISON: Compare current vs previous 14-day period
        trend_adjustment = 0.0
        if self.enable_acos_trend_comparison:
            trend_result = self._compare_acos_trend(performance_data, filtered_performance_data)
            if trend_result['should_skip']:
                self.logger.info(
                    f"Skipping bid adjustment for {entity_type} {entity_id}: "
                    f"ACOS declining ({trend_result['current_acos']:.2%} vs {trend_result['previous_acos']:.2%})"
                )
                proposals.append(AdjustmentProposal(
                    source='acos_trend_decline',
                    percentage=0.0,
                    priority='high',
                    confidence=1.0,
                    veto=True,
                    reason='ACOS trend declining beyond threshold'
                ))
            # Apply trend-based adjustments only if not vetoed
            # Apply trend-based adjustments only when not vetoed
            elif trend_result.get('trend_adjustment'):
                trend_adjustment = trend_result['trend_adjustment']
                self.logger.info(
                    f"ACOS trend adjustment for {entity_type} {entity_id}: "
                    f"{trend_result['trend']} ({trend_result['current_acos']:.2%} vs {trend_result['previous_acos']:.2%}) = {trend_adjustment:+.0%}"
                )
        
        # 6. SPEND-BASED NO SALE LOGIC: Now handled directly in _calculate_performance_adjustment
        # No separate check needed - the new logic integrates no-sale scenarios
        
        # Calculate performance-based adjustment (with new strategy matrix logic)
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
        
        # Combine adjustments via coordination engine (#7)
        coordination_inputs: List[AdjustmentProposal] = []
        coordination_inputs.append(AdjustmentProposal(
            source='performance',
            percentage=performance_adjustment,
            priority='high',
            confidence=self.weights['performance'],
            reason='ACOS/ROAS performance'
        ))
        if intelligence_adjustment != 0:
            coordination_inputs.append(AdjustmentProposal(
                source='intelligence',
                percentage=intelligence_adjustment,
                priority='medium',
                confidence=self.weights['intelligence'],
                reason='Intelligence signals'
            ))
        if seasonality_adjustment != 0:
            coordination_inputs.append(AdjustmentProposal(
                source='seasonality',
                percentage=seasonality_adjustment,
                priority='medium',
                confidence=self.weights['seasonality'],
                reason='Seasonality engine'
            ))
        if profit_adjustment != 0:
            coordination_inputs.append(AdjustmentProposal(
                source='profit',
                percentage=profit_adjustment,
                priority='medium',
                confidence=self.weights['profit'],
                reason='Profit safeguard'
            ))
        if trend_adjustment != 0:
            coordination_inputs.append(AdjustmentProposal(
                source='trend',
                percentage=trend_adjustment,
                priority='medium',
                confidence=0.5,
                reason='ACOS trend comparison'
            ))
        proposals.extend(coordination_inputs)

        resolution = self._resolve_adjustments(proposals)
        if not resolution['allowed']:
            self.logger.info(
                f"Bid adjustment vetoed for {entity_type} {entity_id}: {resolution['reason']}"
            )
            self.telemetry.increment(
                'bid_optimizer_veto',
                labels={'reason': (resolution.get('reason') or 'unknown'), 'entity_type': entity_type}
            )
            return None
        
        # Observability: Track recommendation generation (#21)
        self.telemetry.increment(
            'bid_optimizer_recommendations_generated',
            labels={'entity_type': entity_type}
        )
        total_adjustment = resolution['percentage']
        proposal_contributions = resolution.get('contributions', [])

        # Explicit A/B strategy assignment (#23) - prevents feedback loop leakage
        strategy_id, policy_variant = self._assign_policy_variant(entity_data)
        if policy_variant == 'control':
            total_adjustment *= 0.5  # dampen control variants for A/B holdout
            self.logger.debug(f"Control variant assigned to {entity_type} {entity_id} - reducing adjustment by 50%")
        
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
        
        # Apply bid constraints overrides (#24)
        new_bid, cap_metadata = self._apply_bid_caps(entity_data, new_bid)
        
        # Recalculate actual adjustment
        actual_adjustment = new_bid - current_bid
        adjustment_percentage = (actual_adjustment / current_bid * 100) if current_bid > 0 else 0
        
        # FIX #9: Use config min_bid_change_threshold consistently (0.05 means 5%)
        min_change_threshold_pct = decimal_to_percentage(self.config.get('min_bid_change_threshold', 0.05))
        if abs(adjustment_percentage) < min_change_threshold_pct:
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
            
            # Check if bid adjustment is allowed (FIX #5: Pass db_connector for DB lock check)
            try:
                re_entry_result = self.re_entry_controller.should_adjust_bid(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    current_bid=current_bid,
                    proposed_bid=new_bid,
                    last_change_date=last_change.get('change_date') if last_change and isinstance(last_change, dict) else None,
                    last_bid=last_change.get('new_bid') if last_change and isinstance(last_change, dict) else None,
                    acos_history=acos_history,
                    bid_change_history=bid_history,
                    db_connector=self.db  # FIX #5: Pass DB for persistent lock check
                )
            except Exception as e:
                self.logger.error(f"Error in re-entry control check for {entity_type} {entity_id}: {e}")
                # On error, allow the adjustment (fail open) but log the issue
                re_entry_result = type('obj', (object,), {'allowed': True, 'reason': 'Error in re-entry check, allowing adjustment'})()
            
            if not re_entry_result.allowed:
                self.logger.info(
                    f"Bid adjustment blocked for {entity_type} {entity_id}: {re_entry_result.reason}"
                )
                # Observability: Track re-entry control blocks (#21)
                self.telemetry.increment(
                    're_entry_control_blocked',
                    labels={'entity_type': entity_type, 'reason': re_entry_result.reason[:50]}
                )
                # Return None to skip this adjustment
                return None
            else:
                self.logger.debug(
                    f"Bid adjustment approved for {entity_type} {entity_id}: {re_entry_result.reason}"
                )
        
        # Build contributing factors from coordination engine
        contributing_factors = [
            f"{c['source']}: {c['percentage']:+.1%}"
            for c in proposal_contributions
            if abs(c['percentage']) > 0.02
        ]
        if not contributing_factors:
            contributing_factors.append("Minor blended adjustments")
        
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
            # FIX #4: Use float('inf') for ACOS when sales == 0 instead of 0
            current_acos = (total_spend / total_sales) if total_sales > 0 else float('inf')
            current_roas = (total_sales / total_spend) if total_spend > 0 else 0
            total_impressions = sum(float(record.get('impressions', 0)) for record in filtered_performance_data)
            total_clicks = sum(float(record.get('clicks', 0)) for record in filtered_performance_data)
            current_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # STEP 5: Predict success probability before making adjustment
        prob_success = 0.5  # Default
        ml_explanation = None  # FIX #29: Store explanation for later use
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
                if performance_snapshot:
                    current_metrics_for_pred.update(performance_snapshot)
                
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
                
                # FIX #18: Extract cluster features for hierarchical model
                cluster_features = None
                if entity_attributes:
                    cluster_features = {
                        'category': entity_attributes.get('category'),
                        'price_tier': entity_attributes.get('price_tier'),
                        'fulfillment': entity_attributes.get('fulfillment_type'),
                        'asin': entity_attributes.get('asin')
                    }
                
                # FIX #26: Pass performance history for time-series models
                performance_history = None
                if hasattr(self.model_trainer, 'time_series_trainer') and self.model_trainer.time_series_trainer:
                    seq_len = getattr(self.model_trainer.time_series_trainer, 'sequence_length', 14)
                    if len(filtered_performance_data) >= seq_len:
                        performance_history = filtered_performance_data[:seq_len]
                
                prediction_result = self.model_trainer.predict_success_probability(
                    current_metrics=current_metrics_for_pred,
                    proposed_adjustment=total_adjustment,
                    current_bid=current_bid,
                    entity_type=entity_type,
                    intelligence_signals=intelligence_summary if intelligence_summary else None,
                    cluster_features=cluster_features,  # FIX #18: Pass cluster features for hierarchical model
                    performance_history=performance_history  # FIX #26: Pass for time-series models
                )
                
                # Handle tuple return (probability, explanation) from updated predict_success_probability
                if isinstance(prediction_result, tuple):
                    prob_success, explanation = prediction_result
                    # FIX #29: Store explanation for later use in BidOptimization metadata
                    if explanation and explanation.get('status') == 'success':
                        ml_explanation = explanation
                else:
                    prob_success = prediction_result
                    ml_explanation = None
                
                # COLD START FIX: Handle warm-up mode (insufficient training data)
                if prob_success is None:
                    # Warm-up mode: Skip AI prediction gating, use math-based ACOS tiers only
                    self.logger.info(
                        f"Warm-up mode active for {entity_type} {entity_id}: "
                        f"Using math-based ACOS tiers (insufficient training data). "
                        f"Proceeding with calculated adjustment: {total_adjustment:.1%}"
                    )
                    # Continue with the math-based adjustment without AI gating
                else:
                    # FIX #3: Apply predictive gating with thresholds from checklist
                    # Use thresholds: <0.45 skip, 0.45-0.6 reduce 50%, 0.6-0.75 reduce 20%, else full
                    if prob_success < 0.45:
                        self.logger.info(
                            f"Skipping bid adjustment for {entity_type} {entity_id}: "
                            f"low success probability ({prob_success:.2%} < 0.45)"
                        )
                        return None
                    elif 0.45 <= prob_success < 0.6:
                        # Reduce adjustment by 50%
                        total_adjustment = total_adjustment * 0.5
                        self.logger.info(
                            f"Reducing adjustment 50% for {entity_type} {entity_id}: "
                            f"moderate success probability ({prob_success:.2%})"
                        )
                    elif 0.6 <= prob_success < 0.75:
                        # Reduce adjustment by 20%
                        total_adjustment = total_adjustment * 0.8
                        self.logger.info(
                            f"Reducing adjustment 20% for {entity_type} {entity_id}: "
                            f"good success probability ({prob_success:.2%})"
                        )
                    # else: prob_success >= 0.75, apply full adjustment
                
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
        
        # FIX #9: Use config min_bid_change_threshold consistently (0.05 means 5%)
        min_change_threshold_pct = decimal_to_percentage(self.config.get('min_bid_change_threshold', 0.05))
        if abs(adjustment_percentage) < min_change_threshold_pct:
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
        
        recommendation = BidOptimization(
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
                'ml_explanation': ml_explanation,  # FIX #29: Include SHAP explanation if available
                'signals_count': len(intelligence_signals),
                'predicted_success_probability': prob_success,
                'proposal_contributions': proposal_contributions,
                'strategy_id': strategy_id,
                'policy_variant': policy_variant,
                'bid_cap_metadata': cap_metadata,
                'entity_attributes': entity_attributes,
                'performance_snapshot': performance_snapshot
            }
        )
        
        # FIX #21: Record comprehensive metrics
        self.telemetry.increment(
            'bid_optimizer_recommendations',
            labels={'entity_type': entity_type, 'policy_variant': policy_variant}
        )
        try:
            self.telemetry.record_bid_change_magnitude(entity_type, adjustment_percentage)
        except Exception as e:
            self.logger.warning(f"Error recording bid change magnitude: {e}")
        
        return recommendation
    
    def _calculate_performance_adjustment(self, performance_data: List[Dict[str, Any]],
                                        low_data_result: Dict[str, Any] = None,
                                        entity_id: int = 0, entity_type: str = 'keyword') -> float:
        """
        Calculate bid adjustment based on performance metrics with new strategy matrix:
        - ACOS-based rank zones (A+, A, B, C, D, E)
        - Order-based bid adjustment scaling
        - No Sale scenarios (NS-1 through NS-6)
        """
        if not performance_data:
            return 0.0
        
        low_data_result = low_data_result or {'in_low_data_zone': False}
        
        # Calculate aggregated metrics
        total_cost = sum(float(record.get('cost', 0)) for record in performance_data)
        total_sales = sum(self._get_daily_sales(record) for record in performance_data)
        total_impressions = sum(float(record.get('impressions', 0)) for record in performance_data)
        total_clicks = sum(float(record.get('clicks', 0)) for record in performance_data)
        total_conversions = sum(int(record.get('attributed_conversions_7d', 0)) for record in performance_data)
        
        # Calculate current metrics
        current_acos = (total_cost / total_sales) if total_sales > 0 else float('inf')
        current_roas = (total_sales / total_cost) if total_cost > 0 else 0
        current_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # PRIORITY 1: Check for No Sale scenarios (NS-1 through NS-6)
        # These override ACOS-based logic when there are no sales
        if total_sales == 0:
            return self._handle_no_sale_scenarios(
                total_impressions, total_clicks, total_cost, entity_id, entity_type
            )
        
        # PRIORITY 2: ACOS-based rank zones with order-based scaling
        # Determine ACOS rank zone
        acos_rank = self._determine_acos_rank(current_acos)
        
        # Get bid adjustment multiplier based on rank and order count
        bid_multiplier = self._get_bid_multiplier_for_rank_and_orders(acos_rank, total_conversions)
        
        # Convert multiplier to adjustment percentage
        # Multiplier 1.15 = +15% adjustment, 0.85 = -15% adjustment
        adjustment = bid_multiplier - 1.0
        
        self.logger.debug(
            f"ACOS Rank {acos_rank}: ACOS={current_acos:.2%}, Orders={total_conversions}, "
            f"Multiplier={bid_multiplier:.2f}, Adjustment={adjustment:+.1%}"
        )
        
        # Apply low data zone limit
        if low_data_result.get('in_low_data_zone', False):
            adjustment = max(-self.low_data_zone_adjustment_limit, 
                           min(self.low_data_zone_adjustment_limit, adjustment))
            self.logger.debug(f"Low data zone: limiting adjustment to {self.low_data_zone_adjustment_limit:.0%}")
        
        # Cap adjustment to reasonable limits
        return max(-0.30, min(0.35, adjustment))
    
    def _handle_no_sale_scenarios(self, total_impressions: int, total_clicks: int, 
                                   total_spend: float, entity_id: int, entity_type: str) -> float:
        """
        Handle No Sale scenarios (NS-1 through NS-6) based on the strategy matrix
        
        Returns bid adjustment as a percentage (e.g., 0.15 for +15%, -0.30 for -30%)
        """
        # NS-1: No Clicks / No Activity (Impressions < 500)
        if total_impressions <= self.config.get('ns1_no_clicks_no_activity_impr_max', 500):
            multiplier = self.config.get('ns1_bid_adjustment', 1.15)
            adjustment = multiplier - 1.0
            self.logger.info(f"NS-1 No Clicks/No Activity: impressions={total_impressions}, adjustment={adjustment:+.1%}")
            return adjustment
        
        # NS-2: Low Data Zone (Spend < $5 OR Clicks < 10)
        if total_spend < self.config.get('ns2_low_data_zone_spend_max', 5.0) or \
           total_clicks < self.config.get('ns2_low_data_zone_clicks_max', 10):
            multiplier = self.config.get('ns2_bid_adjustment', 1.10)
            adjustment = multiplier - 1.0
            self.logger.info(f"NS-2 Low Data Zone: spend=${total_spend:.2f}, clicks={total_clicks}, adjustment={adjustment:+.1%}")
            return adjustment
        
        # NS-3: High Spend, Few Clicks, No Orders (Spend $5-$10, Clicks < 3)
        if (self.config.get('ns3_high_spend_few_clicks_spend_min', 5.0) <= total_spend < 
            self.config.get('ns3_high_spend_few_clicks_spend_max', 10.0)) and \
           total_clicks < self.config.get('ns3_high_spend_few_clicks_clicks_max', 3):
            multiplier = self.config.get('ns3_bid_adjustment', 1.00)
            adjustment = multiplier - 1.0
            self.logger.info(f"NS-3 High Spend Few Clicks: spend=${total_spend:.2f}, clicks={total_clicks}, adjustment={adjustment:+.1%}")
            return adjustment
        
        # NS-4: No Sales - Moderate Spend ($10-$15)
        if (self.config.get('ns4_no_sales_moderate_spend_min', 10.0) <= total_spend < 
            self.config.get('ns4_no_sales_moderate_spend_max', 15.0)):
            multiplier = self.config.get('ns4_bid_adjustment', 0.90)
            adjustment = multiplier - 1.0
            self.logger.info(f"NS-4 No Sales Moderate Spend: spend=${total_spend:.2f}, adjustment={adjustment:+.1%}")
            return adjustment
        
        # NS-5: No Sales - High Spend ($15-$30)
        if (self.config.get('ns5_no_sales_high_spend_min', 15.0) <= total_spend < 
            self.config.get('ns5_no_sales_high_spend_max', 30.0)):
            multiplier = self.config.get('ns5_bid_adjustment', 0.80)
            adjustment = multiplier - 1.0
            self.logger.info(f"NS-5 No Sales High Spend: spend=${total_spend:.2f}, adjustment={adjustment:+.1%}")
            return adjustment
        
        # NS-6: No Sales - Heavy Spend ($30+)
        if total_spend >= self.config.get('ns6_no_sales_heavy_spend_min', 30.0):
            multiplier = self.config.get('ns6_bid_adjustment', 0.70)
            adjustment = multiplier - 1.0
            self.logger.info(f"NS-6 No Sales Heavy Spend: spend=${total_spend:.2f}, adjustment={adjustment:+.1%}")
            return adjustment
        
        # Default: No specific scenario matched, return 0
        return 0.0
    
    def _determine_acos_rank(self, current_acos: float) -> str:
        """
        Determine ACOS rank zone (A+, A, B, C, D, E) based on current ACOS
        
        Returns rank as string: 'A+', 'A', 'B', 'C', 'D', or 'E'
        """
        if current_acos == float('inf'):
            return 'E'  # No sales = worst rank
        
        # E: Severe Overspend (6.75% - 7.5%+)
        if current_acos >= self.config.get('acos_tier_e_severe_overspend_min', 0.0675):
            return 'E'
        
        # D: Moderately High ACOS (6% - 6.75%)
        if current_acos >= self.config.get('acos_tier_d_moderately_high_min', 0.06):
            return 'D'
        
        # C: Slightly Above Target (5% - 6%)
        if current_acos >= self.config.get('acos_tier_c_slightly_above_min', 0.05):
            return 'C'
        
        # B: Optimal Zone (3.5% - 5%)
        if current_acos >= self.config.get('acos_tier_b_optimal_min', 0.035):
            return 'B'
        
        # A: High Efficiency (2.25% - 3.5%)
        if current_acos >= self.config.get('acos_tier_a_high_efficiency_min', 0.0225):
            return 'A'
        
        # A+: Ultra Profitable (0% - 2.25%)
        return 'A+'
    
    def _get_bid_multiplier_for_rank_and_orders(self, acos_rank: str, order_count: int) -> float:
        """
        Get bid adjustment multiplier based on ACOS rank and order count
        
        Returns multiplier (e.g., 1.15 for +15%, 0.85 for -15%)
        """
        # Rank E: Severe Overspend - always reduce
        if acos_rank == 'E':
            return self.config.get('bid_adjustment_e_order_1', 0.75)
        
        # Rank D: Moderately High - reduce
        if acos_rank == 'D':
            return self.config.get('bid_adjustment_d_order_1', 0.85)
        
        # Rank C: Slightly Above Target - slight reduction
        if acos_rank == 'C':
            return self.config.get('bid_adjustment_c_order_1', 0.95)
        
        # Rank B: Optimal Zone - scale based on orders
        if acos_rank == 'B':
            if order_count == 1:
                return self.config.get('bid_adjustment_b_order_1', 1.00)
            elif order_count == 2:
                return self.config.get('bid_adjustment_b_order_2', 1.05)
            elif order_count >= 4:
                return self.config.get('bid_adjustment_b_order_4', 1.10)
            else:
                return 1.00
        
        # Rank A: High Efficiency - scale based on orders
        if acos_rank == 'A':
            if order_count == 1:
                return self.config.get('bid_adjustment_a_order_1', 1.10)
            elif order_count == 2:
                return self.config.get('bid_adjustment_a_order_2', 1.15)
            elif order_count >= 4:
                return self.config.get('bid_adjustment_a_order_4', 1.25)
            else:
                return 1.10
        
        # Rank A+: Ultra Profitable - aggressive scaling based on orders
        if acos_rank == 'A+':
            if order_count == 1:
                return self.config.get('bid_adjustment_aplus_order_1', 1.15)
            elif order_count == 2:
                return self.config.get('bid_adjustment_aplus_order_2', 1.25)
            elif order_count >= 4:
                return self.config.get('bid_adjustment_aplus_order_4', 1.30)
            else:
                return 1.15
        
        # Default: no adjustment
        return 1.0
    
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
        """
        Apply exponential smoothing to metrics
        
        FIX #6: Handle NaNs and ensure stable smoothing
        """
        import math
        
        if not sorted_data:
            return {'acos': 0, 'roas': 0, 'ctr': 0}
        
        # Initialize with first record
        first_record = sorted_data[0]
        total_cost = float(first_record.get('cost', 0) or 0)
        total_sales = self._get_daily_sales(first_record) or 0
        total_impressions = float(first_record.get('impressions', 0) or 0)
        total_clicks = float(first_record.get('clicks', 0) or 0)
        
        # Apply exponential smoothing to subsequent records
        alpha = self.exponential_smoothing_alpha
        for record in sorted_data[1:]:
            cost = float(record.get('cost', 0) or 0)
            sales = self._get_daily_sales(record) or 0
            impressions = float(record.get('impressions', 0) or 0)
            clicks = float(record.get('clicks', 0) or 0)
            
            # FIX #6: Skip NaN/inf values
            if not (math.isnan(cost) or math.isinf(cost)):
                total_cost = alpha * cost + (1 - alpha) * total_cost
            if not (math.isnan(sales) or math.isinf(sales)):
                total_sales = alpha * sales + (1 - alpha) * total_sales
            if not (math.isnan(impressions) or math.isinf(impressions)):
                total_impressions = alpha * impressions + (1 - alpha) * total_impressions
            if not (math.isnan(clicks) or math.isinf(clicks)):
                total_clicks = alpha * clicks + (1 - alpha) * total_clicks
        
        # FIX #4 & #6: Use float('inf') for ACOS when sales == 0, handle NaNs
        if math.isnan(total_cost) or math.isnan(total_sales):
            acos = float('inf')
        else:
            acos = (total_cost / total_sales) if total_sales > 0 else float('inf')
        
        if math.isnan(total_cost) or math.isnan(total_sales):
            roas = 0
        else:
            roas = (total_sales / total_cost) if total_cost > 0 else 0
        
        if math.isnan(total_impressions) or math.isnan(total_clicks):
            ctr = 0
        else:
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # FIX #6: Ensure no NaNs in return
        return {
            'acos': acos if not math.isnan(acos) else float('inf'),
            'roas': roas if not math.isnan(roas) else 0,
            'ctr': ctr if not math.isnan(ctr) else 0
        }
    
    def _weighted_moving_average(self, sorted_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Apply weighted moving average (more weight to recent data)
        
        FIX #6: Handle NaNs and ensure stable smoothing
        """
        import math
        
        window_size = min(self.moving_average_window, len(sorted_data))
        window_data = sorted_data[:window_size]
        
        # Calculate weights (more recent = higher weight)
        weights = []
        total_weight = 0
        for i in range(window_size):
            weight = window_size - i  # More recent = higher weight
            weights.append(weight)
            total_weight += weight
        
        # Calculate weighted averages (FIX #6: Handle NaNs)
        weighted_cost = sum(float(r.get('cost', 0) or 0) * weights[i] for i, r in enumerate(window_data))
        weighted_sales = sum((self._get_daily_sales(r) or 0) * weights[i] for i, r in enumerate(window_data))
        weighted_impressions = sum(float(r.get('impressions', 0) or 0) * weights[i] for i, r in enumerate(window_data))
        weighted_clicks = sum(float(r.get('clicks', 0) or 0) * weights[i] for i, r in enumerate(window_data))
        
        total_cost = weighted_cost / total_weight if total_weight > 0 else 0
        total_sales = weighted_sales / total_weight if total_weight > 0 else 0
        total_impressions = weighted_impressions / total_weight if total_weight > 0 else 0
        total_clicks = weighted_clicks / total_weight if total_weight > 0 else 0
        
        # FIX #4 & #6: Use float('inf') for ACOS when sales == 0, handle NaNs
        if math.isnan(total_cost) or math.isnan(total_sales):
            acos = float('inf')
        else:
            acos = (total_cost / total_sales) if total_sales > 0 else float('inf')
        
        if math.isnan(total_cost) or math.isnan(total_sales):
            roas = 0
        else:
            roas = (total_sales / total_cost) if total_cost > 0 else 0
        
        if math.isnan(total_impressions) or math.isnan(total_clicks):
            ctr = 0
        else:
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # FIX #6: Ensure no NaNs in return
        return {
            'acos': acos if not math.isnan(acos) else float('inf'),
            'roas': roas if not math.isnan(roas) else 0,
            'ctr': ctr if not math.isnan(ctr) else 0
        }
    
    def _simple_moving_average(self, sorted_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Apply simple moving average
        
        FIX #6: Handle NaNs and ensure stable smoothing
        """
        import math
        
        window_size = min(self.moving_average_window, len(sorted_data))
        window_data = sorted_data[:window_size]
        
        # FIX #6: Handle NaNs in input data
        total_cost = sum(float(r.get('cost', 0) or 0) for r in window_data)
        total_sales = sum(self._get_daily_sales(r) or 0 for r in window_data)
        total_impressions = sum(float(r.get('impressions', 0) or 0) for r in window_data)
        total_clicks = sum(float(r.get('clicks', 0) or 0) for r in window_data)
        
        # FIX #4 & #6: Use float('inf') for ACOS when sales == 0, handle NaNs
        if math.isnan(total_cost) or math.isnan(total_sales):
            acos = float('inf')
        else:
            acos = (total_cost / total_sales) if total_sales > 0 else float('inf')
        
        if math.isnan(total_cost) or math.isnan(total_sales):
            roas = 0
        else:
            roas = (total_sales / total_cost) if total_cost > 0 else 0
        
        if math.isnan(total_impressions) or math.isnan(total_clicks):
            ctr = 0
        else:
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # FIX #6: Ensure no NaNs in return
        return {
            'acos': acos if not math.isnan(acos) else float('inf'),
            'roas': roas if not math.isnan(roas) else 0,
            'ctr': ctr if not math.isnan(ctr) else 0
        }
    
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
        # FIX #4: Use float('inf') for ACOS when sales == 0
        current_acos = (current_cost / current_sales) if current_sales > 0 else float('inf')
        result['current_acos'] = current_acos
        
        if current_acos == 0 or current_acos == float('inf'):
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
        # FIX #4: Use float('inf') for ACOS when sales == 0
        previous_acos = (previous_cost / previous_sales) if previous_sales > 0 else float('inf')
        result['previous_acos'] = previous_acos
        
        if previous_acos == 0 or previous_acos == float('inf'):
            return result
        
        # Compare trends
        acos_change = (current_acos - previous_acos) / previous_acos if previous_acos > 0 else 0
        
        if acos_change >= self.acos_trend_decline_threshold:
            # ACOS ↑ >30% (getting worse) - apply bid multiplier 0.90 (-10%)
            result['should_skip'] = self.skip_on_acos_decline
            result['trend'] = 'declining'
            # Use bid multiplier from config (default 0.90 = -10%)
            bid_multiplier = self.config.get('acos_trend_decline_bid_multiplier', 0.90)
            result['trend_adjustment'] = bid_multiplier - 1.0  # Convert to adjustment
            self.logger.info(
                f"ACOS trend declining: {current_acos:.2%} vs {previous_acos:.2%} "
                f"({acos_change:+.1%} change) = bid multiplier {bid_multiplier:.2f}"
            )
        elif acos_change <= -self.acos_trend_improvement_threshold:
            # ACOS ↓ >30% (improving) - apply bid multiplier 1.10 (+10%)
            result['trend'] = 'improving'
            # Use bid multiplier from config (default 1.10 = +10%)
            bid_multiplier = self.config.get('acos_trend_improvement_bid_multiplier', 1.10)
            result['trend_adjustment'] = bid_multiplier - 1.0  # Convert to adjustment
            self.logger.info(
                f"ACOS trend improving: {current_acos:.2%} vs {previous_acos:.2%} "
                f"({acos_change:+.1%} change) = bid multiplier {bid_multiplier:.2f}"
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
    
    def _check_comprehensive_safety_veto(self, performance_data: List[Dict[str, Any]],
                                       entity_id: int, entity_type: str,
                                       entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive safety-first veto layer (#19)
        
        Prevents catastrophic budget burns with multiple safety checks:
        1. Spend spike with unchanged conversions (force reduce bid 50%)
        2. Account daily limit exceeded (pause campaign or reduce bids)
        
        Args:
            performance_data: Performance data for the entity
            entity_id: Entity ID
            entity_type: Entity type
            entity_data: Full entity data including campaign_id
            
        Returns:
            Dictionary with veto decision: {'veto': bool, 'reason': str, 'action': str, 'veto_type': str}
        """
        result = {
            'veto': False,
            'reason': '',
            'action': None,
            'veto_type': None,
            'reduction_factor': 0.5
        }
        
        if not performance_data or len(performance_data) < self.spend_spike_veto_lookback_days + 1:
            return result
        
        # Sort by date (most recent first)
        sorted_data = sorted(
            performance_data,
            key=lambda x: self._get_record_date(x),
            reverse=True
        )
        
        # Check 1: Spend spike with unchanged conversions (last 3 days)
        if self.spend_spike_veto_conversion_check:
            recent_days = sorted_data[:self.spend_spike_veto_lookback_days]
            previous_days = sorted_data[self.spend_spike_veto_lookback_days:self.spend_spike_veto_lookback_days * 2]
            
            if len(recent_days) >= self.spend_spike_veto_lookback_days and len(previous_days) >= self.spend_spike_veto_lookback_days:
                recent_spend = sum(float(r.get('cost', 0)) for r in recent_days)
                previous_spend = sum(float(r.get('cost', 0)) for r in previous_days)
                recent_conversions = sum(int(r.get('attributed_conversions_7d', 0)) for r in recent_days)
                previous_conversions = sum(int(r.get('attributed_conversions_7d', 0)) for r in previous_days)
                
                if previous_spend > 0 and recent_spend >= self.min_spend_for_safeguard:
                    spend_increase_ratio = recent_spend / previous_spend
                    
                    # Check if spend increased > threshold AND conversions unchanged
                    if (spend_increase_ratio >= self.spend_spike_veto_threshold and 
                        recent_conversions <= previous_conversions):
                        result['veto'] = True
                        result['reason'] = (
                            f"Spend increased {spend_increase_ratio:.0%} in last {self.spend_spike_veto_lookback_days} days "
                            f"(${recent_spend:.2f} vs ${previous_spend:.2f}) with conversions unchanged "
                            f"({recent_conversions} vs {previous_conversions}) - forcing bid reduction"
                        )
                        result['action'] = 'reduce_bid'
                        result['veto_type'] = 'spend_spike_no_conversions'
                        result['reduction_factor'] = 0.5  # Force reduce bid by 50%
                        return result
        
        # Check 2: Account daily limit exceeded
        if self.account_daily_limit > 0 and self.db:
            try:
                # Get total account spend for today
                today = datetime.now().date()
                account_spend_query = """
                SELECT COALESCE(SUM(cost), 0) as total_spend
                FROM (
                    SELECT cost FROM campaign_performance WHERE report_date = %s
                    UNION ALL
                    SELECT cost FROM ad_group_performance WHERE report_date = %s
                    UNION ALL
                    SELECT cost FROM keyword_performance WHERE report_date = %s
                ) combined
                """
                
                with self.db.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(account_spend_query, (today, today, today))
                        row = cursor.fetchone()
                        total_account_spend = float(row[0]) if row and row[0] else 0.0
                
                if total_account_spend >= self.account_daily_limit:
                    result['veto'] = True
                    result['reason'] = (
                        f"Account daily limit exceeded: ${total_account_spend:.2f} >= ${self.account_daily_limit:.2f} - "
                        f"{self.account_daily_limit_action} required"
                    )
                    result['action'] = self.account_daily_limit_action
                    result['veto_type'] = 'account_daily_limit'
                    result['reduction_factor'] = self.account_daily_limit_reduction_factor
                    
                    # If entity is a campaign and action is pause, mark for pausing
                    if entity_type == 'campaign' and self.account_daily_limit_action == 'pause':
                        self.logger.critical(
                            f"Campaign {entity_id} should be PAUSED due to account daily limit"
                        )
                    return result
            except Exception as e:
                self.logger.warning(f"Error checking account daily limit: {e}")
        
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
    
    def _build_performance_snapshot(self, performance_data: List[Dict[str, Any]],
                                    entity_attributes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Collect extended performance metrics for ML feature engineering (#12/#13)."""
        if not performance_data:
            return None
        
        sorted_records = sorted(
            performance_data,
            key=lambda x: self._get_record_date(x),
            reverse=True
        )
        
        total_cost = sum(float(r.get('cost', 0)) for r in sorted_records)
        total_sales = sum(self._get_daily_sales(r) for r in sorted_records)
        total_impressions = sum(float(r.get('impressions', 0)) for r in sorted_records)
        total_clicks = sum(float(r.get('clicks', 0)) for r in sorted_records)
        total_conversions = sum(int(r.get('attributed_conversions_7d', 0)) for r in sorted_records)
        
        snapshot = {
            'acos': (total_cost / total_sales) if total_sales > 0 else float('inf'),
            'roas': (total_sales / total_cost) if total_cost > 0 else 0,
            'ctr': (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
            'spend': total_cost,
            'sales': total_sales,
            'conversions': total_conversions,
            'impressions': total_impressions,
            'clicks': total_clicks,
            'seasonal_month': datetime.now().month,
            'seasonal_day_of_week': datetime.now().weekday(),
            'entity_category': entity_attributes.get('category'),
            'entity_price_tier': entity_attributes.get('price_tier'),
            'entity_fulfillment': entity_attributes.get('fulfillment_type'),
            'buy_box_share': entity_attributes.get('buy_box_share'),
            'competitor_density': entity_attributes.get('competitor_density')
        }
        
        metric_series = []
        for record in sorted_records:
            cost = float(record.get('cost', 0))
            sales = self._get_daily_sales(record)
            impressions = float(record.get('impressions', 0))
            clicks = float(record.get('clicks', 0))
            conversions = int(record.get('attributed_conversions_7d', 0))
            metric_series.append({
                'acos': (cost / sales) if sales > 0 else None,
                'roas': (sales / cost) if cost > 0 else None,
                'ctr': (clicks / impressions * 100) if impressions > 0 else None,
                'conversions': conversions,
                'report_date': self._get_record_date(record)
            })
        
        def _rolling(metric: str, window: int, stat: str = 'mean') -> float:
            values = [
                entry[metric] for entry in metric_series[:window]
                if entry[metric] is not None
            ]
            if not values:
                return 0.0
            if stat == 'mean':
                return float(sum(values) / len(values))
            if len(values) < 2:
                return 0.0
            return float(statistics.pstdev(values))
        
        for metric in ('acos', 'roas', 'ctr'):
            snapshot[f'rolling_{metric}_mean_7d'] = _rolling(metric, 7, 'mean')
            snapshot[f'rolling_{metric}_std_7d'] = _rolling(metric, 7, 'std')
            snapshot[f'rolling_{metric}_mean_14d'] = _rolling(metric, 14, 'mean')
            snapshot[f'rolling_{metric}_std_14d'] = _rolling(metric, 14, 'std')
            snapshot[f'rolling_{metric}_mean_30d'] = _rolling(metric, 30, 'mean')
            snapshot[f'rolling_{metric}_std_30d'] = _rolling(metric, 30, 'std')
        
        # Trend flags based on most recent vs prior windows
        if len(metric_series) >= 14:
            recent_acos = _rolling('acos', 7, 'mean')
            prior_acos = _rolling('acos', 14, 'mean')
            snapshot['acos_trend_direction'] = 'improving' if prior_acos and recent_acos < prior_acos else 'declining'
            recent_ctr = _rolling('ctr', 7, 'mean')
            prior_ctr = _rolling('ctr', 14, 'mean')
            snapshot['ctr_trend_direction'] = 'improving' if prior_ctr and recent_ctr > prior_ctr else 'declining'
        else:
            snapshot['acos_trend_direction'] = 'stable'
            snapshot['ctr_trend_direction'] = 'stable'
        
        # Days since last conversion
        days_since_conversion = None
        today = datetime.now()
        for entry in metric_series:
            if entry['conversions'] > 0 and entry['report_date']:
                days_since_conversion = (today - entry['report_date']).days
                break
        snapshot['days_since_last_conversion'] = days_since_conversion
        
        return snapshot
    
    def _resolve_adjustments(self, proposals: List[AdjustmentProposal]) -> Dict[str, Any]:
        """Coordinate proposals from multiple subsystems (Checklist #7)."""
        if not proposals:
            return {'allowed': True, 'percentage': 0.0, 'contributions': []}
        
        vetoes = [p for p in proposals if p.veto]
        if vetoes:
            reason = vetoes[0].reason or f"Veto triggered by {vetoes[0].source}"
            return {
                'allowed': False,
                'reason': reason,
                'veto_sources': [v.source for v in vetoes],
                'contributions': []
            }
        
        contributions = []
        weighted_sum = 0.0
        weight_total = 0.0
        for proposal in proposals:
            if proposal.percentage == 0:
                continue
            weight = self._priority_weight(proposal.priority) * max(0.05, proposal.confidence)
            weighted_sum += proposal.percentage * weight
            weight_total += weight
            contributions.append({
                'source': proposal.source,
                'percentage': proposal.percentage,
                'weight': weight,
                'reason': proposal.reason
            })
        
        percentage = weighted_sum / weight_total if weight_total else 0.0
        
        return {
            'allowed': True,
            'percentage': percentage,
            'contributions': contributions
        }
    
    def _priority_weight(self, priority: str) -> float:
        mapping = {
            'critical': 1.0,
            'high': 0.8,
            'medium': 0.5,
            'low': 0.3
        }
        return mapping.get(priority, 0.3)
    
    def _assign_policy_variant(self, entity_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Explicit A/B strategy assignment (#23)
        
        Prevents feedback loop leakage by:
        1. Using deterministic hash-based assignment (consistent per entity)
        2. Randomizing strategy assignment based on entity_id
        3. Tracking strategy_id in all outcomes for offline evaluation
        
        Args:
            entity_data: Entity data including entity_id
            
        Returns:
            Tuple of (strategy_id, policy_variant)
        """
        import hashlib
        
        # Get entity ID for deterministic assignment
        entity_id = entity_data.get('entity_id') or entity_data.get('keyword_id') or entity_data.get('ad_group_id') or entity_data.get('campaign_id', 0)
        
        # Use hash-based deterministic assignment (consistent per entity)
        # This ensures same entity always gets same variant, but distribution is random
        entity_hash = int(hashlib.md5(f"{entity_id}_{self.strategy_id}".encode()).hexdigest(), 16)
        assignment_ratio = (entity_hash % 100) / 100.0
        
        # Assign based on holdout percentage
        if assignment_ratio < self.policy_holdout_pct:
            policy_variant = 'control'
            strategy_id = f"{self.strategy_id}_control"
        else:
            policy_variant = 'treatment'
            strategy_id = self.strategy_id
        
        # Observability: Track strategy assignment (#23)
        if self.telemetry:
            self.telemetry.increment(
                'strategy_assignment',
                labels={'strategy_id': strategy_id, 'policy_variant': policy_variant}
            )
        
        return strategy_id, policy_variant
    
    def _apply_bid_caps(self, entity_data: Dict[str, Any], proposed_bid: float) -> Tuple[float, Dict[str, Any]]:
        """Apply per-ASIN/category caps from config or DB (#24)."""
        cap_metadata = {
            'cap_applied': False,
            'floor_applied': False,
            'sources': []
        }
        caps_to_consider: List[Dict[str, Any]] = []
        asin = entity_data.get('asin') or entity_data.get('product_asin')
        category = entity_data.get('category')
        
        if asin:
            config_cap = self.config.get('product_bid_caps', {}).get(str(asin))
            if config_cap:
                caps_to_consider.append({'bid_cap': config_cap, 'source': f'config_product_{asin}'})
            if self.db and hasattr(self.db, 'get_bid_constraint'):
                db_cap = self.db.get_bid_constraint('asin', str(asin))
                if db_cap:
                    db_cap['source'] = f'db_product_{asin}'
                    caps_to_consider.append(db_cap)
        if category:
            config_cap = self.config.get('category_bid_caps', {}).get(str(category))
            if config_cap:
                caps_to_consider.append({'bid_cap': config_cap, 'source': f'config_category_{category}'})
            if self.db and hasattr(self.db, 'get_bid_constraint'):
                db_cap = self.db.get_bid_constraint('category', str(category))
                if db_cap:
                    db_cap['source'] = f'db_category_{category}'
                    caps_to_consider.append(db_cap)
        
        adjusted_bid = proposed_bid
        for cap in caps_to_consider:
            if cap.get('bid_cap') is not None:
                adjusted_bid = min(adjusted_bid, float(cap['bid_cap']))
                cap_metadata['cap_applied'] = cap_metadata['cap_applied'] or (adjusted_bid != proposed_bid)
                cap_metadata['sources'].append(cap.get('source'))
            if cap.get('bid_floor') is not None:
                adjusted_bid = max(adjusted_bid, float(cap['bid_floor']))
                cap_metadata['floor_applied'] = cap_metadata['floor_applied'] or (adjusted_bid != proposed_bid)
                if cap.get('source') not in cap_metadata['sources']:
                    cap_metadata['sources'].append(cap.get('source'))
        
        return adjusted_bid, cap_metadata
    
    def log_bid_change(self, bid_optimization: BidOptimization, 
                      current_metrics: Dict[str, Any],
                      performance_data: Optional[List[Dict[str, Any]]] = None,
                      performance_snapshot: Optional[Dict[str, Any]] = None) -> bool:
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
        if performance_snapshot:
            performance_before = performance_snapshot
        elif performance_data:
            filtered_data = self._filter_performance_data_by_timeframe(
                performance_data, self.bid_optimization_lookback_days
            )
            if filtered_data:
                performance_before = self._build_performance_snapshot(
                    filtered_data,
                    bid_optimization.metadata.get('entity_attributes', {})
                )
        
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
        
        # FIX #10 & #11: Make log_bid_change atomic and prevent race conditions
        # Use DB transaction to ensure both save_bid_change and create_bid_lock succeed together
        try:
            with self.db.get_connection() as conn:
                try:
                    # Start transaction
                    with conn.cursor() as cursor:
                        # FIX #11: Check for existing lock first to prevent race condition
                        check_lock_query = """
                        SELECT id FROM bid_adjustment_locks
                        WHERE entity_type = %s AND entity_id = %s
                        AND locked_until > CURRENT_TIMESTAMP
                        FOR UPDATE
                        """
                        cursor.execute(check_lock_query, (bid_optimization.entity_type, bid_optimization.entity_id))
                        existing_lock = cursor.fetchone()
                        
                        if existing_lock:
                            self.logger.warning(
                                f"Bid change blocked: {bid_optimization.entity_type} {bid_optimization.entity_id} "
                                f"already has active lock"
                            )
                            conn.rollback()
                            return False
                        
                        # Save bid change
                        save_query = """
                        INSERT INTO bid_change_history (
                            entity_type, entity_id, entity_name, change_date,
                            old_bid, new_bid, change_amount, change_percentage,
                            reason, triggered_by, acos_at_change, roas_at_change,
                            ctr_at_change, conversions_at_change, metadata,
                            performance_before, performance_after, outcome_score, outcome_label, evaluated_at
                        ) VALUES (
                            %(entity_type)s, %(entity_id)s, %(entity_name)s, %(change_date)s,
                            %(old_bid)s, %(new_bid)s, %(change_amount)s, %(change_percentage)s,
                            %(reason)s, %(triggered_by)s, %(acos_at_change)s, %(roas_at_change)s,
                            %(ctr_at_change)s, %(conversions_at_change)s, %(metadata)s,
                            %(performance_before)s, %(performance_after)s, %(outcome_score)s, %(outcome_label)s, %(evaluated_at)s
                        )
                        RETURNING id
                        """
                        import json as _json
                        cursor.execute(save_query, {
                            **change_record,
                            'performance_before': _json.dumps(change_record.get('performance_before')) if change_record.get('performance_before') else None,
                            'performance_after': change_record.get('performance_after'),
                            'outcome_score': change_record.get('outcome_score'),
                            'outcome_label': change_record.get('outcome_label'),
                            'evaluated_at': change_record.get('evaluated_at')
                        })
                        change_id_row = cursor.fetchone()
                        if not change_id_row:
                            self.logger.error("Bid change insert returned no ID inside atomic logger")
                            conn.rollback()
                            return False
                        change_id = change_id_row[0]
                        
                        # Create bid lock atomically
                        cooldown_days = self.config.get('bid_change_cooldown_days', 3)
                        locked_until = datetime.now() + timedelta(days=cooldown_days)
                        
                        lock_query = """
                        INSERT INTO bid_adjustment_locks (
                            entity_type, entity_id, locked_until, lock_reason, last_change_id
                        ) VALUES (
                            %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (entity_type, entity_id) DO UPDATE SET
                            locked_until = EXCLUDED.locked_until,
                            lock_reason = EXCLUDED.lock_reason,
                            last_change_id = EXCLUDED.last_change_id
                        WHERE bid_adjustment_locks.locked_until < EXCLUDED.locked_until
                        """
                        cursor.execute(lock_query, (
                            bid_optimization.entity_type,
                            bid_optimization.entity_id,
                            locked_until,
                            f"Cooldown after bid adjustment ({bid_optimization.adjustment_percentage:+.1f}%)",
                            change_id
                        ))
                        
                        # Commit transaction
                        conn.commit()
                        self.logger.info(f"Bid change logged atomically: ID {change_id}")
                        return True
                        
                except Exception as e:
                    conn.rollback()
                    self.logger.error(f"Error in atomic bid change logging: {e}")
                    return False
        except Exception as e:
            self.logger.error(f"Error getting DB connection for bid change: {e}")
            return False


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
        
        # FIX #4: Use float('inf') for ACOS when sales == 0
        acos = (total_cost / total_sales) if total_sales > 0 else float('inf')
        roas = (total_sales / total_cost) if total_cost > 0 else 0
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
        
        # FIX #4: Use float('inf') for ACOS when sales == 0
        acos = (total_cost / total_sales) if total_sales > 0 else float('inf')
        roas = (total_sales / total_cost) if total_cost > 0 else 0
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
        
        # FIX #4: Use float('inf') for ACOS when sales == 0
        acos = (total_cost / total_sales) if total_sales > 0 else float('inf')
        roas = (total_sales / total_cost) if total_cost > 0 else 0
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

