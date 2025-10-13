require('dotenv').config();
const fs = require('fs');
const path = require('path');

// Helper function to load SSL certificate
function getSSLConfig() {
  if (process.env.DB_SSL !== 'true') {
    return false;
  }

  const sslConfig = {
    rejectUnauthorized: process.env.DB_SSL_REJECT_UNAUTHORIZED !== 'false'
  };

  // Option 1: Load from file
  if (process.env.DB_SSL_CA_FILE) {
    try {
      const certPath = path.resolve(process.cwd(), process.env.DB_SSL_CA_FILE);
      sslConfig.ca = fs.readFileSync(certPath, 'utf8');
    } catch (error) {
      console.error('Failed to load SSL certificate file:', error.message);
      throw error;
    }
  }
  // Option 2: Load from environment variable (inline)
  else if (process.env.DB_SSL_CA) {
    sslConfig.ca = process.env.DB_SSL_CA;
  }

  return sslConfig;
}

module.exports = {
  amazon: {
    clientId: process.env.AMAZON_CLIENT_ID,
    clientSecret: process.env.AMAZON_CLIENT_SECRET,
    refreshToken: process.env.AMAZON_REFRESH_TOKEN,
    profileId: process.env.AMAZON_PROFILE_ID,
    region: process.env.AMAZON_API_REGION || 'na',
    endpoint: process.env.AMAZON_API_ENDPOINT || 'https://advertising-api.amazon.com',
    tokenEndpoint: 'https://api.amazon.com/auth/o2/token'
  },
  database: {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT) || 5432,
    database: process.env.DB_NAME || 'amazon_ads',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD,
    // SSL configuration for cloud databases (Aiven, AWS RDS, etc.)
    ssl: getSSLConfig(),
    // Connection pool settings
    max: parseInt(process.env.DB_POOL_MAX) || 20,
    idleTimeoutMillis: parseInt(process.env.DB_IDLE_TIMEOUT) || 30000,
    connectionTimeoutMillis: parseInt(process.env.DB_CONNECTION_TIMEOUT) || 10000
  },
  sync: {
    hour: parseInt(process.env.SYNC_HOUR) || 2,
    minute: parseInt(process.env.SYNC_MINUTE) || 0,
    daysToFetch: parseInt(process.env.DAYS_TO_FETCH) || 7
  },
  server: {
    port: parseInt(process.env.PORT) || 3000,
    nodeEnv: process.env.NODE_ENV || 'development'
  }
};

