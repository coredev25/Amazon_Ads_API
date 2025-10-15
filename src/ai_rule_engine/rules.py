"""
Rule implementations for AI Rule Engine
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta


@dataclass
class RuleResult:
    """Result of a rule evaluation"""
    rule_name: str
    entity_type: str  # 'campaign', 'ad_group', 'keyword'
    entity_id: int
    triggered: bool
    severity: str  # 'low', 'medium', 'high', 'critical'
    current_value: float
    target_value: float
    recommended_adjustment: float
    adjustment_type: str  # 'bid', 'budget', 'negative_keyword'
    reason: str
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any]


class BaseRule(ABC):
    """Base class for all rules"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def evaluate(self, performance_data: List[Dict[str, Any]], 
                entity_info: Dict[str, Any]) -> Optional[RuleResult]:
        """
        Evaluate rule against performance data
        
        Args:
            performance_data: List of performance records
            entity_info: Entity information (campaign, ad_group, keyword)
            
        Returns:
            RuleResult if rule is triggered, None otherwise
        """
        pass
    
    def calculate_trend(self, values: List[float], days: int = 7) -> float:
        """Calculate trend slope for given values over time"""
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression slope
        n = len(values)
        x = list(range(n))
        y = values
        
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def calculate_average(self, values: List[float]) -> float:
        """Calculate average of values, excluding zeros"""
        non_zero_values = [v for v in values if v > 0]
        return sum(non_zero_values) / len(non_zero_values) if non_zero_values else 0.0


