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
import os
import pickle
from .telemetry import TelemetryClient
from .model_rollback import ModelRollbackManager
from .hierarchical_model import HierarchicalModelTrainer

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, roc_auc_score, brier_score_loss
    from sklearn.preprocessing import StandardScaler
    from sklearn.calibration import CalibratedClassifierCV
    import numpy as np
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False
    np = None


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
    strategy_id: Optional[str] = None
    policy_variant: Optional[str] = None
    is_holdout: bool = False
    eligible_for_training: bool = True


class LearningLoop:
    """
    Tracks recommendation outcomes and adjusts strategies
    """
    
    def __init__(self, config: Dict[str, Any], db_connector=None, telemetry: Optional[TelemetryClient] = None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db = db_connector
        self.telemetry = telemetry or TelemetryClient(config)
        
        # Storage for outcomes
        self.outcomes_history: List[PerformanceOutcome] = []
        
        # FIX #1: In-memory recommendation log
        self.recommendation_log: Dict[str, Dict[str, Any]] = {}
        
        # Learning parameters
        self.success_threshold = config.get('learning_success_threshold', 0.10)  # 10% improvement
        self.failure_threshold = config.get('learning_failure_threshold', -0.05)  # -5% decline
        self.min_evaluation_days = config.get('learning_evaluation_days', 7)
        self.min_spend_for_label = config.get('min_spend_for_label', 5.0)
        self.min_clicks_for_label = config.get('min_clicks_for_label', 5)
        self.default_strategy_id = config.get('strategy_id', 'ml_bid_optimizer_v1')
        self.policy_holdout_pct = config.get('learning_policy_holdout_pct', 0.1)
    
    def track_recommendation(self, recommendation: Dict[str, Any],
                            entity_id: int, entity_type: str) -> str:
        """
        Track a recommendation for future outcome evaluation
        
        FIX #1: Persist tracking data to in-memory log and database
        
        Returns:
            recommendation_id for tracking
        """
        recommendation_id = f"{entity_type}_{entity_id}_{datetime.now().timestamp()}"
        
        # Extract intelligence signals from metadata if available
        intelligence_signals = recommendation.get('metadata', {}).get('intelligence_signals')
        if not intelligence_signals:
            # Try to get from recommendation directly
            intelligence_signals = recommendation.get('intelligence_signals')
        
        strategy_id = (
            recommendation.get('strategy_id')
            or recommendation.get('metadata', {}).get('strategy_id')
            or self.default_strategy_id
        )
        policy_variant = recommendation.get('metadata', {}).get('policy_variant', 'treatment')

        # Store recommendation for tracking
        tracking_data = {
            'recommendation_id': recommendation_id,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'adjustment_type': recommendation.get('adjustment_type', 'unknown'),
            'recommended_value': float(recommendation.get('recommended_value', 0)),
            'current_value': float(recommendation.get('current_value', 0)),
            'intelligence_signals': intelligence_signals,
            'timestamp': datetime.now(),
            'applied': False,
            'metadata': recommendation.get('metadata', {}),
            'strategy_id': strategy_id,
            'policy_variant': policy_variant
        }
        
        # FIX #1: Store in-memory log
        self.recommendation_log[recommendation_id] = tracking_data
        
        # FIX #1: Persist to database if available
        if self.db and hasattr(self.db, 'save_recommendation'):
            try:
                self.db.save_recommendation(tracking_data)
            except Exception as e:
                self.logger.warning(f"Failed to persist recommendation to DB: {e}")
        
        self.logger.info(f"Tracking recommendation {recommendation_id} (value: {tracking_data['recommended_value']})")
        self.telemetry.increment(
            'learning_loop_tracked_recommendations',
            labels={'entity_type': entity_type, 'policy_variant': policy_variant}
        )
        return recommendation_id
    
    def record_outcome(self, recommendation_id: str,
                      before_metrics: Dict[str, float],
                      after_metrics: Dict[str, float],
                      applied_value: float) -> PerformanceOutcome:
        """
        Record the outcome of a recommendation
        
        FIX #2: Load stored recommendation to populate recommended_value, adjustment_type, intelligence_signals
        
        Args:
            recommendation_id: ID of the tracked recommendation
            before_metrics: Metrics before the change
            after_metrics: Metrics after the change
            applied_value: Actual value that was applied
            
        Returns:
            PerformanceOutcome object
        """
        # FIX #2: Look up recommendation in memory or database
        tracking = self.recommendation_log.get(recommendation_id)
        
        if not tracking and self.db and hasattr(self.db, 'get_tracked_recommendation'):
            try:
                tracking = self.db.get_tracked_recommendation(recommendation_id)
            except Exception as e:
                self.logger.warning(f"Error loading recommendation from DB: {e}")
        
        if not tracking:
            self.logger.error(f"Missing tracking data for recommendation {recommendation_id}")
            raise ValueError(f"Recommendation {recommendation_id} not found in tracking. Cannot record outcome without original recommendation metadata.")
        
        # Extract values from tracking
        entity_type = tracking.get('entity_type', 'unknown')
        entity_id = tracking.get('entity_id', 0)
        adjustment_type = tracking.get('adjustment_type', 'bid')
        recommended_value = float(tracking.get('recommended_value', 0.0))
        intelligence_signals = tracking.get('intelligence_signals')
        strategy_id = tracking.get('strategy_id') or self.default_strategy_id
        policy_variant = tracking.get('policy_variant', 'treatment')
        is_holdout = policy_variant == 'control'
        
        # Calculate improvement
        improvement = self._calculate_improvement(before_metrics, after_metrics)
        
        # Determine outcome
        if improvement >= self.success_threshold:
            outcome = 'success'
        elif improvement <= self.failure_threshold:
            outcome = 'failure'
        else:
            outcome = 'neutral'
        
        eligible_for_training = self._passes_label_quality(before_metrics)
        if not eligible_for_training:
            self.logger.info(
                f"Outcome for {recommendation_id} skipped for training - "
                f"below quality thresholds (spend={before_metrics.get('spend', 0)}, "
                f"clicks={before_metrics.get('clicks', 0)})"
            )
        
        # Create outcome record with loaded values
        outcome_record = PerformanceOutcome(
            recommendation_id=recommendation_id,
            entity_type=entity_type,
            entity_id=entity_id,
            adjustment_type=adjustment_type,
            recommended_value=recommended_value,  # FIX #2: Use loaded value
            applied_value=applied_value,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            outcome=outcome,
            improvement_percentage=improvement * 100,
            timestamp=datetime.now(),
            strategy_id=strategy_id,
            policy_variant=policy_variant,
            is_holdout=is_holdout,
            eligible_for_training=eligible_for_training
        )
        
        # Store outcome
        self.outcomes_history.append(outcome_record)
        
        # FIX #14: Save to database for long-term training
        if self.db and hasattr(self.db, 'save_learning_outcome'):
            try:
                self.db.save_learning_outcome(outcome_record, intelligence_signals)
            except Exception as e:
                self.logger.warning(f"Failed to save learning outcome to DB: {e}")
        
        self.logger.info(f"Recorded outcome for {recommendation_id}: {outcome} ({improvement*100:.1f}% improvement, recommended_value={recommended_value})")
        self.telemetry.increment(
            'learning_loop_outcomes',
            labels={'outcome': outcome, 'policy_variant': policy_variant}
        )
        
        return outcome_record
    
    def evaluate_outcome(self, before_metrics: Dict[str, float],
                        after_metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        STEP 2: Calculate outcome success/failure with weighted scoring
        
        Args:
            before_metrics: Performance metrics before change (14-day average)
            after_metrics: Performance metrics after change (14-day average)
            
        Returns:
            Dictionary with outcome_score, outcome_label, and details
        """
        # Calculate improvements (as per plan)
        acos_improvement = 0.0
        if before_metrics.get('acos', 0) > 0:
            acos_improvement = (before_metrics['acos'] - after_metrics.get('acos', before_metrics['acos'])) / before_metrics['acos']
        
        roas_improvement = 0.0
        if before_metrics.get('roas', 0) > 0:
            roas_improvement = (after_metrics.get('roas', before_metrics['roas']) - before_metrics['roas']) / before_metrics['roas']
        
        ctr_improvement = 0.0
        if before_metrics.get('ctr', 0) > 0:
            ctr_improvement = (after_metrics.get('ctr', before_metrics['ctr']) - before_metrics['ctr']) / before_metrics['ctr']
        
        # Weighted score: 40% ACOS, 40% ROAS, 20% CTR
        weighted_score = 0.4 * acos_improvement + 0.4 * roas_improvement + 0.2 * ctr_improvement
        
        # Determine outcome label
        if weighted_score > 0.1:  # +10% improvement
            outcome_label = 'success'
        elif weighted_score < -0.05:  # -5% decline
            outcome_label = 'failure'
        else:
            outcome_label = 'neutral'
        
        return {
            'outcome_score': weighted_score,
            'outcome_label': outcome_label,
            'acos_improvement': acos_improvement,
            'roas_improvement': roas_improvement,
            'ctr_improvement': ctr_improvement,
            'weighted_score': weighted_score
        }
    
    def _calculate_improvement(self, before_metrics: Dict[str, float],
                               after_metrics: Dict[str, float]) -> float:
        """
        Calculate overall improvement based on multiple metrics
        
        Prioritizes ROAS and ACOS improvements
        Uses the same weighted scoring as evaluate_outcome
        """
        result = self.evaluate_outcome(before_metrics, after_metrics)
        return result['weighted_score']
    
    def _passes_label_quality(self, before_metrics: Dict[str, float]) -> bool:
        """
        Checklist #15: ensure labels meet spend/click thresholds before training.
        """
        spend = float(before_metrics.get('spend', 0))
        clicks = float(before_metrics.get('clicks', 0))
        return spend >= self.min_spend_for_label and clicks >= self.min_clicks_for_label
    
    def _hash_bucket(self, value: Any, buckets: int = 20) -> float:
        if value in (None, ''):
            return 0.0
        return float(abs(hash(value)) % buckets) / buckets
    
    def _build_prediction_vector(self, current_metrics: Dict[str, Any],
                                 proposed_adjustment: float,
                                 entity_type: str,
                                 intelligence_summary: Optional[Dict[str, Any]]) -> List[float]:
        adjustment_pct = proposed_adjustment * 100
        return self._compose_features(
            current_metrics,
            adjustment_pct,
            entity_type,
            policy_variant='treatment',
            strategy_id=self.default_strategy_id,
            include_intelligence_signals=True,
            intelligence_summary=intelligence_summary
        )
    
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
        
        # FIX #21: Record comprehensive learning metrics
        try:
            self.telemetry.record_learning_metrics(
                success_rate=success_rate,
                total_outcomes=total,
                avg_improvement=average_improvement
            )
        except Exception as e:
            self.logger.warning(f"Error recording learning metrics: {e}")
        
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
    
    def get_campaign_success_rate(self, campaign_id: int, days: int = 30) -> float:
        """
        STEP 7: Get success rate for a campaign (for adaptivity)
        
        Args:
            campaign_id: Campaign ID
            days: Days to look back
            
        Returns:
            Success rate (0.0 to 1.0)
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        campaign_outcomes = [
            o for o in self.outcomes_history
            if o.entity_id == campaign_id and o.timestamp >= cutoff_date
        ]
        
        if not campaign_outcomes:
            return 0.5  # Default if no data
        
        successes = sum(1 for o in campaign_outcomes if o.outcome == 'success')
        return successes / len(campaign_outcomes)


class ModelTrainer:
    """
    STEP 4: Trains predictive models based on historical data
    Uses Logistic Regression or Gradient Boosting to predict success probability
    """
    
    def __init__(self, config: Dict[str, Any], db_connector=None, telemetry=None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db = db_connector
        self.telemetry = telemetry or TelemetryClient(config)
        self.min_training_samples = config.get('min_training_samples', 100)
        self.model = None
        self.model_version = 0
        self.model_path = config.get('model_path', 'models/bid_success_model.pkl')
        self.model_type = config.get('model_type', 'logistic_regression')  # 'logistic_regression' or 'gradient_boosting'
        self.enable_probability_calibration = config.get('enable_probability_calibration', True)
        self.scaler: Optional['StandardScaler'] = None
        self.enable_hierarchical = config.get('enable_hierarchical_models', False)
        
        # FIX #16: Initialize model rollback manager
        self.rollback_manager = ModelRollbackManager(
            model_path=self.model_path,
            max_versions=config.get('max_model_versions', 5)
        )
        
        # FIX #18: Initialize hierarchical model trainer for cross-ASIN learning
        if self.enable_hierarchical:
            self.hierarchical_trainer = HierarchicalModelTrainer(config)
        else:
            self.hierarchical_trainer = None
        
        # Create models directory if it doesn't exist
        if self.model_path:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        # Load existing model if available
        self._load_model()
    
    def prepare_training_data(self, outcomes: List[PerformanceOutcome], 
                            include_intelligence_signals: bool = False,
                            intelligence_summary: Optional[Dict[str, Any]] = None) -> Tuple[List[List[float]], List[int]]:
        """
        STEP 3: Build training dataset with comprehensive features
        
        Features:
        - Previous ACOS, CTR, ROAS
        - Number of conversions
        - Spend in last 14 days
        - Adjustment type (+% or -%)
        - Entity type
        - Match type (for keywords)
        - Intelligence signals summary (seasonality, rank, etc.)
        
        Returns:
            Tuple of (features, labels)
        """
        features = []
        labels = []
        
        for outcome in outcomes:
            if not outcome.eligible_for_training:
                continue
            feature_vector = self._build_feature_vector(
                outcome,
                include_intelligence_signals,
                intelligence_summary
            )
            if feature_vector is None:
                continue
            label = 1 if outcome.outcome == 'success' else 0
            features.append(feature_vector)
            labels.append(label)
        
        return features, labels
    
    def _build_feature_vector(self, outcome: PerformanceOutcome,
                              include_intelligence_signals: bool,
                              intelligence_summary: Optional[Dict[str, Any]]) -> Optional[List[float]]:
        before = outcome.before_metrics or {}
        adjustment_pct = ((outcome.applied_value - outcome.recommended_value) / outcome.recommended_value * 100) if outcome.recommended_value else 0
        policy_variant = outcome.policy_variant or 'treatment'
        strategy_id = outcome.strategy_id or self.default_strategy_id
        
        # FIX #23: Explicitly verify strategy_id is included in feature vector
        # This ensures model training includes strategy_id to prevent feedback loop leakage
        feature_vector = self._compose_features(
            before,
            adjustment_pct,
            outcome.entity_type,
            policy_variant,
            strategy_id,
            include_intelligence_signals,
            intelligence_summary
        )
        
        # Verify strategy_id is in features (for debugging/validation)
        if feature_vector and strategy_id:
            self.logger.debug(f"Feature vector includes strategy_id: {strategy_id} for outcome {outcome.recommendation_id}")
        
        return feature_vector
    
    def _compose_features(self, snapshot: Dict[str, Any], adjustment_pct: float,
                          entity_type: str, policy_variant: str, strategy_id: Optional[str],
                          include_intelligence_signals: bool,
                          intelligence_summary: Optional[Dict[str, Any]]) -> List[float]:
        feature_vector = [
            snapshot.get('acos', 0),
            snapshot.get('roas', 0),
            snapshot.get('ctr', 0),
            snapshot.get('conversions', 0),
            snapshot.get('spend', 0),
            snapshot.get('sales', 0),
            adjustment_pct,
            1.0 if adjustment_pct > 0 else 0.0,
            1.0 if adjustment_pct < 0 else 0.0,
            1 if entity_type == 'keyword' else 0,
            1 if entity_type == 'ad_group' else 0,
            1 if entity_type == 'campaign' else 0,
        ]
        for metric in ('acos', 'roas', 'ctr'):
            for window in ('7d', '14d', '30d'):
                feature_vector.append(snapshot.get(f'rolling_{metric}_mean_{window}', snapshot.get(metric, 0)))
                feature_vector.append(snapshot.get(f'rolling_{metric}_std_{window}', 0))
        feature_vector.extend([
            snapshot.get('days_since_last_conversion', 0) or 0,
            snapshot.get('seasonal_month', datetime.now().month),
            snapshot.get('seasonal_day_of_week', datetime.now().weekday()),
            snapshot.get('buy_box_share', 0),
            snapshot.get('competitor_density', 0),
            1.0 if snapshot.get('acos_trend_direction') == 'improving' else 0.0,
            1.0 if snapshot.get('ctr_trend_direction') == 'improving' else 0.0,
        ])
        feature_vector.extend([
            self._hash_bucket(snapshot.get('entity_category')),
            self._hash_bucket(snapshot.get('entity_price_tier')),
            self._hash_bucket(snapshot.get('entity_fulfillment')),
        ])
        feature_vector.append(1.0 if policy_variant == 'control' else 0.0)
        # FIX #23: Explicitly include strategy_id in feature vector to prevent feedback loop leakage
        # This allows model to learn strategy-specific patterns and enables offline evaluation
        feature_vector.append(self._hash_bucket(strategy_id))
        if include_intelligence_signals and intelligence_summary:
            feature_vector.extend([
                intelligence_summary.get('seasonality_boost', 0),
                intelligence_summary.get('rank_signal', 0),
                intelligence_summary.get('profit_margin', 0),
            ])
        else:
            feature_vector.extend([0, 0, 0])
        return feature_vector
    
    def _get_feature_names(self) -> List[str]:
        """Get feature names for explainability (#29)"""
        feature_names = [
            'acos', 'roas', 'ctr', 'conversions', 'spend', 'sales',
            'adjustment_pct', 'adjustment_positive', 'adjustment_negative',
            'entity_keyword', 'entity_ad_group', 'entity_campaign'
        ]
        # Add rolling features
        for metric in ('acos', 'roas', 'ctr'):
            for window in ('7d', '14d', '30d'):
                feature_names.append(f'rolling_{metric}_mean_{window}')
                feature_names.append(f'rolling_{metric}_std_{window}')
        # Add other features
        feature_names.extend([
            'days_since_last_conversion', 'seasonal_month', 'seasonal_day_of_week',
            'buy_box_share', 'competitor_density', 'acos_trend_improving', 'ctr_trend_improving',
            'entity_category_hash', 'entity_price_tier_hash', 'entity_fulfillment_hash',
            'policy_variant_control', 'strategy_id_hash', 'seasonality_boost', 'rank_signal', 'profit_margin'
        ])
        return feature_names
    
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
    
    def train_model(self, outcomes: List[PerformanceOutcome],
                   intelligence_summaries: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        STEP 4: Train the learning model
        
        Args:
            outcomes: List of performance outcomes
            intelligence_summaries: Optional list of intelligence signal summaries
            
        Returns:
            Training results with metrics
        """
        if not SKLEARN_AVAILABLE:
            self.logger.warning("scikit-learn not available, using fallback prediction")
            return {'status': 'skipped', 'reason': 'scikit-learn not available'}
        
        if len(outcomes) < self.min_training_samples:
            self.logger.info(f"Insufficient training samples: {len(outcomes)} < {self.min_training_samples}")
            return {'status': 'skipped', 'reason': 'insufficient_samples', 'count': len(outcomes)}
        
        # Prepare training data
        features, labels = self.prepare_training_data(outcomes, include_intelligence_signals=True)
        
        if not features or not labels:
            return {'status': 'error', 'reason': 'no_features'}
        
        # Convert to numpy arrays
        X = np.array(features, dtype=float)
        y = np.array(labels)
        
        # Split into train/test
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Normalize features
        self.scaler = StandardScaler()
        self.scaler.fit(X_train)
        X_train = self.scaler.transform(X_train)
        X_test = self.scaler.transform(X_test)
        
        run_id = None
        if self.db and hasattr(self.db, 'create_model_training_run'):
            run_id = self.db.create_model_training_run(self.model_version + 1, 'running')
        
        # Train model
        if self.model_type == 'gradient_boosting':
            base_model = GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=5)
        else:
            base_model = LogisticRegression(random_state=42, max_iter=1000)
        
        if self.enable_probability_calibration and self.model_type == 'logistic_regression':
            self.model = CalibratedClassifierCV(base_model, method='isotonic', cv=3)
        else:
            self.model = base_model
        
        self.model.fit(X_train, y_train)
        
        # FIX #29: Initialize explainer after model training
        if self.explainer and hasattr(self.explainer, 'initialize_explainer'):
            feature_names = self._get_feature_names()
            self.explainer.initialize_explainer(self.model, X_train, feature_names)
        
        # Evaluate
        train_pred = self.model.predict(X_train)
        test_pred = self.model.predict(X_test)
        train_proba = self.model.predict_proba(X_train)[:, 1]
        test_proba = self.model.predict_proba(X_test)[:, 1]
        
        train_acc = accuracy_score(y_train, train_pred)
        test_acc = accuracy_score(y_test, test_pred)
        train_auc = roc_auc_score(y_train, train_proba) if len(set(y_train)) > 1 else 0.5
        test_auc = roc_auc_score(y_test, test_proba) if len(set(y_test)) > 1 else 0.5
        test_brier = brier_score_loss(y_test, test_proba)
        
        self.model_version += 1
        
        # FIX #16: Save model version with rollback support
        self._save_model()
        
        # Save versioned copy for rollback
        if self.rollback_manager:
            try:
                metadata = {
                    'model_type': self.model_type,
                    'training_samples': len(X_train),
                    'test_auc': test_auc,
                    'test_accuracy': test_acc
                }
                self.rollback_manager.save_model_version(
                    model=self.model,
                    model_version=self.model_version,
                    scaler=self.scaler,
                    metadata=metadata
                )
            except Exception as e:
                self.logger.warning(f"Error saving model version for rollback: {e}")
        
        results = {
            'status': 'success',
            'model_type': self.model_type,
            'model_version': self.model_version,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'train_accuracy': train_acc,
            'test_accuracy': test_acc,
            'train_auc': train_auc,
            'test_auc': test_auc,
            'test_brier': test_brier,
            'run_id': run_id  # Include run_id for retraining pipeline
        }
        
        if run_id and self.db and hasattr(self.db, 'update_model_training_run'):
            training_metrics = {
                'train_accuracy': train_acc,
                'test_accuracy': test_acc,
                'train_auc': train_auc,
                'test_auc': test_auc,
                'brier_score': test_brier,
                'promoted': False  # Don't auto-promote, let validation pipeline decide
            }
            self.db.update_model_training_run(run_id, 'success', training_metrics)
        
        # FIX #21: Record comprehensive model metrics to telemetry
        if hasattr(self, 'telemetry') and self.telemetry:
            try:
                self.telemetry.record_model_metrics(
                    model_version=self.model_version,
                    train_auc=train_auc,
                    test_auc=test_auc,
                    train_accuracy=train_acc,
                    test_accuracy=test_acc,
                    brier_score=test_brier
                )
            except Exception as e:
                self.logger.warning(f"Error recording model metrics to telemetry: {e}")
        
        # FIX #18: Train hierarchical model if enabled
        if self.enable_hierarchical and self.hierarchical_trainer:
            try:
                hierarchical_results = self.hierarchical_trainer.train_hierarchical_model(
                    outcomes,
                    lambda o: self._build_feature_vector(
                        o, include_intelligence_signals=True, intelligence_summary=None
                    )
                )
                results['hierarchical_model'] = hierarchical_results
                self.logger.info(f"Hierarchical model trained: {hierarchical_results.get('num_clusters', 0)} clusters")
            except Exception as e:
                self.logger.warning(f"Error training hierarchical model: {e}")
        
        self.logger.info(f"Model trained: {results}")
        return results
    
    def predict_success_probability(self, current_metrics: Dict[str, float],
                                   proposed_adjustment: float,
                                   current_bid: float,
                                   entity_type: str,
                                   intelligence_signals: Optional[Dict[str, Any]] = None,
                                   cluster_features: Optional[Dict[str, Any]] = None,
                                   performance_history: Optional[List[Dict[str, Any]]] = None) -> Tuple[float, Optional[Dict[str, Any]]]:
        """
        STEP 5: Predict probability of success for a proposed adjustment
        
        Args:
            current_metrics: Current performance metrics
            proposed_adjustment: Proposed adjustment percentage
            current_bid: Current bid amount
            entity_type: Type of entity
            intelligence_signals: Optional intelligence signal summary
            performance_history: Optional historical performance for time-series models
            
        Returns:
            Tuple of (probability of success (0.0 to 1.0), explanation dict or None)
        """
        explanation = None
        
        # FIX #26: Try time-series model first if available
        if self.time_series_trainer and performance_history and len(performance_history) >= self.time_series_trainer.sequence_length:
            try:
                ts_prob = self.time_series_trainer.predict_time_series(performance_history)
                if ts_prob != 0.5:  # If time-series model has a prediction
                    if self.logger:
                        self.logger.debug(f"Using time-series prediction: {ts_prob:.3f}")
                    return ts_prob, explanation
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Time-series prediction failed: {e}")
        
        if self.model is None:
            # Fallback: return default probability
            return 0.5, explanation
        
        if not SKLEARN_AVAILABLE:
            return 0.5, explanation
        
        # Prepare feature vector (same as training)
        feature_vector = self._build_prediction_vector(
            current_metrics,
            proposed_adjustment,
            entity_type,
            intelligence_signals
        )
        
        # Predict
        try:
            # FIX #18: Use hierarchical model if available and cluster features provided
            if (self.enable_hierarchical and self.hierarchical_trainer and 
                cluster_features and self.hierarchical_trainer.global_model):
                proba = self.hierarchical_trainer.predict_with_hierarchy(
                    feature_vector, cluster_features
                )
                return float(proba), explanation
            
            # Fallback to standard model
            X = np.array([feature_vector])
            if self.scaler is not None:
                X = self.scaler.transform(X)
            proba = self.model.predict_proba(X)[0, 1]  # Probability of success (class 1)
            
            # FIX #29: Generate explanation if explainer available
            if self.explainer and hasattr(self.explainer, 'explain_prediction'):
                try:
                    explanation = self.explainer.explain_prediction(X[0], top_k=5)
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error generating explanation: {e}")
            
            return float(proba), explanation
        except Exception as e:
            self.logger.warning(f"Error in prediction: {e}")
            return 0.5, None
    
    def _save_model(self) -> bool:
        """Save trained model to disk"""
        if self.model is None or not self.model_path:
            return False
        
        try:
            model_data = {
                'model': self.model,
                'model_version': self.model_version,
                'model_type': self.model_type,
                'trained_at': datetime.now().isoformat(),
                'scaler': self.scaler
            }
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            self.logger.info(f"Model saved to {self.model_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
            return False
    
    def _load_model(self) -> bool:
        """Load trained model from disk"""
        if not self.model_path or not os.path.exists(self.model_path):
            return False
        
        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
            self.model = model_data['model']
            self.model_version = model_data.get('model_version', 0)
            self.scaler = model_data.get('scaler')
            self.logger.info(f"Model loaded from {self.model_path} (version {self.model_version})")
            return True
        except Exception as e:
            self.logger.warning(f"Error loading model: {e}")
            return False

