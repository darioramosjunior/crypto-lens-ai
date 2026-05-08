---
description: "Airflow Migration Guide - Move from cron orchestration to Apache Airflow"
---

# Crypto-Lens Airflow Migration Guide

This guide helps you migrate the Crypto-Lens pipeline from cron-based orchestration to Apache Airflow while maintaining the same scheduling, execution sequence, and configurability.

## Quick Comparison: Cron vs. Airflow

| Aspect | Cron (Old) | Airflow (New) |
|--------|-----------|--------------|
| **Orchestrator** | System crontab | Airflow Scheduler |
| **Configuration** | `config.conf` | `config.conf` (read by DAG) |
| **Main Schedule** | `*/5 * * * *` (every 5 min) | Same (from config.conf) |
| **Cleanup Schedule** | `0 15 * * *` (3 PM daily) | Same (from config.conf) |
| **Execution** | Sequential Python scripts | DAG tasks with dependencies |
| **Monitoring** | Log files | Airflow Web UI + logs |
| **Error Handling** | Continue on failure | Configurable retries/alerts |
| **Visibility** | Tail logs | Real-time DAG visualization |
| **Deployment** | Simple shell script | Airflow setup + DAG directory |

## Architecture

### File Structure

```
crypto-lens-ai/
├── dags/
│   ├── __init__.py                    # DAG module marker
│   ├── airflow_config_loader.py       # Parse config.conf for schedules
│   ├── crypto_lens_main_pipeline.py   # Main pipeline DAG (5 min interval)
│   └── crypto_lens_logs_cleanup.py    # Logs cleanup DAG (3 PM daily)
├── config.conf                        # Schedules read by DAG config loader
├── requirements.txt                   # Includes apache-airflow dependencies
├── [other pipeline scripts unchanged]
```

### DAG Execution Sequence

#### **Main Pipeline DAG** (`crypto_lens_main_pipeline.py`)
Runs every 5 minutes (configurable):

```
coin_data_collector 
    ↓
hourly_fetch_and_pulse 
    ↓
daily_fetch_and_pulse 
    ↓
market_breadth 
    ↓
oi_change_screener 
    ↓
pipeline_observability
```

**Schedule**: `*/5 * * * *` (every 5 minutes, from `config.conf`)

#### **Logs Cleanup DAG** (`crypto_lens_logs_cleanup.py`)
Runs daily at 3 PM (configurable):

```
logs_cleaner
```

**Schedule**: `0 15 * * *` (3 PM daily, from `config.conf`)

## Installation & Setup

### Prerequisites

- **Ubuntu 20.04 LTS or 22.04 LTS** (EC2 instance)
- **Python 3.9+**
- **Apache Airflow 2.7+**

### Step 1: Update System & Install Dependencies

```bash
# Update package manager
sudo apt-get update && sudo apt-get upgrade -y

# Install Python and build tools
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev \
    build-essential libssl-dev libffi-dev python3-pip git curl

# Verify Python version
python3.11 --version
```

### Step 2: Create Application Directory & Virtual Environment

```bash
# Create app directory
sudo mkdir -p /opt/crypto-lens-ai
sudo chown $USER:$USER /opt/crypto-lens-ai
cd /opt/crypto-lens-ai

# Clone your project (or copy files via SCP)
git clone <your-repo-url> .

# Create virtual environment
python3.11 -m venv airflow-venv
source airflow-venv/bin/activate

# Verify activation (prompt should show (airflow-venv))
```

### Step 3: Install Airflow

```bash
# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Airflow
export AIRFLOW_HOME=/opt/crypto-lens-ai/airflow-home
pip install apache-airflow==2.7.3

# Install providers
pip install apache-airflow-providers-python

# Install project requirements
pip install -r requirements.txt
```

### Step 4: Initialize Airflow

```bash
# Set environment variables
export AIRFLOW_HOME=/opt/crypto-lens-ai/airflow-home
mkdir -p $AIRFLOW_HOME

# Initialize database
airflow db init

# Create admin user
airflow users create \
    --username admin \
    --firstname Crypto \
    --lastname Lens \
    --role Admin \
    --email admin@example.com \
    --password airflow123

# Verify user created
airflow users list
```

