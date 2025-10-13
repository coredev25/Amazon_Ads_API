# Amazon Ads API Integration

A comprehensive Node.js application for integrating with Amazon Ads API (Vendor Central), featuring automated daily data synchronization, performance tracking, and report generation.

## Features

✅ **Secure Amazon Ads API Connection**
- OAuth 2.0 authentication with automatic token refresh
- Secure credential management via environment variables

✅ **Automated Data Sync**
- Daily scheduled synchronization of campaigns, ad groups, and keywords
- Performance data fetching with configurable date ranges
- Hourly metadata updates
- Comprehensive sync logging

✅ **PostgreSQL Database Storage**
- Structured schema for campaigns, ad groups, and keywords
- Performance tracking tables with historical data
- Automatic timestamp management
- Foreign key relationships and data integrity

✅ **Report Export**
- CSV export for campaign, ad group, and keyword performance
- Summary reports with aggregated metrics
- Customizable date ranges
- Calculated metrics (CTR, CPC, ROAS)

✅ **RESTful API**
- Manual sync triggers
- Report generation endpoints
- Performance data queries
- Sync log access

## Prerequisites

- Node.js (v14 or higher)
- PostgreSQL (v12 or higher)
- Amazon Ads API credentials (Vendor Central access)

## Installation

### 1. Clone or navigate to the project directory

```bash
cd /home/carter/Desktop/AmazonAds
```

### 2. Install dependencies

```bash
npm install
```

### 3. Configure environment variables

Create a `.env` file in the root directory (use `env.example` as template):

```bash
cp env.example .env
```

Edit `.env` with your credentials:

```env
# Amazon Ads API Credentials
AMAZON_CLIENT_ID=your_client_id_here
AMAZON_CLIENT_SECRET=your_client_secret_here
AMAZON_REFRESH_TOKEN=your_refresh_token_here
AMAZON_PROFILE_ID=your_profile_id_here

# API Configuration
AMAZON_API_REGION=na
AMAZON_API_ENDPOINT=https://advertising-api.amazon.com

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=amazon_ads
DB_USER=postgres
DB_PASSWORD=your_db_password

# Sync Configuration
SYNC_HOUR=2
SYNC_MINUTE=0
DAYS_TO_FETCH=7

# Server Configuration
PORT=3000
NODE_ENV=development
```

### 4. Set up PostgreSQL database

Create the database:

```bash
createdb amazon_ads
```

Or using psql:

```sql
CREATE DATABASE amazon_ads;
```

### 5. Initialize database schema

```bash
npm run setup-db
```

## Getting Amazon Ads API Credentials

### Step 1: Register Your Application

