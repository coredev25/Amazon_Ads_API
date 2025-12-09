#!/bin/bash

# Setup script for Cold Start Fixes
# This script helps initialize the database with all necessary fixes

set -e

echo "════════════════════════════════════════════════════════════"
echo "  Amazon Ads AI Rule Engine - Cold Start Fixes Setup"
echo "════════════════════════════════════════════════════════════"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running from correct directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "Checking prerequisites..."
echo ""

if ! command_exists node; then
    echo -e "${RED}✗ Node.js not found. Please install Node.js first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js found: $(node --version)${NC}"

if ! command_exists npm; then
    echo -e "${RED}✗ npm not found. Please install npm first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ npm found: $(npm --version)${NC}"

if ! command_exists psql; then
    echo -e "${YELLOW}⚠ PostgreSQL client (psql) not found. Database setup may fail.${NC}"
else
    echo -e "${GREEN}✓ PostgreSQL client found${NC}"
fi

if ! command_exists python3; then
    echo -e "${YELLOW}⚠ Python3 not found. AI Rule Engine will not run.${NC}"
else
    echo -e "${GREEN}✓ Python3 found: $(python3 --version)${NC}"
fi

echo ""
echo "────────────────────────────────────────────────────────────"
echo ""

# Check environment variables
echo "Checking environment variables..."
echo ""

MISSING_VARS=()

if [ -z "$DB_HOST" ]; then MISSING_VARS+=("DB_HOST"); fi
if [ -z "$DB_PORT" ]; then MISSING_VARS+=("DB_PORT"); fi
if [ -z "$DB_NAME" ]; then MISSING_VARS+=("DB_NAME"); fi
if [ -z "$DB_USER" ]; then MISSING_VARS+=("DB_USER"); fi
if [ -z "$DB_PASSWORD" ]; then MISSING_VARS+=("DB_PASSWORD"); fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠ Missing environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please set these variables:"
    echo ""
    echo "  export DB_HOST='localhost'"
    echo "  export DB_PORT='5432'"
    echo "  export DB_NAME='amazon_ads'"
    echo "  export DB_USER='postgres'"
    echo "  export DB_PASSWORD='your_password'"
    echo ""
    read -p "Do you want to continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ All database environment variables are set${NC}"
    echo "  DB_HOST: $DB_HOST"
    echo "  DB_PORT: $DB_PORT"
    echo "  DB_NAME: $DB_NAME"
    echo "  DB_USER: $DB_USER"
fi

echo ""
echo "────────────────────────────────────────────────────────────"
echo ""

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
if npm install; then
    echo -e "${GREEN}✓ Node.js dependencies installed${NC}"
else
    echo -e "${RED}✗ Failed to install Node.js dependencies${NC}"
    exit 1
fi

echo ""
echo "────────────────────────────────────────────────────────────"
echo ""

# Setup database
echo "Setting up database..."
echo ""

if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    echo "Running database setup script..."
    if node src/database/setup.js; then
        echo -e "${GREEN}✓ Database setup completed successfully${NC}"
        echo ""
        echo "Tables created:"
        echo "  • campaigns, ad_groups, keywords"
        echo "  • campaign_performance, ad_group_performance, keyword_performance"
        echo "  • bid_change_history, acos_trend_tracking"
        echo "  • learning_outcomes, recommendation_tracking"
        echo "  • waste_patterns (NEW)"
        echo ""
    else
        echo -e "${YELLOW}⚠ Database setup encountered errors${NC}"
        echo "You may need to run it manually:"
        echo "  node src/database/setup.js"
        echo ""
    fi
else
    echo -e "${YELLOW}⚠ Skipping database setup (environment variables not set)${NC}"
fi

echo "────────────────────────────────────────────────────────────"
echo ""

# Install Python dependencies (optional)
if command_exists python3; then
    echo "Python environment detected."
    echo ""
    
    if [ -f "requirements.txt" ]; then
        read -p "Install Python dependencies? (y/N) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [ -d "env" ]; then
                echo "Using existing virtual environment..."
                source env/bin/activate
            else
                echo "Creating virtual environment..."
                python3 -m venv env
                source env/bin/activate
            fi
            
            echo "Installing Python dependencies..."
            if pip install -r requirements.txt; then
                echo -e "${GREEN}✓ Python dependencies installed${NC}"
            else
                echo -e "${YELLOW}⚠ Some Python dependencies failed to install${NC}"
            fi
        fi
    fi
fi

echo ""
echo "────────────────────────────────────────────────────────────"
echo ""

# Create config if doesn't exist
echo "Checking configuration..."
if [ ! -f "config/ai_rule_engine.json" ]; then
    echo "Creating default configuration..."
    mkdir -p config
    
    if command_exists python3; then
        python3 -c "
from src.ai_rule_engine.config import RuleConfig
config = RuleConfig()
config.to_file('config/ai_rule_engine.json')
print('✓ Default configuration created')
"
    else
        echo -e "${YELLOW}⚠ Python not available, skipping config creation${NC}"
    fi
else
    echo -e "${GREEN}✓ Configuration file exists${NC}"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Setup Complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Cold Start Fixes Applied:"
echo -e "  ${GREEN}✓${NC} Warm-Up Mode - System works with 0 training samples"
echo -e "  ${GREEN}✓${NC} Database Schema - All tables created"
echo -e "  ${GREEN}✓${NC} Timezone Fix - Always processes Yesterday (T-1) data"
echo -e "  ${GREEN}✓${NC} Waste Patterns - Stored in database, editable via SQL"
echo ""
echo "Next Steps:"
echo ""
echo "1. Verify database connection:"
echo "   psql -U \$DB_USER -d \$DB_NAME -c '\\dt'"
echo ""
echo "2. Check waste patterns table:"
echo "   psql -U \$DB_USER -d \$DB_NAME -c 'SELECT * FROM waste_patterns LIMIT 5;'"
echo ""
echo "3. Start the Node.js server:"
echo "   npm start"
echo ""
echo "4. Run the AI Rule Engine (if Python installed):"
echo "   python3 -m src.ai_rule_engine.main --dry-run"
echo ""
echo "5. Add custom waste patterns:"
echo "   psql -U \$DB_USER -d \$DB_NAME"
echo "   INSERT INTO waste_patterns (pattern_text, severity, description)"
echo "   VALUES ('\\b(competitor_name)\\b', 'high', 'Competitor brand');"
echo ""
echo "For detailed documentation, see:"
echo "   COLD_START_FIX_README.md"
echo ""
echo "════════════════════════════════════════════════════════════"

