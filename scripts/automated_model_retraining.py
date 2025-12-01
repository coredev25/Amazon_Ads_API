#!/usr/bin/env python3
"""
Automated Model Retraining Pipeline (#16)

Daily cron job that:
1. Extracts labeled outcomes from DB
2. Trains new model
3. Validates against holdout set
4. Promotes model only if metrics improve (test_auc, test_accuracy thresholds)
5. Keeps rollback to previous version if metrics degrade

Usage:
    python scripts/automated_model_retraining.py [--dry-run] [--force-retrain]

Cron setup:
    0 2 * * * cd /path/to/AmazonAds && /path/to/venv/bin/python scripts/automated_model_retraining.py >> logs/retraining.log 2>&1
"""

import sys
import os
import argparse
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_rule_engine.config import RuleConfig
from src.ai_rule_engine.database import DatabaseConnector
from src.ai_rule_engine.learning_loop import LearningLoop, ModelTrainer, PerformanceOutcome
from src.ai_rule_engine.evaluation_pipeline import EvaluationPipeline
from src.ai_rule_engine.model_rollback import ModelRollbackManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automated_retraining.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutomatedRetrainingPipeline:
    """
    Automated retraining pipeline with validation gating (#16)
    """
    
    def __init__(self, config: RuleConfig, db_connector: DatabaseConnector, dry_run: bool = False):
        self.config = config
        self.db = db_connector
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)
        
        # Validation thresholds
        self.min_test_auc_improvement = config.__dict__.get('min_test_auc_improvement', 0.02)  # 2% improvement
        self.min_test_accuracy_improvement = config.__dict__.get('min_test_accuracy_improvement', 0.01)  # 1% improvement
        self.min_test_auc = config.__dict__.get('min_test_auc', 0.60)  # Minimum AUC to promote
        self.min_test_accuracy = config.__dict__.get('min_test_accuracy', 0.55)  # Minimum accuracy to promote
        
        # Initialize learning components
        self.learning_loop = LearningLoop(config.__dict__, db_connector)
        self.model_trainer = ModelTrainer(config.__dict__, db_connector)
        self.evaluation_pipeline = EvaluationPipeline(
            config.__dict__, db_connector, self.learning_loop, self.model_trainer
        )
    
    def extract_training_data_from_db(self, months_back: int = 3) -> List[PerformanceOutcome]:
        """
        Extract labeled outcomes from database for training
        
        Args:
            months_back: Number of months to look back
            
        Returns:
            List of PerformanceOutcome objects
        """
        self.logger.info(f"Extracting training data from last {months_back} months")
        
        cutoff_date = datetime.now() - timedelta(days=months_back * 30)
        
        query = """
        SELECT 
            recommendation_id, entity_type, entity_id, adjustment_type,
            recommended_value, applied_value, before_metrics, after_metrics,
            outcome, improvement_percentage, label, strategy_id, policy_variant,
            is_holdout, features, timestamp
        FROM learning_outcomes
        WHERE timestamp >= %s
        ORDER BY timestamp ASC
        """
        
        outcomes = []
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (cutoff_date,))
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        import json
                        outcome = PerformanceOutcome(
                            recommendation_id=row[0],
                            entity_type=row[1],
                            entity_id=row[2],
                            adjustment_type=row[3],
                            recommended_value=float(row[4]),
                            applied_value=float(row[5]),
                            before_metrics=json.loads(row[6]) if row[6] else {},
                            after_metrics=json.loads(row[7]) if row[7] else {},
                            outcome=row[8],
                            improvement_percentage=float(row[9]),
                            timestamp=row[15],
                            strategy_id=row[11],
                            policy_variant=row[12],
                            is_holdout=row[13] if row[13] else False,
                            eligible_for_training=True
                        )
                        outcomes.append(outcome)
            
            self.logger.info(f"Extracted {len(outcomes)} training samples from database")
            return outcomes
            
        except Exception as e:
            self.logger.error(f"Error extracting training data: {e}")
            return []
    
    def get_latest_model_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get metrics from the latest promoted model
        
        Returns:
            Dictionary with model metrics or None
        """
        latest_run = self.db.get_latest_model_training_run()
        if not latest_run or not latest_run.get('promoted'):
            return None
        
        return {
            'test_auc': latest_run.get('test_auc'),
            'test_accuracy': latest_run.get('test_accuracy'),
            'brier_score': latest_run.get('brier_score'),
            'model_version': latest_run.get('model_version')
        }
    
    def validate_model_improvement(self, new_metrics: Dict[str, Any], 
                                  previous_metrics: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that new model improves over previous model
        
        Args:
            new_metrics: Metrics from newly trained model
            previous_metrics: Metrics from previous promoted model
            
        Returns:
            Dictionary with validation result
        """
        result = {
            'should_promote': False,
            'reason': '',
            'improvements': {}
        }
        
        # If no previous model, promote if meets minimum thresholds
        if not previous_metrics:
            if (new_metrics.get('test_auc', 0) >= self.min_test_auc and
                new_metrics.get('test_accuracy', 0) >= self.min_test_accuracy):
                result['should_promote'] = True
                result['reason'] = 'First model meets minimum thresholds'
            else:
                result['reason'] = (
                    f"First model below minimum thresholds: "
                    f"AUC {new_metrics.get('test_auc', 0):.3f} < {self.min_test_auc}, "
                    f"Accuracy {new_metrics.get('test_accuracy', 0):.3f} < {self.min_test_accuracy}"
                )
            return result
        
        # Check minimum thresholds
        if new_metrics.get('test_auc', 0) < self.min_test_auc:
            result['reason'] = f"Test AUC {new_metrics.get('test_auc', 0):.3f} below minimum {self.min_test_auc}"
            return result
        
        if new_metrics.get('test_accuracy', 0) < self.min_test_accuracy:
            result['reason'] = f"Test accuracy {new_metrics.get('test_accuracy', 0):.3f} below minimum {self.min_test_accuracy}"
            return result
        
        # Check improvements
        auc_improvement = new_metrics.get('test_auc', 0) - previous_metrics.get('test_auc', 0)
        accuracy_improvement = new_metrics.get('test_accuracy', 0) - previous_metrics.get('test_accuracy', 0)
        brier_improvement = previous_metrics.get('brier_score', 1.0) - new_metrics.get('brier_score', 1.0)  # Lower is better
        
        result['improvements'] = {
            'auc': auc_improvement,
            'accuracy': accuracy_improvement,
            'brier': brier_improvement
        }
        
        # Require improvement in AUC or accuracy
        if (auc_improvement >= self.min_test_auc_improvement or 
            accuracy_improvement >= self.min_test_accuracy_improvement):
            result['should_promote'] = True
            result['reason'] = (
                f"Model improved: AUC +{auc_improvement:.3f}, Accuracy +{accuracy_improvement:.3f}, "
                f"Brier {brier_improvement:+.3f}"
            )
        else:
            result['reason'] = (
                f"Model did not improve sufficiently: "
                f"AUC +{auc_improvement:.3f} < {self.min_test_auc_improvement}, "
                f"Accuracy +{accuracy_improvement:.3f} < {self.min_test_accuracy_improvement}"
            )
        
        return result
    
    def run_retraining_pipeline(self, force: bool = False) -> Dict[str, Any]:
        """
        Run the complete retraining pipeline
        
        Args:
            force: Force retraining even if not needed
            
        Returns:
            Pipeline results
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting Automated Model Retraining Pipeline")
        self.logger.info("=" * 60)
        
        if self.dry_run:
            self.logger.info("DRY RUN MODE - No changes will be made")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': self.dry_run,
            'evaluation': None,
            'training': None,
            'validation': None,
            'promotion': None,
            'error': None
        }
        
        try:
            # Step 1: Run daily evaluation to get latest outcomes
            self.logger.info("Step 1: Running daily evaluation")
            eval_results = self.evaluation_pipeline.run_daily_evaluation()
            results['evaluation'] = eval_results
            
            # Step 2: Extract training data from DB
            self.logger.info("Step 2: Extracting training data from database")
            training_outcomes = self.extract_training_data_from_db(months_back=3)
            
            if len(training_outcomes) < self.config.min_training_samples:
                self.logger.warning(
                    f"Insufficient training samples: {len(training_outcomes)} < {self.config.min_training_samples}"
                )
                results['error'] = 'insufficient_samples'
                return results
            
            # Step 3: Get previous model metrics
            self.logger.info("Step 3: Getting previous model metrics")
            previous_metrics = self.get_latest_model_metrics()
            if previous_metrics:
                self.logger.info(
                    f"Previous model: AUC={previous_metrics.get('test_auc', 0):.3f}, "
                    f"Accuracy={previous_metrics.get('test_accuracy', 0):.3f}"
                )
            
            # Step 4: Train new model
            self.logger.info(f"Step 4: Training new model with {len(training_outcomes)} samples")
            if self.dry_run:
                self.logger.info("DRY RUN: Would train model here")
                training_results = {'status': 'dry_run'}
            else:
                training_results = self.model_trainer.train_model(training_outcomes)
            results['training'] = training_results
            
            if training_results.get('status') != 'success':
                self.logger.error(f"Training failed: {training_results.get('reason')}")
                results['error'] = 'training_failed'
                return results
            
            # Step 5: Validate model improvement
            self.logger.info("Step 5: Validating model improvement")
            new_metrics = {
                'test_auc': training_results.get('test_auc', 0),
                'test_accuracy': training_results.get('test_accuracy', 0),
                'brier_score': training_results.get('test_brier', 1.0),
                'model_version': training_results.get('model_version', 0)
            }
            
            validation_result = self.validate_model_improvement(new_metrics, previous_metrics)
            results['validation'] = validation_result
            
            # Step 6: Promote model if validated
            if validation_result['should_promote']:
                self.logger.info(f"Model validation passed: {validation_result['reason']}")
                
                if self.dry_run:
                    self.logger.info("DRY RUN: Would promote model here")
                    results['promotion'] = {'status': 'dry_run', 'would_promote': True}
                else:
                    # Update model training run to promoted
                    run_id = training_results.get('run_id')
                    if run_id and self.db:
                        self.db.update_model_training_run(
                            run_id, 'success',
                            {'promoted': True}
                        )
                    results['promotion'] = {
                        'status': 'promoted',
                        'model_version': new_metrics['model_version'],
                        'metrics': new_metrics
                    }
                    self.logger.info(f"Model version {new_metrics['model_version']} promoted successfully")
            else:
                self.logger.warning(f"Model validation failed: {validation_result['reason']}")
                results['promotion'] = {
                    'status': 'rejected',
                    'reason': validation_result['reason']
                }
                
                # FIX #16: If model degraded, offer rollback option
                if previous_metrics:
                    previous_version = previous_metrics.get('model_version')
                    if previous_version:
                        self.logger.info(
                            f"Model validation failed. Previous version {previous_version} "
                            f"available for rollback if needed."
                        )
                        results['rollback_available'] = True
                        results['previous_version'] = previous_version
            
            self.logger.info("=" * 60)
            self.logger.info("Retraining Pipeline Complete")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"Error in retraining pipeline: {e}", exc_info=True)
            results['error'] = str(e)
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Automated Model Retraining Pipeline')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    parser.add_argument('--force-retrain', action='store_true', help='Force retraining even if not needed')
    parser.add_argument('--config', type=str, default='config/ai_rule_engine.json', help='Config file path')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = RuleConfig.from_file(args.config)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)
    
    # Initialize database
    try:
        db = DatabaseConnector()
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        sys.exit(1)
    
    # Run pipeline
    pipeline = AutomatedRetrainingPipeline(config, db, dry_run=args.dry_run)
    results = pipeline.run_retraining_pipeline(force=args.force_retrain)
    
    # Print summary
    print("\n" + "=" * 60)
    print("RETRAINING PIPELINE SUMMARY")
    print("=" * 60)
    print(f"Status: {'SUCCESS' if not results.get('error') else 'FAILED'}")
    if results.get('training'):
        print(f"Training: {results['training'].get('status')}")
    if results.get('validation'):
        print(f"Validation: {'PASSED' if results['validation'].get('should_promote') else 'FAILED'}")
        print(f"Reason: {results['validation'].get('reason')}")
    if results.get('promotion'):
        print(f"Promotion: {results['promotion'].get('status')}")
    print("=" * 60)
    
    # Exit with error code if failed
    if results.get('error'):
        sys.exit(1)


if __name__ == '__main__':
    main()

