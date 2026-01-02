#!/usr/bin/env python3
"""
Unified Management System for AI Rule Engine, Bid Adjustments, and Learning Loop

This script provides a comprehensive interface to manage:
1. AI Rule Engine (bid adjustments and recommendations)
2. Learning Loop (outcome evaluation and tracking)
3. Model Retraining (automated model updates)

Usage:
    python scripts/manage_ai_system.py [command] [options]

Commands:
    run-engine          Run AI Rule Engine analysis cycle
    run-learning        Run learning loop evaluation only
    run-retraining      Run model retraining pipeline
    run-all             Run engine, learning, and retraining in sequence
    status              Show system status and health
    schedule            Start scheduled execution (daemon mode)
    stop                Stop scheduled execution
"""

import sys
import os
import argparse
import logging
import json
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from threading import Event
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_rule_engine.config import RuleConfig
from src.ai_rule_engine.database import DatabaseConnector
from src.ai_rule_engine.main import run_analysis_cycle
from scripts.automated_model_retraining import AutomatedRetrainingPipeline

os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ai_system_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AISystemManager:
    def __init__(self, config_path: str = 'config/ai_rule_engine.json', use_database: bool = True):
        self.config_path = config_path
        self.use_database = use_database
        
        try:
            self.db = DatabaseConnector()
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
        
        if use_database:
            self.config = RuleConfig.from_database(self.db, fallback_to_file=True, config_path=config_path)
        else:
            self.config = RuleConfig.from_file(config_path)
        
        self.config.validate()
        
        self.stop_event = Event()
        self.last_run_times = {}
        self.run_stats = {
            'engine_runs': 0,
            'learning_runs': 0,
            'retraining_runs': 0,
            'last_engine_run': None,
            'last_learning_run': None,
            'last_retraining_run': None,
            'errors': []
        }
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, stopping...")
        self.stop_event.set()
    
    def run_engine(self, campaigns: Optional[List[int]] = None, 
                   sync: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """Run AI Rule Engine analysis cycle"""
        logger.info("=" * 60)
        logger.info("Running AI Rule Engine Analysis Cycle")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        result = {
            'success': False,
            'start_time': start_time.isoformat(),
            'duration_seconds': 0,
            'recommendations_count': 0,
            'error': None
        }
        
        try:
            class Args:
                def __init__(self, campaigns_list, dry_run_flag, sync_flag):
                    self.campaigns = campaigns_list
                    self.output = f'reports/ai_recommendations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                    self.format = 'json'
                    self.log_level = 'INFO'
                    self.max_recommendations = 100
                    self.min_confidence = 0.3
                    self.dry_run = dry_run_flag
                    self.sync = sync_flag
                    self.skip_download = False
                    self.skip_upload = False
                    self.continuous = False
                    self.interval = 3600
            
            args = Args(campaigns, dry_run, sync)
            recommendations = run_analysis_cycle(self.config, self.db, args, f"engine_run_{self.run_stats['engine_runs'] + 1}")
            
            result['success'] = True
            result['recommendations_count'] = len(recommendations) if recommendations else 0
            result['end_time'] = datetime.now().isoformat()
            result['duration_seconds'] = (datetime.now() - start_time).total_seconds()
            
            self.run_stats['engine_runs'] += 1
            self.run_stats['last_engine_run'] = datetime.now().isoformat()
            self.last_run_times['engine'] = datetime.now()
            
            logger.info(f"Engine run completed: {result['recommendations_count']} recommendations in {result['duration_seconds']:.1f}s")
            
        except Exception as e:
            result['error'] = str(e)
            result['end_time'] = datetime.now().isoformat()
            result['duration_seconds'] = (datetime.now() - start_time).total_seconds()
            self.run_stats['errors'].append({
                'time': datetime.now().isoformat(),
                'component': 'engine',
                'error': str(e)
            })
            logger.error(f"Engine run failed: {e}", exc_info=True)
        
        return result
    
    def run_learning(self) -> Dict[str, Any]:
        """Run learning loop evaluation only"""
        logger.info("=" * 60)
        logger.info("Running Learning Loop Evaluation")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        result = {
            'success': False,
            'start_time': start_time.isoformat(),
            'duration_seconds': 0,
            'evaluated': 0,
            'outcomes': None,
            'error': None
        }
        
        try:
            from src.ai_rule_engine.learning_loop import LearningLoop
            from src.ai_rule_engine.evaluation_pipeline import EvaluationPipeline
            from src.ai_rule_engine.learning_loop import ModelTrainer
            
            learning_loop = LearningLoop(self.config.__dict__, self.db)
            model_trainer = ModelTrainer(self.config.__dict__, self.db)
            
            evaluation_pipeline = EvaluationPipeline(
                self.config.__dict__, self.db, learning_loop, model_trainer
            )
            
            eval_results = evaluation_pipeline.run_daily_evaluation()
            
            result['success'] = True
            result['evaluated'] = eval_results.get('evaluation', {}).get('evaluated', 0)
            result['outcomes'] = eval_results
            result['end_time'] = datetime.now().isoformat()
            result['duration_seconds'] = (datetime.now() - start_time).total_seconds()
            
            self.run_stats['learning_runs'] += 1
            self.run_stats['last_learning_run'] = datetime.now().isoformat()
            self.last_run_times['learning'] = datetime.now()
            
            logger.info(f"Learning evaluation completed: {result['evaluated']} outcomes evaluated in {result['duration_seconds']:.1f}s")
            
        except Exception as e:
            result['error'] = str(e)
            result['end_time'] = datetime.now().isoformat()
            result['duration_seconds'] = (datetime.now() - start_time).total_seconds()
            self.run_stats['errors'].append({
                'time': datetime.now().isoformat(),
                'component': 'learning',
                'error': str(e)
            })
            logger.error(f"Learning evaluation failed: {e}", exc_info=True)
        
        return result
    
    def run_retraining(self, force: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """Run model retraining pipeline"""
        logger.info("=" * 60)
        logger.info("Running Model Retraining Pipeline")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        result = {
            'success': False,
            'start_time': start_time.isoformat(),
            'duration_seconds': 0,
            'training_results': None,
            'promoted': False,
            'error': None
        }
        
        try:
            pipeline = AutomatedRetrainingPipeline(self.config, self.db, dry_run=dry_run)
            training_results = pipeline.run_retraining_pipeline(force=force)
            
            # Handle case where training_results might be None
            if training_results is None:
                result['error'] = 'Pipeline returned None'
                result['success'] = False
            else:
                result['success'] = training_results.get('error') is None
                result['training_results'] = training_results
                # Safely get promotion status
                promotion = training_results.get('promotion', {})
                result['promoted'] = promotion.get('status') == 'promoted' if promotion else False
            
            result['end_time'] = datetime.now().isoformat()
            result['duration_seconds'] = (datetime.now() - start_time).total_seconds()
            
            self.run_stats['retraining_runs'] += 1
            self.run_stats['last_retraining_run'] = datetime.now().isoformat()
            self.last_run_times['retraining'] = datetime.now()
            
            status = "promoted" if result['promoted'] else "not promoted"
            if result.get('error'):
                status = f"failed: {result['error']}"
            logger.info(f"Retraining completed: {status} in {result['duration_seconds']:.1f}s")
            
        except Exception as e:
            result['error'] = str(e)
            result['end_time'] = datetime.now().isoformat()
            result['duration_seconds'] = (datetime.now() - start_time).total_seconds()
            self.run_stats['errors'].append({
                'time': datetime.now().isoformat(),
                'component': 'retraining',
                'error': str(e)
            })
            logger.error(f"Retraining failed: {e}", exc_info=True)
        
        return result
    
    def run_all(self, campaigns: Optional[List[int]] = None,
                sync: bool = False, dry_run: bool = False,
                skip_retraining: bool = False) -> Dict[str, Any]:
        """Run all components in sequence: engine -> learning -> retraining"""
        logger.info("=" * 60)
        logger.info("Running Complete AI System Pipeline")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        results = {
            'start_time': start_time.isoformat(),
            'engine': None,
            'learning': None,
            'retraining': None,
            'success': False,
            'duration_seconds': 0
        }
        
        engine_result = self.run_engine(campaigns=campaigns, sync=sync, dry_run=dry_run)
        results['engine'] = engine_result
        
        if not engine_result['success']:
            logger.warning("Engine run failed, continuing with learning anyway...")
        
        learning_result = self.run_learning()
        results['learning'] = learning_result
        
        if not skip_retraining:
            retraining_result = self.run_retraining(dry_run=dry_run)
            results['retraining'] = retraining_result
        else:
            logger.info("Skipping retraining (use --skip-retraining to skip)")
            results['retraining'] = {'skipped': True}
        
        results['end_time'] = datetime.now().isoformat()
        results['duration_seconds'] = (datetime.now() - start_time).total_seconds()
        results['success'] = all([
            engine_result.get('success', False),
            learning_result.get('success', False),
            results['retraining'].get('success', True) if not results['retraining'].get('skipped') else True
        ])
        
        logger.info(f"Complete pipeline finished in {results['duration_seconds']:.1f}s")
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status and health information"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'run_stats': self.run_stats.copy(),
            'config_enabled': {
                'learning_loop': self.config.enable_learning_loop,
                'advanced_bid_optimization': self.config.enable_advanced_bid_optimization,
                'intelligence_engines': self.config.enable_intelligence_engines,
                're_entry_control': self.config.enable_re_entry_control
            },
            'last_runs': {},
            'database_connected': False,
            'recent_errors': self.run_stats['errors'][-10:] if self.run_stats['errors'] else []
        }
        
        for component in ['engine', 'learning', 'retraining']:
            if component in self.last_run_times:
                last_run = self.last_run_times[component]
                age_seconds = (datetime.now() - last_run).total_seconds()
                status['last_runs'][component] = {
                    'last_run_time': last_run.isoformat(),
                    'age_seconds': age_seconds,
                    'age_hours': age_seconds / 3600,
                    'age_days': age_seconds / 86400
                }
            else:
                status['last_runs'][component] = {
                    'last_run_time': None,
                    'status': 'never_run'
                }
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            status['database_connected'] = True
        except Exception as e:
            status['database_connected'] = False
            status['database_error'] = str(e)
        
        return status
    
    def schedule(self, engine_interval_hours: int = 6,
                 learning_interval_hours: int = 24,
                 retraining_interval_hours: int = 168,
                 sync: bool = False,
                 dry_run: bool = False) -> None:
        """Run scheduled execution (daemon mode)"""
        logger.info("=" * 60)
        logger.info("Starting Scheduled Execution Mode")
        logger.info("=" * 60)
        logger.info(f"Engine interval: {engine_interval_hours} hours")
        logger.info(f"Learning interval: {learning_interval_hours} hours")
        logger.info(f"Retraining interval: {retraining_interval_hours} hours")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        next_engine_run = datetime.now()
        next_learning_run = datetime.now()
        next_retraining_run = datetime.now()
        
        while not self.stop_event.is_set():
            now = datetime.now()
            
            if now >= next_engine_run:
                logger.info("Scheduled engine run starting...")
                try:
                    self.run_engine(sync=sync, dry_run=dry_run)
                except Exception as e:
                    logger.error(f"Scheduled engine run error: {e}")
                next_engine_run = now + timedelta(hours=engine_interval_hours)
                logger.info(f"Next engine run scheduled for: {next_engine_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if now >= next_learning_run:
                logger.info("Scheduled learning evaluation starting...")
                try:
                    self.run_learning()
                except Exception as e:
                    logger.error(f"Scheduled learning run error: {e}")
                next_learning_run = now + timedelta(hours=learning_interval_hours)
                logger.info(f"Next learning run scheduled for: {next_learning_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if now >= next_retraining_run:
                logger.info("Scheduled retraining starting...")
                try:
                    self.run_retraining(dry_run=dry_run)
                except Exception as e:
                    logger.error(f"Scheduled retraining error: {e}")
                next_retraining_run = now + timedelta(hours=retraining_interval_hours)
                logger.info(f"Next retraining scheduled for: {next_retraining_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            sleep_seconds = min(
                (next_engine_run - now).total_seconds(),
                (next_learning_run - now).total_seconds(),
                (next_retraining_run - now).total_seconds(),
                60
            )
            
            if sleep_seconds > 0:
                self.stop_event.wait(sleep_seconds)
        
        logger.info("Scheduled execution stopped")


def print_status(status: Dict[str, Any]):
    """Print formatted status information"""
    print("\n" + "=" * 60)
    print("AI SYSTEM STATUS")
    print("=" * 60)
    print(f"Timestamp: {status['timestamp']}")
    print(f"\nDatabase: {'Connected' if status['database_connected'] else 'Disconnected'}")
    
    print(f"\nConfiguration Enabled:")
    for key, value in status['config_enabled'].items():
        print(f"  {key}: {'Yes' if value else 'No'}")
    
    print(f"\nRun Statistics:")
    print(f"  Engine runs: {status['run_stats']['engine_runs']}")
    print(f"  Learning runs: {status['run_stats']['learning_runs']}")
    print(f"  Retraining runs: {status['run_stats']['retraining_runs']}")
    
    print(f"\nLast Run Times:")
    for component, info in status['last_runs'].items():
        if info.get('last_run_time'):
            age = info['age_seconds']
            if age < 3600:
                age_str = f"{age/60:.1f} minutes ago"
            elif age < 86400:
                age_str = f"{age/3600:.1f} hours ago"
            else:
                age_str = f"{age/86400:.1f} days ago"
            print(f"  {component.capitalize()}: {info['last_run_time'][:19]} ({age_str})")
        else:
            print(f"  {component.capitalize()}: Never run")
    
    if status['recent_errors']:
        print(f"\nRecent Errors ({len(status['recent_errors'])}):")
        for error in status['recent_errors'][-5]:
            print(f"  [{error['time'][:19]}] {error['component']}: {error['error'][:100]}")
    else:
        print("\nNo recent errors")
    
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Unified Management System for AI Rule Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('command', choices=[
        'run-engine', 'run-learning', 'run-retraining', 'run-all',
        'status', 'schedule', 'stop'
    ], help='Command to execute')
    
    parser.add_argument('--config', '-c', default='config/ai_rule_engine.json',
                       help='Configuration file path')
    parser.add_argument('--campaigns', '-p', nargs='+', type=int,
                       help='Specific campaign IDs to analyze (for run-engine)')
    parser.add_argument('--sync', action='store_true',
                       help='Enable Amazon API sync (download/upload)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run without making changes')
    parser.add_argument('--force-retrain', action='store_true',
                       help='Force retraining even if not needed')
    parser.add_argument('--skip-retraining', action='store_true',
                       help='Skip retraining in run-all command')
    
    parser.add_argument('--engine-interval', type=int, default=6,
                       help='Engine run interval in hours (for schedule mode, default: 6)')
    parser.add_argument('--learning-interval', type=int, default=24,
                       help='Learning evaluation interval in hours (for schedule mode, default: 24)')
    parser.add_argument('--retraining-interval', type=int, default=168,
                       help='Retraining interval in hours (for schedule mode, default: 168 = 1 week)')
    
    args = parser.parse_args()
    
    manager = AISystemManager(config_path=args.config)
    
    if args.command == 'run-engine':
        result = manager.run_engine(campaigns=args.campaigns, sync=args.sync, dry_run=args.dry_run)
        print(f"\nEngine Run Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"Recommendations: {result['recommendations_count']}")
        print(f"Duration: {result['duration_seconds']:.1f}s")
        if result.get('error'):
            print(f"Error: {result['error']}")
        sys.exit(0 if result['success'] else 1)
    
    elif args.command == 'run-learning':
        result = manager.run_learning()
        print(f"\nLearning Evaluation Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"Evaluated: {result['evaluated']}")
        print(f"Duration: {result['duration_seconds']:.1f}s")
        if result.get('error'):
            print(f"Error: {result['error']}")
        sys.exit(0 if result['success'] else 1)
    
    elif args.command == 'run-retraining':
        result = manager.run_retraining(force=args.force_retrain, dry_run=args.dry_run)
        print(f"\nRetraining Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"Model Promoted: {'Yes' if result.get('promoted') else 'No'}")
        print(f"Duration: {result['duration_seconds']:.1f}s")
        if result.get('error'):
            print(f"Error: {result['error']}")
        sys.exit(0 if result['success'] else 1)
    
    elif args.command == 'run-all':
        results = manager.run_all(
            campaigns=args.campaigns,
            sync=args.sync,
            dry_run=args.dry_run,
            skip_retraining=args.skip_retraining
        )
        print(f"\nComplete Pipeline Result: {'SUCCESS' if results['success'] else 'FAILED'}")
        print(f"Engine: {'SUCCESS' if results['engine']['success'] else 'FAILED'}")
        print(f"Learning: {'SUCCESS' if results['learning']['success'] else 'FAILED'}")
        if not results['retraining'].get('skipped'):
            print(f"Retraining: {'SUCCESS' if results['retraining']['success'] else 'FAILED'}")
        print(f"Total Duration: {results['duration_seconds']:.1f}s")
        sys.exit(0 if results['success'] else 1)
    
    elif args.command == 'status':
        status = manager.get_status()
        print_status(status)
        sys.exit(0)
    
    elif args.command == 'schedule':
        manager.schedule(
            engine_interval_hours=args.engine_interval,
            learning_interval_hours=args.learning_interval,
            retraining_interval_hours=args.retraining_interval,
            sync=args.sync,
            dry_run=args.dry_run
        )
        sys.exit(0)
    
    elif args.command == 'stop':
        print("Stop command: This would stop a running daemon process")
        print("Currently, scheduled execution runs in foreground. Use Ctrl+C to stop.")
        sys.exit(0)


if __name__ == '__main__':
    main()

