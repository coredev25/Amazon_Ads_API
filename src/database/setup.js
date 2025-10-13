const fs = require('fs');
const path = require('path');
const db = require('./connection');
const logger = require('../utils/logger');

async function setupDatabase() {
  try {
    logger.info('Setting up database...');

    // Test connection first
    const isConnected = await db.testConnection();
    if (!isConnected) {
      throw new Error('Failed to connect to database');
    }

    // Read and execute schema
    const schemaPath = path.join(__dirname, 'schema.sql');
    const schema = fs.readFileSync(schemaPath, 'utf8');

    // Split by semicolon but handle dollar-quoted strings properly
    const statements = [];
    let currentStatement = '';
    let inDollarQuote = false;
    let dollarTag = '';
    
    const lines = schema.split('\n');
    
    for (const line of lines) {
      currentStatement += line + '\n';
      
      // Check for start of dollar-quoted string
      const dollarMatch = line.match(/\$([^$]*)\$/);
      if (dollarMatch && !inDollarQuote) {
        inDollarQuote = true;
        dollarTag = dollarMatch[1];
      }
      // Check for end of dollar-quoted string
      else if (inDollarQuote && line.includes(`$${dollarTag}$`)) {
        inDollarQuote = false;
        dollarTag = '';
      }
      
      // Only split on semicolon if not inside a dollar-quoted string
      if (!inDollarQuote && line.trim().endsWith(';')) {
        const statement = currentStatement.trim();
        if (statement.length > 0) {
          statements.push(statement);
        }
        currentStatement = '';
      }
    }
    
    // Add any remaining statement
    if (currentStatement.trim().length > 0) {
      statements.push(currentStatement.trim());
    }

    for (const statement of statements) {
      if (statement.trim()) {
        await db.query(statement);
      }
    }

    logger.info('Database setup completed successfully');
    console.log('✓ Database setup completed successfully');
    
  } catch (error) {
    logger.error('Database setup failed:', error);
    console.error('✗ Database setup failed:', error.message);
    throw error;
  } finally {
    await db.close();
  }
}

// Run if called directly
if (require.main === module) {
  setupDatabase()
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}

module.exports = setupDatabase;

