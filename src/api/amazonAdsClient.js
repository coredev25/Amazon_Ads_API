const axios = require('axios');
const logger = require('../utils/logger');
const config = require('../config/config');

class AmazonAdsClient {
  constructor() {
    this.accessToken = null;
    this.tokenExpiry = null;
    this.config = config.amazon;
  }

  /**
   * Refresh the access token using the refresh token
   */
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
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });

      this.accessToken = response.data.access_token;
      // Set token expiry (default to 1 hour minus 5 minutes for safety)
      this.tokenExpiry = Date.now() + ((response.data.expires_in || 3600) - 300) * 1000;

      logger.info('Access token refreshed successfully');
      return this.accessToken;
    } catch (error) {
      logger.error('Error refreshing access token:', error.response?.data || error.message);
      throw new Error('Failed to refresh access token: ' + (error.response?.data?.error_description || error.message));
    }
  }

  /**
   * Get a valid access token, refreshing if necessary
   */
  async getAccessToken() {
    if (!this.accessToken || Date.now() >= this.tokenExpiry) {
      await this.refreshAccessToken();
    }
    return this.accessToken;
  }

  /**
   * Make an authenticated API request
   */
  async makeRequest(method, endpoint, data = null, params = null) {
    try {
      const token = await this.getAccessToken();

      const headers = {
        'Authorization': `Bearer ${token}`,
        'Amazon-Advertising-API-ClientId': this.config.clientId,
        'Amazon-Advertising-API-Scope': this.config.profileId,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      };

      const requestConfig = {
        method,
        url: `${this.config.endpoint}${endpoint}`,
        headers,
        params
      };

      if (data) {
        requestConfig.data = data;
      }

      logger.debug(`Making API request: ${method} ${this.config.endpoint}${endpoint}`, { params });

      const response = await axios(requestConfig);
      return response.data;
    } catch (error) {
      logger.error(`API request failed: ${method} ${endpoint}`, {
        error: error.response?.data || error.message,
        status: error.response?.status,
        url: `${this.config.endpoint}${endpoint}`
      });
      
      // Provide more specific error messages
      if (error.response?.status === 404) {
        throw new Error(`API endpoint not found: ${endpoint}. Please check if the API version is correct.`);
      } else if (error.response?.status === 401) {
        throw new Error('Authentication failed. Please check your API credentials.');
      } else if (error.response?.status === 403) {
        throw new Error('Access forbidden. Please check your API permissions and profile ID.');
      } else if (error.response?.status === 425) {
        // Handle duplicate report requests - extract the duplicate report ID
        const errorDetail = error.response.data?.detail || '';
        const reportIdMatch = errorDetail.match(/duplicate of : ([a-f0-9-]+)/);
        if (reportIdMatch) {
          const duplicateReportId = reportIdMatch[1];
          logger.info(`Report request is a duplicate of existing report: ${duplicateReportId}`);
          logger.info(`Using existing report instead of creating a new one`);
          // Return the duplicate report ID instead of throwing an error
          return { reportId: duplicateReportId };
        }
        throw new Error(`Duplicate request detected: ${errorDetail}`);
      }
      
      throw error;
    }
  }


  /**
   * Get all campaigns
   */
  async getCampaigns(params = {}) {
    logger.info('Fetching campaigns...');
    const defaultParams = {
      stateFilter: 'enabled,paused,archived',
      ...params
    };
    return await this.makeRequest('GET', '/v2/campaigns', null, defaultParams);
  }

  /**
   * Get ad groups for a campaign
   */
  async getAdGroups(params = {}) {
    logger.info('Fetching ad groups...');
    const defaultParams = {
      stateFilter: 'enabled,paused,archived',
      ...params
    };
    return await this.makeRequest('GET', '/v2/adGroups', null, defaultParams);
  }

  /**
   * Get keywords
   */
  async getKeywords(params = {}) {
    logger.info('Fetching keywords...');
    const defaultParams = {
      stateFilter: 'enabled,paused,archived',
      ...params
    };
    return await this.makeRequest('GET', '/v2/keywords', null, defaultParams);
  }

  /**
   * Request a performance report using v3 API
   * According to: https://advertising.amazon.com/API/docs/en-us/guides/reporting/v3/report-types/overview
   */
  async requestReport(reportType, reportDate, metrics) {
    logger.info(`Requesting ${reportType} report for ${reportDate} using v3 API...`);

    const metricsArray = metrics || this.getDefaultMetrics(reportType);
    const reportTypeMap = {
      'campaigns': 'spCampaigns',
      'adGroups': 'spAdGroups',
      'keywords': 'spKeywords'
    };

    // Convert YYYYMMDD format to YYYY-MM-DD format for API
    const formattedDate = this.formatDateForAPI(reportDate);

    // v3 API format - dates go at top level, not inside configuration
    const reportConfig = {
      name: `${reportType}_${reportDate}`,
      startDate: formattedDate,  // Dates are at top level in YYYY-MM-DD format
      endDate: formattedDate,
      configuration: {
        adProduct: 'SPONSORED_PRODUCTS',
        groupBy: [reportType === 'campaigns' ? 'campaign' : reportType === 'adGroups' ? 'adGroup' : 'keyword'],
        columns: metricsArray,
        reportTypeId: reportTypeMap[reportType],
        timeUnit: 'DAILY',
        format: 'GZIP_JSON'
      }
    };

    logger.debug('v3 Report request config:', reportConfig);

    const response = await this.makeRequest('POST', '/reporting/reports', reportConfig);
    return response.reportId;
  }

  /**
   * Convert date from YYYYMMDD format to YYYY-MM-DD format for API
   */
  formatDateForAPI(apiDate) {
    if (apiDate.includes('-')) return apiDate; // Already formatted
    // Convert 20251022 to 2025-10-22
    return `${apiDate.substr(0, 4)}-${apiDate.substr(4, 2)}-${apiDate.substr(6, 2)}`;
  }

  /**
   * Get report status using v3 API
   */
  async getReportStatus(reportId) {
    return await this.makeRequest('GET', `/reporting/reports/${reportId}`);
  }

  /**
   * Download report data from v3 API
   * v3 API returns GZIP compressed JSON data
   */
  async downloadReport(reportUrl) {
    try {
      const zlib = require('zlib');
      const { promisify } = require('util');
      const gunzip = promisify(zlib.gunzip);

      logger.info(`Downloading report from: ${reportUrl}`);
      
      // Download the gzipped report file
      const response = await axios.get(reportUrl, {
        responseType: 'arraybuffer',  // Get as buffer for decompression
        timeout: 60000  // 60 second timeout for large files
      });

      logger.debug(`Downloaded ${response.data.length} bytes (compressed)`);

      // Decompress gzip data
      const decompressed = await gunzip(response.data);
      logger.debug(`Decompressed to ${decompressed.length} bytes`);
      
      // Parse JSON
      const jsonData = JSON.parse(decompressed.toString('utf-8'));
      
      logger.info(`Report downloaded successfully, records: ${Array.isArray(jsonData) ? jsonData.length : Object.keys(jsonData).length}`);
      return jsonData;
    } catch (error) {
      logger.error('Error downloading report:', {
        message: error.message,
        url: reportUrl,
        stack: error.stack
      });
      throw new Error(`Failed to download/decompress report: ${error.message}`);
    }
  }

  /**
   * Get default metrics for a report type
   * Updated for Amazon Ads API v3 with correct column names
   */
  getDefaultMetrics(reportType) {
    const metricsMap = {
      campaigns: [
        'campaignId',
        'campaignName',
        'campaignStatus',
        'impressions',
        'clicks',
        'cost',
        'purchases1d',
        'purchases7d',
        'purchases14d',
        'purchases30d',
        'sales1d',
        'sales7d',
        'sales14d',
        'sales30d'
      ],
      adGroups: [
        'campaignId',
        'adGroupId',
        'impressions',
        'clicks',
        'cost',
        'purchases1d',
        'purchases7d',
        'sales1d',
        'sales7d'
      ],
      keywords: [
        'campaignId',
        'adGroupId',
        'keywordId',
        'impressions',
        'clicks',
        'cost',
        'purchases1d',
        'purchases7d',
        'sales1d',
        'sales7d'
      ]
    };

    return metricsMap[reportType] || [];
  }

  /**
   * Wait for report to be ready and download it (v3 API)
   * v3 API statuses: PENDING, PROCESSING, COMPLETED, FAILED
   * Similar to Python sample's status checking loop
   */
  async waitAndDownloadReport(reportId, maxAttempts = 60, delayMs = 30000) {
    logger.info(`Starting report status check for ${reportId}...`);
    
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const statusResponse = await this.getReportStatus(reportId);

        logger.info(`Report ${reportId} status: ${statusResponse.status} (attempt ${attempt + 1}/${maxAttempts})`);

        if (statusResponse.status === 'COMPLETED' || statusResponse.status === 'SUCCESS') {
          logger.info(`Report ${reportId} is ready, downloading...`);
          
          // Get download URL (v3 uses 'url', v2 uses 'location')
          const downloadUrl = statusResponse.url || statusResponse.location;
          
          if (!downloadUrl) {
            throw new Error('Report completed but no download URL provided');
          }
          
          return await this.downloadReport(downloadUrl);
        } else if (statusResponse.status === 'FAILED' || statusResponse.status === 'FAILURE') {
          const errorDetail = statusResponse.failureReason || statusResponse.statusDetails || 'Unknown error';
          throw new Error(`Report ${reportId} generation failed: ${errorDetail}`);
        } else if (statusResponse.status === 'IN_PROGRESS' || statusResponse.status === 'PROCESSING' || statusResponse.status === 'PENDING') {
          // Use exponential backoff for longer waits
          const waitTime = Math.min(delayMs * Math.pow(1.2, Math.floor(attempt / 5)), 120000); // Max 2 minutes
          logger.info(`Report generation in progress, waiting ${waitTime / 1000} seconds...`);
          await new Promise(resolve => setTimeout(resolve, waitTime));
        } else {
          logger.warn(`Unknown report status: ${statusResponse.status}`);
          await new Promise(resolve => setTimeout(resolve, delayMs));
        }
      } catch (error) {
        if (error.message.includes('generation failed')) {
          throw error; // Don't retry if report generation explicitly failed
        }
        logger.warn(`Error checking report status (attempt ${attempt + 1}/${maxAttempts}):`, error.message);
        
        if (attempt === maxAttempts - 1) {
          throw error; // Throw on last attempt
        }
        
        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
    }

    throw new Error(`Report ${reportId} timed out after ${maxAttempts} attempts (${(maxAttempts * delayMs) / 60000} minutes)`);
  }

  /**
   * Get performance data for a date range using v3 API
   * v3 API supports date ranges natively
   */
  async getPerformanceData(reportType, startDate, endDate) {
    logger.info(`Fetching ${reportType} performance data for ${startDate} using v3 API...`);

    // v3 API can handle both startDate and endDate (for now, using single date)
    const reportId = await this.requestReport(reportType, startDate);
    const reportData = await this.waitAndDownloadReport(reportId);

    return reportData;
  }
}

module.exports = AmazonAdsClient;

