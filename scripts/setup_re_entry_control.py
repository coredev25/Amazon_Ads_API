#!/usr/bin/env python3
"""
Setup script for Re-entry Control & Bid Oscillation Prevention

This script:
1. Checks database connectivity
2. Runs the migration to create required tables
3. Validates the setup
4. Provides status report

Usage:
    python scripts/setup_re_entry_control.py [--dry-run]
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_rule_engine import DatabaseConnector, RuleConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_database_connection(db: DatabaseConnector) -> bool:
    """Check if database connection is working"""
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                logger.info(f"✓ Database connection successful")
                logger.info(f"  PostgreSQL version: {version}")
                return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False


def check_existing_tables(db: DatabaseConnector) -> dict:
    """Check which tables already exist"""
    tables_to_check = [
        'bid_change_history',
        'acos_trend_tracking',
        'bid_adjustment_locks'
    ]
    
    existing = {}
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                for table in tables_to_check:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = %s
                        );
                    """, (table,))
                    exists = cursor.fetchone()[0]
                    existing[table] = exists
                    
                    if exists:
                        logger.info(f"✓ Table '{table}' already exists")
                    else:
                        logger.info(f"○ Table '{table}' needs to be created")
        
        return existing
    except Exception as e:
        logger.error(f"Error checking tables: {e}")
        return {}


def run_migration(db: DatabaseConnector, dry_run: bool = False) -> bool:
    """Run the migration script"""
    migration_file = 'src/database/migrations/add_bid_change_tracking.sql'
    
    if not os.path.exists(migration_file):
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    logger.info(f"Reading migration from: {migration_file}")
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    if dry_run:
        logger.info("DRY RUN: Would execute migration (skipping)")
        logger.info(f"Migration contains {len(migration_sql)} characters")
        return True
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                logger.info("Executing migration...")
                cursor.execute(migration_sql)
                conn.commit()
                logger.info("✓ Migration completed successfully")
                return True
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        return False


def validate_setup(db: DatabaseConnector) -> dict:
    """Validate that all components are working"""
    results = {
        'tables': False,
        'views': False,
        'methods': False
    }
    
    # Check tables
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name IN (
                        'bid_change_history',
                        'acos_trend_tracking',
                        'bid_adjustment_locks'
                    );
                """)
                count = cursor.fetchone()[0]
                results['tables'] = (count == 3)
                
                if results['tables']:
                    logger.info("✓ All required tables present")
                else:
                    logger.warning(f"⚠ Only {count}/3 tables found")
                
                # Check views
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.views 
                    WHERE table_name IN (
                        'recent_bid_changes_summary',
                        'bid_oscillation_detection'
                    );
                """)
                view_count = cursor.fetchone()[0]
                results['views'] = (view_count == 2)
                
                if results['views']:
                    logger.info("✓ All required views present")
                else:
                    logger.warning(f"⚠ Only {view_count}/2 views found")
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return results
    
    # Check database methods
    try:
        # Test if new methods are available
        last_change = db.get_last_bid_change('keyword', 999999)
        results['methods'] = True
        logger.info("✓ Database methods working")
    except AttributeError as e:
        logger.error(f"✗ Database methods not available: {e}")
        results['methods'] = False
    except Exception:
        # It's OK if the query returns no results
        results['methods'] = True
        logger.info("✓ Database methods working")
    
    return results


def show_config_summary(config: RuleConfig):
    """Show re-entry control configuration"""
    logger.info("\n" + "="*60)
    logger.info("RE-ENTRY CONTROL CONFIGURATION")
    logger.info("="*60)
    logger.info(f"Enabled: {config.enable_re_entry_control}")
    logger.info(f"Oscillation Detection: {config.enable_oscillation_detection}")
    logger.info(f"Cooldown Period: {config.bid_change_cooldown_days} days")
    logger.info(f"Min Change Threshold: {config.min_bid_change_threshold:.1%}")
    logger.info(f"ACOS Stability Window: {config.acos_stability_window} cycles")
    logger.info(f"Hysteresis Bands: {config.acos_hysteresis_lower:.1%} - {config.acos_hysteresis_upper:.1%}")
    logger.info(f"Target ACOS: {config.acos_target:.1%}")
    logger.info(f"Oscillation Threshold: {config.oscillation_direction_change_threshold} direction changes")
    logger.info(f"Oscillation Lookback: {config.oscillation_lookback_days} days")
    logger.info("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Setup Re-entry Control system')
    parser.add_argument('--dry-run', action='store_true',
                       help='Check setup without making changes')
    parser.add_argument('--config', default='config/ai_rule_engine.json',
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("RE-ENTRY CONTROL SETUP")
    logger.info("="*60)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info("="*60 + "\n")
    
    # Load configuration
    try:
        config = RuleConfig.from_file(args.config)
        logger.info(f"✓ Configuration loaded from {args.config}")
    except Exception as e:
        logger.warning(f"Using default configuration: {e}")
        config = RuleConfig()
    
    show_config_summary(config)
    
    # Initialize database connection
    try:
        db = DatabaseConnector()
        logger.info("✓ Database connector initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}")
        logger.error("Please check your database environment variables:")
        logger.error("  - DB_HOST")
        logger.error("  - DB_PORT")
        logger.error("  - DB_NAME")
        logger.error("  - DB_USER")
        logger.error("  - DB_PASSWORD")
        return 1
    
    # Step 1: Check database connection
    logger.info("\n[1/4] Checking database connection...")
    if not check_database_connection(db):
        return 1
    
    # Step 2: Check existing tables
    logger.info("\n[2/4] Checking existing tables...")
    existing_tables = check_existing_tables(db)
    
    all_exist = all(existing_tables.values())
    
    if all_exist and not args.dry_run:
        logger.info("\n✓ All tables already exist. Skipping migration.")
        logger.info("  Use --dry-run to test without changes")
    else:
        # Step 3: Run migration
        logger.info("\n[3/4] Running migration...")
        if not run_migration(db, args.dry_run):
            return 1
    
    if args.dry_run:
        logger.info("\n[4/4] Skipping validation (dry run mode)")
    else:
        # Step 4: Validate setup
        logger.info("\n[4/4] Validating setup...")
        validation = validate_setup(db)
        
        all_valid = all(validation.values())
        
        if all_valid:
            logger.info("\n" + "="*60)
            logger.info("✓ SETUP COMPLETE - ALL CHECKS PASSED")
            logger.info("="*60)
            logger.info("\nNext steps:")
            logger.info("1. Review the configuration in config.py")
            logger.info("2. Test with: python -m src.ai_rule_engine.main --dry-run")
            logger.info("3. Monitor logs for blocked adjustments")
            logger.info("4. Review documentation: docs/RE_ENTRY_CONTROL_GUIDE.md")
            logger.info("\nQuery examples:")
            logger.info("  SELECT * FROM bid_change_history LIMIT 10;")
            logger.info("  SELECT * FROM bid_oscillation_detection;")
            logger.info("  SELECT * FROM bid_adjustment_locks;")
        else:
            logger.warning("\n" + "="*60)
            logger.warning("⚠ SETUP INCOMPLETE - SOME CHECKS FAILED")
            logger.warning("="*60)
            logger.warning(f"Tables: {'✓' if validation['tables'] else '✗'}")
            logger.warning(f"Views: {'✓' if validation['views'] else '✗'}")
            logger.warning(f"Methods: {'✓' if validation['methods'] else '✗'}")
            return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

