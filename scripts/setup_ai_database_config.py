#!/usr/bin/env python3
"""
Setup script to initialize AI settings in database
Migrates settings from JSON config file to database
"""

import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_rule_engine.config import RuleConfig
from src.ai_rule_engine.database import DatabaseConnector
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_database_schema(db: DatabaseConnector) -> bool:
    """Create database tables for AI settings"""
    schema_path = Path(__file__).parent.parent / 'src' / 'database' / 'ai_settings_schema.sql'
    
    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        return False
    
    try:
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
                conn.commit()
        
        logger.info("Database schema created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating database schema: {e}")
        return False


def migrate_config_to_database(config_path: str, dry_run: bool = False) -> bool:
    """Migrate config from JSON file to database"""
    logger.info("=" * 60)
    logger.info("AI Configuration Database Migration")
    logger.info("=" * 60)
    
    try:
        db = DatabaseConnector()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
    
    logger.info("Setting up database schema...")
    if not setup_database_schema(db):
        logger.error("Failed to setup database schema")
        return False
    
    logger.info(f"Loading configuration from: {config_path}")
    config = RuleConfig.from_file(config_path)
    
    if dry_run:
        logger.info("DRY RUN: Would save the following settings to database:")
        config_dict = config.to_dict()
        for key, value in list(config_dict.items())[:10]:
            logger.info(f"  {key}: {value}")
        logger.info(f"  ... and {len(config_dict) - 10} more settings")
        return True
    
    logger.info("Saving configuration to database...")
    success = config.to_database(db, created_by='migration_script')
    
    if success:
        logger.info("✓ Configuration saved to database successfully")
        logger.info("You can now use database-backed configuration")
    else:
        logger.error("✗ Failed to save configuration to database")
    
    return success


def main():
    parser = argparse.ArgumentParser(description='Setup AI settings in database')
    parser.add_argument('--config', default='config/ai_rule_engine.json',
                       help='Path to config file to migrate')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be migrated without making changes')
    
    args = parser.parse_args()
    
    success = migrate_config_to_database(args.config, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

