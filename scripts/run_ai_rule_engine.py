#!/usr/bin/env python3
"""
Convenience script to run the AI Rule Engine
"""

import os
import sys
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    """Run the AI Rule Engine with common configurations"""
    
    # Ensure we're in the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    
    # Check if database environment variables are set
    required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("Error: Missing required database environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these environment variables:")
        print("export DB_HOST='localhost'")
        print("export DB_PORT='5432'")
        print("export DB_NAME='amazon_ads'")
        print("export DB_USER='postgres'")
        print("export DB_PASSWORD='your_password'")
        sys.exit(1)
    
    # Parse command line arguments
    args = sys.argv[1:]
    
    # Default arguments
    default_args = [
        '--config', 'config/ai_rule_engine.json',
        '--output', f'reports/ai_recommendations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        '--log-level', 'INFO'
    ]
    
    # Combine default and user arguments
    all_args = default_args + args
    
    # Build command
    cmd = [sys.executable, '-m', 'src.ai_rule_engine.main'] + all_args
    
    print(f"Running AI Rule Engine...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        # Run the command
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\nAI Rule Engine completed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"\nAI Rule Engine failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\nAI Rule Engine interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError running AI Rule Engine: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
