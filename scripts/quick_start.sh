#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT" || exit 1

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "Amazon Ads API - Quick Start"
echo "==========================================${NC}"
echo ""

# Check if database is set up
echo -e "${YELLOW}Checking database setup...${NC}"
if python3 -c "
from src.ai_rule_engine.database import DatabaseConnector
try:
    db = DatabaseConnector()
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';\")
            count = cursor.fetchone()[0]
            if count < 5:
                exit(1)
except:
    exit(1)
" 2>/dev/null; then
    echo -e "${GREEN}✓ Database appears to be set up${NC}"
else
    echo -e "${YELLOW}⚠️  Database not fully set up${NC}"
    read -p "Would you like to run database setup now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Running database setup..."
        bash scripts/setup_database.sh
    else
        echo "Skipping database setup. You can run it later with: ./scripts/setup_database.sh"
    fi
fi

echo ""
echo -e "${BLUE}Starting application...${NC}"
echo ""

# Run the main run script
bash scripts/run.sh