class ACOSRule(BaseRule):
    """Rule for ACOS (Advertising Cost of Sales) optimization"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.target_acos = config.get('acos_target', 0.30)
        self.tolerance = config.get('acos_tolerance', 0.05)
        self.adjustment_factor = config.get('acos_bid_adjustment_factor', 0.1)
        self.min_conversions = config.get('min_conversions', 1)
    
    def evaluate(self, performance_data: List[Dict[str, Any]], 
                entity_info: Dict[str, Any]) -> Optional[RuleResult]:
        """Evaluate ACOS rule"""
        if not performance_data:
            return None
        
        # Calculate current ACOS - convert decimal to float
        total_cost = sum(float(record.get('cost', 0)) for record in performance_data)
        total_sales = sum(float(record.get('attributed_sales_7d', 0)) for record in performance_data)
        total_conversions = sum(float(record.get('attributed_conversions_7d', 0)) for record in performance_data)
        
        if total_sales == 0 or total_conversions < self.min_conversions:
            return None
        
        current_acos = total_cost / total_sales if total_sales > 0 else 0
        
        # Check if ACOS is outside tolerance
        acos_deviation = abs(current_acos - self.target_acos)
        
        if acos_deviation <= self.tolerance:
            return None
        
        # Determine adjustment direction and severity
        if current_acos > self.target_acos + self.tolerance:
            # ACOS too high - reduce bid
            adjustment_multiplier = -self.adjustment_factor
            severity = self._get_severity(acos_deviation, self.tolerance)
            reason = f"ACOS {current_acos:.3f} exceeds target {self.target_acos:.3f} by {acos_deviation:.3f}"
        else:
            # ACOS too low - increase bid
            adjustment_multiplier = self.adjustment_factor
            severity = 'low'  # Low severity for increasing bids
            reason = f"ACOS {current_acos:.3f} below target {self.target_acos:.3f} by {acos_deviation:.3f}"
        
        # Calculate recommended bid adjustment - convert decimal to float
        current_bid = float(entity_info.get('bid', entity_info.get('default_bid', 0)))
        recommended_adjustment = current_bid * adjustment_multiplier
        
        # Calculate confidence based on data quality
        confidence = min(1.0, len(performance_data) / 7.0)  # More data = higher confidence
        
        return RuleResult(
            rule_name="ACOS_RULE",
            entity_type=entity_info.get('entity_type', 'unknown'),
            entity_id=entity_info.get('id', 0),
            triggered=True,
            severity=severity,
            current_value=current_acos,
            target_value=self.target_acos,
            recommended_adjustment=recommended_adjustment,
            adjustment_type='bid',
            reason=reason,
            confidence=confidence,
            metadata={
                'total_cost': total_cost,
                'total_sales': total_sales,
                'total_conversions': total_conversions,
                'acos_deviation': acos_deviation
            }
        )
    
    def _get_severity(self, deviation: float, tolerance: float) -> str:
        """Determine severity based on deviation from target"""
        ratio = deviation / tolerance
        if ratio >= 3.0:
            return 'critical'
        elif ratio >= 2.0:
            return 'high'
        elif ratio >= 1.5:
            return 'medium'
        else:
            return 'low'


class ROASRule(BaseRule):
    """Rule for ROAS (Return on Ad Spend) optimization"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.target_roas = config.get('roas_target', 4.0)
        self.tolerance = config.get('roas_tolerance', 0.5)
        self.adjustment_factor = config.get('roas_bid_adjustment_factor', 0.15)
        self.min_conversions = config.get('min_conversions', 1)
    
    def evaluate(self, performance_data: List[Dict[str, Any]], 
                entity_info: Dict[str, Any]) -> Optional[RuleResult]:
        """Evaluate ROAS rule"""
        if not performance_data:
            return None
        
        # Calculate current ROAS - convert decimal to float
        total_cost = sum(float(record.get('cost', 0)) for record in performance_data)
        total_sales = sum(float(record.get('attributed_sales_7d', 0)) for record in performance_data)
        total_conversions = sum(float(record.get('attributed_conversions_7d', 0)) for record in performance_data)
        
        if total_cost == 0 or total_conversions < self.min_conversions:
            return None
        
        current_roas = total_sales / total_cost if total_cost > 0 else 0
        
        # Check if ROAS is outside tolerance
        roas_deviation = abs(current_roas - self.target_roas)
        
        if roas_deviation <= self.tolerance:
            return None
        
        # Determine adjustment direction and severity
        if current_roas < self.target_roas - self.tolerance:
            # ROAS too low - reduce bid
            adjustment_multiplier = -self.adjustment_factor
            severity = self._get_severity(roas_deviation, self.tolerance)
            reason = f"ROAS {current_roas:.2f} below target {self.target_roas:.2f} by {roas_deviation:.2f}"
        else:
            # ROAS too high - increase bid
            adjustment_multiplier = self.adjustment_factor
            severity = 'low'  # Low severity for increasing bids
            reason = f"ROAS {current_roas:.2f} above target {self.target_roas:.2f} by {roas_deviation:.2f}"
        
        # Calculate recommended bid adjustment - convert decimal to float
        current_bid = float(entity_info.get('bid', entity_info.get('default_bid', 0)))
        recommended_adjustment = current_bid * adjustment_multiplier
        
        # Calculate confidence based on data quality
        confidence = min(1.0, len(performance_data) / 7.0)
        
        return RuleResult(
            rule_name="ROAS_RULE",
            entity_type=entity_info.get('entity_type', 'unknown'),
            entity_id=entity_info.get('id', 0),
            triggered=True,
            severity=severity,
            current_value=current_roas,
            target_value=self.target_roas,
            recommended_adjustment=recommended_adjustment,
            adjustment_type='bid',
            reason=reason,
            confidence=confidence,
            metadata={
                'total_cost': total_cost,
                'total_sales': total_sales,
                'total_conversions': total_conversions,
                'roas_deviation': roas_deviation
            }
        )
    
    def _get_severity(self, deviation: float, tolerance: float) -> str:
        """Determine severity based on deviation from target"""
        ratio = deviation / tolerance
        if ratio >= 3.0:
            return 'critical'
        elif ratio >= 2.0:
            return 'high'
        elif ratio >= 1.5:
            return 'medium'
        else:
            return 'low'