### Step 5: Configure Airflow

Edit `$AIRFLOW_HOME/airflow.cfg`:

```bash
nano $AIRFLOW_HOME/airflow.cfg
```

Key changes:

```ini
[core]
# Point to your DAGs directory
dags_folder = /opt/crypto-lens-ai/dags

# LocalExecutor for single EC2 instance
executor = LocalExecutor

# Database (SQLite for now, upgrade to PostgreSQL for production)
sql_alchemy_conn = sqlite:////opt/crypto-lens-ai/airflow-home/airflow.db

# Disable example DAGs
load_examples = False

# Timezone
default_timezone = UTC

[logging]
# Keep logs on EC2
base_log_folder = /opt/crypto-lens-ai/airflow-home/logs

[scheduler]
dag_discovery_interval = 30
max_active_tasks_per_dag = 1

[webserver]
expose_config = False
web_server_port = 8080
```

### Step 6: Set Up Environment File

Create `/opt/crypto-lens-ai/.env`:

```bash
nano /opt/crypto-lens-ai/.env
```

Add:
```bash
export AIRFLOW_HOME=/opt/crypto-lens-ai/airflow-home
export PYTHONPATH=/opt/crypto-lens-ai:$PYTHONPATH

# Your API keys and secrets
export CMC_API_KEY="your-cmc-api-key"
export HOURLY_WEBHOOK="your-discord-webhook"
export DAILY_WEBHOOK="your-discord-webhook"
```

### Step 7: Verify DAG Discovery

```bash
# List discovered DAGs
airflow dags list

# Should show:
# dag_id                          | filepath
# crypto_lens_logs_cleanup        | crypto_lens_logs_cleanup.py
# crypto_lens_main_pipeline       | crypto_lens_main_pipeline.py
```

### Step 8: Set Up Systemd Services

Create Scheduler Service (`/etc/systemd/system/airflow-scheduler.service`):

```bash
sudo nano /etc/systemd/system/airflow-scheduler.service
```

Paste:
```ini
[Unit]
Description=Airflow Scheduler
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/crypto-lens-ai
EnvironmentFile=/opt/crypto-lens-ai/.env
ExecStart=/opt/crypto-lens-ai/airflow-venv/bin/airflow scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create Webserver Service (`/etc/systemd/system/airflow-webserver.service`):

```bash
sudo nano /etc/systemd/system/airflow-webserver.service
```

Paste:
```ini
[Unit]
Description=Airflow Webserver
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/crypto-lens-ai
EnvironmentFile=/opt/crypto-lens-ai/.env
ExecStart=/opt/crypto-lens-ai/airflow-venv/bin/airflow webserver --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and Start:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable airflow-scheduler
sudo systemctl enable airflow-webserver

# Start services
sudo systemctl start airflow-scheduler
sudo systemctl start airflow-webserver

# Check status
sudo systemctl status airflow-scheduler
sudo systemctl status airflow-webserver
```

### Step 9: Configure Security Group

In AWS EC2 Console:
1. Go to **Security Groups**
2. Edit your instance's security group
3. Add Inbound Rule:
   - **Type**: Custom TCP
   - **Port**: 8080
   - **Source**: Your IP (e.g., `203.0.113.0/32`) or restrict as needed

### Step 10: Access Airflow Web UI

Open in browser:
```
http://<your-ec2-public-ip>:8080
```

Login:
- **Username**: admin
- **Password**: airflow123

## Configuration

### Schedule Configuration

Schedules are read from `config.conf` in the `[schedules]` section:

```ini
[schedules]
main_cron_sched=*/5 * * * *          # Main pipeline every 5 minutes
logs_cleaner_cron_sched=0 15 * * *   # Logs cleanup daily at 3 PM
```

**Cron Format Reference**:
```
# ┌──────────── minute (0-59)
# │ ┌────────── hour (0-23)
# │ │ ┌──────── day of month (1-31)
# │ │ │ ┌────── month (1-12)
# │ │ │ │ ┌──── day of week (0-6, Sunday=0)
# │ │ │ │ │
# * * * * *

