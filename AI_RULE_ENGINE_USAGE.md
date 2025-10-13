# AI Rule Engine - Production Usage Guide

## Quick Start

### 1. Setup (One-time)
```bash
# Install dependencies and create configuration
python3 scripts/setup_ai_rule_engine.py

# Set your database connection
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="amazon_ads"
export DB_USER="postgres"
export DB_PASSWORD="your_password"

# Validate installation
python3 scripts/validate_ai_rule_engine.py
```

### 2. Run AI Rule Engine

#### Basic Usage
```bash
# Analyze all campaigns and generate recommendations
python3 scripts/run_ai_rule_engine.py

# Analyze specific campaigns
python3 scripts/run_ai_rule_engine.py --campaigns 12345 67890

# Export as CSV
python3 scripts/run_ai_rule_engine.py --format csv --output recommendations.csv
```

#### Advanced Usage
```bash
# Custom configuration
python3 scripts/run_ai_rule_engine.py --config custom_config.json

# High confidence only
python3 scripts/run_ai_rule_engine.py --min-confidence 0.7

# Limit recommendations
python3 scripts/run_ai_rule_engine.py --max-recommendations 50

# Debug mode
python3 scripts/run_ai_rule_engine.py --log-level DEBUG

# Dry run (no changes)
python3 scripts/run_ai_rule_engine.py --dry-run
```

## What It Does

The AI Rule Engine automatically analyzes your Amazon Ads performance and generates recommendations for:

- **Bid Adjustments** based on ACOS, ROAS, and CTR
- **Budget Scaling** based on overall performance  
- **Negative Keywords** identification
- **Safety Limits** enforcement (bid floors/caps, cooldown periods)

## Output

The engine generates JSON or CSV files with recommendations like:

```json
{
  "entity_type": "keyword",
  "entity_id": 12345,
  "adjustment_type": "bid",
  "current_value": 1.50,
  "recommended_value": 1.20,
  "adjustment_amount": -0.30,
  "priority": "high",
  "confidence": 0.85,
  "reason": "ACOS 0.35 exceeds target 0.30"
}
```

## Configuration

Edit `config/ai_rule_engine.json` to customize:

- **ACOS Target**: Default 30% (adjust bids when ACOS deviates)
- **ROAS Target**: Default 4:1 (adjust bids when ROAS deviates)  
- **CTR Minimum**: Default 0.5% (increase bids for low CTR)
- **Bid Limits**: $0.01 - $10.00 range
- **Budget Limits**: $1 - $1000 daily range
- **Safety Limits**: Cooldown periods, daily limits

## Integration

To apply recommendations automatically:

1. **Parse the output JSON/CSV**
2. **Connect to Amazon Ads API**
3. **Apply bid/budget changes**
4. **Add negative keywords**

## Monitoring

- **Logs**: Check `logs/ai_rule_engine_YYYYMMDD.log`
- **Reports**: Generated in `reports/` directory
- **Status**: Use `--log-level DEBUG` for detailed output

## Troubleshooting

- **Database Connection**: Ensure DB_HOST, DB_PORT, DB_NAME, DB_USER, and DB_PASSWORD are set correctly
- **No Recommendations**: Check minimum impression thresholds
- **Configuration Errors**: Validate JSON syntax in config file

For detailed documentation, see `AI_RULE_ENGINE_DOCUMENTATION.md`.