class CTRRule(BaseRule):
    """Rule for CTR (Click-Through Rate) optimization"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.minimum_ctr = config.get('ctr_minimum', 0.5)
        self.target_ctr = config.get('ctr_target', 2.0)
        self.adjustment_factor = config.get('ctr_bid_adjustment_factor', 0.2)
        self.min_impressions = config.get('min_impressions', 100)
    
    def evaluate(self, performance_data: List[Dict[str, Any]], 
                entity_info: Dict[str, Any]) -> Optional[RuleResult]:
        """Evaluate CTR rule"""
        if not performance_data:
            return None
        
        # Calculate current CTR - convert decimal to float
        total_impressions = sum(float(record.get('impressions', 0)) for record in performance_data)
        total_clicks = sum(float(record.get('clicks', 0)) for record in performance_data)
        
        if total_impressions < self.min_impressions:
            return None
        
        current_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # Check if CTR is below minimum threshold
        if current_ctr >= self.minimum_ctr:
            return None
        
        # Determine adjustment direction and severity
        ctr_ratio = current_ctr / self.minimum_ctr
        adjustment_multiplier = self.adjustment_factor
        
        if ctr_ratio < 0.5:
            # Very low CTR - more aggressive adjustment
            adjustment_multiplier *= 1.5
            severity = 'high'
        elif ctr_ratio < 0.7:
            severity = 'medium'
        else:
            severity = 'low'
        
        reason = f"CTR {current_ctr:.2f}% below minimum {self.minimum_ctr:.2f}% (ratio: {ctr_ratio:.2f})"
        
        # Calculate recommended bid adjustment - convert decimal to float
        current_bid = float(entity_info.get('bid', entity_info.get('default_bid', 0)))
        recommended_adjustment = current_bid * adjustment_multiplier
        
        # Calculate confidence based on data quality
        confidence = min(1.0, total_impressions / 1000.0)  # More impressions = higher confidence
        
        return RuleResult(
            rule_name="CTR_RULE",
            entity_type=entity_info.get('entity_type', 'unknown'),
            entity_id=entity_info.get('id', 0),
            triggered=True,
            severity=severity,
            current_value=current_ctr,
            target_value=self.minimum_ctr,
            recommended_adjustment=recommended_adjustment,
            adjustment_type='bid',
            reason=reason,
            confidence=confidence,
            metadata={
                'total_impressions': total_impressions,
                'total_clicks': total_clicks,
                'ctr_ratio': ctr_ratio
            }
        )


class NegativeKeywordRule(BaseRule):
    """Rule for identifying negative keyword candidates"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.ctr_threshold = config.get('negative_keyword_ctr_threshold', 0.1)
        self.impression_threshold = config.get('negative_keyword_impression_threshold', 1000)
        self.min_impressions = config.get('min_impressions', 100)
    
    def evaluate(self, performance_data: List[Dict[str, Any]], 
                entity_info: Dict[str, Any]) -> Optional[RuleResult]:
        """Evaluate negative keyword rule"""
        if not performance_data:
            return None
        
        # Calculate current CTR - convert decimal to float
        total_impressions = sum(float(record.get('impressions', 0)) for record in performance_data)
        total_clicks = sum(float(record.get('clicks', 0)) for record in performance_data)
        
        if total_impressions < self.impression_threshold:
            return None
        
        current_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # Check if CTR is below negative keyword threshold
        if current_ctr >= self.ctr_threshold:
            return None
        
        # Determine severity based on CTR
        ctr_ratio = current_ctr / self.ctr_threshold
        if ctr_ratio < 0.3:
            severity = 'high'
        elif ctr_ratio < 0.6:
            severity = 'medium'
        else:
            severity = 'low'
        
        reason = f"CTR {current_ctr:.2f}% below negative keyword threshold {self.ctr_threshold:.2f}%"
        
        # Calculate confidence based on data quality
        confidence = min(1.0, total_impressions / 2000.0)  # More impressions = higher confidence
        
        return RuleResult(
            rule_name="NEGATIVE_KEYWORD_RULE",
            entity_type=entity_info.get('entity_type', 'unknown'),
            entity_id=entity_info.get('id', 0),
            triggered=True,
            severity=severity,
            current_value=current_ctr,
            target_value=self.ctr_threshold,
            recommended_adjustment=0.0,  # No bid adjustment for negative keywords
            adjustment_type='negative_keyword',
            reason=reason,
            confidence=confidence,
            metadata={
                'total_impressions': total_impressions,
                'total_clicks': total_clicks,
                'ctr_ratio': ctr_ratio,
                'keyword_text': entity_info.get('keyword_text', ''),
                'match_type': entity_info.get('match_type', '')
            }
        )


