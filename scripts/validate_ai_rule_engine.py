#!/usr/bin/env python3
"""
Quick validation script for AI Rule Engine
"""

import sys
import os

def main():
    """Quick validation"""
    print("Validating AI Rule Engine...")
    
    try:
        from src.ai_rule_engine import AIRuleEngine, RuleConfig, DatabaseConnector
        print("✓ Modules imported successfully")
        
        config = RuleConfig.from_file('config/ai_rule_engine.json')
        config.validate()
        print("✓ Configuration loaded and validated")
        
        print("\n✅ AI Rule Engine is ready!")
        print("\nTo run the engine:")
        print("1. Set database environment variables (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)")
        print("2. Run: python3 scripts/run_ai_rule_engine.py")
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
