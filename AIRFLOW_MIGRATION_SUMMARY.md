---
description: "Summary of Airflow migration changes for Crypto-Lens AI"
---

# Crypto-Lens Airflow Migration Summary

## Overview

Successfully migrated Crypto-Lens orchestration from **cron-based** execution to **Apache Airflow**, maintaining:
- ✅ Same execution frequency (every 5 minutes for main pipeline, 3 PM daily for cleanup)
- ✅ Same execution sequence (coin_data_collector → hourly → daily → breadth → OI → observability)
- ✅ Same configurability (schedules in config.conf)
- ✅ Backward compatibility (old setup.sh preserved, can run parallel)

## Files Added

### Core Airflow Components

1. **`dags/` directory** (new folder)
   - Airflow DAGs directory structure
   - Discovered automatically by Airflow scheduler

2. **`dags/__init__.py`** (new file)
   - Package marker for dags directory
   - Contains module documentation

3. **`dags/airflow_config_loader.py`** (new file)
   - Reads cron schedules from `config.conf`
   - Provides `AirflowConfigLoader` class
   - Supports fallback defaults if config not found
   - **Configurability maintained**: Change `main_cron_sched` and `logs_cleaner_cron_sched` in config.conf, DAG auto-reloads

4. **`dags/crypto_lens_main_pipeline.py`** (new file)
   - Main Airflow DAG
   - Orchestrates 6-task sequential pipeline:
     1. coin_data_collector
     2. hourly_fetch_and_pulse
     3. daily_fetch_and_pulse
     4. market_breadth
     5. oi_change_screener
     6. pipeline_observability
   - Schedule: `*/5 * * * *` (from config.conf)
   - Max active runs: 1 (sequential execution)
   - Error handling: retries with 2-minute delays

5. **`dags/crypto_lens_logs_cleanup.py`** (new file)
   - Logs cleanup DAG (runs independently)
   - Single task: logs_cleaner
   - Schedule: `0 15 * * *` (3 PM daily, from config.conf)
   - Separate from main pipeline (can scale independently)

### Setup & Documentation

6. **`setup_airflow.py`** (new file)
   - Automated Airflow setup script
   - Features:
     - Checks Python/Airflow requirements
     - Initializes Airflow database
     - Creates admin user
     - Validates DAG files
     - Lists discovered DAGs
   - Usage: `python setup_airflow.py`
   - Supports flags: `--init`, `--validate`, `--list-dags`, `--start`

7. **`AIRFLOW_MIGRATION.md`** (new file)
   - Comprehensive migration guide
   - Sections:
     - Architecture overview
     - Installation & setup (Ubuntu 20.04+ LTS on EC2)
     - Configuration guide
     - Monitoring & observability
     - Migration path (Phase 1-3)
     - Troubleshooting
     - Best practices
     - Reverting to cron (if needed)

8. **`AIRFLOW_QUICKSTART.md`** (new file)
   - Quick reference guide
   - One-liner setup
   - Common tasks (start, trigger, logs, test)
   - Troubleshooting cheat sheet
   - Environment variables
   - Systemd service commands

9. **`airflow.cfg.template`** (new file)
   - Reference Airflow configuration
   - Pre-configured for crypto-lens
   - Includes:
     - DAGs folder path
     - Logging configuration
     - Scheduler settings
     - Optional email/SMTP setup
     - Security considerations

## Files Modified

1. **`requirements.txt`** (modified)
   - **Added**:
     ```
     apache-airflow>=2.7.0
     apache-airflow-providers-python>=4.1.0
     ```
   - All existing dependencies preserved
   - Testing & linting dependencies unchanged

## Files Unchanged (Backward Compatible)

- ✅ `config.conf` - Schedules still read from here
- ✅ `main.py` - Can coexist with Airflow (for manual testing)
- ✅ `setup.sh` - Can run in parallel for validation
- ✅ All pipeline scripts (coin_data_collector.py, etc.)
- ✅ `validations.py`, `utils.py`, `logger.py`
- ✅ `tests/` directory

## Execution Flow Comparison

### Old (Cron-based)
```
User/System
    ↓
Crontab (*/5 * * * *)
    ↓
setup.sh
    ↓
main.py (runs scripts sequentially)
    ↓
Scripts: coin_data → hourly → daily → breadth → OI → observability
    ↓
Logs: /var/log/crypto-lens/
```

### New (Airflow-based)
```
User/System
    ↓
Airflow Scheduler (reads config.conf: */5 * * * *)
    ↓
DAG: crypto_lens_main_pipeline
    ↓
Tasks (with dependencies):
coin_data_collector → hourly_fetch → daily_fetch → market_breadth → oi_screener → observability
    ↓
Logs: $AIRFLOW_HOME/logs/ + /var/log/crypto-lens/
    ↓
Web UI: http://localhost:8080 (monitoring & alerts)
```

## Key Improvements with Airflow

| Feature | Cron | Airflow |
|---------|------|---------|
| **Web UI Dashboard** | ❌ | ✅ Real-time monitoring |
| **Task Dependencies** | Manual scripts | ✅ Automatic DAG management |
| **Failure Recovery** | Manual re-run | ✅ Automatic retries |
| **Scheduling Flexibility** | Cron only | ✅ Multiple scheduling options |
| **Alerting** | Manual emails | ✅ Native email/Slack alerts |
| **Backfilling** | Manual script runs | ✅ One command |
| **Historical Runs** | Log files | ✅ Database with queries |
| **Scalability** | Limited | ✅ Distributed (CeleryExecutor) |
| **Version Control** | Script-based | ✅ Code-based DAGs |

## Configuration Details

### Schedule Sources

