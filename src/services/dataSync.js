const AmazonAdsClient = require('../api/amazonAdsClient');
const db = require('../database/connection');
const logger = require('../utils/logger');

class DataSyncService {
  constructor() {
    this.client = new AmazonAdsClient();
  }

  /**
   * Sync campaigns data
   */
  async syncCampaigns() {
    try {
      logger.info('Syncing campaigns...');
      const campaigns = await this.client.getCampaigns();

      let synced = 0;
      for (const campaign of campaigns) {
        await db.query(
          `INSERT INTO campaigns (
            campaign_id, campaign_name, campaign_status, 
            targeting_type, start_date, end_date,
            budget_amount, budget_type
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
          ON CONFLICT (campaign_id) 
          DO UPDATE SET
            campaign_name = $2,
            campaign_status = $3,
            targeting_type = $4,
            start_date = $5,
            end_date = $6,
            budget_amount = $7,
            budget_type = $8,
            updated_at = CURRENT_TIMESTAMP`,
          [
            campaign.campaignId,
            campaign.name,
            campaign.state,
            campaign.targetingType,
            campaign.startDate,
            campaign.endDate,
            campaign.budget?.amount,
            campaign.budget?.type
          ]
        );
        synced++;
      }

      logger.info(`Synced ${synced} campaigns`);
      return synced;
    } catch (error) {
      logger.error('Error syncing campaigns:', error);
      throw error;
    }
  }

  /**
   * Sync ad groups data
   */
  async syncAdGroups() {
    try {
      logger.info('Syncing ad groups...');
      const adGroups = await this.client.getAdGroups();

      let synced = 0;
      let skipped = 0;
      
      for (const adGroup of adGroups) {
        // Check if campaign exists before inserting ad group
        const campaignCheck = await db.query(
          'SELECT campaign_id FROM campaigns WHERE campaign_id = $1',
          [adGroup.campaignId]
        );
        
        if (campaignCheck.rows.length === 0) {
          logger.warn(`Skipping ad group ${adGroup.adGroupId} - campaign ${adGroup.campaignId} not found`);
          skipped++;
          continue;
        }
        
        await db.query(
          `INSERT INTO ad_groups (
            ad_group_id, ad_group_name, campaign_id,
            default_bid, state
          ) VALUES ($1, $2, $3, $4, $5)
          ON CONFLICT (ad_group_id)
          DO UPDATE SET
            ad_group_name = $2,
            campaign_id = $3,
            default_bid = $4,
            state = $5,
            updated_at = CURRENT_TIMESTAMP`,
          [
            adGroup.adGroupId,
            adGroup.name,
            adGroup.campaignId,
            adGroup.defaultBid,
            adGroup.state
          ]
        );
        synced++;
      }

      logger.info(`Synced ${synced} ad groups, skipped ${skipped} (missing campaigns)`);
      return synced;
    } catch (error) {
      logger.error('Error syncing ad groups:', error);
      throw error;
    }
  }

  /**
   * Sync keywords data
   */
  async syncKeywords() {
    try {
      logger.info('Syncing keywords...');
      const keywords = await this.client.getKeywords();

      let synced = 0;
      let skipped = 0;
      
      for (const keyword of keywords) {
        // Check if campaign and ad group exist before inserting keyword
        const campaignCheck = await db.query(
          'SELECT campaign_id FROM campaigns WHERE campaign_id = $1',
          [keyword.campaignId]
        );
        
        const adGroupCheck = await db.query(
          'SELECT ad_group_id FROM ad_groups WHERE ad_group_id = $1',
          [keyword.adGroupId]
        );
        
        if (campaignCheck.rows.length === 0) {
          logger.warn(`Skipping keyword ${keyword.keywordId} - campaign ${keyword.campaignId} not found`);
          skipped++;
          continue;
        }
        
        if (adGroupCheck.rows.length === 0) {
          logger.warn(`Skipping keyword ${keyword.keywordId} - ad group ${keyword.adGroupId} not found`);
          skipped++;
          continue;
        }
        
        await db.query(
          `INSERT INTO keywords (
            keyword_id, keyword_text, match_type,
            campaign_id, ad_group_id, bid, state
          ) VALUES ($1, $2, $3, $4, $5, $6, $7)
          ON CONFLICT (keyword_id)
          DO UPDATE SET
            keyword_text = $2,
            match_type = $3,
            campaign_id = $4,
            ad_group_id = $5,
            bid = $6,
            state = $7,
            updated_at = CURRENT_TIMESTAMP`,
          [
            keyword.keywordId,
            keyword.keywordText,
            keyword.matchType,
            keyword.campaignId,
            keyword.adGroupId,
            keyword.bid,
            keyword.state
          ]
        );
        synced++;
      }

      logger.info(`Synced ${synced} keywords, skipped ${skipped} (missing campaigns/ad groups)`);
      return synced;
    } catch (error) {
      logger.error('Error syncing keywords:', error);
      throw error;
    }
  }

