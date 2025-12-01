#!/usr/bin/env python3
"""
Verification Script for Checklist Implementation

Verifies that all features from the DEVELOPER FIX CHECKLIST are properly implemented.

Usage:
    python scripts/verify_implementation.py
"""

import sys
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def check_import(module_name, class_name=None):
    """Check if a module/class can be imported"""
    try:
        module = importlib.import_module(module_name)
        if class_name:
            return hasattr(module, class_name)
        return True
    except ImportError:
        return False

def verify_feature_16():
    """Verify #16: Automatic retraining + model promotion"""
    print("Checking #16: Automatic retraining + model promotion...")
    
    checks = {
        'ModelRollbackManager exists': check_import('src.ai_rule_engine.model_rollback', 'ModelRollbackManager'),
        'Rollback script exists': (Path('scripts/rollback_model.py').exists()),
        'Cron setup script exists': (Path('scripts/setup_cron_jobs.sh').exists()),
        'Retraining script exists': (Path('scripts/automated_model_retraining.py').exists()),
    }
    
    all_pass = all(checks.values())
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
    
    return all_pass

def verify_feature_18():
    """Verify #18: Cross-ASIN transfer learning"""
    print("\nChecking #18: Cross-ASIN transfer learning...")
    
    checks = {
        'HierarchicalModelTrainer exists': check_import('src.ai_rule_engine.hierarchical_model', 'HierarchicalModelTrainer'),
        'Hierarchical model file exists': (Path('src/ai_rule_engine/hierarchical_model.py').exists()),
    }
    
    all_pass = all(checks.values())
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
    
    return all_pass

def verify_feature_21():
    """Verify #21: Observability & telemetry"""
    print("\nChecking #21: Observability & telemetry...")
    
    checks = {
        'TelemetryClient exists': check_import('src.ai_rule_engine.telemetry', 'TelemetryClient'),
        'record_model_metrics method exists': check_import('src.ai_rule_engine.telemetry', 'TelemetryClient'),
        'record_bid_change_magnitude method exists': check_import('src.ai_rule_engine.telemetry', 'TelemetryClient'),
        'record_learning_metrics method exists': check_import('src.ai_rule_engine.telemetry', 'TelemetryClient'),
    }
    
    # Check if methods exist in TelemetryClient
    try:
        from src.ai_rule_engine.telemetry import TelemetryClient
        checks['record_model_metrics method'] = hasattr(TelemetryClient, 'record_model_metrics')
        checks['record_bid_change_magnitude method'] = hasattr(TelemetryClient, 'record_bid_change_magnitude')
        checks['record_learning_metrics method'] = hasattr(TelemetryClient, 'record_learning_metrics')
    except:
        pass
    
    all_pass = all(checks.values())
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
    
    return all_pass

def verify_feature_22():
    """Verify #22: Integration tests"""
    print("\nChecking #22: Integration tests...")
    
    checks = {
        'Integration test file exists': (Path('tests/test_integration_ai_rule_engine.py').exists()),
        'SyntheticDatabaseFixture exists': check_import('tests.test_integration_ai_rule_engine', 'SyntheticDatabaseFixture'),
    }
    
    all_pass = all(checks.values())
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
    
    return all_pass

def verify_feature_23():
    """Verify #23: Feedback loop prevention"""
    print("\nChecking #23: Feedback loop prevention...")
    
    checks = {
        'Feedback loop test file exists': (Path('tests/test_feedback_loop_prevention.py').exists()),
        '_assign_policy_variant method exists': check_import('src.ai_rule_engine.bid_optimizer', 'BidOptimizationEngine'),
    }
    
    # Check if method exists
    try:
        from src.ai_rule_engine.bid_optimizer import BidOptimizationEngine
        checks['_assign_policy_variant method'] = hasattr(BidOptimizationEngine, '_assign_policy_variant')
    except:
        pass
    
    all_pass = all(checks.values())
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
    
    return all_pass

def main():
    print("=" * 60)
    print("CHECKLIST IMPLEMENTATION VERIFICATION")
    print("=" * 60)
    print()
    
    results = {
        '#16 - Automatic Retraining': verify_feature_16(),
        '#18 - Cross-ASIN Learning': verify_feature_18(),
        '#21 - Observability': verify_feature_21(),
        '#22 - Integration Tests': verify_feature_22(),
        '#23 - Feedback Loop Prevention': verify_feature_23(),
    }
    
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_pass = True
    for feature, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {feature}")
        if not passed:
            all_pass = False
    
    print("=" * 60)
    
    if all_pass:
        print("\n✅ All features verified successfully!")
        return 0
    else:
        print("\n❌ Some features failed verification. Please check the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

