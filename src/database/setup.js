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

    // Try to rollback any existing aborted transaction
    try {
      await db.query('ROLLBACK');
      logger.debug('Rolled back any existing transaction');
    } catch (err) {
      // Ignore error if no transaction was active
      logger.debug('No existing transaction to rollback');
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

    // Execute statements with better error handling
    let successCount = 0;
    let errorCount = 0;
    const errors = [];

    for (let i = 0; i < statements.length; i++) {
      const statement = statements[i].trim();
      if (!statement) continue;

      try {
        // Skip standalone comment lines and empty statements
        // But don't skip multi-line statements that contain SQL commands
        const trimmedStatement = statement.trim();
        if (trimmedStatement.length === 0) {
          continue;
        }
        
        // Skip only if it's ONLY a comment (starts with -- and no other SQL)
        const lines = trimmedStatement.split('\n');
        const hasSQL = lines.some(line => {
          const trimmedLine = line.trim();
          return trimmedLine.length > 0 && !trimmedLine.startsWith('--');
        });
        
        if (!hasSQL) {
          continue; // Skip comment-only statements
        }

        await db.query(trimmedStatement);
        successCount++;
        
        // Log progress for large schemas
        if ((i + 1) % 10 === 0) {
          logger.debug(`Executed ${i + 1}/${statements.length} statements...`);
        }
      } catch (error) {
        errorCount++;
        const errorMsg = error.message || String(error);
        
        // Check if it's a "already exists" error (non-critical)
        const isNonCritical = 
          errorMsg.includes('already exists') ||
          errorMsg.includes('duplicate') ||
          errorMsg.includes('relation') && errorMsg.includes('does not exist') && 
          (statement.includes('CREATE INDEX') || statement.includes('CREATE TRIGGER'));
        
        if (isNonCritical) {
          logger.debug(`Skipping non-critical error: ${errorMsg.substring(0, 100)}`);
          successCount++; // Count as success since it's expected
        } else {
          // Critical error - log and collect
          logger.warn(`Statement ${i + 1} failed: ${errorMsg.substring(0, 200)}`);
          errors.push({
            statement: statement.substring(0, 100) + (statement.length > 100 ? '...' : ''),
            error: errorMsg
          });
        }
      }
    }

    if (errors.length > 0) {
      logger.warn(`Database setup completed with ${errors.length} critical error(s)`);
      console.warn(`⚠ Database setup completed with ${errors.length} critical error(s):`);
      errors.forEach((err, idx) => {
        console.warn(`  ${idx + 1}. ${err.error}`);
      });
    } else {
      logger.info(`Database setup completed successfully (${successCount} statements executed)`);
      console.log(`✓ Database setup completed successfully (${successCount} statements executed)`);
    }
    
  } catch (error) {
    logger.error('Database setup failed:', error);
    console.error('✗ Database setup failed:', error.message);
    
    // Provide helpful error messages for common issues
    if (error.message && error.message.includes('self-signed certificate')) {
      console.error('\n💡 SSL Certificate Error:');
      console.error('   Set DB_SSL_CA_FILE or DB_SSL_CA in your .env file');
      console.error('   Or set DB_SSL_REJECT_UNAUTHORIZED=false for local development');
    } else if (error.message && error.message.includes('password authentication')) {
      console.error('\n💡 Authentication Error:');
      console.error('   Check your DB_USER and DB_PASSWORD in .env file');
    } else if (error.message && error.message.includes('does not exist')) {
      console.error('\n💡 Database Error:');
      console.error('   The database may not exist. Create it first:');
      console.error('   createdb -U postgres amazon_ads');
    }
    
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

