# Amazon Ads API - Setup & Run Guide

## Quick Start

### 1. Setup Database
```bash
./scripts/setup_database.sh
```

This script will:
- Check for `.env` file and create from `env.example` if needed
- Set up main database schema
- Set up AI settings schema
- Set up dashboard auth schema
- Set up re-entry control tables
- Verify database connection

### 2. Run Application
```bash
./scripts/run.sh
```

Or use npm:
```bash
npm run run
```

This will start:
- API server on http://localhost:8000
- Frontend on http://localhost:3000

### 3. Quick Start (All-in-One)
```bash
./scripts/quick_start.sh
```

## Prerequisites

1. **PostgreSQL Database**
   - PostgreSQL 12+ installed and running
   - Database created (default: `amazon_ads`)

2. **Python 3.8+**
   - Virtual environment will be created automatically if missing

3. **Node.js 16+**
   - For frontend and some backend scripts

4. **Environment Variables**
   - Copy `env.example` to `.env` and configure
   - Copy `dashboard/env.example` to `dashboard/.env` and configure

## Environment Configuration

### Main `.env` file
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=amazon_ads
DB_USER=postgres
DB_PASSWORD=your_password
```

### Dashboard `.env` file (`dashboard/.env`)
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=amazon_ads
DB_USER=postgres
DB_PASSWORD=your_password
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Manual Setup Steps

### Database Setup
1. Create PostgreSQL database:
   ```sql
   CREATE DATABASE amazon_ads;
   ```

2. Run setup script:
   ```bash
   ./scripts/setup_database.sh
   ```

### Python Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r dashboard/requirements.txt
```

### Node.js Dependencies
```bash
npm install
cd dashboard/frontend && npm install
```

## Running Services Separately

### API Server Only
```bash
cd dashboard
python -m uvicorn api.main:app --reload --port 8000
```

### Frontend Only
```bash
cd dashboard/frontend
npm run dev
```

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check credentials in `.env` file
- Test connection: `psql -h localhost -U postgres -d amazon_ads`

### Port Already in Use
- API (8000): Change `API_PORT` in `dashboard/.env`
- Frontend (3000): Change port in `dashboard/frontend/package.json`

### Missing Dependencies
- Python: `pip install -r requirements.txt`
- Node.js: `npm install` in root and `dashboard/frontend`

## Scripts Reference

- `scripts/setup_database.sh` - Complete database setup
- `scripts/run.sh` - Start API and frontend together
- `scripts/quick_start.sh` - Quick start with checks
- `scripts/manage_ai.sh` - AI system management wrapper

## Access Points

After starting:
- **Frontend Dashboard**: http://localhost:3000
- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/api/health

