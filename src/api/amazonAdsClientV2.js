const axios = require('axios');
const zlib = require('zlib');
const { promisify } = require('util');
const logger = require('../utils/logger');
const config = require('../config/config');

const gunzip = promisify(zlib.gunzip);

/**
 * Amazon Ads API v2 Client (DEPRECATED - For Reference Only)
 * 
 * ⚠️ WARNING: v2 API is deprecated since 2023-03-30
 * Use amazonAdsClient.js (v3) instead
 * 
 * This is a JavaScript equivalent of the Python sample provided,
 * kept for reference or backward compatibility if absolutely needed.
 */
class AmazonAdsClientV2 {
  constructor() {
    this.accessToken = null;
    this.tokenExpiry = null;
    this.config = config.amazon;
  }

  /**
   * Get Access Token (equivalent to Python's get_access_token)
   */
  async getAccessToken() {
    if (!this.accessToken || Date.now() >= this.tokenExpiry) {
      await this.refreshAccessToken();
    }
    return this.accessToken;
  }

  async refreshAccessToken() {
    try {
      logger.info('Refreshing Amazon Ads API access token...');

      const params = new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: this.config.refreshToken,
        client_id: this.config.clientId,
        client_secret: this.config.clientSecret
      });

      const response = await axios.post(this.config.tokenEndpoint, params.toString(), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }
      });

      this.accessToken = response.data.access_token;
      this.tokenExpiry = Date.now() + ((response.data.expires_in || 3600) - 300) * 1000;

      logger.info('Access token refreshed successfully');
      return this.accessToken;
    } catch (error) {
      logger.error('Error refreshing access token:', error.response?.data || error.message);
      throw new Error('Failed to refresh access token: ' + (error.response?.data?.error_description || error.message));
    }
  }

  /**
   * Request Report (equivalent to Python's re quest_report)
   * Uses DEPRECATED v2 API
   */
  async requestReport(recordType, reportDate, metrics = null, segment = null) {
    try {
      const token = await this.getAccessToken();

      const headers = {
        'Amazon-Advertising-API-ClientId': this.config.clientId,
        'Authorization': `Bearer ${token}`,
        'Amazon-Advertising-API-Scope': this.config.profileId,
        'Content-Type': 'application/json'
      };

      // Default metrics if not provided
      const defaultMetrics = 'impressions,clicks,cost,purchases1d,sales1d';
      
      const body = {
        reportDate: reportDate, // e.g., "20241020"
        metrics: metrics || defaultMetrics
      };

      // Add segment for keyword reports (like Python sample)
      if (segment) {
        body.segment = segment;
      }

      // v2 endpoint
      const endpoint = `${this.config.endpoint}/v2/${recordType}/report`;

      logger.info(`Requesting ${recordType} report for ${reportDate} (v2 API - DEPRECATED)...`);
      logger.debug('Request body:', body);

      const response = await axios.post(endpoint, body, { headers });

      return response.data.reportId;
    } catch (error) {
      logger.error(`Error requesting report:`, {
        error: error.response?.data || error.message,
        status: error.response?.status
      });
      throw error;
    }
  }

  /**
   * Get Report Data (equivalent to Python's get_report_data)
   * Checks status and downloads when ready
   */
  async getReportData(reportId, maxAttempts = 30, delaySeconds = 30) {
    try {
      const token = await this.getAccessToken();

      const headers = {
        'Amazon-Advertising-API-ClientId': this.config.clientId,
        'Authorization': `Bearer ${token}`,
        'Amazon-Advertising-API-Scope': this.config.profileId
      };

      const statusEndpoint = `${this.config.endpoint}/v2/reports/${reportId}`;

      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        logger.info(`Checking report status (attempt ${attempt + 1}/${maxAttempts})...`);

        const response = await axios.get(statusEndpoint, { headers });
        const reportStatus = response.data;

        if (reportStatus.status === 'SUCCESS') {
          logger.info('Report generation successful, downloading...');
          
          const reportLocation = reportStatus.location;
          
          // Download the report file
          const reportFileResponse = await axios.get(reportLocation, {
            responseType: 'arraybuffer',
            timeout: 60000
          });

          // Decompress the gzipped report data
          const decompressed = await gunzip(reportFileResponse.data);
          const reportData = JSON.parse(decompressed.toString('utf-8'));

          logger.info(`Report downloaded successfully, records: ${reportData.length}`);
          return reportData;

        } else if (reportStatus.status === 'IN_PROGRESS') {
          logger.info(`Report generation in progress, waiting ${delaySeconds} seconds...`);
          await new Promise(resolve => setTimeout(resolve, delaySeconds * 1000));

        } else if (reportStatus.status === 'FAILURE') {
          const errorDetails = reportStatus.statusDetails || 'Unknown error';
          throw new Error(`Report generation failed: ${errorDetails}`);

        } else {
          logger.warn(`Unknown status: ${reportStatus.status}`);
          await new Promise(resolve => setTimeout(resolve, delaySeconds * 1000));
        }
      }

      throw new Error(`Report ${reportId} timed out after ${maxAttempts} attempts`);

    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Report ${reportId} not found`);
      }
      logger.error('Error getting report data:', error.message);
      throw error;
    }
  }

  /**
   * Main method combining request and retrieval
   * (Like the Python sample's main execution flow)
   */
  async getPerformanceData(recordType, reportDate, customMetrics = null, segment = null) {
    logger.info(`Fetching ${recordType} performance data for ${reportDate}...`);
    
    // Step 1: Request report generation
    const reportId = await this.requestReport(recordType, reportDate, customMetrics, segment);
    logger.info(`Report requested with ID: ${reportId}`);

    // Step 2: Wait for report and download
    const reportData = await this.getReportData(reportId);
    
    return reportData;
  }
}

module.exports = AmazonAdsClientV2;

