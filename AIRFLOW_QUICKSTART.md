# Crypto-Lens Airflow Quick Reference

## One-Liner Setup

```bash
# Clone/navigate to project
cd /path/to/crypto-lens-ai

# Install dependencies
pip install -r requirements.txt

# Run setup script
python setup_airflow.py

# Start services (in two terminals)
export AIRFLOW_HOME=/path/to/crypto-lens-ai/airflow-home
airflow scheduler    # Terminal 1

export AIRFLOW_HOME=/path/to/crypto-lens-ai/airflow-home
airflow webserver    # Terminal 2

# Visit http://localhost:8080
```

## Key Files Changed/Added

| File | Status | Purpose |
|------|--------|---------|
| `dags/` | **NEW** | Airflow DAGs directory |
| `dags/crypto_lens_main_pipeline.py` | **NEW** | Main pipeline DAG (every 5 min) |
| `dags/crypto_lens_logs_cleanup.py` | **NEW** | Logs cleanup DAG (daily 3 PM) |
| `dags/airflow_config_loader.py` | **NEW** | Config reader from config.conf |
| `dags/__init__.py` | **NEW** | Package marker |
| `setup_airflow.py` | **NEW** | Airflow setup automation |
| `AIRFLOW_MIGRATION.md` | **NEW** | Full migration guide |
| `airflow.cfg.template` | **NEW** | Reference Airflow config |
| `requirements.txt` | **UPDATED** | Added apache-airflow |
| `config.conf` | **UNCHANGED** | Schedules read from here |
| `main.py` | **UNCHANGED** | Can keep for backward compatibility |
| `setup.sh` | **UNCHANGED** | Can disable/remove after migration |

## Most Important Concepts

### **Schedule Source: config.conf**

```ini
[schedules]
main_cron_sched=*/5 * * * *          # Main pipeline (change here!)
logs_cleaner_cron_sched=0 15 * * *   # Cleanup schedule (change here!)
```

**To change schedules**: Edit `config.conf`, no restart needed.

### **Execution Model**

```
CRON (Old)                          AIRFLOW (New)
┌─────────────────┐                ┌──────────────────────┐
│ System Crontab  │                │ Airflow Scheduler    │
└────────┬────────┘                └──────────┬───────────┘
         │                                    │
    Runs script                     Runs DAG tasks
    in sequence                     with dependencies
         │                                    │
    coin_data_collector    →        coin_data_collector
    → hourly_fetch         →        → hourly_fetch
    → daily_fetch          →        → daily_fetch
    → market_breadth       →        → market_breadth
    → oi_screener          →        → oi_screener
    → observability        →        → observability
```

## Common Tasks

### Start Everything

```bash
# Terminal 1: Scheduler
export AIRFLOW_HOME=/path/to/airflow-home
airflow scheduler

# Terminal 2: Web UI
export AIRFLOW_HOME=/path/to/airflow-home
airflow webserver --port 8080

# Then visit: http://localhost:8080
# Login: admin / admin
```

### View DAG Status

```bash
# List all DAGs
airflow dags list

# Get DAG details
airflow dags info crypto_lens_main_pipeline

# View latest run
airflow dags list-runs --dag-id crypto_lens_main_pipeline --limit 5
```

### Manual DAG Trigger

```bash
# Trigger main pipeline now
airflow dags trigger crypto_lens_main_pipeline

# Trigger on specific date
airflow dags trigger crypto_lens_main_pipeline --exec-date 2024-04-26
```

### View Task Logs

```bash
# Recent logs
airflow tasks logs crypto_lens_main_pipeline coin_data_collector

# Specific execution
airflow tasks logs crypto_lens_main_pipeline coin_data_collector \
    --execution-date 2024-04-26T10:00:00
```

### Test a Single Task

```bash
# Dry-run without side effects
airflow tasks test crypto_lens_main_pipeline coin_data_collector 2024-04-26

# Actual run
airflow tasks run crypto_lens_main_pipeline coin_data_collector 2024-04-26
```

### Backfill Historical Data

```bash
# Run pipeline for past dates
airflow dags backfill crypto_lens_main_pipeline \
    --start-date 2024-04-01 \
    --end-date 2024-04-20
```

### Clear Task History

```bash
# Clear failed task and retry
airflow tasks clear crypto_lens_main_pipeline coin_data_collector

# Clear entire DAG run
airflow dags delete crypto_lens_main_pipeline
```

### Pause/Resume DAGs

```bash
# Pause DAG (stop scheduling)
airflow dags pause crypto_lens_main_pipeline

# Resume DAG
airflow dags unpause crypto_lens_main_pipeline
```

## Troubleshooting Cheat Sheet

