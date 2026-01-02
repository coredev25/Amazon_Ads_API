#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT" || exit 1

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================="
echo "Amazon Ads API - Application Runner"
echo "==========================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    if [ -f "env.example" ]; then
        echo "Creating .env from env.example..."
        cp env.example .env
        echo -e "${GREEN}✓ Created .env file. Please update it with your credentials.${NC}"
    else
        echo -e "${RED}✗ Error: env.example file not found${NC}"
        exit 1
    fi
fi

# Check if dashboard .env exists
if [ ! -f "dashboard/.env" ]; then
    echo -e "${YELLOW}⚠️  Warning: dashboard/.env file not found${NC}"
    if [ -f "dashboard/env.example" ]; then
        echo "Creating dashboard/.env from env.example..."
        cp dashboard/env.example dashboard/.env
        echo -e "${GREEN}✓ Created dashboard/.env file. Please update it with your credentials.${NC}"
    fi
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo -e "${YELLOW}⚠️  Warning: Virtual environment not found${NC}"
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing Python dependencies..."
    pip install -q -r requirements.txt
    if [ -f "dashboard/requirements.txt" ]; then
        pip install -q -r dashboard/requirements.txt
    fi
    echo -e "${GREEN}✓ Virtual environment created and dependencies installed${NC}"
fi

# Check if Node.js dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
    echo -e "${GREEN}✓ Node.js dependencies installed${NC}"
fi

# Check if frontend dependencies are installed
if [ ! -d "dashboard/frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd dashboard/frontend
    npm install
    cd "$PROJECT_ROOT"
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
fi

echo ""
echo -e "${GREEN}Starting services...${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"
    kill $API_PID $FRONTEND_PID 2>/dev/null || true
    wait $API_PID $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}Services stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start API server
echo -e "${GREEN}Starting API server on port 8000...${NC}"
cd "$PROJECT_ROOT"
python3 -m uvicorn dashboard.api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!
sleep 3

# Check if API started successfully
if ! kill -0 $API_PID 2>/dev/null; then
    echo -e "${RED}✗ Failed to start API server${NC}"
    exit 1
fi

echo -e "${GREEN}✓ API server started (PID: $API_PID)${NC}"
echo "  API URL: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""

# Start Frontend server
echo -e "${GREEN}Starting frontend server on port 3000...${NC}"
cd "$PROJECT_ROOT/dashboard/frontend"
npm run dev &
FRONTEND_PID=$!
sleep 5

# Check if Frontend started successfully
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}✗ Failed to start frontend server${NC}"
    kill $API_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}✓ Frontend server started (PID: $FRONTEND_PID)${NC}"
echo "  Frontend URL: http://localhost:3000"
echo ""

echo -e "${GREEN}=========================================="
echo "✓ All services are running!"
echo "==========================================${NC}"
echo ""
echo "Services:"
echo "  - API Server:    http://localhost:8000"
echo "  - API Docs:      http://localhost:8000/docs"
echo "  - Frontend:      http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for processes
wait $API_PID $FRONTEND_PID

