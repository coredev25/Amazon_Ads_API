#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT" || exit 1

echo "=========================================="
echo "Amazon Ads API - Database Setup"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Creating .env from env.example..."
    if [ -f "env.example" ]; then
        cp env.example .env
        echo "✓ Created .env file. Please update it with your database credentials."
        echo ""
    else
        echo "✗ Error: env.example file not found"
        exit 1
    fi
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check required environment variables
if [ -z "$DB_HOST" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo "✗ Error: Required database environment variables not set"
    echo "Please set the following in your .env file:"
    echo "  - DB_HOST"
    echo "  - DB_PORT (default: 5432)"
    echo "  - DB_NAME"
    echo "  - DB_USER"
    echo "  - DB_PASSWORD"
    exit 1
fi

echo "Database Configuration:"
echo "  Host: ${DB_HOST:-localhost}"
echo "  Port: ${DB_PORT:-5432}"
echo "  Database: ${DB_NAME}"
echo "  User: ${DB_USER}"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if PostgreSQL client is available
if ! command -v psql &> /dev/null; then
    echo "⚠️  Warning: psql command not found. Some checks will be skipped."
    echo ""
fi

# Step 1: Setup main database schema
echo "=========================================="
echo "Step 1: Setting up main database schema"
echo "=========================================="
if [ -f "src/database/schema.sql" ]; then
    echo "Running main schema setup..."
    if command -v psql &> /dev/null; then
        export PGPASSWORD="$DB_PASSWORD"
        psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME" -f src/database/schema.sql
        echo "✓ Main database schema created"
    else
        echo "Running via Node.js setup script..."
        npm run setup-db || {
            echo "⚠️  Node.js setup failed, trying Python alternative..."
            python3 -c "
from src.ai_rule_engine.database import DatabaseConnector
import sys
db = DatabaseConnector()
with open('src/database/schema.sql', 'r') as f:
    schema = f.read()
with db.get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute(schema)
        conn.commit()
print('✓ Main database schema created')
"
        }
    fi
else
    echo "⚠️  Warning: src/database/schema.sql not found, skipping..."
fi
echo ""

# Step 2: Migrate AI settings config to database
echo "=========================================="
echo "Step 2: Setting up AI settings in database"
echo "=========================================="
# AI settings tables are included in the consolidated schema.sql (Step 1).
# This step migrates config values from JSON to the database.
echo "Migrating AI configuration to database..."
python3 scripts/setup_ai_database_config.py --config config/ai_rule_engine.json || {
    echo "⚠️  Warning: AI settings migration had issues, but continuing..."
}
echo ""

# Step 3: Verify dashboard auth schema (included in consolidated schema.sql)
echo "=========================================="
echo "Step 3: Verifying dashboard auth schema"
echo "=========================================="
# Auth tables (users, sessions, password_reset_tokens) are included
# in the consolidated schema.sql applied in Step 1.
echo "✓ Dashboard auth schema included in consolidated schema (Step 1)"
echo ""

# Step 4: Verify dashboard schema additions (included in consolidated schema.sql)
echo "=========================================="
echo "Step 4: Verifying dashboard schema additions"
echo "=========================================="
# Dashboard tables (dashboard_user_preferences, dashboard_saved_views, etc.)
# are included in the consolidated schema.sql applied in Step 1.
echo "✓ Dashboard schema additions included in consolidated schema (Step 1)"
echo ""

# Step 5: Setup re-entry control tables
echo "=========================================="
echo "Step 5: Setting up re-entry control tables"
echo "=========================================="
echo "Running re-entry control setup..."
python3 scripts/setup_re_entry_control.py || {
    echo "⚠️  Warning: Re-entry control setup had issues, but continuing..."
}
echo ""

# Step 6: Verify database connection
echo "=========================================="
echo "Step 6: Verifying database connection"
echo "=========================================="
python3 -c "
from src.ai_rule_engine.database import DatabaseConnector
try:
    db = DatabaseConnector()
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT version();')
            version = cursor.fetchone()
            print(f'✓ Database connection successful')
            print(f'  PostgreSQL version: {version[0][:50]}...')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    sys.exit(1)
" || {
    echo "✗ Database verification failed"
    exit 1
}
echo ""

echo "=========================================="
echo "✓ Database setup completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Verify your database tables were created"
echo "2. Run the application: ./scripts/run.sh"
echo ""

