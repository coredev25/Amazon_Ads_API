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
   * Sync campaigns data using v3 API
   * v3 API field names are different from v2:
   * - state -> state (ENABLED, PAUSED, ARCHIVED) - stored as-is in uppercase
   * - name -> name
   * - budget -> budget.budget or dailyBudget
   */
  async syncCampaigns() {
    try {
      logger.info('📋 Syncing campaigns from Amazon Ads API v3...');
      const campaigns = await this.client.getCampaigns();

      if (!campaigns || campaigns.length === 0) {
        logger.warn('⚠️  No campaigns returned from API');
        return 0;
      }

      logger.info(`📥 Retrieved ${campaigns.length} campaigns, saving to database...`);

      let synced = 0;
      let errors = 0;
      
      for (const campaign of campaigns) {
        try {
        // v3 API response structure
        // {
        //   campaignId, name, state, targetingType, startDate, endDate,
        //   budget: { budgetType, budget }, dynamicBidding, ...
        // }
          
          // Validate required fields
          if (!campaign.campaignId) {
            logger.warn('Skipping campaign without campaignId:', campaign);
            errors++;
            continue;
          }
          
          const campaignId = String(campaign.campaignId); // Ensure string for BIGINT
          const campaignName = campaign.name || 'Unnamed Campaign';
          const campaignState = (campaign.state || 'ENABLED').toUpperCase(); // ENABLED, PAUSED, ARCHIVED - store in uppercase
          const targetingType = campaign.targetingType || 'MANUAL';
        const startDate = campaign.startDate || null;
        const endDate = campaign.endDate || null;
          
          // Handle budget - v3 API can return budget in different formats
          let budgetAmount = null;
          let budgetType = 'DAILY';
          
          if (campaign.budget) {
            budgetAmount = campaign.budget.budget || campaign.budget.budgetAmount || null;
            budgetType = campaign.budget.budgetType || campaign.budget.type || 'DAILY';
          } else if (campaign.dailyBudget) {
            budgetAmount = campaign.dailyBudget;
            budgetType = 'DAILY';
          }

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
            campaignId,
            campaignName,
            campaignState,
            targetingType,
            startDate,
            endDate,
            budgetAmount,
            budgetType
          ]
        );
        synced++;
        
        // Log progress every 50 campaigns
        if (synced % 50 === 0) {
          logger.info(`📋 Campaigns progress: ${synced}/${campaigns.length}`);
          }
        } catch (error) {
          logger.error(`Error syncing campaign ${campaign.campaignId}:`, error.message);
          errors++;
        }
      }

      logger.info(`✅ Synced ${synced} campaigns${errors > 0 ? `, ${errors} errors` : ''}`);
      return synced;
    } catch (error) {
      logger.error('❌ Error syncing campaigns:', error.message);
      throw error;
    }
  }

  /**
   * Sync ad groups data using v3 API
   * v3 API response structure:
   * { adGroupId, name, campaignId, defaultBid, state }
   */
  async syncAdGroups() {
    try {
      logger.info('📋 Syncing ad groups from Amazon Ads API v3...');
      const adGroups = await this.client.getAdGroups();

      if (!adGroups || adGroups.length === 0) {
        logger.warn('⚠️  No ad groups returned from API');
        return 0;
      }

      logger.info(`📥 Retrieved ${adGroups.length} ad groups, saving to database...`);

      let synced = 0;
      let skipped = 0;
      let errors = 0;
      
      // Build set of existing campaign IDs for faster lookup
      const campaignResult = await db.query('SELECT campaign_id FROM campaigns');
      const existingCampaignIds = new Set(campaignResult.rows.map(r => String(r.campaign_id)));
      
      for (const adGroup of adGroups) {
        try {
          // Validate required fields
          if (!adGroup.adGroupId) {
            logger.warn('Skipping ad group without adGroupId:', adGroup);
            errors++;
            continue;
          }
          
          if (!adGroup.campaignId) {
            logger.warn(`Skipping ad group ${adGroup.adGroupId} without campaignId`);
            errors++;
            continue;
          }
          
          // Check if campaign exists
          const campaignIdStr = String(adGroup.campaignId);
          if (!existingCampaignIds.has(campaignIdStr)) {
          logger.debug(`Skipping ad group ${adGroup.adGroupId} - campaign ${adGroup.campaignId} not found`);
          skipped++;
          continue;
        }

          // v3 API response fields - ensure proper data types and defaults
          const adGroupId = String(adGroup.adGroupId); // BIGINT as string
          const adGroupName = adGroup.name || 'Unnamed Ad Group';
          const campaignId = campaignIdStr;
        const defaultBid = adGroup.defaultBid || adGroup.bid || null;
          const state = (adGroup.state || 'ENABLED').toUpperCase(); // ENABLED, PAUSED, ARCHIVED - store in uppercase
        
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
            adGroupId,
            adGroupName,
            campaignId,
            defaultBid,
            state
          ]
        );
        synced++;
        
        // Log progress every 100 ad groups
        if (synced % 100 === 0) {
          logger.info(`📋 Ad groups progress: ${synced}/${adGroups.length}`);
          }
        } catch (error) {
          logger.error(`Error syncing ad group ${adGroup.adGroupId}:`, error.message);
          errors++;
        }
      }

      logger.info(`✅ Synced ${synced} ad groups, skipped ${skipped} (missing campaigns)${errors > 0 ? `, ${errors} errors` : ''}`);
      return synced;
    } catch (error) {
      logger.error('❌ Error syncing ad groups:', error.message);
      throw error;
    }
  }

  /**
   * Sync keywords data using v3 API
   * v3 API response structure:
   * { keywordId, keywordText, matchType, campaignId, adGroupId, bid, state }
   */
  async syncKeywords() {
    try {
      logger.info('📋 Syncing keywords from Amazon Ads API v3...');
      const keywords = await this.client.getKeywords();

      if (!keywords || keywords.length === 0) {
        logger.warn('⚠️  No keywords returned from API');
        return 0;
      }

      logger.info(`📥 Retrieved ${keywords.length} keywords, saving to database...`);

      let synced = 0;
      let skipped = 0;
      let errors = 0;
      
      // Build a set of existing campaign and ad group IDs for faster lookup
      const campaignResult = await db.query('SELECT campaign_id FROM campaigns');
      const adGroupResult = await db.query('SELECT ad_group_id FROM ad_groups');
      const campaignIds = new Set(campaignResult.rows.map(r => String(r.campaign_id)));
      const adGroupIds = new Set(adGroupResult.rows.map(r => String(r.ad_group_id)));
      
      for (const keyword of keywords) {
        try {
          // Validate required fields
          if (!keyword.keywordId) {
            logger.warn('Skipping keyword without keywordId:', keyword);
            errors++;
            continue;
          }
          
          if (!keyword.campaignId || !keyword.adGroupId) {
            logger.warn(`Skipping keyword ${keyword.keywordId} without campaignId or adGroupId`);
            errors++;
            continue;
          }
          
        // Check if campaign and ad group exist
          const campaignIdStr = String(keyword.campaignId);
          const adGroupIdStr = String(keyword.adGroupId);
          
          if (!campaignIds.has(campaignIdStr)) {
          logger.debug(`Skipping keyword ${keyword.keywordId} - campaign ${keyword.campaignId} not found`);
          skipped++;
          continue;
        }
        
          if (!adGroupIds.has(adGroupIdStr)) {
          logger.debug(`Skipping keyword ${keyword.keywordId} - ad group ${keyword.adGroupId} not found`);
          skipped++;
          continue;
        }

          // v3 API response fields - ensure proper data types and defaults
          const keywordId = String(keyword.keywordId); // BIGINT as string
          const keywordText = keyword.keywordText || keyword.keyword || '';
          const matchType = (keyword.matchType || 'BROAD').toUpperCase(); // BROAD, PHRASE, EXACT
          const campaignId = campaignIdStr;
          const adGroupId = adGroupIdStr;
        const bid = keyword.bid || null;
          const state = (keyword.state || 'ENABLED').toUpperCase(); // ENABLED, PAUSED, ARCHIVED - store in uppercase
        
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
            keywordId,
            keywordText,
            matchType,
            campaignId,
            adGroupId,
            bid,
            state
          ]
        );
        synced++;
        
        // Log progress every 200 keywords
        if (synced % 200 === 0) {
          logger.info(`📋 Keywords progress: ${synced}/${keywords.length}`);
          }
        } catch (error) {
          logger.error(`Error syncing keyword ${keyword.keywordId}:`, error.message);
          errors++;
        }
      }

      logger.info(`✅ Synced ${synced} keywords, skipped ${skipped} (missing campaigns/ad groups)${errors > 0 ? `, ${errors} errors` : ''}`);
      return synced;
    } catch (error) {
      logger.error('❌ Error syncing keywords:', error.message);
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
   * v3 API now returns campaignId in report data
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
      let skipped = 0;
      const total = reportData.length;

      // Build lookup for ad groups if campaignId not in report
      const adGroupResult = await db.query('SELECT ad_group_id, campaign_id FROM ad_groups');
      const adGroupToCampaign = {};
      adGroupResult.rows.forEach(r => {
        adGroupToCampaign[String(r.ad_group_id)] = r.campaign_id;
      });

      for (const record of reportData) {
        if (!record.adGroupId) continue;

        // Use campaignId from report if available, otherwise lookup from database
        let campaignId = record.campaignId;
        if (!campaignId) {
          campaignId = adGroupToCampaign[String(record.adGroupId)];
          if (!campaignId) {
            logger.debug(`Skipping ad group performance for ${record.adGroupId} - ad group not found in database`);
            skipped++;
            continue;
          }
        }

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
            campaignId,
            record.adGroupId,
            dbDate,
            record.impressions || 0,
            record.clicks || 0,
            record.cost || 0,
            record.purchases1d || 0,  // API v3 returns purchases1d
            record.purchases7d || 0,  // API v3 returns purchases7d
            record.sales1d || 0,      // API v3 returns sales1d
            record.sales7d || 0       // API v3 returns sales7d
          ]
        );
        synced++;
        
        // Log progress every 50 records
        if (synced % 50 === 0) {
          logger.info(`📊 [AD GROUPS] Progress: ${synced}/${total} records saved`);
        }
      }

      logger.info(`✅ [AD GROUPS] Successfully synced ${synced} ad group performance records for ${reportDate}, skipped ${skipped}`);
      return synced;
    } catch (error) {
      logger.error(`❌ [AD GROUPS] Error syncing ad group performance:`, error.message);
      throw error;
    }
  }

  /**
   * Sync performance data for keywords
   * v3 API now returns campaignId and adGroupId in report data
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
      let skipped = 0;
      const total = reportData.length;

      // Build lookup for keywords if data not in report
      const keywordResult = await db.query('SELECT keyword_id, campaign_id, ad_group_id FROM keywords');
      const keywordData = {};
      keywordResult.rows.forEach(r => {
        keywordData[String(r.keyword_id)] = { campaign_id: r.campaign_id, ad_group_id: r.ad_group_id };
      });

      for (const record of reportData) {
        if (!record.keywordId) continue;

        // Use data from report if available, otherwise lookup from database
        let campaignId = record.campaignId;
        let adGroupId = record.adGroupId;
        
        // Check if keyword exists in database (required for foreign key constraint)
        const kwData = keywordData[String(record.keywordId)];
        if (!kwData) {
          // This is likely a product target, not a keyword - skip it
          skipped++;
          continue;
        }
        
        // Use lookup data if not provided in report
        campaignId = campaignId || kwData.campaign_id;
        adGroupId = adGroupId || kwData.ad_group_id;

        try {
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
              campaignId,
              adGroupId,
              record.keywordId,
              dbDate,
              record.impressions || 0,
              record.clicks || 0,
              record.cost || 0,
              record.purchases1d || 0,  // API v3 returns purchases1d
              record.purchases7d || 0,  // API v3 returns purchases7d
              record.sales1d || 0,      // API v3 returns sales1d
              record.sales7d || 0       // API v3 returns sales7d
            ]
          );
          synced++;
        } catch (dbError) {
          // Handle foreign key constraint errors gracefully
          if (dbError.message.includes('foreign key constraint')) {
            skipped++;
            continue;
          }
          throw dbError;
        }
        
        // Log progress every 100 records
        if (synced % 100 === 0) {
          logger.info(`📊 [KEYWORDS] Progress: ${synced}/${total} records saved`);
        }
      }

      logger.info(`✅ [KEYWORDS] Successfully synced ${synced} keyword performance records for ${reportDate}, skipped ${skipped}`);
      return synced;
    } catch (error) {
      logger.error(`❌ [KEYWORDS] Error syncing keyword performance:`, error.message);
      throw error;
    }
  }

  /**
   * Sync product ads data using v3 API
   * Product ads link products (ASINs) to ad groups
   */
  async syncProductAds() {
    try {
      logger.info('📋 Syncing product ads from Amazon Ads API v3...');
      const productAds = await this.client.getProductAds();

      if (!productAds || productAds.length === 0) {
        logger.warn('⚠️  No product ads returned from API');
        return 0;
      }

      logger.info(`📥 Retrieved ${productAds.length} product ads, saving to database...`);

      // Build lookup for existing campaigns and ad groups
      const campaignResult = await db.query('SELECT campaign_id FROM campaigns');
      const adGroupResult = await db.query('SELECT ad_group_id FROM ad_groups');
      const campaignIds = new Set(campaignResult.rows.map(r => String(r.campaign_id)));
      const adGroupIds = new Set(adGroupResult.rows.map(r => String(r.ad_group_id)));

      let synced = 0;
      let skipped = 0;
      let errors = 0;

      for (const ad of productAds) {
        try {
          // Validate required fields
          if (!ad.adId) {
            logger.warn('Skipping product ad without adId:', ad);
            errors++;
            continue;
          }
          
          if (!ad.campaignId || !ad.adGroupId) {
            logger.warn(`Skipping product ad ${ad.adId} without campaignId or adGroupId`);
            errors++;
            continue;
          }
          
        // Check if campaign and ad group exist
          const campaignIdStr = String(ad.campaignId);
          const adGroupIdStr = String(ad.adGroupId);
          
          if (!campaignIds.has(campaignIdStr)) {
          logger.debug(`Skipping product ad ${ad.adId} - campaign ${ad.campaignId} not found`);
          skipped++;
          continue;
        }

          if (!adGroupIds.has(adGroupIdStr)) {
          logger.debug(`Skipping product ad ${ad.adId} - ad group ${ad.adGroupId} not found`);
          skipped++;
          continue;
        }

        await db.query(
          `INSERT INTO product_ads (
            ad_id, campaign_id, ad_group_id, asin, sku, state
          ) VALUES ($1, $2, $3, $4, $5, $6)
          ON CONFLICT (ad_id)
          DO UPDATE SET
            campaign_id = $2,
            ad_group_id = $3,
            asin = $4,
            sku = $5,
            state = $6,
            updated_at = CURRENT_TIMESTAMP`,
          [
              String(ad.adId), // BIGINT as string
              campaignIdStr,
              adGroupIdStr,
            ad.asin || null,
            ad.sku || null,
              (ad.state || 'ENABLED').toUpperCase() // Store in uppercase
          ]
        );
        synced++;

        if (synced % 100 === 0) {
          logger.info(`📋 Product ads progress: ${synced}/${productAds.length}`);
          }
        } catch (error) {
          logger.error(`Error syncing product ad ${ad.adId}:`, error.message);
          errors++;
        }
      }

      logger.info(`✅ Synced ${synced} product ads, skipped ${skipped}${errors > 0 ? `, ${errors} errors` : ''}`);
      return synced;
    } catch (error) {
      logger.error('❌ Error syncing product ads:', error.message);
      throw error;
    }
  }

  /**
   * Sync search term performance data
   * Used for negative keyword analysis and search term harvesting
   */
  async syncSearchTermPerformance(reportDate) {
    try {
      logger.info(`📊 [SEARCH TERMS] Syncing search term performance for ${reportDate}...`);
      
      const reportData = await this.client.getSearchTermPerformanceData(reportDate);

      if (!reportData || reportData.length === 0) {
        logger.warn(`⚠️  [SEARCH TERMS] No search term data returned for ${reportDate}`);
        return 0;
      }

      logger.info(`📊 [SEARCH TERMS] Received ${reportData.length} records, saving to database...`);
      
      const dbDate = this.formatDateForDB(reportDate);
      let synced = 0;
      let skipped = 0;

      for (const record of reportData) {
        if (!record.searchTerm) continue;

        await db.query(
          `INSERT INTO search_term_performance (
            campaign_id, ad_group_id, keyword_id, search_term, report_date,
            impressions, clicks, cost,
            attributed_conversions_1d, attributed_conversions_7d,
            attributed_sales_1d, attributed_sales_7d
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
          ON CONFLICT (search_term, keyword_id, report_date)
          DO UPDATE SET
            campaign_id = $1,
            ad_group_id = $2,
            impressions = $6,
            clicks = $7,
            cost = $8,
            attributed_conversions_1d = $9,
            attributed_conversions_7d = $10,
            attributed_sales_1d = $11,
            attributed_sales_7d = $12,
            updated_at = CURRENT_TIMESTAMP`,
          [
            record.campaignId,
            record.adGroupId,
            record.keywordId || null,
            record.searchTerm,
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

        if (synced % 500 === 0) {
          logger.info(`📊 [SEARCH TERMS] Progress: ${synced}/${reportData.length} records saved`);
        }
      }

      logger.info(`✅ [SEARCH TERMS] Successfully synced ${synced} search term records for ${reportDate}`);
      return synced;
    } catch (error) {
      logger.error(`❌ [SEARCH TERMS] Error syncing search term performance:`, error.message);
      throw error;
    }
  }

  /**
   * Sync negative keywords from Amazon Ads
   */
  async syncNegativeKeywords() {
    try {
      logger.info('📋 Syncing negative keywords from Amazon Ads API v3...');
      
      const [adGroupNegatives, campaignNegatives] = await Promise.all([
        this.client.getNegativeKeywords(),
        this.client.getCampaignNegativeKeywords()
      ]);

      logger.info(`📥 Retrieved ${adGroupNegatives.length} ad group negatives, ${campaignNegatives.length} campaign negatives`);

      // For now, just log - the negative_keyword_history table is used by the AI rule engine
      // We could store these for reference if needed
      
      return adGroupNegatives.length + campaignNegatives.length;
    } catch (error) {
      logger.error('❌ Error syncing negative keywords:', error.message);
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
   * Full sync - campaigns, ad groups, keywords, product ads, and performance data
   */
  async fullSync(daysBack = 7) {
    const startTime = new Date();
    const totalRecords = { campaigns: 0, adGroups: 0, keywords: 0, productAds: 0, performance: 0 };

    try {
      logger.info('═══════════════════════════════════════════════════════');
      logger.info('🚀 STARTING FULL DATA SYNC (Amazon Ads API v3)');
      logger.info(`📅 Syncing performance data for the last ${daysBack} days`);
      logger.info('═══════════════════════════════════════════════════════');

      // Sync metadata
      // logger.info('\n📋 PHASE 1: Syncing Metadata');
      // logger.info('───────────────────────────────────────────────────────');
      // totalRecords.campaigns = await this.syncCampaigns();
      // totalRecords.adGroups = await this.syncAdGroups();
      // totalRecords.keywords = await this.syncKeywords();
      
      // // Try to sync product ads (may fail on some accounts)
      // try {
      //   totalRecords.productAds = await this.syncProductAds();
      // } catch (error) {
      //   logger.warn(`⚠️  Product ads sync skipped: ${error.message}`);
      //   totalRecords.productAds = 0;
      // }
      
      // logger.info(`✅ Metadata sync complete: ${totalRecords.campaigns} campaigns, ${totalRecords.adGroups} ad groups, ${totalRecords.keywords} keywords, ${totalRecords.productAds} product ads`);

      // Sync performance data for the last N days
      logger.info('\n📊 PHASE 2: Syncing Performance Data');
      logger.info('───────────────────────────────────────────────────────');
      
      // TIMEZONE FIX: Always start from Yesterday (T-1) to ensure complete data
      // Amazon Ads data resets at midnight in marketplace timezone (PST/GMT)
      // Processing Yesterday ensures data is fully attributed and closed
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1); // Start from Yesterday (T-1)
      
      logger.info(`📅 Processing data starting from Yesterday (${yesterday.toISOString().split('T')[0]}) to ensure complete attribution`);
      
      const performancePromises = [];
      
      // Process each day sequentially to avoid overwhelming the API
      // Start from Yesterday and go back N days
      for (let i = 0; i < daysBack; i++) {
        const date = new Date(yesterday);
        date.setDate(date.getDate() - i);
        // Amazon Ads API expects date in YYYYMMDD format (e.g., 20241020)
        const reportDate = date.toISOString().split('T')[0].replace(/-/g, '');
        const displayDate = date.toISOString().split('T')[0];

        logger.info(`\n📅 Processing Day ${i + 1}/${daysBack}: ${displayDate}`);
        logger.info('─────────────────────────────────────────────────────');
        
        try {
          // Process campaigns first, then ad groups and keywords in parallel
          const campaignPerf = await this.syncCampaignPerformance(reportDate);
          
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
      logger.info(`   • Product Ads synced: ${totalRecords.productAds}`);
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