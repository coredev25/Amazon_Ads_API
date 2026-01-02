#!/bin/bash
# Convenience wrapper script for manage_ai_system.py

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT" || exit 1

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the management script with all arguments
python3 "$SCRIPT_DIR/manage_ai_system.py" "$@"

