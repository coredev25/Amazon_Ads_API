#!/usr/bin/env python3
"""
Setup script for AI Rule Engine
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_directories():
    """Create necessary directories"""
    directories = [
        'logs',
        'reports', 
        'config',
        'src/ai_rule_engine/examples'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def create_default_config():
    """Create default configuration file"""
    config_path = 'config/ai_rule_engine.json'
    
    if not os.path.exists(config_path):
        default_config = {
            "acos_target": 0.30,
            "acos_tolerance": 0.05,
            "acos_bid_adjustment_factor": 0.1,
            "roas_target": 4.0,
            "roas_tolerance": 0.5,
            "roas_bid_adjustment_factor": 0.15,
            "ctr_minimum": 0.5,
            "ctr_target": 2.0,
            "ctr_bid_adjustment_factor": 0.2,
            "bid_floor": 0.01,
            "bid_cap": 10.0,
            "bid_max_adjustment": 0.5,
            "budget_min_daily": 1.0,
            "budget_max_daily": 1000.0,
            "budget_adjustment_factor": 0.2,
            "min_impressions": 100,
            "min_clicks": 5,
            "min_conversions": 1,
            "performance_lookback_days": 7,
            "trend_analysis_days": 14,
            "negative_keyword_ctr_threshold": 0.1,
            "negative_keyword_impression_threshold": 1000,
            "max_daily_adjustments": 3,
            "cooldown_hours": 6
        }
        
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        print(f"✓ Created default configuration: {config_path}")
    else:
        print(f"✓ Configuration already exists: {config_path}")

def create_env_example():
    """Create environment example file"""
    env_example_path = '.env.example'
    
    if not os.path.exists(env_example_path):
        env_content = """# Amazon Ads AI Rule Engine Environment Variables

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=amazon_ads
DB_USER=postgres
DB_PASSWORD=your_db_password

# Optional: Amazon Ads API Configuration (for future integration)
# AMAZON_ADS_CLIENT_ID=your_client_id
# AMAZON_ADS_CLIENT_SECRET=your_client_secret
# AMAZON_ADS_REFRESH_TOKEN=your_refresh_token
# AMAZON_ADS_PROFILE_ID=your_profile_id

# Optional: Logging Configuration
# LOG_LEVEL=INFO
# LOG_FILE=logs/ai_rule_engine.log

# Optional: Email Notifications (for future integration)
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your_email@gmail.com
# SMTP_PASSWORD=your_app_password
# NOTIFICATION_EMAIL=admin@yourcompany.com
"""
        
        with open(env_example_path, 'w') as f:
            f.write(env_content)
        
        print(f"✓ Created environment example: {env_example_path}")
    else:
        print(f"✓ Environment example already exists: {env_example_path}")

def install_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True, capture_output=True)
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error installing dependencies: {e}")
        print("Please install manually: pip install -r requirements.txt")
        return False
    
    return True

def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    
    print(f"✓ Python version: {sys.version.split()[0]}")
    return True

def create_quick_test():
    """Create a quick validation script"""
    test_script_path = 'scripts/validate_ai_rule_engine.py'
    
    test_content = '''#!/usr/bin/env python3
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
        
        print("\\n✅ AI Rule Engine is ready!")
        print("\\nTo run the engine:")
        print("1. Set database environment variables (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)")
        print("2. Run: python3 scripts/run_ai_rule_engine.py")
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
'''
    
    with open(test_script_path, 'w') as f:
        f.write(test_content)
    
    # Make executable
    os.chmod(test_script_path, 0o755)
    print(f"✓ Created validation script: {test_script_path}")

def main():
    """Main setup function"""
    print("Amazon Ads AI Rule Engine Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    print()
    
    # Create directories
    print("Creating directories...")
    create_directories()
    print()
    
    # Create configuration files
    print("Creating configuration files...")
    create_default_config()
    create_env_example()
    print()
    
    # Install dependencies
    print("Installing dependencies...")
    if not install_dependencies():
        print("Please install dependencies manually and run setup again.")
        sys.exit(1)
    print()
    
    # Create validation script
    print("Creating validation script...")
    create_quick_test()
    print()
    
    print("Setup completed successfully!")
    print()
    print("Next steps:")
    print("1. Set database environment variables:")
    print("   export DB_HOST='localhost'")
    print("   export DB_PORT='5432'")
    print("   export DB_NAME='amazon_ads'")
    print("   export DB_USER='postgres'")
    print("   export DB_PASSWORD='your_password'")
    print("2. Run: python3 scripts/validate_ai_rule_engine.py")
    print("3. Run: python3 scripts/run_ai_rule_engine.py --help")
    print("4. Read AI_RULE_ENGINE_DOCUMENTATION.md for detailed usage")

if __name__ == '__main__':
    main()
