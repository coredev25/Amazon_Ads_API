# Amazon Ads API Integration - API Documentation

## Base URL

```
http://localhost:3000
```

## Authentication

All API endpoints are currently open. In production, implement proper authentication middleware.

---

## Health & Status Endpoints

### Check Application Health

```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Get Scheduler Information

```http
GET /api/scheduler/info
```

**Response:**
```json
{
  "tasks": [
    {
      "name": "daily-sync",
      "schedule": "0 2 * * *"
    },
    {
      "name": "hourly-metadata-sync",
      "schedule": "0 * * * *"
    }
  ]
}
```

---

## Sync Endpoints

### Trigger Full Sync

Initiates a complete synchronization of all campaigns, ad groups, keywords, and performance data.

```http
POST /api/sync/full
Content-Type: application/json
```

**Request Body:**
```json
{
  "daysBack": 7
}
```

**Parameters:**
- `daysBack` (optional): Number of days of performance data to sync. Default: 7

**Response:**
```json
{
  "status": "started",
  "message": "Full sync initiated",
  "daysBack": 7
}
```

**Note:** Sync runs asynchronously. Check logs for completion status.

---

### Sync Campaigns Only

Synchronizes campaign metadata only.

```http
POST /api/sync/campaigns
```

**Response:**
```json
{
  "status": "success",
  "recordsSynced": 45
}
```

---

### Sync Ad Groups Only

Synchronizes ad group metadata only.

```http
POST /api/sync/ad-groups
```

**Response:**
```json
{
  "status": "success",
  "recordsSynced": 123
}
```

---

### Sync Keywords Only

Synchronizes keyword metadata only.

```http
POST /api/sync/keywords
```

**Response:**
```json
{
  "status": "success",
  "recordsSynced": 456
}
```

---

## Report Endpoints

### Export Reports

Generates and exports performance reports in CSV format.

```http
POST /api/reports/export
Content-Type: application/json
```

**Request Body:**
```json
{
  "startDate": "2024-01-01",
  "endDate": "2024-01-31",
  "type": "all"
}
```

**Parameters:**
- `startDate` (required): Start date in YYYY-MM-DD format
- `endDate` (required): End date in YYYY-MM-DD format
- `type` (optional): Report type. Options:
  - `all` - All report types (default)
  - `campaigns` - Campaign performance only
  - `ad-groups` - Ad group performance only
  - `keywords` - Keyword performance only
  - `summary` - Summary report only

**Response (type: all):**
```json
{
  "status": "success",
  "reports": [
    {
      "filepath": "/home/carter/Desktop/AmazonAds/reports/campaign_performance_2024-01-01_to_2024-01-31.csv",
      "filename": "campaign_performance_2024-01-01_to_2024-01-31.csv",
      "recordCount": 450
    },
    {
      "filepath": "/home/carter/Desktop/AmazonAds/reports/ad_group_performance_2024-01-01_to_2024-01-31.csv",
      "filename": "ad_group_performance_2024-01-01_to_2024-01-31.csv",
      "recordCount": 1230
    },
    {
      "filepath": "/home/carter/Desktop/AmazonAds/reports/keyword_performance_2024-01-01_to_2024-01-31.csv",
      "filename": "keyword_performance_2024-01-01_to_2024-01-31.csv",
      "recordCount": 4560
    }
  ]
}
```

**Response (single report type):**
```json
{
  "status": "success",
  "reports": {
    "filepath": "/home/carter/Desktop/AmazonAds/reports/campaign_performance_2024-01-01_to_2024-01-31.csv",
    "filename": "campaign_performance_2024-01-01_to_2024-01-31.csv",
    "recordCount": 450
  }
}
```

---

## Data Query Endpoints

### Get All Campaigns

Retrieves all campaigns from the database.

```http
GET /api/campaigns
```

**Response:**
```json
{
  "campaigns": [
    {
      "id": 1,
      "campaign_id": 123456789,
      "campaign_name": "Summer Sale Campaign",
      "campaign_status": "enabled",
      "targeting_type": "manual",
      "start_date": "2024-01-01",
      "end_date": null,
      "budget_amount": "1000.00",
      "budget_type": "daily",
      "created_at": "2024-01-15T10:30:00.000Z",
      "updated_at": "2024-01-15T10:30:00.000Z"
    }
  ]
}
```

---

### Get Campaign Performance

Retrieves performance data for a specific campaign.

```http
GET /api/campaigns/:campaignId/performance?startDate=2024-01-01&endDate=2024-01-31
```

**Parameters:**
- `campaignId` (required): Campaign ID from path
- `startDate` (optional): Filter by start date
- `endDate` (optional): Filter by end date

**Response:**
```json
{
  "performance": [
    {
      "id": 1,
      "campaign_id": 123456789,
      "report_date": "2024-01-15",
      "impressions": 10000,
      "clicks": 250,
      "cost": "125.50",
      "attributed_conversions_1d": 5,
      "attributed_conversions_7d": 12,
      "attributed_conversions_14d": 15,
      "attributed_conversions_30d": 18,
      "attributed_sales_1d": "500.00",
      "attributed_sales_7d": "1200.00",
      "attributed_sales_14d": "1500.00",
      "attributed_sales_30d": "1800.00",
      "created_at": "2024-01-15T10:30:00.000Z",
      "updated_at": "2024-01-15T10:30:00.000Z"
    }
  ]
}
```

---

### Get Sync Logs

Retrieves synchronization operation logs.

```http
GET /api/sync/logs?limit=50
```

**Parameters:**
- `limit` (optional): Maximum number of logs to return. Default: 50

**Response:**
```json
{
  "logs": [
    {
      "id": 1,
      "sync_type": "full_sync",
      "start_time": "2024-01-15T02:00:00.000Z",
      "end_time": "2024-01-15T02:15:30.000Z",
      "status": "success",
      "records_processed": 5000,
      "error_message": null,
      "created_at": "2024-01-15T02:15:30.000Z"
    }
  ]
}
```

---

## Error Responses

All endpoints return standard error responses:

### 400 Bad Request

```json
{
  "error": "startDate and endDate are required"
}
```

### 500 Internal Server Error

```json
{
  "error": "Database connection failed"
}
```

---

## Example Usage with cURL

### Trigger Full Sync

```bash
curl -X POST http://localhost:3000/api/sync/full \
  -H "Content-Type: application/json" \
  -d '{"daysBack": 7}'