class BudgetRule(BaseRule):
    """Rule for budget optimization based on performance"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.budget_adjustment_factor = config.get('budget_adjustment_factor', 0.2)
        self.min_daily_budget = config.get('budget_min_daily', 1.0)
        self.max_daily_budget = config.get('budget_max_daily', 1000.0)
        self.min_conversions = config.get('min_conversions', 1)
    
    def evaluate(self, performance_data: List[Dict[str, Any]], 
                entity_info: Dict[str, Any]) -> Optional[RuleResult]:
        """Evaluate budget rule"""
        if not performance_data:
            return None
        
        # Calculate performance metrics - convert decimal to float
        total_cost = sum(float(record.get('cost', 0)) for record in performance_data)
        total_sales = sum(float(record.get('attributed_sales_7d', 0)) for record in performance_data)
        total_conversions = sum(float(record.get('attributed_conversions_7d', 0)) for record in performance_data)
        
        if total_conversions < self.min_conversions:
            return None
        
        current_roas = total_sales / total_cost if total_cost > 0 else 0
        current_budget = float(entity_info.get('budget_amount', 0))
        
        # Determine budget adjustment based on ROAS
        if current_roas > 3.0:  # High ROAS - increase budget
            adjustment_multiplier = self.budget_adjustment_factor
            severity = 'low'
            reason = f"High ROAS {current_roas:.2f} - recommend budget increase"
        elif current_roas < 1.5:  # Low ROAS - decrease budget
            adjustment_multiplier = -self.budget_adjustment_factor
            severity = 'medium'
            reason = f"Low ROAS {current_roas:.2f} - recommend budget decrease"
        else:
            return None  # ROAS in acceptable range
        
        # Calculate recommended budget adjustment
        recommended_adjustment = current_budget * adjustment_multiplier
        new_budget = current_budget + recommended_adjustment
        
        # Apply budget limits
        if new_budget < self.min_daily_budget:
            recommended_adjustment = self.min_daily_budget - current_budget
            reason += f" (capped at minimum ${self.min_daily_budget})"
        elif new_budget > self.max_daily_budget:
            recommended_adjustment = self.max_daily_budget - current_budget
            reason += f" (capped at maximum ${self.max_daily_budget})"
        
        # Calculate confidence based on data quality
        confidence = min(1.0, len(performance_data) / 7.0)
        
        return RuleResult(
            rule_name="BUDGET_RULE",
            entity_type=entity_info.get('entity_type', 'unknown'),
            entity_id=entity_info.get('id', 0),
            triggered=True,
            severity=severity,
            current_value=current_roas,
            target_value=3.0 if adjustment_multiplier > 0 else 1.5,
            recommended_adjustment=recommended_adjustment,
            adjustment_type='budget',
            reason=reason,
            confidence=confidence,
            metadata={
                'total_cost': total_cost,
                'total_sales': total_sales,
                'total_conversions': total_conversions,
                'current_budget': current_budget,
                'new_budget': current_budget + recommended_adjustment
            }
        )
