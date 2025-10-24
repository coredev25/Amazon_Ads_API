"""
Feedback & Learning Loop
Implements machine learning components for continuous improvement
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import statistics
from collections import defaultdict


@dataclass
class PerformanceOutcome:
    """Tracks outcome of a recommendation"""
    recommendation_id: str
    entity_type: str
    entity_id: int
    adjustment_type: str
    recommended_value: float
    applied_value: float
    before_metrics: Dict[str, float]
    after_metrics: Dict[str, float]
    outcome: str  # 'success', 'failure', 'neutral'
    improvement_percentage: float
    timestamp: datetime


class LearningLoop:
    """
    Tracks recommendation outcomes and adjusts strategies
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Storage for outcomes
        self.outcomes_history: List[PerformanceOutcome] = []
        
        # Learning parameters
        self.success_threshold = config.get('learning_success_threshold', 0.10)  # 10% improvement
        self.failure_threshold = config.get('learning_failure_threshold', -0.05)  # -5% decline
        self.min_evaluation_days = config.get('learning_evaluation_days', 7)
    
    def track_recommendation(self, recommendation: Dict[str, Any],
                            entity_id: int, entity_type: str) -> str:
        """
        Track a recommendation for future outcome evaluation
        
        Returns:
            recommendation_id for tracking
        """
        recommendation_id = f"{entity_type}_{entity_id}_{datetime.now().timestamp()}"
        
        # Store recommendation for tracking
        tracking_data = {
            'recommendation_id': recommendation_id,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'adjustment_type': recommendation.get('adjustment_type', 'unknown'),
            'recommended_value': recommendation.get('recommended_value', 0),
            'current_value': recommendation.get('current_value', 0),
            'timestamp': datetime.now().isoformat(),
            'applied': False
        }
        
        self.logger.info(f"Tracking recommendation {recommendation_id}")
        return recommendation_id
    
    def record_outcome(self, recommendation_id: str,
                      before_metrics: Dict[str, float],
                      after_metrics: Dict[str, float],
                      applied_value: float) -> PerformanceOutcome:
        """
        Record the outcome of a recommendation
        
        Args:
            recommendation_id: ID of the tracked recommendation
            before_metrics: Metrics before the change
            after_metrics: Metrics after the change
            applied_value: Actual value that was applied
            
        Returns:
            PerformanceOutcome object
        """
        # Parse recommendation ID
        parts = recommendation_id.split('_')
        entity_type = parts[0] if len(parts) > 0 else 'unknown'
        entity_id = int(parts[1]) if len(parts) > 1 else 0
        
        # Calculate improvement
        improvement = self._calculate_improvement(before_metrics, after_metrics)
        
        # Determine outcome
        if improvement >= self.success_threshold:
            outcome = 'success'
        elif improvement <= self.failure_threshold:
            outcome = 'failure'
        else:
            outcome = 'neutral'
        
        # Create outcome record
        outcome_record = PerformanceOutcome(
            recommendation_id=recommendation_id,
            entity_type=entity_type,
            entity_id=entity_id,
            adjustment_type='bid',  # Default
            recommended_value=0.0,  # Would be loaded from tracking
            applied_value=applied_value,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            outcome=outcome,
            improvement_percentage=improvement * 100,
            timestamp=datetime.now()
        )
        
        # Store outcome
        self.outcomes_history.append(outcome_record)
        
        self.logger.info(f"Recorded outcome for {recommendation_id}: {outcome} ({improvement*100:.1f}% improvement)")
        
        return outcome_record
    
    def _calculate_improvement(self, before_metrics: Dict[str, float],
                               after_metrics: Dict[str, float]) -> float:
        """
        Calculate overall improvement based on multiple metrics
        
        Prioritizes ROAS and ACOS improvements
        """
        improvements = []
        
        # ROAS improvement (higher is better)
        if 'roas' in before_metrics and 'roas' in after_metrics:
            if before_metrics['roas'] > 0:
                roas_improvement = (after_metrics['roas'] - before_metrics['roas']) / before_metrics['roas']
                improvements.append(('roas', roas_improvement, 0.40))  # 40% weight
        
        # ACOS improvement (lower is better)
        if 'acos' in before_metrics and 'acos' in after_metrics:
            if before_metrics['acos'] > 0:
                acos_improvement = -(after_metrics['acos'] - before_metrics['acos']) / before_metrics['acos']
                improvements.append(('acos', acos_improvement, 0.40))  # 40% weight
        
        # CTR improvement (higher is better)
        if 'ctr' in before_metrics and 'ctr' in after_metrics:
            if before_metrics['ctr'] > 0:
                ctr_improvement = (after_metrics['ctr'] - before_metrics['ctr']) / before_metrics['ctr']
                improvements.append(('ctr', ctr_improvement, 0.20))  # 20% weight
        
        # Calculate weighted average
        if not improvements:
            return 0.0
        
        total_weight = sum(weight for _, _, weight in improvements)
        weighted_improvement = sum(imp * weight for _, imp, weight in improvements) / total_weight
        
        return weighted_improvement
    
    def analyze_performance_trends(self, entity_type: Optional[str] = None,
                                   days: int = 30) -> Dict[str, Any]:
        """
        Analyze performance trends of recommendations
        
        Args:
            entity_type: Filter by entity type (optional)
            days: Number of days to analyze
            
        Returns:
            Analysis results
        """
        # Filter outcomes
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_outcomes = [
            o for o in self.outcomes_history
            if o.timestamp >= cutoff_date and (entity_type is None or o.entity_type == entity_type)
        ]
        
        if not filtered_outcomes:
            return {
                'total_outcomes': 0,
                'success_rate': 0.0,
                'average_improvement': 0.0,
                'recommendations': []
            }
        
        # Calculate statistics
        total = len(filtered_outcomes)
        successes = sum(1 for o in filtered_outcomes if o.outcome == 'success')
        failures = sum(1 for o in filtered_outcomes if o.outcome == 'failure')
        neutrals = sum(1 for o in filtered_outcomes if o.outcome == 'neutral')
        
        success_rate = successes / total if total > 0 else 0
        
        improvements = [o.improvement_percentage for o in filtered_outcomes]
        average_improvement = statistics.mean(improvements) if improvements else 0
        
        return {
            'total_outcomes': total,
            'successes': successes,
            'failures': failures,
            'neutrals': neutrals,
            'success_rate': success_rate,
            'average_improvement': average_improvement,
            'median_improvement': statistics.median(improvements) if improvements else 0,
            'best_improvement': max(improvements) if improvements else 0,
            'worst_improvement': min(improvements) if improvements else 0,
            'recommendations': self._generate_learning_recommendations(filtered_outcomes)
        }
    
    def _generate_learning_recommendations(self, outcomes: List[PerformanceOutcome]) -> List[str]:
        """Generate recommendations based on learning"""
        recommendations = []
        
        if not outcomes:
            return ["Insufficient data for learning recommendations"]
        
        # Analyze success patterns
        successes = [o for o in outcomes if o.outcome == 'success']
        failures = [o for o in outcomes if o.outcome == 'failure']
        
        success_rate = len(successes) / len(outcomes) if outcomes else 0
        
        if success_rate < 0.5:
            recommendations.append("Success rate below 50% - consider reviewing recommendation thresholds")
        elif success_rate > 0.7:
            recommendations.append(f"Strong success rate ({success_rate:.1%}) - current strategy is effective")
        
        # Analyze adjustment magnitudes
        if successes:
            success_adjustments = [abs(o.applied_value - o.recommended_value) for o in successes 
                                  if o.recommended_value != 0]
            if success_adjustments:
                avg_success_adj = statistics.mean(success_adjustments)
                recommendations.append(f"Successful adjustments average magnitude: {avg_success_adj:.2f}")
        
        # Entity-type specific insights
        entity_performance = defaultdict(list)
        for outcome in outcomes:
            entity_performance[outcome.entity_type].append(outcome.outcome)
        
        for entity_type, outcome_list in entity_performance.items():
            entity_success_rate = sum(1 for o in outcome_list if o == 'success') / len(outcome_list)
            if entity_success_rate < 0.4:
                recommendations.append(f"{entity_type} recommendations underperforming ({entity_success_rate:.1%} success rate)")
        
        return recommendations
    
    def get_adaptive_adjustment_factor(self, entity_type: str,
                                       adjustment_type: str,
                                       default_factor: float = 0.15) -> float:
        """
        Get adaptive adjustment factor based on historical performance
        
        Args:
            entity_type: Type of entity
            adjustment_type: Type of adjustment
            default_factor: Default adjustment factor
            
        Returns:
            Adjusted factor based on learning
        """
        # Filter relevant outcomes
        relevant_outcomes = [
            o for o in self.outcomes_history[-100:]  # Last 100 outcomes
            if o.entity_type == entity_type and o.adjustment_type == adjustment_type
        ]
        
        if len(relevant_outcomes) < 10:
            return default_factor  # Not enough data
        
        # Calculate success rate
        successes = sum(1 for o in relevant_outcomes if o.outcome == 'success')
        success_rate = successes / len(relevant_outcomes)
        
        # Adjust factor based on success rate
        if success_rate > 0.7:
            # High success rate - can be more aggressive
            return default_factor * 1.2
        elif success_rate < 0.4:
            # Low success rate - be more conservative
            return default_factor * 0.7
        else:
            return default_factor
    
    def export_learning_data(self, output_path: str) -> None:
        """Export learning data for analysis"""
        data = {
            'exported_at': datetime.now().isoformat(),
            'total_outcomes': len(self.outcomes_history),
            'outcomes': [
                {
                    'recommendation_id': o.recommendation_id,
                    'entity_type': o.entity_type,
                    'entity_id': o.entity_id,
                    'outcome': o.outcome,
                    'improvement_percentage': o.improvement_percentage,
                    'before_metrics': o.before_metrics,
                    'after_metrics': o.after_metrics,
                    'timestamp': o.timestamp.isoformat()
                }
                for o in self.outcomes_history
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Exported learning data to {output_path}")


class ModelTrainer:
    """
    Trains predictive models based on historical data
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.min_training_samples = config.get('min_training_samples', 100)
    
    def prepare_training_data(self, outcomes: List[PerformanceOutcome]) -> Tuple[List[List[float]], List[int]]:
        """
        Prepare training data from outcomes
        
        Returns:
            Tuple of (features, labels)
        """
        features = []
        labels = []
        
        for outcome in outcomes:
            # Extract features
            feature_vector = [
                outcome.before_metrics.get('roas', 0),
                outcome.before_metrics.get('acos', 0),
                outcome.before_metrics.get('ctr', 0),
                outcome.applied_value,
                1 if outcome.entity_type == 'keyword' else 0,
                1 if outcome.entity_type == 'campaign' else 0,
            ]
            
            # Label (1 for success, 0 for failure/neutral)
            label = 1 if outcome.outcome == 'success' else 0
            
            features.append(feature_vector)
            labels.append(label)
        
        return features, labels
    
    def calculate_feature_importance(self, outcomes: List[PerformanceOutcome]) -> Dict[str, float]:
        """
        Calculate which factors are most predictive of success
        
        This is a simplified version - in production, use scikit-learn or similar
        """
        if len(outcomes) < self.min_training_samples:
            return {
                'roas': 0.25,
                'acos': 0.25,
                'ctr': 0.20,
                'entity_type': 0.15,
                'adjustment_magnitude': 0.15
            }
        
        # Group by success/failure
        successes = [o for o in outcomes if o.outcome == 'success']
        failures = [o for o in outcomes if o.outcome == 'failure']
        
        importance = {}
        
        # ROAS importance
        if successes and failures:
            success_roas = [o.before_metrics.get('roas', 0) for o in successes]
            failure_roas = [o.before_metrics.get('roas', 0) for o in failures]
            
            success_avg = statistics.mean(success_roas) if success_roas else 0
            failure_avg = statistics.mean(failure_roas) if failure_roas else 0
            
            roas_diff = abs(success_avg - failure_avg)
            importance['roas'] = min(1.0, roas_diff / 5.0)  # Normalize
        
        # Default weights
        importance.setdefault('roas', 0.25)
        importance.setdefault('acos', 0.25)
        importance.setdefault('ctr', 0.20)
        importance.setdefault('entity_type', 0.15)
        importance.setdefault('adjustment_magnitude', 0.15)
        
        return importance
    
    def predict_success_probability(self, current_metrics: Dict[str, float],
                                   proposed_adjustment: float,
                                   entity_type: str,
                                   outcomes: List[PerformanceOutcome]) -> float:
        """
        Predict probability of success for a proposed adjustment
        
        Simple implementation - in production, use trained ML model
        """
        if len(outcomes) < 20:
            return 0.5  # Default probability
        
        # Find similar historical cases
        similar_outcomes = []
        
        for outcome in outcomes:
            # Calculate similarity
            similarity = 0.0
            
            # ROAS similarity
            if 'roas' in current_metrics and 'roas' in outcome.before_metrics:
                roas_diff = abs(current_metrics['roas'] - outcome.before_metrics['roas'])
                similarity += max(0, 1 - roas_diff / 5.0) * 0.4
            
            # Entity type match
            if outcome.entity_type == entity_type:
                similarity += 0.3
            
            # Adjustment magnitude similarity
            adj_diff = abs(proposed_adjustment - outcome.applied_value)
            similarity += max(0, 1 - adj_diff / 2.0) * 0.3
            
            if similarity > 0.5:  # Threshold for similarity
                similar_outcomes.append(outcome)
        
        if not similar_outcomes:
            return 0.5
        
        # Calculate success rate among similar cases
        successes = sum(1 for o in similar_outcomes if o.outcome == 'success')
        success_probability = successes / len(similar_outcomes)
        
        return success_probability