1. Go to [Amazon Advertising API](https://advertising.amazon.com/API/docs/en-us/get-started/overview)
2. Register your application to get Client ID and Client Secret
3. Set up OAuth 2.0 redirect URI

### Step 2: Get Refresh Token

1. Use the authorization URL to get an authorization code:
```
https://www.amazon.com/ap/oa?client_id=YOUR_CLIENT_ID&scope=advertising::campaign_management&response_type=code&redirect_uri=YOUR_REDIRECT_URI
```

2. Exchange the authorization code for a refresh token:
```bash
curl -X POST \
  https://api.amazon.com/auth/o2/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=authorization_code&code=YOUR_AUTH_CODE&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&redirect_uri=YOUR_REDIRECT_URI'
```

3. Save the `refresh_token` from the response

### Step 3: Get Profile ID

```bash
curl -X GET \
  https://advertising-api.amazon.com/v2/profiles \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'Amazon-Advertising-API-ClientId: YOUR_CLIENT_ID'
```

## Usage

### Start the Application

```bash
npm start
```

The server will start on port 3000 (or your configured PORT) with:
- Automated daily sync scheduled
- Hourly metadata refresh
- REST API endpoints available

### Manual Data Sync

Sync all data for the last 7 days:

```bash
npm run sync
```

Sync with custom days back:

```bash
node src/sync.js 30
```

### Export Reports

Export all reports for a date range:

```bash
npm run export
# Then follow the prompts or use:
node src/export.js 2024-01-01 2024-01-31 all
```

Export specific report types:

```bash
# Campaign performance only
node src/export.js 2024-01-01 2024-01-31 campaigns

# Ad group performance only
node src/export.js 2024-01-01 2024-01-31 ad-groups

# Keyword performance only
node src/export.js 2024-01-01 2024-01-31 keywords

# Summary report only
node src/export.js 2024-01-01 2024-01-31 summary
```

Reports are saved to the `reports/` directory.

## API Endpoints

### Health Check

```bash
GET /health
```

### Scheduler Information

```bash
GET /api/scheduler/info
```

Returns information about scheduled tasks.

### Manual Sync Triggers

**Full Sync**
```bash
POST /api/sync/full
Content-Type: application/json

{
  "daysBack": 7
}
```

**Sync Campaigns Only**
```bash
POST /api/sync/campaigns
```

**Sync Ad Groups Only**
```bash
POST /api/sync/ad-groups
```

**Sync Keywords Only**
```bash
POST /api/sync/keywords
```

### Report Export

```bash
POST /api/reports/export
Content-Type: application/json

{
  "startDate": "2024-01-01",
  "endDate": "2024-01-31",
  "type": "all"
}
```

Types: `all`, `campaigns`, `ad-groups`, `keywords`, `summary`

### Data Queries

**Get All Campaigns**
```bash
GET /api/campaigns
```

**Get Campaign Performance**
```bash
GET /api/campaigns/:campaignId/performance?startDate=2024-01-01&endDate=2024-01-31
```

**Get Sync Logs**
```bash
GET /api/sync/logs?limit=50
```

## Database Schema

### Tables

- **campaigns**: Campaign metadata
- **ad_groups**: Ad group metadata
- **keywords**: Keyword metadata
- **campaign_performance**: Daily campaign performance metrics
- **ad_group_performance**: Daily ad group performance metrics
- **keyword_performance**: Daily keyword performance metrics
- **sync_logs**: Synchronization operation logs

### Performance Metrics

Each performance table includes:
- Impressions
- Clicks
- Cost
- Attributed Conversions (1d, 7d, 14d, 30d)
- Attributed Sales (1d, 7d, 14d, 30d)
- CTR (Click-Through Rate) - calculated
- CPC (Cost Per Click) - calculated
- ROAS (Return on Ad Spend) - calculated

## Scheduled Tasks

### Daily Full Sync
- **Schedule**: Configurable (default: 2:00 AM)
- **Action**: Syncs all campaigns, ad groups, keywords, and performance data
- **Lookback**: Configurable days (default: 7 days)

### Hourly Metadata Sync
- **Schedule**: Every hour at minute 0
- **Action**: Updates campaigns, ad groups, and keywords metadata only

## Logging

Logs are stored in the `logs/` directory:
- `combined.log`: All logs
- `error.log`: Error logs only

In development mode, logs are also output to the console.

## Error Handling

The application includes comprehensive error handling:
- Automatic token refresh on expiry
- Database connection retry logic
- Sync operation logging
- Graceful shutdown on SIGTERM/SIGINT

## Development

### Run in Development Mode

```bash
npm run dev
```

Uses `nodemon` for automatic restart on file changes.

### Project Structure

```
AmazonAds/
├── src/
│   ├── api/
│   │   └── amazonAdsClient.js      # Amazon Ads API client
│   ├── config/
│   │   └── config.js               # Configuration management
│   ├── database/
│   │   ├── connection.js           # Database connection pool
│   │   ├── schema.sql             # Database schema
│   │   └── setup.js               # Database setup script
│   ├── services/
│   │   ├── dataSync.js            # Data synchronization service
│   │   └── reportExport.js        # Report export service
│   ├── utils/
│   │   └── logger.js              # Winston logger configuration
│   ├── scheduler.js               # Cron job scheduler
│   ├── index.js                   # Main application entry
│   ├── sync.js                    # Manual sync script
│   └── export.js                  # Manual export script
├── logs/                          # Application logs
├── reports/                       # Generated CSV reports
├── .env                          # Environment configuration (not in git)
├── env.example                   # Environment template
├── package.json                  # Dependencies and scripts
└── README.md                     # This file
```

## Troubleshooting

### Database Connection Issues

1. Verify PostgreSQL is running:
```bash
sudo systemctl status postgresql
```

2. Check connection parameters in `.env`
3. Ensure database exists:
```bash
psql -U postgres -l
```

### API Authentication Issues

1. Verify credentials in `.env`
2. Check access token refresh logs
3. Ensure API profile has proper permissions
4. Verify refresh token hasn't expired

### Sync Failures

1. Check logs in `logs/error.log`
2. Query sync logs:
```bash
curl http://localhost:3000/api/sync/logs
```
3. Verify API rate limits haven't been exceeded

## Performance Considerations

- API rate limits: Amazon Ads API has rate limits; the application includes built-in retry logic
- Database indexes: All foreign keys and date columns are indexed for optimal query performance
- Report generation: Large date ranges may take longer to process
- Concurrent syncs: Avoid running multiple full syncs simultaneously

## Security Best Practices

1. Never commit `.env` file to version control
2. Use strong PostgreSQL passwords
3. Restrict database access to localhost in production
4. Use HTTPS in production environments
5. Regularly rotate API credentials
6. Monitor logs for suspicious activity

## Support

For issues related to:
- **Amazon Ads API**: [Amazon Advertising API Documentation](https://advertising.amazon.com/API/docs)
- **PostgreSQL**: [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- **Node.js**: [Node.js Documentation](https://nodejs.org/docs/)

## License

MIT

## Milestone 1 Deliverables ✅

This implementation fulfills all Milestone 1 requirements:

1. ✅ **Secure Amazon Ads API Connection**: OAuth 2.0 with automatic token refresh
2. ✅ **Daily Data Sync**: Automated scheduling with configurable intervals
3. ✅ **Campaign/Ad Group/Keyword Data**: Complete metadata and performance tracking
4. ✅ **PostgreSQL Storage**: Structured tables with relationships and indexes
5. ✅ **Access Token Refresh**: Automatic refresh before expiration
6. ✅ **Sample Report Export**: Multiple report types with CSV export
7. ✅ **Verified API Data Feed**: RESTful API with manual trigger endpoints

The application is production-ready and includes comprehensive logging, error handling, and monitoring capabilities.

