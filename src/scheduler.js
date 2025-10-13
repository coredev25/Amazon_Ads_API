const cron = require('node-cron');
const DataSyncService = require('./services/dataSync');
const logger = require('./utils/logger');
const config = require('./config/config');

class Scheduler {
  constructor() {
    this.syncService = new DataSyncService();
    this.tasks = [];
  }

  /**
   * Schedule daily data sync
   */
  scheduleDailySync() {
    const { hour, minute, daysToFetch } = config.sync;
    const cronExpression = `${minute} ${hour} * * *`; // Daily at configured time

    logger.info(`Scheduling daily sync at ${hour}:${minute} (cron: ${cronExpression})`);

    const task = cron.schedule(cronExpression, async () => {
      logger.info('Running scheduled daily sync...');
      try {
        await this.syncService.fullSync(daysToFetch);
        logger.info('Scheduled sync completed successfully');
      } catch (error) {
        logger.error('Scheduled sync failed:', error);
      }
    });

    this.tasks.push({ name: 'daily-sync', task, schedule: cronExpression });
    return task;
  }

  /**
   * Schedule hourly metadata sync (campaigns, ad groups, keywords only)
   */
  scheduleHourlyMetadataSync() {
    const cronExpression = '0 * * * *'; // Every hour at minute 0

    logger.info(`Scheduling hourly metadata sync (cron: ${cronExpression})`);

    const task = cron.schedule(cronExpression, async () => {
      logger.info('Running scheduled metadata sync...');
      try {
        await this.syncService.syncCampaigns();
        await this.syncService.syncAdGroups();
        await this.syncService.syncKeywords();
        logger.info('Scheduled metadata sync completed successfully');
      } catch (error) {
        logger.error('Scheduled metadata sync failed:', error);
      }
    });

    this.tasks.push({ name: 'hourly-metadata-sync', task, schedule: cronExpression });
    return task;
  }

  /**
   * Start all scheduled tasks
   */
  startAll() {
    logger.info('Starting all scheduled tasks...');
    this.scheduleDailySync();
    this.scheduleHourlyMetadataSync();
    logger.info(`${this.tasks.length} tasks scheduled`);
  }

  /**
   * Stop all scheduled tasks
   */
  stopAll() {
    logger.info('Stopping all scheduled tasks...');
    this.tasks.forEach(({ name, task }) => {
      task.stop();
      logger.info(`Stopped task: ${name}`);
    });
    this.tasks = [];
  }

  /**
   * Get all scheduled tasks info
   */
  getTasksInfo() {
    return this.tasks.map(({ name, schedule }) => ({ name, schedule }));
  }
}

module.exports = Scheduler;

