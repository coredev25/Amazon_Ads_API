# Amazon Ads API Integration - Setup Guide

This guide will walk you through setting up the Amazon Ads API Integration from scratch.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Amazon Ads API Setup](#amazon-ads-api-setup)
3. [PostgreSQL Setup](#postgresql-setup)
4. [Application Setup](#application-setup)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Node.js** (v14 or higher)
   ```bash
   node --version
   # Should output v14.x.x or higher
   ```

   If not installed:
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs
   ```

2. **PostgreSQL** (v12 or higher)
   ```bash
   psql --version
   # Should output psql (PostgreSQL) 12.x or higher
   ```

   If not installed:
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   ```

3. **Git** (optional, for version control)
   ```bash
   git --version
   ```

---

## Amazon Ads API Setup

### Step 1: Create an Amazon Advertising Account

1. Go to [Amazon Advertising](https://advertising.amazon.com)
2. Sign up for a Vendor Central account
3. Verify your account and complete the onboarding

### Step 2: Register Your Application

1. Navigate to [Amazon Advertising API](https://advertising.amazon.com/API/docs/en-us/get-started/overview)
2. Click on **"Register Application"**
3. Fill in the application details:
   - **Application Name**: Amazon Ads Integration
   - **Application Type**: Web Application
   - **Redirect URI**: `http://localhost:3000/callback` (or your preferred callback URL)
4. Save your **Client ID** and **Client Secret**

### Step 3: Obtain Authorization Code

1. Build the authorization URL:
   ```
   https://www.amazon.com/ap/oa?client_id=YOUR_CLIENT_ID&scope=advertising::campaign_management&response_type=code&redirect_uri=http://localhost:3000/callback
   ```

2. Replace `YOUR_CLIENT_ID` with your actual Client ID
3. Open this URL in a browser
4. Log in with your Amazon Advertising credentials
5. Authorize the application
6. You'll be redirected to your callback URL with a `code` parameter
7. Copy the authorization code from the URL

### Step 4: Exchange Code for Refresh Token

Run this curl command (replace placeholders):

```bash
curl -X POST https://api.amazon.com/auth/o2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=YOUR_AUTHORIZATION_CODE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=http://localhost:3000/callback"
```

Response:
```json
{
  "access_token": "Atza|...",
  "refresh_token": "Atzr|...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Save the `refresh_token` - you'll need it for the application!**

### Step 5: Get Your Profile ID

First, get an access token (it's only valid for 1 hour):

```bash
curl -X POST https://api.amazon.com/auth/o2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=YOUR_REFRESH_TOKEN" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

Then get your profile ID:

```bash
curl -X GET https://advertising-api.amazon.com/v2/profiles \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Amazon-Advertising-API-ClientId: YOUR_CLIENT_ID"
```

Response:
```json
[
  {
    "profileId": 1234567890,
    "countryCode": "US",
    "currencyCode": "USD",
    "accountInfo": {
      "marketplaceStringId": "...",
      "type": "vendor"
    }
  }
]
```

**Save the `profileId` - you'll need it for the application!**

---

## PostgreSQL Setup

### Step 1: Start PostgreSQL Service

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql  # Enable auto-start on boot
```

### Step 2: Set PostgreSQL Password

```bash
sudo -u postgres psql
```

In the PostgreSQL prompt:
```sql
ALTER USER postgres WITH PASSWORD 'your_secure_password';
\q
```

### Step 3: Create Application Database

```bash
sudo -u postgres createdb amazon_ads
```

Or using psql:
```bash
sudo -u postgres psql
CREATE DATABASE amazon_ads;
\q
```

### Step 4: Verify Database Creation

```bash
sudo -u postgres psql -l
```

You should see `amazon_ads` in the list.

---

## Application Setup

### Step 1: Navigate to Project Directory

```bash
cd /home/carter/Desktop/AmazonAds
```

### Step 2: Install Dependencies

```bash
npm install
```

This will install all required packages:
- axios (API requests)
- dotenv (environment variables)
- pg (PostgreSQL client)
- node-cron (task scheduling)
- winston (logging)
- express (web server)

### Step 3: Configure Environment Variables

Create the `.env` file:

```bash
cp env.example .env
nano .env  # or use your preferred editor
```

Fill in your actual credentials:

```env
# Amazon Ads API Credentials
AMAZON_CLIENT_ID=amzn1.application-oa2-client.xxxxxxxxxxxxx
AMAZON_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AMAZON_REFRESH_TOKEN=Atzr|IwEBIxxxxxxxxxxxxxxxxxxxxxxx
AMAZON_PROFILE_ID=1234567890

# API Configuration
AMAZON_API_REGION=na
AMAZON_API_ENDPOINT=https://advertising-api.amazon.com

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=amazon_ads
DB_USER=postgres
DB_PASSWORD=your_secure_password

# Sync Configuration
SYNC_HOUR=2
SYNC_MINUTE=0
DAYS_TO_FETCH=7

# Server Configuration
PORT=3000
NODE_ENV=development
```

**Important**: 
- Replace all placeholder values with your actual credentials
- Keep this file secure and never commit it to version control

### Step 4: Initialize Database Schema

```bash
npm run setup-db
```

You should see:
```
✓ Database setup completed successfully
```

This creates all necessary tables:
- campaigns
- ad_groups
- keywords
- campaign_performance
- ad_group_performance
- keyword_performance
- sync_logs

### Step 5: Verify Database Tables

```bash
sudo -u postgres psql amazon_ads
```

In psql:
```sql
\dt  -- List all tables
\d campaigns  -- Describe campaigns table
\q
```

---

## Verification

### Step 1: Test Manual Sync

```bash
npm run sync
```

Expected output:
```
🔄 Starting Amazon Ads data sync...

Configuration:
  - Days back: 7
  - Date: 2024-01-15T10:30:00.000Z

✅ Sync completed successfully!

Results:
  - Campaigns synced: 45
  - Ad Groups synced: 123
  - Keywords synced: 456
  - Performance records synced: 3150
  - Total records: 3774
```

If you see errors, check:
- Amazon API credentials are correct
- Database connection is working
- You have active campaigns in your Amazon Ads account

### Step 2: Verify Data in Database

```bash
sudo -u postgres psql amazon_ads
```

```sql
-- Check campaigns
SELECT campaign_id, campaign_name, campaign_status FROM campaigns LIMIT 5;

-- Check ad groups
SELECT ad_group_id, ad_group_name FROM ad_groups LIMIT 5;

-- Check keywords
SELECT keyword_id, keyword_text, match_type FROM keywords LIMIT 5;

-- Check performance data
SELECT report_date, SUM(impressions), SUM(clicks), SUM(cost) 
FROM campaign_performance 
GROUP BY report_date 
ORDER BY report_date DESC 
LIMIT 7;
```

### Step 3: Test Report Export

```bash
# Get date range (last 7 days)
START_DATE=$(date -d '7 days ago' +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)

# Export reports
node src/export.js $START_DATE $END_DATE all
```

Check the `reports/` directory:
```bash
ls -lh reports/
```

You should see CSV files:
- campaign_performance_*.csv
- ad_group_performance_*.csv
- keyword_performance_*.csv
- summary_report_*.csv

### Step 4: Start the Application

```bash
npm start
```

Expected output:
```
╔════════════════════════════════════════════════════════════════╗
║         Amazon Ads API Integration - READY                     ║
╠════════════════════════════════════════════════════════════════╣
║  Server:    http://localhost:3000                              ║
║  Status:    http://localhost:3000/health                       ║
║  API Docs:  See README.md for endpoints                        ║
╠════════════════════════════════════════════════════════════════╣
║  Scheduled Tasks:                                              ║
║    - daily-sync: 0 2 * * *                                     ║
║    - hourly-metadata-sync: 0 * * * *                           ║
╚════════════════════════════════════════════════════════════════╝
```

### Step 5: Test API Endpoints

In a new terminal:

```bash
# Health check
curl http://localhost:3000/health

# Get campaigns
curl http://localhost:3000/api/campaigns

# Get scheduler info
curl http://localhost:3000/api/scheduler/info

# Trigger manual sync
curl -X POST http://localhost:3000/api/sync/campaigns \
  -H "Content-Type: application/json"
```

---

## Troubleshooting

### Issue: "Database connection failed"

**Solution:**
1. Check PostgreSQL is running:
   ```bash
   sudo systemctl status postgresql
   ```

2. Verify credentials in `.env`:
   ```bash
   cat .env | grep DB_
   ```

3. Test connection manually:
   ```bash
   psql -h localhost -U postgres -d amazon_ads
   ```

### Issue: "Failed to refresh access token"

**Solution:**
1. Verify Amazon credentials in `.env`
2. Check if refresh token is still valid:
   ```bash
   curl -X POST https://api.amazon.com/auth/o2/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=refresh_token" \
     -d "refresh_token=$AMAZON_REFRESH_TOKEN" \
     -d "client_id=$AMAZON_CLIENT_ID" \
     -d "client_secret=$AMAZON_CLIENT_SECRET"
   ```

3. If token expired, get a new authorization code and repeat Step 4 of Amazon API Setup

### Issue: "No campaigns found"

**Solution:**
1. Verify you have active campaigns in Amazon Advertising
2. Check if profile ID is correct:
   ```bash
   echo $AMAZON_PROFILE_ID
   ```
3. Verify API permissions for the profile

### Issue: "Port 3000 already in use"

**Solution:**
1. Change PORT in `.env`:
   ```env
   PORT=3001
   ```

2. Or kill the process using port 3000:
   ```bash
   sudo lsof -ti:3000 | xargs kill -9
   ```

### Issue: Permission denied for PostgreSQL

**Solution:**
```bash
# Grant permissions
sudo -u postgres psql amazon_ads
GRANT ALL PRIVILEGES ON DATABASE amazon_ads TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
\q
```

---

## Next Steps

Once setup is complete:

1. **Monitor Logs**: Check `logs/combined.log` for application activity
2. **Schedule Tasks**: The application will automatically run daily syncs
3. **Generate Reports**: Use the export script or API to generate performance reports
4. **API Integration**: Use the REST API to integrate with other systems

For detailed API documentation, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Change `NODE_ENV=production` in `.env`
- [ ] Use strong database passwords
- [ ] Enable PostgreSQL authentication (pg_hba.conf)
- [ ] Set up SSL/TLS for database connections
- [ ] Implement API authentication middleware
- [ ] Set up log rotation
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Use process manager (PM2, systemd)
- [ ] Back up database regularly
- [ ] Review and adjust sync schedules for your timezone
- [ ] Test disaster recovery procedures

---

## Support Resources

- **Amazon Advertising API**: https://advertising.amazon.com/API/docs
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Node.js Documentation**: https://nodejs.org/docs/
- **Express.js Guide**: https://expressjs.com/
- **PM2 Process Manager**: https://pm2.keymetrics.io/

---

**Congratulations!** Your Amazon Ads API Integration is now set up and running. The system will automatically sync your advertising data daily and provide comprehensive performance reports.

