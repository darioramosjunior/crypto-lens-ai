---
description: "AI coding agent instructions for the Crypto-Lens AI project - a real-time cryptocurrency intelligence platform with async data pipelines, Discord alerts, and Grafana dashboards."
---

# Crypto-Lens AI — Agent Instructions

**Crypto-Lens** is a production-ready cryptocurrency intelligence platform that monitors 24/7 market activity, analyzes trends with technical indicators, screens for anomalies, and alerts traders via Discord.

## Quick Start Commands

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_utils.py -v

# Run with coverage
pytest --cov=. --cov-report=html tests/

# Run main data pipeline (orchestrates all components)
python main.py

# Set up pre-commit hooks (optional)
python setup_pre_commit.py
```

## Architecture Overview

The project follows a **sequential data pipeline** executed by [main.py](main.py):

| Component | Purpose | Inputs | Outputs |
|-----------|---------|--------|---------|
| [coin_data_collector.py](coin_data_collector.py) | Market metadata collection | Binance API, CoinMarketCap API | `coin_data.csv` |
| [hourly_fetch_and_pulse.py](hourly_fetch_and_pulse.py) | 1-hour market analysis (RSI, sentiment) | OHLCV 1h data | `prices_1h.csv`, chart, Discord alert |
| [daily_fetch_and_pulse.py](daily_fetch_and_pulse.py) | Daily market summaries | OHLCV 1d data | `prices_1d.csv`, chart, Discord alert |
| [market_breadth.py](market_breadth.py) | Market-wide sentiment metrics | `prices_1d.csv` | BTC%, BTCD%, advancing/declining counts |
| [oi_change_screener.py](oi_change_screener.py) | Open interest anomaly detection | Binance OI endpoints | Top 20 movers, alerts on changes |
| [pipeline_observability.py](pipeline_observability.py) | Pipeline health monitoring | Log files | Error/warning summary → Discord |

## Key Conventions

### Module Structure
Every script follows this pattern:
1. Environment setup & config loading
2. Utility imports from `utils.py`
3. Core processing logic
4. Main function orchestration
5. Log output to `/var/log/crypto-lens/` or `/var/run/crypto-lens/`

**Example entry point**:
```python
import config, logger, utils
from utils import FileUtility, ConfigManager

# Ensure directories exist
config.ensure_log_directory()
log_path = config.get_log_file_path("module_name")
FileUtility.ensure_log_file_exists(log_path)

# Process and validate
try:
    data = fetch_and_validate_data()
    utils.save_to_s3(data)  # Backup to S3
except Exception as e:
    logger.log_event("ERROR", f"Failed: {e}", log_path)
```

### Data Validation
**All data is validated using Pydantic models** before processing/persistence:
- See [validations.py](validations.py) for all model definitions
- Use model constructors to validate: `OHLCVCandle(**data)` raises on invalid data
- Common models: `CoinDataModel`, `OHLCVCandle`, `PriceChangeData`, `MarketBreadthData`

**Example**:
```python
from validations import OHLCVCandle
try:
    candle = OHLCVCandle(timestamp=ts, open=o, high=h, low=l, close=c, volume=v)
except ValidationError as e:
    logger.log_event("ERROR", f"Invalid candle: {e}", log_path)
```

### Error Handling & Logging
- **All errors logged via** `logger.log_event(category, message, log_path)`
- **Categories**: "INFO", "WARNING", "ERROR"
- **Format**: `[TIMESTAMP] CATEGORY: message`
- **Graceful degradation**: Try-catch blocks with fallback values
- **No silent failures**: Always log errors before continuing

### Configuration Pattern
- **INI file defaults**: [config.conf](config.conf) with paths, cron schedules, API endpoints
- **Python overrides**: [config.py](config.py) with environment variables and fallbacks
- **Environment variables**: `.env` file with API keys, AWS region, Discord webhooks
  - Required: `cmc_api_key`, `AWS_REGION`, `[HOURLY|DAILY|BREADTH|OI|PIPELINE]_WEBHOOK`

### Async Operations
Windows compatibility is critical:
```python
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

## Testing Structure

**Framework**: pytest (minversion 7.0)  
**Test markers** (from [pytest.ini](pytest.ini)):
- `@pytest.mark.unit` — Unit tests (fast, no external APIs)
- `@pytest.mark.integration` — Integration tests
- `@pytest.mark.slow` — Slow tests (>1s)
- `@pytest.mark.external_api` — Tests requiring live Binance/CMC APIs

