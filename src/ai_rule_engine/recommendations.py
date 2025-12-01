"""
Recommendation engine for AI Rule Engine
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime
from .rules import RuleResult
from .config import RuleConfig


@dataclass
class Recommendation:
    """A recommendation for bid or budget adjustment"""
    entity_type: str  # 'campaign', 'ad_group', 'keyword'
    entity_id: int
    entity_name: str
    adjustment_type: str  # 'bid', 'budget', 'negative_keyword'
    current_value: float
    recommended_value: float
    adjustment_amount: float
    adjustment_percentage: float
    priority: str  # 'low', 'medium', 'high', 'critical'
    confidence: float
    reason: str
    rules_triggered: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    strategy_id: Optional[str] = None


class RecommendationEngine:
    """Engine for generating and prioritizing recommendations"""
    
    def __init__(self, config: RuleConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def generate_recommendations(self, rule_results: List[RuleResult], 
                               entity_info: Dict[int, Dict[str, Any]]) -> List[Recommendation]:
        """
        Generate recommendations from rule results
        
        Args:
            rule_results: List of triggered rule results
            entity_info: Dictionary mapping entity IDs to their information
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Group rule results by entity
        entity_results = {}
        for result in rule_results:
            entity_id = result.entity_id
            if entity_id not in entity_results:
                entity_results[entity_id] = []
            entity_results[entity_id].append(result)
        
        # Generate recommendations for each entity
        for entity_id, results in entity_results.items():
            entity_data = entity_info.get(entity_id, {})
            entity_recommendations = self._generate_entity_recommendations(
                entity_id, results, entity_data
            )
            recommendations.extend(entity_recommendations)
        
        # Sort by priority and confidence
        recommendations.sort(key=lambda r: (self._get_priority_score(r.priority), -r.confidence))
        
        return recommendations
    
    def _generate_entity_recommendations(self, entity_id: int, 
                                       rule_results: List[RuleResult],
                                       entity_info: Dict[str, Any]) -> List[Recommendation]:
        """Generate recommendations for a specific entity"""
        recommendations = []
        
        # Separate results by adjustment type
        bid_results = [r for r in rule_results if r.adjustment_type == 'bid']
        budget_results = [r for r in rule_results if r.adjustment_type == 'budget']
        negative_keyword_results = [r for r in rule_results if r.adjustment_type == 'negative_keyword']
        
        # Generate bid recommendation
        if bid_results:
            bid_rec = self._create_bid_recommendation(entity_id, bid_results, entity_info)
            if bid_rec:
                recommendations.append(bid_rec)
        
        # Generate budget recommendation
        if budget_results:
            budget_rec = self._create_budget_recommendation(entity_id, budget_results, entity_info)
            if budget_rec:
                recommendations.append(budget_rec)
        
        # Generate negative keyword recommendations
        for result in negative_keyword_results:
            neg_kw_rec = self._create_negative_keyword_recommendation(entity_id, result, entity_info)
            if neg_kw_rec:
                recommendations.append(neg_kw_rec)
        
        return recommendations
    
    def _create_bid_recommendation(self, entity_id: int, 
                                 bid_results: List[RuleResult],
                                 entity_info: Dict[str, Any]) -> Optional[Recommendation]:
        """Create a bid recommendation from multiple bid rule results"""
        if not bid_results:
            return None
        
        # Calculate weighted average adjustment based on confidence and severity
        total_weight = 0
        weighted_adjustment = 0
        triggered_rules = []
        reasons = []
        
        for result in bid_results:
            weight = result.confidence * self._get_severity_weight(result.severity)
            total_weight += weight
            weighted_adjustment += result.recommended_adjustment * weight
            triggered_rules.append(result.rule_name)
            reasons.append(result.reason)
        
        if total_weight == 0:
            return None
        
        # Calculate final adjustment
        final_adjustment = weighted_adjustment / total_weight
        
        # Apply bid limits - convert decimal to float
        current_bid = float(entity_info.get('bid', entity_info.get('default_bid', 0)))
        new_bid = current_bid + final_adjustment
        
        # Apply bid floor and cap
        if new_bid < self.config.bid_floor:
            final_adjustment = self.config.bid_floor - current_bid
            new_bid = self.config.bid_floor
        elif new_bid > self.config.bid_cap:
            final_adjustment = self.config.bid_cap - current_bid
            new_bid = self.config.bid_cap
        
        # Calculate adjustment percentage
        adjustment_percentage = (final_adjustment / current_bid * 100) if current_bid > 0 else 0
        
        # Determine priority based on highest severity
        max_severity = max(result.severity for result in bid_results)
        priority = self._map_severity_to_priority(max_severity)
        
        # Calculate overall confidence
        avg_confidence = sum(result.confidence for result in bid_results) / len(bid_results)
        
        # Combine reasons
        combined_reason = "; ".join(reasons)
        
        return Recommendation(
            entity_type=entity_info.get('entity_type', 'unknown'),
            entity_id=entity_id,
            entity_name=entity_info.get('name', f"Entity {entity_id}"),
            adjustment_type='bid',
            current_value=current_bid,
            recommended_value=new_bid,
            adjustment_amount=final_adjustment,
            adjustment_percentage=adjustment_percentage,
            priority=priority,
            confidence=avg_confidence,
            reason=combined_reason,
            rules_triggered=triggered_rules,
            metadata={
                'original_adjustment': weighted_adjustment / total_weight,
                'bid_floor_applied': new_bid == self.config.bid_floor,
                'bid_cap_applied': new_bid == self.config.bid_cap,
                'rule_count': len(bid_results)
            },
            created_at=datetime.now()
        )
    
    def _create_budget_recommendation(self, entity_id: int,
                                    budget_results: List[RuleResult],
                                    entity_info: Dict[str, Any]) -> Optional[Recommendation]:
        """Create a budget recommendation from budget rule results"""
        if not budget_results:
            return None
        
        # Use the first budget result (there should typically be only one)
        result = budget_results[0]
        
        current_budget = float(entity_info.get('budget_amount', 0))
        new_budget = current_budget + result.recommended_adjustment
        
        # Apply budget limits
        if new_budget < self.config.budget_min_daily:
            result.recommended_adjustment = self.config.budget_min_daily - current_budget
            new_budget = self.config.budget_min_daily
        elif new_budget > self.config.budget_max_daily:
            result.recommended_adjustment = self.config.budget_max_daily - current_budget
            new_budget = self.config.budget_max_daily
        
        # Calculate adjustment percentage
        adjustment_percentage = (result.recommended_adjustment / current_budget * 100) if current_budget > 0 else 0
        
        return Recommendation(
            entity_type=entity_info.get('entity_type', 'unknown'),
            entity_id=entity_id,
            entity_name=entity_info.get('name', f"Entity {entity_id}"),
            adjustment_type='budget',
            current_value=current_budget,
            recommended_value=new_budget,
            adjustment_amount=result.recommended_adjustment,
            adjustment_percentage=adjustment_percentage,
            priority=self._map_severity_to_priority(result.severity),
            confidence=result.confidence,
            reason=result.reason,
            rules_triggered=[result.rule_name],
            metadata={
                'budget_min_applied': new_budget == self.config.budget_min_daily,
                'budget_max_applied': new_budget == self.config.budget_max_daily
            },
            created_at=datetime.now()
        )
    
    def _create_negative_keyword_recommendation(self, entity_id: int,
                                             result: RuleResult,
                                             entity_info: Dict[str, Any]) -> Optional[Recommendation]:
        """Create a negative keyword recommendation"""
        keyword_text = result.metadata.get('keyword_text', '')
        match_type = result.metadata.get('match_type', '')
        
        if not keyword_text:
            return None
        
        return Recommendation(
            entity_type=entity_info.get('entity_type', 'unknown'),
            entity_id=entity_id,
            entity_name=f"Keyword: {keyword_text}",
            adjustment_type='negative_keyword',
            current_value=0,  # No current value for negative keywords
            recommended_value=0,
            adjustment_amount=0,
            adjustment_percentage=0,
            priority=self._map_severity_to_priority(result.severity),
            confidence=result.confidence,
            reason=result.reason,
            rules_triggered=[result.rule_name],
            metadata={
                'keyword_text': keyword_text,
                'match_type': match_type,
                'ctr': result.current_value,
                'impressions': result.metadata.get('total_impressions', 0)
            },
            created_at=datetime.now()
        )
    
    def _get_severity_weight(self, severity: str) -> float:
        """Get weight multiplier for severity level"""
        weights = {
            'critical': 4.0,
            'high': 3.0,
            'medium': 2.0,
            'low': 1.0
        }
        return weights.get(severity, 1.0)
    
    def _map_severity_to_priority(self, severity: str) -> str:
        """Map severity to priority level"""
        mapping = {
            'critical': 'critical',
            'high': 'high',
            'medium': 'medium',
            'low': 'low'
        }
        return mapping.get(severity, 'low')
    
    def _get_priority_score(self, priority: str) -> int:
        """Get numeric score for priority sorting"""
        scores = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        return scores.get(priority, 1)
    
    def filter_recommendations(self, recommendations: List[Recommendation],
                             max_recommendations: int = 50,
                             min_confidence: float = 0.3) -> List[Recommendation]:
        """Filter recommendations based on criteria"""
        filtered = []
        
        for rec in recommendations:
            # Apply confidence filter
            if rec.confidence < min_confidence:
                continue
            
            # Apply maximum recommendations limit
            if len(filtered) >= max_recommendations:
                break
            
            filtered.append(rec)
        
        return filtered
    
    def group_recommendations_by_entity(self, recommendations: List[Recommendation]) -> Dict[int, List[Recommendation]]:
        """Group recommendations by entity ID"""
        grouped = {}
        for rec in recommendations:
            if rec.entity_id not in grouped:
                grouped[rec.entity_id] = []
            grouped[rec.entity_id].append(rec)
        return grouped
    
    def generate_summary(self, recommendations: List[Recommendation]) -> Dict[str, Any]:
        """Generate summary statistics for recommendations"""
        if not recommendations:
            return {
                'total_recommendations': 0,
                'by_type': {},
                'by_priority': {},
                'by_entity_type': {},
                'total_adjustment_value': 0
            }
        
        summary = {
            'total_recommendations': len(recommendations),
            'by_type': {},
            'by_priority': {},
            'by_entity_type': {},
            'total_adjustment_value': 0
        }
        
        for rec in recommendations:
            # Count by type
            rec_type = rec.adjustment_type
            summary['by_type'][rec_type] = summary['by_type'].get(rec_type, 0) + 1
            
            # Count by priority
            priority = rec.priority
            summary['by_priority'][priority] = summary['by_priority'].get(priority, 0) + 1
            
            # Count by entity type
            entity_type = rec.entity_type
            summary['by_entity_type'][entity_type] = summary['by_entity_type'].get(entity_type, 0) + 1
            
            # Sum adjustment values (for bid and budget adjustments)
            if rec.adjustment_type in ['bid', 'budget']:
                summary['total_adjustment_value'] += abs(rec.adjustment_amount)
        
        return summary
