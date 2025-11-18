"""
STEP 6: Continuous Evaluation & Retraining Pipeline
Runs daily to evaluate matured bid changes and retrain models
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from .database import DatabaseConnector
from .learning_loop import LearningLoop, ModelTrainer, PerformanceOutcome


class EvaluationPipeline:
    """
    STEP 6: Continuous evaluation and retraining pipeline
    
    Runs daily to:
    1. Evaluate bid changes that are ≥14 days old
    2. Update outcomes in database
    3. Retrain models weekly or when dataset grows 20%+
    """
    
    def __init__(self, config: Dict[str, Any], db_connector: DatabaseConnector,
                 learning_loop: LearningLoop, model_trainer: ModelTrainer):
        self.config = config
        self.db = db_connector
        self.learning_loop = learning_loop
        self.model_trainer = model_trainer
        self.logger = logging.getLogger(__name__)
        
        self.evaluation_days = config.get('learning_evaluation_days', 14)
        self.min_training_samples = config.get('min_training_samples', 100)
        self.retrain_trigger_growth = config.get('retrain_trigger_growth', 0.20)  # 20% growth
        
    def evaluate_matured_changes(self) -> Dict[str, Any]:
        """
        Evaluate all bid changes that are ≥14 days old
        
        Returns:
            Summary of evaluation results
        """
        self.logger.info("Starting evaluation of matured bid changes")
        
        # Get bid changes ready for evaluation
        changes = self.db.get_bid_changes_for_evaluation(min_age_days=self.evaluation_days)
        
        if not changes:
            self.logger.info("No bid changes ready for evaluation")
            return {
                'evaluated': 0,
                'successes': 0,
                'failures': 0,
                'neutrals': 0
            }
        
        evaluated = 0
        successes = 0
        failures = 0
        neutrals = 0
        
        for change in changes:
            try:
                # Parse performance_before
                performance_before = json.loads(change['performance_before']) if change.get('performance_before') else {}
                
                # Get performance_after (14 days after change)
                performance_after = self._get_performance_after(change)
                
                if not performance_after:
                    self.logger.warning(f"Could not get performance_after for change {change['id']}")
                    continue
                
                # Evaluate outcome
                outcome_result = self.learning_loop.evaluate_outcome(
                    before_metrics=performance_before,
                    after_metrics=performance_after
                )
                
                # Update database
                success = self.db.update_bid_change_outcome(
                    change_id=change['id'],
                    outcome_score=outcome_result['outcome_score'],
                    outcome_label=outcome_result['outcome_label'],
                    performance_after=performance_after
                )
                
                if success:
                    evaluated += 1
                    if outcome_result['outcome_label'] == 'success':
                        successes += 1
                    elif outcome_result['outcome_label'] == 'failure':
                        failures += 1
                    else:
                        neutrals += 1
                    
                    # Create PerformanceOutcome for learning loop
                    outcome = PerformanceOutcome(
                        recommendation_id=f"change_{change['id']}",
                        entity_type=change['entity_type'],
                        entity_id=change['entity_id'],
                        adjustment_type='bid',
                        recommended_value=change['new_bid'],
                        applied_value=change['new_bid'],
                        before_metrics=performance_before,
                        after_metrics=performance_after,
                        outcome=outcome_result['outcome_label'],
                        improvement_percentage=outcome_result['outcome_score'] * 100,
                        timestamp=datetime.now()
                    )
                    self.learning_loop.outcomes_history.append(outcome)
                    
            except Exception as e:
                self.logger.error(f"Error evaluating change {change.get('id')}: {e}")
                continue
        
        result = {
            'evaluated': evaluated,
            'successes': successes,
            'failures': failures,
            'neutrals': neutrals
        }
        
        self.logger.info(f"Evaluation complete: {result}")
        return result
    
    def _get_performance_after(self, change: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Get performance metrics for 14 days after the change
        
        Args:
            change: Bid change record
            
        Returns:
            Performance metrics dictionary or None
        """
        entity_type = change['entity_type']
        entity_id = change['entity_id']
        change_date = change['change_date']
        
        # Calculate date range: change_date to change_date + 14 days
        start_date = change_date
        end_date = change_date + timedelta(days=self.evaluation_days)
        
        # Get performance data for this period
        # Note: This requires a method to get performance data by date range
        # For now, we'll use a simplified approach
        try:
            # This would need to be implemented in DatabaseConnector
            # For now, return None and log a warning
            self.logger.warning(
                f"Performance data retrieval by date range not yet implemented. "
                f"Using placeholder for {entity_type} {entity_id}"
            )
            # TODO: Implement actual performance data retrieval
            return None
        except Exception as e:
            self.logger.error(f"Error getting performance_after: {e}")
            return None
    
    def should_retrain(self, previous_count: int, current_count: int) -> bool:
        """
        Determine if model should be retrained
        
        Args:
            previous_count: Previous training dataset size
            current_count: Current training dataset size
            
        Returns:
            True if should retrain
        """
        if current_count < self.min_training_samples:
            return False
        
        if previous_count == 0:
            return True  # First training
        
        growth = (current_count - previous_count) / previous_count if previous_count > 0 else 0
        return growth >= self.retrain_trigger_growth
    
    def retrain_model(self) -> Dict[str, Any]:
        """
        Retrain the model with updated outcomes
        
        Returns:
            Training results
        """
        if len(self.learning_loop.outcomes_history) < self.min_training_samples:
            return {
                'status': 'skipped',
                'reason': 'insufficient_samples',
                'count': len(self.learning_loop.outcomes_history)
            }
        
        self.logger.info(f"Retraining model with {len(self.learning_loop.outcomes_history)} outcomes")
        
        results = self.model_trainer.train_model(self.learning_loop.outcomes_history)
        
        return results
    
    def run_daily_evaluation(self) -> Dict[str, Any]:
        """
        Run the daily evaluation pipeline
        
        Returns:
            Summary of all operations
        """
        self.logger.info("Running daily evaluation pipeline")
        
        # Step 1: Evaluate matured changes
        eval_results = self.evaluate_matured_changes()
        
        # Step 2: Check if retraining is needed
        current_count = len(self.learning_loop.outcomes_history)
        # TODO: Store previous count in config or database
        previous_count = self.config.get('last_training_count', 0)
        
        retrain_results = None
        if self.should_retrain(previous_count, current_count):
            retrain_results = self.retrain_model()
            if retrain_results.get('status') == 'success':
                self.config['last_training_count'] = current_count
        
        return {
            'evaluation': eval_results,
            'retraining': retrain_results,
            'total_outcomes': current_count
        }