  /**
   * Sync performance data for campaigns
   */
  async syncCampaignPerformance(reportDate) {
    try {
      logger.info(`Syncing campaign performance for ${reportDate}...`);
      const reportData = await this.client.getPerformanceData('campaigns', reportDate, reportDate);

      let synced = 0;
      for (const record of reportData) {
        if (!record.campaignId) continue;

        await db.query(
          `INSERT INTO campaign_performance (
            campaign_id, report_date, impressions, clicks, cost,
            attributed_conversions_1d, attributed_conversions_7d,
            attributed_conversions_14d, attributed_conversions_30d,
            attributed_sales_1d, attributed_sales_7d,
            attributed_sales_14d, attributed_sales_30d
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
          ON CONFLICT (campaign_id, report_date)
          DO UPDATE SET
            impressions = $3,
            clicks = $4,
            cost = $5,
            attributed_conversions_1d = $6,
            attributed_conversions_7d = $7,
            attributed_conversions_14d = $8,
            attributed_conversions_30d = $9,
            attributed_sales_1d = $10,
            attributed_sales_7d = $11,
            attributed_sales_14d = $12,
            attributed_sales_30d = $13,
            updated_at = CURRENT_TIMESTAMP`,
          [
            record.campaignId,
            reportDate,
            record.impressions || 0,
            record.clicks || 0,
            record.cost || 0,
            record.attributedConversions1d || 0,
            record.attributedConversions7d || 0,
            record.attributedConversions14d || 0,
            record.attributedConversions30d || 0,
            record.attributedSales1d || 0,
            record.attributedSales7d || 0,
            record.attributedSales14d || 0,
            record.attributedSales30d || 0
          ]
        );
        synced++;
      }

      logger.info(`Synced ${synced} campaign performance records for ${reportDate}`);
      return synced;
    } catch (error) {
      logger.error('Error syncing campaign performance:', error);
      throw error;
    }
  }

  /**
   * Sync performance data for ad groups
   */
  async syncAdGroupPerformance(reportDate) {
    try {
      logger.info(`Syncing ad group performance for ${reportDate}...`);
      const reportData = await this.client.getPerformanceData('adGroups', reportDate, reportDate);

      let synced = 0;
      for (const record of reportData) {
        if (!record.adGroupId) continue;

        await db.query(
          `INSERT INTO ad_group_performance (
            campaign_id, ad_group_id, report_date,
            impressions, clicks, cost,
            attributed_conversions_1d, attributed_conversions_7d,
            attributed_sales_1d, attributed_sales_7d
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
          ON CONFLICT (ad_group_id, report_date)
          DO UPDATE SET
            campaign_id = $1,
            impressions = $4,
            clicks = $5,
            cost = $6,
            attributed_conversions_1d = $7,
            attributed_conversions_7d = $8,
            attributed_sales_1d = $9,
            attributed_sales_7d = $10,
            updated_at = CURRENT_TIMESTAMP`,
          [
            record.campaignId,
            record.adGroupId,
            reportDate,
            record.impressions || 0,
            record.clicks || 0,
            record.cost || 0,
            record.attributedConversions1d || 0,
            record.attributedConversions7d || 0,
            record.attributedSales1d || 0,
            record.attributedSales7d || 0
          ]
        );
        synced++;
      }

      logger.info(`Synced ${synced} ad group performance records for ${reportDate}`);
      return synced;
    } catch (error) {
      logger.error('Error syncing ad group performance:', error);
      throw error;
    }
  }

