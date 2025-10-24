const AmazonAdsClient = require('../api/amazonAdsClient');
const db = require('../database/connection');
const logger = require('../utils/logger');

class DataSyncService {
  constructor(config = {}) {
    this.config = {
      // Performance optimization settings
      maxRetries: config.maxRetries || 3,
      batchSize: config.batchSize || 50,
      rateLimitDelay: config.rateLimitDelay || 100
    };
    
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
   * Convert API date format (YYYYMMDD) to database format (YYYY-MM-DD)
   */
  formatDateForDB(apiDate) {
    if (apiDate.includes('-')) return apiDate; // Already formatted
    // Convert 20241020 to 2024-10-20
    return `${apiDate.substr(0, 4)}-${apiDate.substr(4, 2)}-${apiDate.substr(6, 2)}`;
  }

  /**
   * Sync performance data for campaigns
   */
  async syncCampaignPerformance(reportDate) {
    try {
      logger.info(`📊 [CAMPAIGNS] Syncing campaign performance for ${reportDate}...`);
      logger.info(`📊 [CAMPAIGNS] Requesting report from Amazon Ads API...`);
      
      const reportData = await this.client.getPerformanceData('campaigns', reportDate, reportDate);

      if (!reportData || reportData.length === 0) {
        logger.warn(`⚠️  [CAMPAIGNS] No campaign performance data returned for ${reportDate}`);
        return 0;
      }

      // Validate report data structure
      if (!Array.isArray(reportData)) {
        logger.error(`❌ [CAMPAIGNS] Invalid report data format for ${reportDate}`);
        return 0;
      }

      logger.info(`📊 [CAMPAIGNS] Received ${reportData.length} records, saving to database...`);
      
      const dbDate = this.formatDateForDB(reportDate);
      let synced = 0;
      const total = reportData.length;

      for (const record of reportData) {
        if (!record.campaignId) continue;

        // Check if campaign exists before inserting performance data
        const campaignCheck = await db.query(
          'SELECT campaign_id FROM campaigns WHERE campaign_id = $1',
          [record.campaignId]
        );
        
        if (campaignCheck.rows.length === 0) {
          logger.warn(`Skipping campaign performance for ${record.campaignId} - campaign not found in campaigns table`);
          continue;
        }

        // Add rate limiting - small delay between database operations
        if (synced > 0 && synced % this.config.batchSize === 0) {
          await new Promise(resolve => setTimeout(resolve, this.config.rateLimitDelay));
        }

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
            dbDate,
            record.impressions || 0,
            record.clicks || 0,
            record.cost || 0,
            record.purchases1d || 0,
            record.purchases7d || 0,
            record.purchases14d || 0,
            record.purchases30d || 0,
            record.sales1d || 0,
            record.sales7d || 0,
            record.sales14d || 0,
            record.sales30d || 0
          ]
        );
        synced++;
        
        // Log progress every 10 records or at the end
        if (synced % 10 === 0 || synced === total) {
          logger.info(`📊 [CAMPAIGNS] Progress: ${synced}/${total} records saved (${Math.round(synced/total*100)}%)`);
        }
      }

      logger.info(`✅ [CAMPAIGNS] Successfully synced ${synced} campaign performance records for ${reportDate}`);
      return synced;
    } catch (error) {
      logger.error(`❌ [CAMPAIGNS] Error syncing campaign performance:`, error.message);
      throw error;
    }
  }

  /**
   * Sync performance data for ad groups
   */
  async syncAdGroupPerformance(reportDate) {
    try {
      logger.info(`📊 [AD GROUPS] Syncing ad group performance for ${reportDate}...`);
      logger.info(`📊 [AD GROUPS] Requesting report from Amazon Ads API...`);
      
      const reportData = await this.client.getPerformanceData('adGroups', reportDate, reportDate);

      if (!reportData || reportData.length === 0) {
        logger.warn(`⚠️  [AD GROUPS] No ad group performance data returned for ${reportDate}`);
        return 0;
      }

      logger.info(`📊 [AD GROUPS] Received ${reportData.length} records, saving to database...`);
      
      const dbDate = this.formatDateForDB(reportDate);
      let synced = 0;
      const total = reportData.length;

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
            dbDate,
            record.impressions || 0,
            record.clicks || 0,
            record.cost || 0,
            record.purchases1d || 0,
            record.purchases7d || 0,
            record.sales1d || 0,
            record.sales7d || 0
          ]
        );
        synced++;
        
        // Log progress every 10 records or at the end
        if (synced % 10 === 0 || synced === total) {
          logger.info(`📊 [AD GROUPS] Progress: ${synced}/${total} records saved (${Math.round(synced/total*100)}%)`);
        }
      }

      logger.info(`✅ [AD GROUPS] Successfully synced ${synced} ad group performance records for ${reportDate}`);
      return synced;
    } catch (error) {
      logger.error(`❌ [AD GROUPS] Error syncing ad group performance:`, error.message);
      throw error;
    }
  }

  /**
   * Sync performance data for keywords
   */
  async syncKeywordPerformance(reportDate) {
    try {
      logger.info(`📊 [KEYWORDS] Syncing keyword performance for ${reportDate}...`);
      logger.info(`📊 [KEYWORDS] Requesting report from Amazon Ads API...`);
      
      const reportData = await this.client.getPerformanceData('keywords', reportDate, reportDate);

      if (!reportData || reportData.length === 0) {
        logger.warn(`⚠️  [KEYWORDS] No keyword performance data returned for ${reportDate}`);
        return 0;
      }

      logger.info(`📊 [KEYWORDS] Received ${reportData.length} records, saving to database...`);
      
      const dbDate = this.formatDateForDB(reportDate);
      let synced = 0;
      const total = reportData.length;

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
            dbDate,
            record.impressions || 0,
            record.clicks || 0,
            record.cost || 0,
            record.purchases1d || 0,
            record.purchases7d || 0,
            record.sales1d || 0,
            record.sales7d || 0
          ]
        );
        synced++;
        
        // Log progress every 20 records or at the end (keywords can be numerous)
        if (synced % 20 === 0 || synced === total) {
          logger.info(`📊 [KEYWORDS] Progress: ${synced}/${total} records saved (${Math.round(synced/total*100)}%)`);
        }
      }

      logger.info(`✅ [KEYWORDS] Successfully synced ${synced} keyword performance records for ${reportDate}`);
      return synced;
    } catch (error) {
      logger.error(`❌ [KEYWORDS] Error syncing keyword performance:`, error.message);
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
      logger.info('═══════════════════════════════════════════════════════');
      logger.info('🚀 STARTING FULL DATA SYNC');
      logger.info(`📅 Syncing performance data for the last ${daysBack} days`);
      logger.info('═══════════════════════════════════════════════════════');

      // Sync metadata
      logger.info('\n📋 PHASE 1: Syncing Metadata');
      logger.info('───────────────────────────────────────────────────────');
      // totalRecords.campaigns = await this.syncCampaigns();
      // totalRecords.adGroups = await this.syncAdGroups();
      // totalRecords.keywords = await this.syncKeywords();
      logger.info(`✅ Metadata sync complete: ${totalRecords.campaigns} campaigns, ${totalRecords.adGroups} ad groups, ${totalRecords.keywords} keywords`);

      // Sync performance data for the last N days
      logger.info('\n📊 PHASE 2: Syncing Performance Data');
      logger.info('───────────────────────────────────────────────────────');
      
      const today = new Date();
      const performancePromises = [];
      
      // Process each day sequentially to avoid overwhelming the API
      for (let i = 0; i < daysBack; i++) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        // Amazon Ads API expects date in YYYYMMDD format (e.g., 20241020)
        const reportDate = date.toISOString().split('T')[0].replace(/-/g, '');
        const displayDate = date.toISOString().split('T')[0];

        logger.info(`\n📅 Processing Day ${i + 1}/${daysBack}: ${displayDate}`);
        logger.info('─────────────────────────────────────────────────────');
        
        try {
          // Process campaigns first, then ad groups and keywords in parallel
          const campaignPerf = 0 // await this.syncCampaignPerformance(reportDate);
          
          // Process ad groups and keywords in parallel
          const [adGroupPerf, keywordPerf] = await Promise.all([
            this.syncAdGroupPerformance(reportDate),
            this.syncKeywordPerformance(reportDate)
          ]);

          const dayTotal = campaignPerf + adGroupPerf + keywordPerf;
          totalRecords.performance += dayTotal;
          
          logger.info(`✅ Day ${i + 1} complete: ${dayTotal} total records synced`);
        } catch (error) {
          logger.error(`❌ Day ${i + 1} failed:`, error.message);
          // Continue with next day instead of failing completely
          continue;
        }
      }

      const total = Object.values(totalRecords).reduce((a, b) => a + b, 0);
      const duration = ((new Date() - startTime) / 1000).toFixed(2);
      
      await this.logSync('full_sync', 'success', total, null, startTime);

      logger.info('\n═══════════════════════════════════════════════════════');
      logger.info('✅ FULL SYNC COMPLETED SUCCESSFULLY');
      logger.info('═══════════════════════════════════════════════════════');
      logger.info(`📊 Summary:`);
      logger.info(`   • Campaigns synced: ${totalRecords.campaigns}`);
      logger.info(`   • Ad Groups synced: ${totalRecords.adGroups}`);
      logger.info(`   • Keywords synced: ${totalRecords.keywords}`);
      logger.info(`   • Performance records: ${totalRecords.performance}`);
      logger.info(`   • Total records: ${total}`);
      logger.info(`   • Duration: ${duration} seconds`);
      logger.info('═══════════════════════════════════════════════════════\n');
      
      return totalRecords;
    } catch (error) {
      const duration = ((new Date() - startTime) / 1000).toFixed(2);
      const total = Object.values(totalRecords).reduce((a, b) => a + b, 0);
      await this.logSync('full_sync', 'failed', total, error.message, startTime);
      
      logger.error('\n═══════════════════════════════════════════════════════');
      logger.error('❌ FULL SYNC FAILED');
      logger.error('═══════════════════════════════════════════════════════');
      logger.error(`Error: ${error.message}`);
      logger.error(`Duration before failure: ${duration} seconds`);
      logger.error('═══════════════════════════════════════════════════════\n');
      
      // Don't throw the error if we've synced some data successfully
      if (total > 0) {
        logger.warn(`⚠️  Partial sync completed: ${total} records synced before failure`);
        return totalRecords;
      }
      
      throw error;
    }
  }
}

module.exports = DataSyncService;