**Test fixtures** (from [tests/conftest.py](tests/conftest.py)):
- Mocked boto3, ccxt, aiohttp, pandas_ta
- Temporary directories for file operations
- Mock Binance and CoinMarketCap responses

**Test files overview**:
- [test_utils.py](tests/test_utils.py) — FileUtility, ConfigManager, DataLoaderUtility
- [test_coin_data_collector.py](tests/test_coin_data_collector.py) — Coin fetching
- [test_logger_config.py](tests/test_logger_config.py) — Logging, config loading
- [test_validations.py](tests/test_validations.py) — Pydantic models
- [test_integration.py](tests/test_integration.py) — End-to-end scenarios
- [test_examples.py](tests/test_examples.py) — Usage examples

**When adding new tests**:
1. Follow `Test*` class naming and `test_*` function naming
2. Use markers: `@pytest.mark.unit` or `@pytest.mark.integration`
3. Leverage mocked fixtures from conftest (boto3, ccxt, pandas_ta)
4. Test happy path, validation errors, and edge cases
5. Validate logged messages when error handling is involved

## Shared Utilities ([utils.py](utils.py))

| Utility | Purpose |
|---------|---------|
| `FileUtility.ensure_log_file_exists(path)` | Create/verify log file with headers |
| `ConfigManager.load_config()` | Load INI config with env var overrides |
| `DataLoaderUtility.load_coins_data()` | Load `coin_data.csv` into DataFrame |
| `BinanceDataFetcher.fetch_ohlcv_data()` | Async OHLCV data collection |
| `IndicatorCalculator.calculate_rsi()` | RSI calculation (14-period) |
| `IndicatorCalculator.trend_direction()` | Detect uptrend/downtrend |
| `S3Manager.upload_dataframe()` | Upload CSV to S3 bucket |
| `discord_integrator.send_alert()` | Send webhook message + image |

## Important Gotchas & Pitfalls

1. **Windows async event loop**: Always set `WindowsSelectorEventLoopPolicy()` on Windows before running async code
2. **API rate limits**: Binance Futures = 1200 req/min; add delays between batch requests
3. **S3 bucket hardcoded**: `data-portfolio-2026` in [utils.py](utils.py) — update for different environments
4. **CSV headers required**: `coin_data.csv` must exist before analysis scripts run (created by coin_data_collector)
5. **Validation before save**: Always validate data via Pydantic models before persisting to CSV/S3
6. **Discord webhooks optional**: Set via env vars; if missing, logs warning and continues
7. **Cron schedules in config**: Main pipeline set to `*/5 * * * *` (every 5 min); logs_cleaner runs daily

## Documentation

- [docs/TESTING.md](docs/TESTING.md) — Comprehensive testing guide
- [TESTING_QUICKSTART.md](TESTING_QUICKSTART.md) — 5-minute test setup
- [README.md](README.md) — Architecture overview, feature list, component diagrams

## Common Development Tasks

### Add a new analysis component
1. Create `new_component.py` following the module structure pattern (config load, utility imports, logging)
2. Define Pydantic model in [validations.py](validations.py) for data validation
3. Add to [main.py](main.py) execution sequence
4. Write tests in `tests/test_new_component.py`
5. Add Discord webhook env var if alerts are needed

### Debug a failed pipeline run
1. Check logs: `/var/log/crypto-lens/` or `/var/run/crypto-lens/`
2. Verify API keys: `cmc_api_key` and Binance credentials in .env
3. Test individual component: `python component_name.py` with mocked data
4. Run unit tests: `pytest tests/test_component_name.py -v`

### Add a new Discord alert
1. Add env var `NEW_ALERT_WEBHOOK` to .env
2. Use `discord_integrator.send_alert(webhook_url, message, image_path)`
3. Log message format: Include metric, change %, time range
4. Test with unit test: Mock webhook and verify call

### Validate data quality
1. Use Pydantic models: `Model(**data)` raises ValidationError on bad data
2. Add custom validators: `@field_validator('field_name')` in model class
3. Log validation failures before continuing (try-except pattern)
4. Example: Check OHLC consistency, price ranges, timestamp ordering
