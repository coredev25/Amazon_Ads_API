#!/bin/bash
# Setup Cron Jobs for Automated Model Retraining (#16)
#
# This script sets up daily cron jobs for:
# 1. Automated model retraining pipeline
# 2. Daily evaluation of matured bid changes
#
# Usage: ./scripts/setup_cron_jobs.sh [--dry-run]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="${PROJECT_DIR}/venv/bin/python"
RETRAINING_SCRIPT="${PROJECT_DIR}/scripts/automated_model_retraining.py"
LOG_DIR="${PROJECT_DIR}/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Default to 2 AM daily for retraining
CRON_SCHEDULE="0 2 * * *"

if [ "$1" == "--dry-run" ]; then
    echo "DRY RUN: Would add the following cron job:"
    echo ""
    echo "$CRON_SCHEDULE cd $PROJECT_DIR && $VENV_PATH $RETRAINING_SCRIPT >> $LOG_DIR/retraining.log 2>&1"
    echo ""
    echo "To actually add this cron job, run without --dry-run"
    exit 0
fi

# Check if cron job already exists
CRON_CMD="$CRON_SCHEDULE cd $PROJECT_DIR && $VENV_PATH $RETRAINING_SCRIPT >> $LOG_DIR/retraining.log 2>&1"

if crontab -l 2>/dev/null | grep -q "$RETRAINING_SCRIPT"; then
    echo "Cron job for model retraining already exists"
    echo "Current crontab:"
    crontab -l | grep "$RETRAINING_SCRIPT"
else
    echo "Adding cron job for automated model retraining..."
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "Cron job added successfully!"
    echo ""
    echo "To view cron jobs: crontab -l"
    echo "To remove cron job: crontab -e (then delete the line)"
fi

echo ""
echo "Cron job will run daily at 2 AM"
echo "Logs will be written to: $LOG_DIR/retraining.log"