| Issue | Solution |
|-------|----------|
| **DAGs not showing** | `airflow dags list` • Check `AIRFLOW_HOME` is set • Verify `dags_folder` in airflow.cfg |
| **Task fails with import error** | Check Python path includes `/opt/crypto-lens-ai` • Verify config.conf exists |
| **Services won't start** | Check systemd service: `sudo systemctl status airflow-scheduler` • View logs: `sudo journalctl -u airflow-scheduler -f` |
| **Config not being read** | Verify config.conf is in parent of dags folder • Check log output: `[INFO] Loaded config from:` |
| **Task stuck/hanging** | Kill scheduler/webserver: `pkill -f airflow` • Check for long-running tasks |
| **Port 8080 already in use** | Use different port: `airflow webserver --port 8081` |
| **Database locked** | Stop scheduler, remove `airflow.db`, run `airflow db init` |
| **Permission denied** | Run with `sudo` or check folder permissions • `sudo chown -R ubuntu:ubuntu /opt/crypto-lens-ai` |

## Environment Variables

```bash
# Essential
export AIRFLOW_HOME=/path/to/airflow-home
export PYTHONPATH=/path/to/crypto-lens-ai:$PYTHONPATH

# Optional (for production)
export AIRFLOW__CORE__EXECUTOR=LocalExecutor
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=sqlite:///./airflow.db
export AIRFLOW__LOGGING__BASE_LOG_FOLDER=/var/log/airflow/
```

## EC2 Ubuntu Systemd Setup

To run Airflow services as system daemons on Ubuntu EC2:

```bash
# Create scheduler service
sudo nano /etc/systemd/system/airflow-scheduler.service

# Paste content from AIRFLOW_MIGRATION.md Step 8
# Then enable and start:

sudo systemctl daemon-reload
sudo systemctl enable airflow-scheduler airflow-webserver
sudo systemctl start airflow-scheduler airflow-webserver

# Monitor:
sudo systemctl status airflow-scheduler
sudo journalctl -u airflow-scheduler -f
```

## Production Deployment Steps

1. **Test everything** (2-3 days with parallel cron)
   ```bash
   # Compare outputs from cron and Airflow
   diff /var/log/cron-output.log /var/log/airflow/logs/
   ```

2. **Disable cron jobs**
   ```bash
   sudo crontab -e
   # Comment out crypto-lens entries
   ```

3. **Monitor Airflow**
   - Watch Web UI daily
   - Check logs for errors
   - Verify output files are generated

4. **Archive old setup** (after 1 week stable)
   ```bash
   tar -czf setup_sh_backup.tar.gz setup.sh
   rm setup.sh
   ```

## DAG Dependency Visualization

View in Airflow Web UI: **DAGs → [dag-name] → Graph**

```
Main Pipeline DAG:
┌─────────────────────────────────────────────────────────────┐
│ coin_data_collector → hourly_fetch → daily_fetch → ...       │
└─────────────────────────────────────────────────────────────┘

Logs Cleanup DAG:
┌──────────────┐
│ logs_cleaner │
└──────────────┘
```

## Switching Between Cron and Airflow

### To Airflow (recommended):
```bash
# 1. Install and test
python setup_airflow.py
# 2. Run parallel for 3-5 days
# 3. Disable cron: sudo crontab -e
```

### Back to Cron (if needed):
```bash
# 1. Stop Airflow
pkill -f "airflow scheduler"
pkill -f "airflow webserver"

# 2. Re-enable cron
sudo crontab -e  # Uncomment crypto-lens entries

# 3. Verify
sudo service cron restart
```

## Logs Location

| Type | Location |
|------|----------|
| Scheduler | `$AIRFLOW_HOME/logs/scheduler.log` |
| Task (Airflow) | `$AIRFLOW_HOME/logs/dag_id/task_id/` |
| Task (Pipeline) | `/var/log/crypto-lens/` (from config.conf) |
| Web server | stdout (terminal) |

## Performance Tuning

For 5-minute intervals with 6 tasks:

```ini
# airflow.cfg
[core]
parallelism = 32              # Global max tasks
max_active_tasks_per_dag = 1  # Keep sequential
max_active_runs_per_dag = 1   # One run at a time

[scheduler]
dag_discovery_interval = 30   # Check for new DAGs every 30s
```

## Resources

- Full guide: [AIRFLOW_MIGRATION.md](AIRFLOW_MIGRATION.md)
- Setup script: [setup_airflow.py](setup_airflow.py)
- Main DAG: [dags/crypto_lens_main_pipeline.py](dags/crypto_lens_main_pipeline.py)
- Config reader: [dags/airflow_config_loader.py](dags/airflow_config_loader.py)
- Airflow docs: https://airflow.apache.org/docs/