Airflow reads from `config.conf`:

```ini
[schedules]
main_cron_sched=*/5 * * * *          # Main pipeline (loaded by crypto_lens_main_pipeline.py)
logs_cleaner_cron_sched=0 15 * * *   # Cleanup (loaded by crypto_lens_logs_cleanup.py)
```

**To change schedules**:
1. Edit `config.conf`
2. Airflow auto-detects changes within 30 seconds
3. New schedule takes effect on next execution

No restart or deployment needed!

### Error Handling

Both DAGs configured with:
- Retries: 1 attempt after failure
- Retry delay: 2-5 minutes
- Catchup: False (don't backfill on startup)
- Max active runs: 1 per DAG (sequential)

## Testing the Migration

### Quick Validation

```bash
# 1. Verify DAG syntax
python -m py_compile dags/crypto_lens_main_pipeline.py
python -m py_compile dags/crypto_lens_logs_cleanup.py

# 2. Test DAG discovery
airflow dags list

# 3. Test a single task
airflow tasks test crypto_lens_main_pipeline coin_data_collector 2024-04-26
```

### Integration Testing

```bash
# Run full pipeline on demand
airflow dags trigger crypto_lens_main_pipeline

# Monitor execution
airflow dags list-runs --dag-id crypto_lens_main_pipeline

# View task logs
airflow tasks logs crypto_lens_main_pipeline coin_data_collector
```

## Migration Steps

### Phase 1: Preparation (Day 1)
- [ ] Read AIRFLOW_MIGRATION.md
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run setup: `python setup_airflow.py`
- [ ] Verify DAGs: `airflow dags list`

### Phase 2: Parallel Testing (Day 2-3)
- [ ] Start Airflow: `airflow scheduler` + `airflow webserver`
- [ ] Let cron run in parallel
- [ ] Compare outputs
- [ ] Monitor Web UI

### Phase 3: Cutover (Day 4)
- [ ] Disable cron jobs: `sudo crontab -e`
- [ ] Monitor Airflow for 2+ days
- [ ] Validate data quality

### Phase 4: Cleanup (Day 7)
- [ ] Archive old setup.sh
- [ ] Remove cron entries
- [ ] Document final configuration

## Backward Compatibility

The migration preserves backward compatibility:

- ✅ All existing scripts remain unchanged
- ✅ config.conf still works (with new schedule keys)
- ✅ main.py can still be run manually
- ✅ setup.sh can be kept for reference
- ✅ Logs still written to /var/log/crypto-lens/
- ✅ Can revert to cron if needed

**To revert**:
```bash
# Stop Airflow
pkill -f "airflow scheduler"
pkill -f "airflow webserver"

# Re-enable cron
sudo crontab -e  # Uncomment crypto-lens entries
```

## Deployment Considerations

### Single Machine (Development/Small Scale)
- ✅ Use **LocalExecutor** (default)
- ✅ SQLite database
- ✅ Single scheduler + webserver
- ✅ Recommended for current setup

### Multiple Machines (Production Scale)
- Upgrade to **CeleryExecutor**
- Use **PostgreSQL** instead of SQLite
- Deploy scheduler + multiple workers
- Add message broker (Redis/RabbitMQ)
- Set up centralized logging

### Cloud Deployment
- **AWS**: Use Managed Workflows for Apache Airflow (MWAA)
- **GCP**: Use Cloud Composer
- **Azure**: Use Synapse or custom Kubernetes

## Support & Troubleshooting

### Common Issues

1. **DAGs not appearing**: Check `AIRFLOW_HOME` and `dags_folder` in airflow.cfg
2. **Config not loaded**: Verify config.conf exists in parent of dags/ folder
3. **Services won't start**: Check systemd service files and EC2 security group
4. **Port conflicts**: Use different port: `airflow webserver --port 8081`

### Getting Help

1. Check logs: `airflow tasks logs [dag_id] [task_id]`
2. Review [AIRFLOW_MIGRATION.md](AIRFLOW_MIGRATION.md) troubleshooting section
3. Run validation: `python setup_airflow.py --validate`
4. Test task: `airflow tasks test [dag_id] [task_id] 2024-04-26`

## Next Steps

1. **Install**: Follow [AIRFLOW_QUICKSTART.md](AIRFLOW_QUICKSTART.md)
2. **Deploy**: Use `setup_airflow.py` for automated setup
3. **Monitor**: Access Web UI at http://localhost:8080
4. **Optimize**: Adjust schedules in config.conf as needed

## Files Reference

| File | Purpose | Link |
|------|---------|------|
| Full Migration Guide | Detailed setup, troubleshooting, best practices | [AIRFLOW_MIGRATION.md](AIRFLOW_MIGRATION.md) |
| Quick Start | Commands cheat sheet, one-liners | [AIRFLOW_QUICKSTART.md](AIRFLOW_QUICKSTART.md) |
| Main Pipeline DAG | Orchestration logic (every 5 min) | [dags/crypto_lens_main_pipeline.py](dags/crypto_lens_main_pipeline.py) |
| Cleanup DAG | Logs cleanup (daily 3 PM) | [dags/crypto_lens_logs_cleanup.py](dags/crypto_lens_logs_cleanup.py) |
| Config Loader | Parse config.conf for schedules | [dags/airflow_config_loader.py](dags/airflow_config_loader.py) |
| Setup Script | Automated installation | [setup_airflow.py](setup_airflow.py) |
| Config Template | Reference airflow.cfg | [airflow.cfg.template](airflow.cfg.template) |

---

**Migration completed successfully!** The Crypto-Lens pipeline is now orchestrated by Apache Airflow while maintaining full backward compatibility and configurability. 🚀
