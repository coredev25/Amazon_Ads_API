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

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, roc_auc_score
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
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
    
    def __init__(self, config: Dict[str, Any], db_connector=None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db = db_connector
        self.min_training_samples = config.get('min_training_samples', 100)
        self.model = None
        self.model_version = 0
        self.model_path = config.get('model_path', 'models/bid_success_model.pkl')
        self.model_type = config.get('model_type', 'logistic_regression')  # 'logistic_regression' or 'gradient_boosting'
        
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
            before = outcome.before_metrics
            adjustment_pct = ((outcome.applied_value - outcome.recommended_value) / outcome.recommended_value * 100) if outcome.recommended_value != 0 else 0
            
            # Extract comprehensive features
            feature_vector = [
                before.get('acos', 0),
                before.get('roas', 0),
                before.get('ctr', 0),
                before.get('conversions', 0),
                before.get('spend', 0),
                before.get('sales', 0),
                adjustment_pct,  # Adjustment percentage
                1.0 if adjustment_pct > 0 else 0.0,  # Is increase
                1.0 if adjustment_pct < 0 else 0.0,  # Is decrease
                1 if outcome.entity_type == 'keyword' else 0,
                1 if outcome.entity_type == 'ad_group' else 0,
                1 if outcome.entity_type == 'campaign' else 0,
            ]
            
            # Add intelligence signals if available
            if include_intelligence_signals and intelligence_summary:
                feature_vector.extend([
                    intelligence_summary.get('seasonality_boost', 0),
                    intelligence_summary.get('rank_signal', 0),
                    intelligence_summary.get('profit_margin', 0),
                ])
            
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
        features, labels = self.prepare_training_data(outcomes, include_intelligence_signals=False)
        
        if not features or not labels:
            return {'status': 'error', 'reason': 'no_features'}
        
        # Convert to numpy arrays
        X = np.array(features)
        y = np.array(labels)
        
        # Split into train/test
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train model
        if self.model_type == 'gradient_boosting':
            self.model = GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=5)
        else:
            self.model = LogisticRegression(random_state=42, max_iter=1000)
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_pred = self.model.predict(X_train)
        test_pred = self.model.predict(X_test)
        train_proba = self.model.predict_proba(X_train)[:, 1]
        test_proba = self.model.predict_proba(X_test)[:, 1]
        
        train_acc = accuracy_score(y_train, train_pred)
        test_acc = accuracy_score(y_test, test_pred)
        train_auc = roc_auc_score(y_train, train_proba) if len(set(y_train)) > 1 else 0.5
        test_auc = roc_auc_score(y_test, test_proba) if len(set(y_test)) > 1 else 0.5
        
        self.model_version += 1
        
        # Save model
        self._save_model()
        
        results = {
            'status': 'success',
            'model_type': self.model_type,
            'model_version': self.model_version,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'train_accuracy': train_acc,
            'test_accuracy': test_acc,
            'train_auc': train_auc,
            'test_auc': test_auc
        }
        
        self.logger.info(f"Model trained: {results}")
        return results
    
    def predict_success_probability(self, current_metrics: Dict[str, float],
                                   proposed_adjustment: float,
                                   current_bid: float,
                                   entity_type: str,
                                   intelligence_signals: Optional[Dict[str, Any]] = None) -> float:
        """
        STEP 5: Predict probability of success for a proposed adjustment
        
        Args:
            current_metrics: Current performance metrics
            proposed_adjustment: Proposed adjustment percentage
            current_bid: Current bid amount
            entity_type: Type of entity
            intelligence_signals: Optional intelligence signal summary
            
        Returns:
            Probability of success (0.0 to 1.0)
        """
        if self.model is None:
            # Fallback: return default probability
            return 0.5
        
        if not SKLEARN_AVAILABLE:
            return 0.5
        
        # Prepare feature vector (same as training)
        adjustment_pct = proposed_adjustment * 100  # Convert to percentage
        
        feature_vector = [
            current_metrics.get('acos', 0),
            current_metrics.get('roas', 0),
            current_metrics.get('ctr', 0),
            current_metrics.get('conversions', 0),
            current_metrics.get('spend', 0),
            current_metrics.get('sales', 0),
            adjustment_pct,
            1.0 if adjustment_pct > 0 else 0.0,
            1.0 if adjustment_pct < 0 else 0.0,
            1 if entity_type == 'keyword' else 0,
            1 if entity_type == 'ad_group' else 0,
            1 if entity_type == 'campaign' else 0,
        ]
        
        # Add intelligence signals if available
        if intelligence_signals:
            feature_vector.extend([
                intelligence_signals.get('seasonality_boost', 0),
                intelligence_signals.get('rank_signal', 0),
                intelligence_signals.get('profit_margin', 0),
            ])
        else:
            feature_vector.extend([0, 0, 0])  # Pad with zeros
        
        # Predict
        try:
            X = np.array([feature_vector])
            proba = self.model.predict_proba(X)[0, 1]  # Probability of success (class 1)
            return float(proba)
        except Exception as e:
            self.logger.warning(f"Error in prediction: {e}")
            return 0.5
    
    def _save_model(self) -> bool:
        """Save trained model to disk"""
        if self.model is None or not self.model_path:
            return False
        
        try:
            model_data = {
                'model': self.model,
                'model_version': self.model_version,
                'model_type': self.model_type,
                'trained_at': datetime.now().isoformat()
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
            self.logger.info(f"Model loaded from {self.model_path} (version {self.model_version})")
            return True
        except Exception as e:
            self.logger.warning(f"Error loading model: {e}")
            return False

