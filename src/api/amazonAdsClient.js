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
   * Request a performance report
   */
  async requestReport(reportType, reportDate, metrics) {
    logger.info(`Requesting ${reportType} report for ${reportDate}...`);

    const reportConfig = {
      reportDate,
      metrics: metrics || this.getDefaultMetrics(reportType)
    };

    const response = await this.makeRequest('POST', `/v2/${reportType}/report`, reportConfig);
    return response.reportId;
  }

  /**
   * Get report status
   */
  async getReportStatus(reportId) {
    return await this.makeRequest('GET', `/v2/reports/${reportId}`);
  }

  /**
   * Download report data
   */
  async downloadReport(reportUrl) {
    try {
      const response = await axios.get(reportUrl, {
        responseType: 'json'
      });
      return response.data;
    } catch (error) {
      logger.error('Error downloading report:', error.message);
      throw error;
    }
  }

  /**
   * Get default metrics for a report type
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
        'attributedConversions1d',
        'attributedConversions7d',
        'attributedConversions14d',
        'attributedConversions30d',
        'attributedSales1d',
        'attributedSales7d',
        'attributedSales14d',
        'attributedSales30d'
      ],
      adGroups: [
        'campaignId',
        'adGroupId',
        'adGroupName',
        'impressions',
        'clicks',
        'cost',
        'attributedConversions1d',
        'attributedConversions7d',
        'attributedSales1d',
        'attributedSales7d'
      ],
      keywords: [
        'campaignId',
        'adGroupId',
        'keywordId',
        'keywordText',
        'matchType',
        'impressions',
        'clicks',
        'cost',
        'attributedConversions1d',
        'attributedConversions7d',
        'attributedSales1d',
        'attributedSales7d'
      ]
    };

    return metricsMap[reportType] || [];
  }

  /**
   * Wait for report to be ready and download it
   */
  async waitAndDownloadReport(reportId, maxAttempts = 30, delayMs = 10000) {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const status = await this.getReportStatus(reportId);

      if (status.status === 'SUCCESS') {
        logger.info(`Report ${reportId} is ready, downloading...`);
        return await this.downloadReport(status.location);
      } else if (status.status === 'FAILURE') {
        throw new Error(`Report ${reportId} generation failed`);
      }

      logger.info(`Report ${reportId} status: ${status.status}, waiting...`);
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }

    throw new Error(`Report ${reportId} timed out after ${maxAttempts} attempts`);
  }

  /**
   * Get performance data for a date range
   */
  async getPerformanceData(reportType, startDate, endDate) {
    logger.info(`Fetching ${reportType} performance data from ${startDate} to ${endDate}...`);

    const reportId = await this.requestReport(reportType, startDate);
    const reportData = await this.waitAndDownloadReport(reportId);

    return reportData;
  }
}

module.exports = AmazonAdsClient;

