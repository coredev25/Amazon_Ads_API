#!/usr/bin/env python3
"""
Main script for AI Rule Engine
Usage: python -m src.ai_rule_engine.main [options]
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_rule_engine import AIRuleEngine, RuleConfig, DatabaseConnector
from ai_rule_engine.recommendations import Recommendation


def setup_logging(level: str = 'INFO') -> None:
    """Setup logging configuration"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'logs/ai_rule_engine_{datetime.now().strftime("%Y%m%d")}.log')
        ]
    )


def load_config(config_path: str) -> RuleConfig:
    """Load configuration from file or create default"""
    if os.path.exists(config_path):
        return RuleConfig.from_file(config_path)
    else:
        print(f"Config file {config_path} not found, creating default configuration")
        config = RuleConfig()
        config.to_file(config_path)
        return config


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Amazon Ads AI Rule Engine')
    parser.add_argument('--config', '-c', default='config/ai_rule_engine.json',
                       help='Configuration file path')
    parser.add_argument('--campaigns', '-p', nargs='+', type=int,
                       help='Specific campaign IDs to analyze (default: all)')
    parser.add_argument('--output', '-o', default='reports/ai_recommendations.json',
                       help='Output file path')
    parser.add_argument('--format', '-f', choices=['json', 'csv'], default='json',
                       help='Output format')
    parser.add_argument('--log-level', '-l', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Logging level')
    parser.add_argument('--max-recommendations', '-m', type=int, default=100,
                       help='Maximum number of recommendations to generate')
    parser.add_argument('--min-confidence', type=float, default=0.3,
                       help='Minimum confidence threshold for recommendations')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run analysis without making changes')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config(args.config)
        config.validate()
        logger.info("Configuration loaded and validated")
        
        # Setup database connection
        try:
            db_connector = DatabaseConnector()
        except ValueError as e:
            logger.error(f"Database configuration error: {e}")
            logger.error("Please ensure DB_HOST, DB_PORT, DB_NAME, DB_USER, and DB_PASSWORD are set")
            sys.exit(1)
        logger.info("Database connector initialized")
        
        # Initialize AI Rule Engine
        engine = AIRuleEngine(config, db_connector)
        logger.info("AI Rule Engine initialized")
        
        # Run analysis
        logger.info("Starting analysis...")
        recommendations = engine.analyze_campaigns(args.campaigns)
        
        # Filter recommendations
        filtered_recommendations = engine.recommendation_engine.filter_recommendations(
            recommendations,
            max_recommendations=args.max_recommendations,
            min_confidence=args.min_confidence
        )
        
        # Generate summary
        summary = engine.get_recommendations_summary(filtered_recommendations)
        
        # Print summary
        print("\n" + "="*60)
        print("AI RULE ENGINE ANALYSIS RESULTS")
        print("="*60)
        print(f"Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total recommendations generated: {summary['total_recommendations']}")
        print(f"Recommendations by type: {summary['by_type']}")
        print(f"Recommendations by priority: {summary['by_priority']}")
        print(f"Recommendations by entity type: {summary['by_entity_type']}")
        print(f"Total adjustment value: ${summary['total_adjustment_value']:.2f}")
        print("="*60)
        
        # Show top recommendations
        if filtered_recommendations:
            print("\nTOP RECOMMENDATIONS:")
            print("-" * 60)
            for i, rec in enumerate(filtered_recommendations[:10], 1):
                print(f"{i:2d}. {rec.entity_type.upper()} {rec.entity_id} - {rec.entity_name}")
                print(f"     {rec.adjustment_type.upper()}: ${rec.current_value:.2f} → ${rec.recommended_value:.2f}")
                print(f"     Priority: {rec.priority.upper()} | Confidence: {rec.confidence:.1%}")
                print(f"     Reason: {rec.reason}")
                print()
        
        # Export recommendations
        if not args.dry_run:
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
            engine.export_recommendations(filtered_recommendations, args.output, args.format)
            print(f"Recommendations exported to: {args.output}")
        else:
            print("DRY RUN: No changes made")
        
        # Show rule documentation
        if args.log_level == 'DEBUG':
            print("\nRULE DOCUMENTATION:")
            print("-" * 60)
            doc = engine.get_rule_documentation()
            for rule_name, rule_doc in doc.items():
                print(f"\n{rule_name.upper()}:")
                for key, value in rule_doc.items():
                    if isinstance(value, list):
                        print(f"  {key}:")
                        for item in value:
                            print(f"    - {item}")
                    else:
                        print(f"  {key}: {value}")
        
        logger.info("Analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
