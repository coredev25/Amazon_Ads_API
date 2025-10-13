#!/usr/bin/env node

/**
 * Manual export script
 * Usage: node src/export.js <startDate> <endDate> [type]
 * Example: node src/export.js 2024-01-01 2024-01-31 all
 * Types: all, campaigns, ad-groups, keywords, summary
 */

const ReportExportService = require('./services/reportExport');
const db = require('./database/connection');
const logger = require('./utils/logger');

async function runExport() {
  const [,, startDate, endDate, type = 'all'] = process.argv;

  if (!startDate || !endDate) {
    console.error('\n❌ Error: startDate and endDate are required');
    console.log('\nUsage: node src/export.js <startDate> <endDate> [type]');
    console.log('Example: node src/export.js 2024-01-01 2024-01-31 all');
    console.log('Types: all, campaigns, ad-groups, keywords, summary\n');
    process.exit(1);
  }

  try {
    console.log('\n📊 Starting report export...\n');
    console.log(`Configuration:`);
    console.log(`  - Date range: ${startDate} to ${endDate}`);
    console.log(`  - Report type: ${type}\n`);

    // Test database connection
    const isConnected = await db.testConnection();
    if (!isConnected) {
      throw new Error('Database connection failed');
    }

    const exportService = new ReportExportService();
    let result;

    switch (type) {
      case 'campaigns':
        result = await exportService.exportCampaignPerformance(startDate, endDate);
        break;
      case 'ad-groups':
        result = await exportService.exportAdGroupPerformance(startDate, endDate);
        break;
      case 'keywords':
        result = await exportService.exportKeywordPerformance(startDate, endDate);
        break;
      case 'summary':
        result = await exportService.exportSummaryReport(startDate, endDate);
        break;
      case 'all':
      default:
        result = await exportService.exportAllReports(startDate, endDate);
        await exportService.exportSummaryReport(startDate, endDate);
        break;
    }

    console.log('\n✅ Export completed successfully!\n');
    
    if (Array.isArray(result)) {
      console.log('Generated reports:');
      result.forEach(r => {
        console.log(`  - ${r.filename} (${r.recordCount} records)`);
      });
    } else {
      console.log(`Generated report: ${result.filename} (${result.recordCount} records)`);
    }
    
    console.log('\n');

    await db.close();
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Export failed:', error.message);
    logger.error('Export script error:', error);
    await db.close();
    process.exit(1);
  }
}

runExport();

