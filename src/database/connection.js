const { Pool } = require('pg');
const logger = require('../utils/logger');
const config = require('../config/config');

class Database {
  constructor() {
    this.pool = new Pool(config.database);
    
    // Handle pool errors
    this.pool.on('error', (err) => {
      logger.error('Unexpected error on idle database client', err);
    });
  }

  /**
   * Execute a query
   */
  async query(text, params) {
    const start = Date.now();
    try {
      const result = await this.pool.query(text, params);
      const duration = Date.now() - start;
      logger.debug('Executed query', { text, duration, rows: result.rowCount });
      return result;
    } catch (error) {
      logger.error('Database query error', { text, error: error.message });
      throw error;
    }
  }

  /**
   * Get a client from the pool for transactions
   */
  async getClient() {
    return await this.pool.connect();
  }

  /**
   * Test database connection
   */
  async testConnection() {
    try {
      const result = await this.pool.query('SELECT NOW()');
      logger.info('Database connection test successful');
      return true;
    } catch (error) {
      logger.error('Database connection test failed', error);
      return false;
    }
  }

  /**
   * Close all connections
   */
  async close() {
    await this.pool.end();
    logger.info('Database pool closed');
  }

}

module.exports = new Database();