```

### Export Campaign Reports

```bash
curl -X POST http://localhost:3000/api/sync/reports/export \
  -H "Content-Type: application/json" \
  -d '{
    "startDate": "2024-01-01",
    "endDate": "2024-01-31",
    "type": "campaigns"
  }'
```

### Get Campaign Performance

```bash
curl "http://localhost:3000/api/campaigns/123456789/performance?startDate=2024-01-01&endDate=2024-01-31"
```

### Get Sync Logs

```bash
curl "http://localhost:3000/api/sync/logs?limit=10"
```

---

## Example Usage with JavaScript (fetch)

### Trigger Full Sync

```javascript
const response = await fetch('http://localhost:3000/api/sync/full', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ daysBack: 7 })
});

const data = await response.json();
console.log(data);
```

### Export Reports

```javascript
const response = await fetch('http://localhost:3000/api/reports/export', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    startDate: '2024-01-01',
    endDate: '2024-01-31',
    type: 'all'
  })
});

const data = await response.json();
console.log(data);
```

### Get Campaigns

```javascript
const response = await fetch('http://localhost:3000/api/campaigns');
const data = await response.json();
console.log(data.campaigns);
```

---

## Rate Limiting

The application respects Amazon Ads API rate limits. If you encounter rate limit errors, the sync will automatically retry with exponential backoff.

## Best Practices

1. **Sync Operations**: Avoid triggering multiple full syncs simultaneously
2. **Date Ranges**: Use reasonable date ranges for reports (e.g., 90 days max)
3. **Scheduling**: Let the automated scheduler handle daily syncs
4. **Error Handling**: Always check response status codes and error messages
5. **Monitoring**: Regularly check sync logs for failures

## Support

For API-related questions or issues, check the application logs in the `logs/` directory or query the `/api/sync/logs` endpoint.

