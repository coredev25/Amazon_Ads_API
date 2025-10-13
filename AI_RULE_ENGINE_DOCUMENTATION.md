# Amazon Ads AI Rule Engine Documentation

## Overview

The AI Rule Engine is a Python-based automation system that adjusts bids and budgets for Amazon Ads campaigns based on performance metrics including ACOS (Advertising Cost of Sales), ROAS (Return on Ad Spend), and CTR (Click-Through Rate). The system includes bid floor/cap limits, negative keyword identification, and comprehensive safety mechanisms.

## Features

### Core Rules

1. **ACOS Rule** - Adjusts bids based on Advertising Cost of Sales
2. **ROAS Rule** - Adjusts bids based on Return on Ad Spend  
3. **CTR Rule** - Adjusts bids based on Click-Through Rate
4. **Negative Keyword Rule** - Identifies underperforming keywords for negative lists
5. **Budget Rule** - Adjusts daily budgets based on overall performance

### Safety Features

- Bid floor and cap limits
- Maximum daily adjustment limits
- Cooldown periods between adjustments
- Confidence-based filtering
- Comprehensive logging and monitoring

## Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL database with Amazon Ads data
- Environment variables configured

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env with your database connection details
   ```

3. **Set up database:**
   ```bash
   # Ensure your PostgreSQL database is running and accessible
   export DB_HOST="localhost"
   export DB_PORT="5432"
   export DB_NAME="amazon_ads"
   export DB_USER="postgres"
   export DB_PASSWORD="your_password"
   ```

4. **Create configuration:**
   ```bash
   # Default configuration will be created automatically
   # Or customize config/ai_rule_engine.json
   ```

## Usage

### Basic Usage

```bash
# Analyze all campaigns
python -m src.ai_rule_engine.main

# Analyze specific campaigns
python -m src.ai_rule_engine.main --campaigns 12345 67890

# Export as CSV
python -m src.ai_rule_engine.main --format csv --output reports/recommendations.csv

# Dry run (no changes)
python -m src.ai_rule_engine.main --dry-run
```

### Advanced Usage

```bash
# Custom configuration
python -m src.ai_rule_engine.main --config custom_config.json

# Adjust confidence threshold
python -m src.ai_rule_engine.main --min-confidence 0.5

# Limit recommendations
python -m src.ai_rule_engine.main --max-recommendations 50