# Examples:
*/5 * * * *     # Every 5 minutes
0 * * * *       # Every hour at :00
0 9 * * *       # Daily at 9 AM
0 15 * * *      # Daily at 3 PM
0 0 * * 0       # Weekly (Sundays at midnight)
0 0 1 * *       # Monthly (1st of month at midnight)
```

### Runtime Configuration

After modifying `config.conf`:
1. The DAG config loader automatically picks up changes on next DAG parse
2. **No restart required** — Airflow scheduler checks DAGs every 30 seconds (by default)
3. New schedules take effect within 1 minute

## Monitoring & Observability

### Web UI

Access the Airflow Web UI at **http://localhost:8080**

**Key views**:
- **DAGs**: Overview of all pipelines
- **Graph**: Task dependencies (same as our linear execution)
- **Logs**: Real-time task logs
- **Admin → Connections**: Manage external service credentials
- **Admin → Variables**: Store sensitive data (API keys, webhooks)

### Command-Line Monitoring

```bash
# Show DAG status
airflow dags status

# Show recent task runs
airflow tasks list crypto_lens_main_pipeline

# Get task logs
airflow tasks logs crypto_lens_main_pipeline coin_data_collector

# Trigger DAG manually
airflow dags trigger crypto_lens_main_pipeline

# Backfill past dates (if needed)
airflow dags backfill crypto_lens_main_pipeline \
    --start-date 2024-01-01 \
    --end-date 2024-01-10
```

### Logs Location

- **Airflow scheduler logs**: `$AIRFLOW_HOME/logs/scheduler.log`
- **DAG task logs**: `$AIRFLOW_HOME/logs/crypto_lens_main_pipeline/task_name/`
- **Pipeline script logs**: `/var/log/crypto-lens/` (from config.conf)

## Migration Path

### Phase 1: Validation (Day 1-2)

```bash
# 1. Install Airflow and DAGs as described above
# 2. Verify DAG discovery
airflow dags list

# 3. Dry-run a DAG task
airflow tasks test crypto_lens_main_pipeline coin_data_collector 2024-04-26

# 4. Check logs
airflow tasks logs crypto_lens_main_pipeline coin_data_collector
```

### Phase 2: Parallel Running (Day 3-7)

```bash
# 1. Start Airflow scheduler in background
airflow scheduler &

# 2. Keep cron jobs running side-by-side
# (they'll overlap but logs help identify any differences)

# 3. Compare outputs daily:
# - Check Airflow Web UI
# - Compare logs from both systems
# - Validate data outputs (prices_1h.csv, prices_1d.csv, etc.)
```

### Phase 3: Cutover (Day 8+)

```bash
# 1. Disable old cron jobs
sudo crontab -e
# Comment out or remove crypto-lens entries

# 2. Verify Airflow handles full workload
# Monitor for 2-3 days

# 3. Archive old logs and setup.sh
```

## Troubleshooting

### Problem: DAGs not appearing in Web UI

**Cause**: DAG file not discovered by Airflow scheduler

**Solution**:
```bash
# 1. Verify dags folder in airflow.cfg
grep dags_folder $AIRFLOW_HOME/airflow.cfg

# 2. Check DAG file exists and is valid Python
python -m py_compile dags/crypto_lens_main_pipeline.py

# 3. Restart scheduler
pkill -f "airflow scheduler"
airflow scheduler
```

### Problem: Tasks fail with "Module not found"

**Cause**: Python path doesn't include crypto-lens modules

**Solution**:
```bash
# Add to your DAG or airflow.cfg
export PYTHONPATH="/path/to/crypto-lens-ai:$PYTHONPATH"

# Or modify the DAG's python_callable wrapper
```

### Problem: Services won't start

**Cause**: Systemd service file has errors or incorrect paths

**Solution**:
```bash
# Check service status and errors
sudo systemctl status airflow-scheduler -l
sudo systemctl status airflow-webserver -l

# View service logs
sudo journalctl -u airflow-scheduler -n 50
sudo journalctl -u airflow-webserver -n 50

# Verify paths in service file
sudo cat /etc/systemd/system/airflow-scheduler.service

