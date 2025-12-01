#!/usr/bin/env python3
"""
Model Rollback Script (#16)

Rolls back to a previous model version if current model degrades in production.

Usage:
    python scripts/rollback_model.py --version <version_number> [--dry-run]
"""

import sys
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_rule_engine.model_rollback import ModelRollbackManager
from src.ai_rule_engine.config import RuleConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Rollback Model to Previous Version')
    parser.add_argument('--version', type=int, required=True, help='Version number to rollback to')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--config', type=str, default='config/ai_rule_engine.json', help='Config file path')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = RuleConfig.from_file(args.config)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)
    
    model_path = config.__dict__.get('model_path', 'models/bid_success_model.pkl')
    rollback_manager = ModelRollbackManager(model_path)
    
    # Get available versions
    available_versions = rollback_manager.get_available_versions()
    
    if not available_versions:
        logger.error("No model versions found")
        sys.exit(1)
    
    logger.info(f"Available versions: {available_versions}")
    
    if args.version not in available_versions:
        logger.error(f"Version {args.version} not found. Available: {available_versions}")
        sys.exit(1)
    
    # Get current version (highest version number)
    current_version = max(available_versions)
    
    if args.dry_run:
        logger.info(f"DRY RUN: Would rollback from version {current_version} to version {args.version}")
    else:
        logger.info(f"Rolling back from version {current_version} to version {args.version}")
        success = rollback_manager.rollback_to_version(args.version, current_version)
        
        if success:
            logger.info(f"Successfully rolled back to version {args.version}")
        else:
            logger.error("Rollback failed")
            sys.exit(1)


if __name__ == '__main__':
    main()

