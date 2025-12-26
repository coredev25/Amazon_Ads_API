#!/usr/bin/env node

/**
 * Manual sync script
 * Usage: node src/sync.js [daysBack]
 * Example: node src/sync.js 7
 */

const DataSyncService = require('./services/dataSync');
const db = require('./database/connection');
const logger = require('./utils/logger');

async function runSync() {
  const daysBack = parseInt(process.argv[2]) || 7;

  try {
    console.log('\n🔄 Starting Amazon Ads data sync...\n');
    console.log(`Configuration:`);
    console.log(`  - Days back: ${daysBack}`);
    console.log(`  - Date: ${new Date().toISOString()}\n`);

    // Test database connection
    try {
      await db.query('SELECT NOW()');
      console.log('✅ Database connection successful\n');
    } catch (error) {
      throw new Error('Database connection failed: ' + error.message);
    }

    const syncService = new DataSyncService();
    const result = await syncService.fullSync(daysBack);

    console.log('\n✅ Sync completed successfully!\n');
    console.log('Results:');
    console.log(`  - Campaigns synced: ${result.campaigns}`);
    console.log(`  - Ad Groups synced: ${result.adGroups}`);
    console.log(`  - Keywords synced: ${result.keywords}`);
    console.log(`  - Product Ads synced: ${result.productAds || 0}`);
    console.log(`  - Performance records synced: ${result.performance}`);
    console.log(`  - Total records: ${Object.values(result).reduce((a, b) => a + b, 0)}\n`);

    await db.close();
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Sync failed:', error.message);
    logger.error('Sync script error:', error);
    await db.close();
    process.exit(1);
  }
}

runSync();