# Debug mode
python -m src.ai_rule_engine.main --log-level DEBUG
```

## Configuration

### Rule Configuration

The engine uses a JSON configuration file (`config/ai_rule_engine.json`) with the following parameters:

#### ACOS Rule
- `acos_target`: Target ACOS (default: 0.30 = 30%)
- `acos_tolerance`: Tolerance range (default: 0.05 = ±5%)
- `acos_bid_adjustment_factor`: Bid adjustment factor (default: 0.1 = 10%)

#### ROAS Rule
- `roas_target`: Target ROAS (default: 4.0 = 4:1)
- `roas_tolerance`: Tolerance range (default: 0.5)
- `roas_bid_adjustment_factor`: Bid adjustment factor (default: 0.15 = 15%)

#### CTR Rule
- `ctr_minimum`: Minimum CTR threshold (default: 0.5%)
- `ctr_target`: Target CTR (default: 2.0%)
- `ctr_bid_adjustment_factor`: Bid adjustment factor (default: 0.2 = 20%)

#### Bid Limits
- `bid_floor`: Minimum bid amount (default: $0.01)
- `bid_cap`: Maximum bid amount (default: $10.00)
- `bid_max_adjustment`: Maximum adjustment per cycle (default: 0.5 = 50%)

#### Budget Configuration
- `budget_min_daily`: Minimum daily budget (default: $1.00)
- `budget_max_daily`: Maximum daily budget (default: $1000.00)
- `budget_adjustment_factor`: Budget adjustment factor (default: 0.2 = 20%)

#### Safety Limits
- `max_daily_adjustments`: Maximum adjustments per day per entity (default: 3)
- `cooldown_hours`: Hours between adjustments for same entity (default: 6)
- `min_impressions`: Minimum impressions for rule evaluation (default: 100)
- `min_clicks`: Minimum clicks for rule evaluation (default: 5)
- `min_conversions`: Minimum conversions for rule evaluation (default: 1)

## Rule Logic

### ACOS Rule

**Purpose:** Optimize Advertising Cost of Sales

**Logic:**
- If ACOS > target + tolerance → Reduce bid
- If ACOS < target - tolerance → Increase bid
- Adjustment amount = current_bid × adjustment_factor

**Example:**
- Target ACOS: 30%
- Current ACOS: 35%
- Action: Reduce bid by 10%

### ROAS Rule

**Purpose:** Optimize Return on Ad Spend

**Logic:**
- If ROAS < target - tolerance → Reduce bid
- If ROAS > target + tolerance → Increase bid
- Adjustment amount = current_bid × adjustment_factor

**Example:**
- Target ROAS: 4:1
- Current ROAS: 2.5:1
- Action: Reduce bid by 15%

### CTR Rule

**Purpose:** Improve Click-Through Rate

**Logic:**
- If CTR < minimum threshold → Increase bid
- Adjustment amount = current_bid × adjustment_factor × severity_multiplier

**Example:**
- Minimum CTR: 0.5%
- Current CTR: 0.3%
- Action: Increase bid by 20%

### Negative Keyword Rule

**Purpose:** Identify underperforming keywords

**Logic:**
- If CTR < threshold AND impressions > minimum → Recommend negative keyword
- Threshold: 0.1% CTR with 1000+ impressions

**Example:**
- Keyword CTR: 0.05%
- Impressions: 1,500
- Action: Add to negative keyword list

### Budget Rule

**Purpose:** Optimize daily budget allocation

**Logic:**
- If ROAS > 3.0 → Increase budget
- If ROAS < 1.5 → Decrease budget
- Adjustment amount = current_budget × adjustment_factor

**Example:**
- Current ROAS: 4.2
- Action: Increase budget by 20%

## Output Format

### JSON Output

```json
{
  "exported_at": "2024-01-15T10:30:00",
  "total_recommendations": 25,
  "summary": {
    "by_type": {
      "bid": 20,
      "budget": 3,
      "negative_keyword": 2
    },
    "by_priority": {
      "high": 5,
      "medium": 15,
      "low": 5
    }
  },
  "recommendations": [
    {
      "entity_type": "keyword",
      "entity_id": 12345,
      "entity_name": "wireless headphones",
      "adjustment_type": "bid",
      "current_value": 1.50,
      "recommended_value": 1.20,
      "adjustment_amount": -0.30,
      "adjustment_percentage": -20.0,
      "priority": "high",
      "confidence": 0.85,
      "reason": "ACOS 0.35 exceeds target 0.30 by 0.05",
      "rules_triggered": ["ACOS_RULE"],
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

### CSV Output

The CSV format includes the same fields as JSON in a tabular format suitable for spreadsheet analysis.

## Integration

### Database Schema

The engine requires the following database tables:
- `campaigns` - Campaign information
- `ad_groups` - Ad group information  
- `keywords` - Keyword information
- `campaign_performance` - Campaign performance data
- `ad_group_performance` - Ad group performance data
- `keyword_performance` - Keyword performance data

### API Integration

To integrate with Amazon Ads API for automatic bid updates:

```python
from ai_rule_engine import AIRuleEngine, RuleConfig, DatabaseConnector

# Initialize engine
config = RuleConfig.from_file('config/ai_rule_engine.json')
db = DatabaseConnector('postgresql://...')
engine = AIRuleEngine(config, db)

# Get recommendations
recommendations = engine.analyze_campaigns()

# Apply recommendations via Amazon Ads API
for rec in recommendations:
    if rec.adjustment_type == 'bid':
        # Update bid via API
        update_bid(rec.entity_id, rec.recommended_value)
    elif rec.adjustment_type == 'budget':
        # Update budget via API
        update_budget(rec.entity_id, rec.recommended_value)
```

## Monitoring and Logging

### Log Files

- `logs/ai_rule_engine_YYYYMMDD.log` - Daily log files
- `logs/combined.log` - Combined application logs
- `logs/error.log` - Error logs only

### Log Levels

- `DEBUG` - Detailed rule evaluation information
- `INFO` - General operation information
- `WARNING` - Non-critical issues
- `ERROR` - Critical errors

### Metrics

The engine tracks:
- Number of recommendations generated
- Rule trigger frequency
- Adjustment success rates
- Performance improvements

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify database environment variables (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
   - Check database server status
   - Verify user permissions

2. **No Recommendations Generated**
   - Check minimum impression thresholds
   - Verify performance data availability
   - Review confidence thresholds

3. **Configuration Errors**
   - Validate JSON syntax in config file
   - Check parameter ranges
   - Review rule logic settings

### Debug Mode

Enable debug logging for detailed analysis:

```bash
python -m src.ai_rule_engine.main --log-level DEBUG
```

## Performance Considerations

### Optimization Tips

1. **Batch Processing** - Process multiple campaigns in batches
2. **Caching** - Cache performance data for repeated analysis
3. **Filtering** - Use specific campaign IDs for targeted analysis
4. **Scheduling** - Run during off-peak hours

### Resource Requirements

- **CPU:** 2+ cores recommended
- **Memory:** 4GB+ RAM for large datasets
- **Storage:** 1GB+ for logs and reports
- **Network:** Stable connection to database

## Security

### Best Practices

1. **Environment Variables** - Store sensitive data in environment variables
2. **Database Access** - Use read-only database users when possible
3. **Logging** - Avoid logging sensitive information
4. **Access Control** - Restrict file system permissions

## Support

For issues and questions:
1. Check the logs for error messages
2. Review configuration settings
3. Verify database connectivity
4. Test with dry-run mode first

## Version History

- **v1.0.0** - Initial release with core rule engine
- ACOS, ROAS, CTR, and Budget rules
- Negative keyword identification
- Comprehensive safety mechanisms
- JSON/CSV export capabilities
