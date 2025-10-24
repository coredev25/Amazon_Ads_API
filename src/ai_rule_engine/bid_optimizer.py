"""
Bid Optimization Engine
Integrates all intelligence engines for intelligent bid adjustments
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass


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
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Bid limits
        self.bid_floor = config.get('bid_floor', 0.01)
        self.bid_cap = config.get('bid_cap', 10.0)
        self.max_adjustment = config.get('bid_max_adjustment', 0.5)
        
        # Target metrics
        self.target_acos = config.get('acos_target', 0.30)
        self.target_roas = config.get('roas_target', 4.0)
        self.target_ctr = config.get('ctr_target', 2.0)
        
        # Adjustment weights for different factors
        self.weights = {
            'performance': config.get('weight_performance', 0.40),
            'intelligence': config.get('weight_intelligence', 0.30),
            'seasonality': config.get('weight_seasonality', 0.15),
            'profit': config.get('weight_profit', 0.15)
        }
    
    def calculate_optimal_bid(self, entity_data: Dict[str, Any],
                              performance_data: List[Dict[str, Any]],
                              intelligence_signals: List[Any]) -> Optional[BidOptimization]:
        """
        Calculate optimal bid based on multiple factors
        
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
        
        # Calculate performance-based adjustment
        performance_adjustment = self._calculate_performance_adjustment(performance_data)
        
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
                'signals_count': len(intelligence_signals)
            }
        )
    
    def _calculate_performance_adjustment(self, performance_data: List[Dict[str, Any]]) -> float:
        """Calculate bid adjustment based on performance metrics"""
        # Aggregate performance
        total_cost = sum(float(record.get('cost', 0)) for record in performance_data)
        total_sales = sum(float(record.get('attributed_sales_7d', 0)) for record in performance_data)
        total_impressions = sum(float(record.get('impressions', 0)) for record in performance_data)
        total_clicks = sum(float(record.get('clicks', 0)) for record in performance_data)
        
        if total_cost == 0 or total_sales == 0:
            return 0.0
        
        # Calculate metrics
        current_acos = total_cost / total_sales if total_sales > 0 else 0
        current_roas = total_sales / total_cost if total_cost > 0 else 0
        current_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        adjustment = 0.0
        
        # ACOS-based adjustment
        if current_acos > 0:
            acos_deviation = (current_acos - self.target_acos) / self.target_acos
            # If ACOS too high, reduce bid (negative adjustment)
            # If ACOS too low, increase bid (positive adjustment)
            adjustment -= acos_deviation * 0.15
        
        # ROAS-based adjustment
        if current_roas > 0:
            roas_deviation = (current_roas - self.target_roas) / self.target_roas
            # If ROAS too low, reduce bid (negative adjustment)
            # If ROAS too high, increase bid (positive adjustment)
            adjustment += roas_deviation * 0.15
        
        # CTR-based adjustment
        if current_ctr > 0:
            ctr_deviation = (current_ctr - self.target_ctr) / self.target_ctr
            # If CTR too low, might need to increase bid for visibility
            adjustment += ctr_deviation * 0.10
        
        # Cap adjustment
        return max(-0.30, min(0.30, adjustment))
    
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


class BudgetOptimizationEngine:
    """
    Advanced budget optimization for campaigns
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.min_daily_budget = config.get('budget_min_daily', 1.0)
        self.max_daily_budget = config.get('budget_max_daily', 1000.0)
        self.target_roas = config.get('roas_target', 4.0)
        self.aggressive_scale_roas = config.get('aggressive_scale_roas', 5.0)
    
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
        
        # Calculate performance metrics
        total_cost = sum(float(record.get('cost', 0)) for record in performance_data)
        total_sales = sum(float(record.get('attributed_sales_7d', 0)) for record in performance_data)
        
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
            'confidence': min(1.0, len(performance_data) / 14.0),
            'metadata': {
                'current_roas': current_roas,
                'target_roas': self.target_roas,
                'budget_utilization': budget_utilization,
                'total_spend': total_cost
            }
        }