# Reload systemd if you edited service files
sudo systemctl daemon-reload

# Restart services
sudo systemctl restart airflow-scheduler airflow-webserver
```

### Problem: Can't access Airflow Web UI (http://<ip>:8080)

**Cause**: Security group not allowing port 8080 or webserver not running

**Solution**:
```bash
# Check if webserver is running
sudo systemctl status airflow-webserver

# Check if port 8080 is listening
sudo lsof -i :8080
netstat -tuln | grep 8080

# Check EC2 security group allows 8080
# AWS Console → EC2 → Security Groups → Edit Inbound Rules
# Add rule: Type=Custom TCP, Port=8080, Source=<your-ip>/32

# Restart webserver
sudo systemctl restart airflow-webserver
```

### Problem: Config.conf not being read

**Cause**: Config loader can't find config.conf

**Solution**:
```bash
# DAG searches up 3 directory levels from dags/
# Make sure config.conf is in the parent of dags/ directory

# Expected: /path/to/crypto-lens-ai/config.conf
# DAG location: /path/to/crypto-lens-ai/dags/crypto_lens_main_pipeline.py

# Verify by checking logs
airflow tasks logs crypto_lens_main_pipeline coin_data_collector
# Should show: "[INFO] Loaded config from: ..."
```

## Best Practices

### 1. Environment Variables

Store sensitive data in environment variables or Airflow Variables, not in code:

```bash
# Set before starting Airflow
export CMC_API_KEY="your-key-here"
export HOURLY_WEBHOOK="your-webhook-url"
```

Or use Airflow Web UI: **Admin → Variables**

### 2. Monitoring Task Health

Monitor task execution in Web UI:
- Green = Success
- Red = Failed
- Yellow = Upstream failed
- Blue = Running

### 3. Alerting

Configure email alerts in `airflow.cfg`:

```ini
[email]
email_backend = airflow.providers.smtp.utils.airflow_provider_email_backend

[smtp]
smtp_host = smtp.gmail.com
smtp_port = 587
smtp_user = your-email@gmail.com
smtp_password = your-app-password
```

Then in DAG:
```python
default_args = {
    "email": ["alerts@yourcompany.com"],
    "email_on_failure": True,
}
```

### 4. Scaling to Production

For production deployments:
- Use **CeleryExecutor** with message broker (Redis/RabbitMQ)
- Use **PostgreSQL** instead of SQLite
- Deploy on **Ubuntu 20.04+ LTS on AWS EC2** (recommended)
- Set up **monitoring** (Prometheus, Grafana)
- Use **Kubernetes** for auto-scaling (advanced)

For details, see [Airflow Production Deployment](https://airflow.apache.org/docs/apache-airflow/stable/production-deployment.html)

## Disabling Cron & Cleanup

Once you've verified Airflow is stable:

```bash
# Remove crypto-lens cron entries
sudo crontab -e

# Find and delete/comment these lines:
# */5 * * * * /path/to/crypto-lens-ai/setup.sh run-main
# 0 15 * * * /path/to/crypto-lens-ai/setup.sh run-cleanup

# Save and exit
```

## Reverting to Cron (if needed)

If you need to roll back:

```bash
# 1. Stop Airflow
pkill -f "airflow scheduler"
pkill -f "airflow webserver"

# 2. Re-enable cron jobs
sudo crontab -e
# Uncomment crypto-lens entries

# 3. Verify cron is running
sudo systemctl restart crond  # or cron (macOS)
```

## Additional Resources

- [Airflow Official Documentation](https://airflow.apache.org/docs/)
- [Airflow Python Operator](https://airflow.apache.org/docs/apache-airflow/stable/operators/python.html)
- [Airflow Scheduling Guide](https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html#scheduling)
- [Cron Expression Reference](https://crontab.guru/)

## Support

For issues specific to Crypto-Lens Airflow migration:
1. Check task logs: `airflow tasks logs crypto_lens_main_pipeline TASK_NAME`
2. Verify config.conf is accessible and valid
3. Run DAG validation: `python -m py_compile dags/*.py`
4. Check Airflow logs: `tail -f $AIRFLOW_HOME/logs/scheduler.log`
