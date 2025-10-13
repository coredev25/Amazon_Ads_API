const fs = require('fs');
const path = require('path');
const db = require('../database/connection');
const logger = require('../utils/logger');

class ReportExportService {
  constructor() {
    this.reportsDir = path.join(__dirname, '../../reports');
    this.ensureReportsDir();
  }

  /**
   * Ensure reports directory exists
   */
  ensureReportsDir() {
    if (!fs.existsSync(this.reportsDir)) {
      fs.mkdirSync(this.reportsDir, { recursive: true });
    }
  }

  /**
   * Convert array of objects to CSV
   */
  arrayToCSV(data) {
    if (!data || data.length === 0) {
      return '';
    }

    const headers = Object.keys(data[0]);
    const csvRows = [];

    // Add header row
    csvRows.push(headers.join(','));

    // Add data rows
    for (const row of data) {
      const values = headers.map(header => {
        const value = row[header];
        // Escape commas and quotes in values
        if (value === null || value === undefined) return '';
        const stringValue = String(value);
        if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
          return `"${stringValue.replace(/"/g, '""')}"`;
        }
        return stringValue;
      });
      csvRows.push(values.join(','));
    }

    return csvRows.join('\n');
  }

  /**
   * Export campaign performance report
   */
  async exportCampaignPerformance(startDate, endDate) {
    try {
      logger.info(`Exporting campaign performance from ${startDate} to ${endDate}...`);

      const query = `
        SELECT 
          c.campaign_id,
          c.campaign_name,
          c.campaign_status,
          cp.report_date,
          cp.impressions,
          cp.clicks,
          CASE WHEN cp.impressions > 0 THEN (cp.clicks::DECIMAL / cp.impressions * 100) ELSE 0 END as ctr,
          cp.cost,
          CASE WHEN cp.clicks > 0 THEN (cp.cost / cp.clicks) ELSE 0 END as cpc,
          cp.attributed_conversions_7d,
          cp.attributed_sales_7d,
          CASE WHEN cp.cost > 0 THEN (cp.attributed_sales_7d / cp.cost) ELSE 0 END as roas
        FROM campaigns c
        LEFT JOIN campaign_performance cp ON c.campaign_id = cp.campaign_id
        WHERE cp.report_date >= $1 AND cp.report_date <= $2
        ORDER BY cp.report_date DESC, c.campaign_name
      `;

      const result = await db.query(query, [startDate, endDate]);
      const csv = this.arrayToCSV(result.rows);

      const filename = `campaign_performance_${startDate}_to_${endDate}.csv`;
      const filepath = path.join(this.reportsDir, filename);
      fs.writeFileSync(filepath, csv);

      logger.info(`Campaign performance report exported to ${filename}`);
      return { filepath, filename, recordCount: result.rows.length };
    } catch (error) {
      logger.error('Error exporting campaign performance:', error);
      throw error;
    }
  }

  /**
   * Export ad group performance report
   */
  async exportAdGroupPerformance(startDate, endDate) {
    try {
      logger.info(`Exporting ad group performance from ${startDate} to ${endDate}...`);

      const query = `
        SELECT 
          c.campaign_name,
          ag.ad_group_name,
          agp.report_date,
          agp.impressions,
          agp.clicks,
          CASE WHEN agp.impressions > 0 THEN (agp.clicks::DECIMAL / agp.impressions * 100) ELSE 0 END as ctr,
          agp.cost,
          CASE WHEN agp.clicks > 0 THEN (agp.cost / agp.clicks) ELSE 0 END as cpc,
          agp.attributed_conversions_7d,
          agp.attributed_sales_7d
        FROM ad_groups ag
        LEFT JOIN campaigns c ON ag.campaign_id = c.campaign_id
        LEFT JOIN ad_group_performance agp ON ag.ad_group_id = agp.ad_group_id
        WHERE agp.report_date >= $1 AND agp.report_date <= $2
        ORDER BY agp.report_date DESC, c.campaign_name, ag.ad_group_name
      `;

      const result = await db.query(query, [startDate, endDate]);
      const csv = this.arrayToCSV(result.rows);

      const filename = `ad_group_performance_${startDate}_to_${endDate}.csv`;
      const filepath = path.join(this.reportsDir, filename);
      fs.writeFileSync(filepath, csv);

      logger.info(`Ad group performance report exported to ${filename}`);
      return { filepath, filename, recordCount: result.rows.length };
    } catch (error) {
      logger.error('Error exporting ad group performance:', error);
      throw error;
    }
  }

  /**
   * Export keyword performance report
   */
  async exportKeywordPerformance(startDate, endDate) {
    try {
      logger.info(`Exporting keyword performance from ${startDate} to ${endDate}...`);

      const query = `
        SELECT 
          c.campaign_name,
          ag.ad_group_name,
          k.keyword_text,
          k.match_type,
          kp.report_date,
          kp.impressions,
          kp.clicks,
          CASE WHEN kp.impressions > 0 THEN (kp.clicks::DECIMAL / kp.impressions * 100) ELSE 0 END as ctr,
          kp.cost,
          CASE WHEN kp.clicks > 0 THEN (kp.cost / kp.clicks) ELSE 0 END as cpc,
          kp.attributed_conversions_7d,
          kp.attributed_sales_7d
        FROM keywords k
        LEFT JOIN campaigns c ON k.campaign_id = c.campaign_id
        LEFT JOIN ad_groups ag ON k.ad_group_id = ag.ad_group_id
        LEFT JOIN keyword_performance kp ON k.keyword_id = kp.keyword_id
        WHERE kp.report_date >= $1 AND kp.report_date <= $2
        ORDER BY kp.report_date DESC, c.campaign_name, ag.ad_group_name, k.keyword_text
      `;

      const result = await db.query(query, [startDate, endDate]);
      const csv = this.arrayToCSV(result.rows);

      const filename = `keyword_performance_${startDate}_to_${endDate}.csv`;
      const filepath = path.join(this.reportsDir, filename);
      fs.writeFileSync(filepath, csv);

      logger.info(`Keyword performance report exported to ${filename}`);
      return { filepath, filename, recordCount: result.rows.length };
    } catch (error) {
      logger.error('Error exporting keyword performance:', error);
      throw error;
    }
  }

  /**
   * Export all reports
   */
  async exportAllReports(startDate, endDate) {
    try {
      logger.info('Exporting all reports...');

      const reports = await Promise.all([
        this.exportCampaignPerformance(startDate, endDate),
        this.exportAdGroupPerformance(startDate, endDate),
        this.exportKeywordPerformance(startDate, endDate)
      ]);

      logger.info('All reports exported successfully');
      return reports;
    } catch (error) {
      logger.error('Error exporting all reports:', error);
      throw error;
    }
  }

  /**
   * Export summary report
   */
  async exportSummaryReport(startDate, endDate) {
    try {
      logger.info('Exporting summary report...');

      const query = `
        SELECT 
          'Campaign' as level,
          COUNT(DISTINCT c.campaign_id) as total_items,
          SUM(cp.impressions) as total_impressions,
          SUM(cp.clicks) as total_clicks,
          CASE WHEN SUM(cp.impressions) > 0 THEN (SUM(cp.clicks)::DECIMAL / SUM(cp.impressions) * 100) ELSE 0 END as avg_ctr,
          SUM(cp.cost) as total_cost,
          SUM(cp.attributed_conversions_7d) as total_conversions,
          SUM(cp.attributed_sales_7d) as total_sales,
          CASE WHEN SUM(cp.cost) > 0 THEN (SUM(cp.attributed_sales_7d) / SUM(cp.cost)) ELSE 0 END as roas
        FROM campaigns c
        LEFT JOIN campaign_performance cp ON c.campaign_id = cp.campaign_id
        WHERE cp.report_date >= $1 AND cp.report_date <= $2
        
        UNION ALL
        
        SELECT 
          'Ad Group' as level,
          COUNT(DISTINCT ag.ad_group_id) as total_items,
          SUM(agp.impressions) as total_impressions,
          SUM(agp.clicks) as total_clicks,
          CASE WHEN SUM(agp.impressions) > 0 THEN (SUM(agp.clicks)::DECIMAL / SUM(agp.impressions) * 100) ELSE 0 END as avg_ctr,
          SUM(agp.cost) as total_cost,
          SUM(agp.attributed_conversions_7d) as total_conversions,
          SUM(agp.attributed_sales_7d) as total_sales,
          CASE WHEN SUM(agp.cost) > 0 THEN (SUM(agp.attributed_sales_7d) / SUM(agp.cost)) ELSE 0 END as roas
        FROM ad_groups ag
        LEFT JOIN ad_group_performance agp ON ag.ad_group_id = agp.ad_group_id
        WHERE agp.report_date >= $1 AND agp.report_date <= $2
        
        UNION ALL
        
        SELECT 
          'Keyword' as level,
          COUNT(DISTINCT k.keyword_id) as total_items,
          SUM(kp.impressions) as total_impressions,
          SUM(kp.clicks) as total_clicks,
          CASE WHEN SUM(kp.impressions) > 0 THEN (SUM(kp.clicks)::DECIMAL / SUM(kp.impressions) * 100) ELSE 0 END as avg_ctr,
          SUM(kp.cost) as total_cost,
          SUM(kp.attributed_conversions_7d) as total_conversions,
          SUM(kp.attributed_sales_7d) as total_sales,
          CASE WHEN SUM(kp.cost) > 0 THEN (SUM(kp.attributed_sales_7d) / SUM(kp.cost)) ELSE 0 END as roas
        FROM keywords k
        LEFT JOIN keyword_performance kp ON k.keyword_id = kp.keyword_id
        WHERE kp.report_date >= $1 AND kp.report_date <= $2
      `;

      const result = await db.query(query, [startDate, endDate]);
      const csv = this.arrayToCSV(result.rows);

      const filename = `summary_report_${startDate}_to_${endDate}.csv`;
      const filepath = path.join(this.reportsDir, filename);
      fs.writeFileSync(filepath, csv);

      logger.info(`Summary report exported to ${filename}`);
      return { filepath, filename, recordCount: result.rows.length };
    } catch (error) {
      logger.error('Error exporting summary report:', error);
      throw error;
    }
  }
}

module.exports = ReportExportService;

