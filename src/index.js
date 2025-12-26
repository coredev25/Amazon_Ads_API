const express = require('express');
const Scheduler = require('./scheduler');
const DataSyncService = require('./services/dataSync');
const ReportExportService = require('./services/reportExport');
const db = require('./database/connection');
const logger = require('./utils/logger');
const config = require('./config/config');

const app = express();
const scheduler = new Scheduler();
const syncService = new DataSyncService();
const reportService = new ReportExportService();

app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Get scheduler info
app.get('/api/scheduler/info', (req, res) => {
  const tasks = scheduler.getTasksInfo();
  res.json({ tasks });
});

// Trigger manual sync
app.post('/api/sync/full', async (req, res) => {
  try {
    const { daysBack = 7 } = req.body;
    logger.info('Manual full sync triggered via API');
    
    // Run sync in background
    syncService.fullSync(daysBack)
      .then(result => logger.info('Manual sync completed', result))
      .catch(error => logger.error('Manual sync failed', error));
    
    res.json({ 
      status: 'started', 
      message: 'Full sync initiated',
      daysBack 
    });
  } catch (error) {
    logger.error('Error triggering sync:', error);
    res.status(500).json({ error: error.message });
  }
});

// Sync campaigns only
app.post('/api/sync/campaigns', async (req, res) => {
  try {
    logger.info('Campaign sync triggered via API');
    const count = await syncService.syncCampaigns();
    res.json({ status: 'success', recordsSynced: count });
  } catch (error) {
    logger.error('Error syncing campaigns:', error);
    res.status(500).json({ error: error.message });
  }
});

// Sync ad groups only
app.post('/api/sync/ad-groups', async (req, res) => {
  try {
    logger.info('Ad group sync triggered via API');
    const count = await syncService.syncAdGroups();
    res.json({ status: 'success', recordsSynced: count });
  } catch (error) {
    logger.error('Error syncing ad groups:', error);
    res.status(500).json({ error: error.message });
  }
});

// Sync keywords only
app.post('/api/sync/keywords', async (req, res) => {
  try {
    logger.info('Keyword sync triggered via API');
    const count = await syncService.syncKeywords();
    res.json({ status: 'success', recordsSynced: count });
  } catch (error) {
    logger.error('Error syncing keywords:', error);
    res.status(500).json({ error: error.message });
  }
});

// Sync product ads only
app.post('/api/sync/product-ads', async (req, res) => {
  try {
    logger.info('Product ads sync triggered via API');
    const count = await syncService.syncProductAds();
    res.json({ status: 'success', recordsSynced: count });
  } catch (error) {
    logger.error('Error syncing product ads:', error);
    res.status(500).json({ error: error.message });
  }
});

// Export reports
app.post('/api/reports/export', async (req, res) => {
  try {
    const { startDate, endDate, type = 'all' } = req.body;
    
    if (!startDate || !endDate) {
      return res.status(400).json({ error: 'startDate and endDate are required' });
    }

    logger.info(`Report export triggered: ${type} from ${startDate} to ${endDate}`);
    
    let result;
    switch (type) {
      case 'campaigns':
        result = await reportService.exportCampaignPerformance(startDate, endDate);
        break;
      case 'ad-groups':
        result = await reportService.exportAdGroupPerformance(startDate, endDate);
        break;
      case 'keywords':
        result = await reportService.exportKeywordPerformance(startDate, endDate);
        break;
      case 'summary':
        result = await reportService.exportSummaryReport(startDate, endDate);
        break;
      case 'all':
      default:
        result = await reportService.exportAllReports(startDate, endDate);
        break;
    }

    res.json({ status: 'success', reports: result });
  } catch (error) {
    logger.error('Error exporting reports:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get sync logs
app.get('/api/sync/logs', async (req, res) => {
  try {
    const { limit = 50 } = req.query;
    const result = await db.query(
      'SELECT * FROM sync_logs ORDER BY created_at DESC LIMIT $1',
      [limit]
    );
    res.json({ logs: result.rows });
  } catch (error) {
    logger.error('Error fetching sync logs:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get campaigns
app.get('/api/campaigns', async (req, res) => {
  try {
    const result = await db.query(
      'SELECT * FROM campaigns ORDER BY updated_at DESC'
    );
    res.json({ campaigns: result.rows });
  } catch (error) {
    logger.error('Error fetching campaigns:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get campaign performance
app.get('/api/campaigns/:campaignId/performance', async (req, res) => {
  try {
    const { campaignId } = req.params;
    const { startDate, endDate } = req.query;
    
    let query = 'SELECT * FROM campaign_performance WHERE campaign_id = $1';
    const params = [campaignId];
    
    if (startDate && endDate) {
      query += ' AND report_date >= $2 AND report_date <= $3';
      params.push(startDate, endDate);
    }
    
    query += ' ORDER BY report_date DESC';
    
    const result = await db.query(query, params);
    res.json({ performance: result.rows });
  } catch (error) {
    logger.error('Error fetching campaign performance:', error);
    res.status(500).json({ error: error.message });
  }
});

// Startup
async function start() {
  try {
    // Test database connection
    logger.info('Testing database connection...');
    const isConnected = await db.testConnection();
    
    if (!isConnected) {
      throw new Error('Database connection failed. Please check your configuration.');
    }

    // Start scheduler
    scheduler.startAll();

    // Start server
    const port = config.server.port;
    app.listen(port, () => {
      logger.info(`Amazon Ads API Integration server started on port ${port}`);
      console.log(`
╔════════════════════════════════════════════════════════════════╗
║         Amazon Ads API Integration - READY                     ║
╠════════════════════════════════════════════════════════════════╣
║  Server:    http://localhost:${port}                           ║
║  Status:    http://localhost:${port}/health                    ║
║  API Docs:  See README.md for endpoints                        ║
╠════════════════════════════════════════════════════════════════╣
║  Scheduled Tasks:                                              ║
${scheduler.getTasksInfo().map(t => `║    - ${t.name}: ${t.schedule}`.padEnd(65) + '║').join('\n')}
╚════════════════════════════════════════════════════════════════╝
      `);
    });

  } catch (error) {
    logger.error('Failed to start application:', error);
    console.error('Failed to start application:', error.message);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully...');
  scheduler.stopAll();
  await db.close();
  process.exit(0);
});

process.on('SIGINT', async () => {
  logger.info('SIGINT received, shutting down gracefully...');
  scheduler.stopAll();
  await db.close();
  process.exit(0);
});

start();