  /**
   * Sync performance data for keywords
   */
  async syncKeywordPerformance(reportDate) {
    try {
      logger.info(`Syncing keyword performance for ${reportDate}...`);
      const reportData = await this.client.getPerformanceData('keywords', reportDate, reportDate);

      let synced = 0;
      for (const record of reportData) {
        if (!record.keywordId) continue;

        await db.query(
          `INSERT INTO keyword_performance (
            campaign_id, ad_group_id, keyword_id, report_date,
            impressions, clicks, cost,
            attributed_conversions_1d, attributed_conversions_7d,
            attributed_sales_1d, attributed_sales_7d
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
          ON CONFLICT (keyword_id, report_date)
          DO UPDATE SET
            campaign_id = $1,
            ad_group_id = $2,
            impressions = $5,
            clicks = $6,
            cost = $7,
            attributed_conversions_1d = $8,
            attributed_conversions_7d = $9,
            attributed_sales_1d = $10,
            attributed_sales_7d = $11,
            updated_at = CURRENT_TIMESTAMP`,
          [
            record.campaignId,
            record.adGroupId,
            record.keywordId,
            reportDate,
            record.impressions || 0,
            record.clicks || 0,
            record.cost || 0,
            record.attributedConversions1d || 0,
            record.attributedConversions7d || 0,
            record.attributedSales1d || 0,
            record.attributedSales7d || 0
          ]
        );
        synced++;
      }

      logger.info(`Synced ${synced} keyword performance records for ${reportDate}`);
      return synced;
    } catch (error) {
      logger.error('Error syncing keyword performance:', error);
      throw error;
    }
  }

  /**
   * Log sync operation
   */
  async logSync(syncType, status, recordsProcessed, errorMessage = null, startTime) {
    try {
      await db.query(
        `INSERT INTO sync_logs (
          sync_type, start_time, end_time, status,
          records_processed, error_message
        ) VALUES ($1, $2, $3, $4, $5, $6)`,
        [
          syncType,
          startTime,
          new Date(),
          status,
          recordsProcessed,
          errorMessage
        ]
      );
    } catch (error) {
      logger.error('Error logging sync:', error);
    }
  }

  /**
   * Full sync - campaigns, ad groups, keywords, and performance data
   */
  async fullSync(daysBack = 7) {
    const startTime = new Date();
    const totalRecords = { campaigns: 0, adGroups: 0, keywords: 0, performance: 0 };

    try {
      logger.info('Starting full data sync...');

      // Sync metadata
      totalRecords.campaigns = await this.syncCampaigns();
      totalRecords.adGroups = await this.syncAdGroups();
      totalRecords.keywords = await this.syncKeywords();

      // Sync performance data for the last N days
      const today = new Date();
      for (let i = 0; i < daysBack; i++) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        const reportDate = date.toISOString().split('T')[0];

        const campaignPerf = await this.syncCampaignPerformance(reportDate);
        const adGroupPerf = await this.syncAdGroupPerformance(reportDate);
        const keywordPerf = await this.syncKeywordPerformance(reportDate);

        totalRecords.performance += campaignPerf + adGroupPerf + keywordPerf;
      }

      const total = Object.values(totalRecords).reduce((a, b) => a + b, 0);
      await this.logSync('full_sync', 'success', total, null, startTime);

      logger.info('Full sync completed successfully', totalRecords);
      return totalRecords;
    } catch (error) {
      await this.logSync('full_sync', 'failed', 0, error.message, startTime);
      logger.error('Full sync failed:', error);
      throw error;
    }
  }
}

module.exports = DataSyncService;

