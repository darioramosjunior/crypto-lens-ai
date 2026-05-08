---
description: "Airflow Migration Documentation Index - Complete guide to Airflow orchestration"
---

# Crypto-Lens Airflow Migration - Documentation Index

Welcome! This is your complete guide to migrating from cron to Apache Airflow orchestration. Start with the appropriate document based on your needs.

## 🚀 Quick Start (5 minutes)

**Start here if you want to get Airflow running immediately:**

→ [AIRFLOW_QUICKSTART.md](AIRFLOW_QUICKSTART.md)

Key sections:
- One-liner setup
- Common tasks (start, trigger, logs)
- Troubleshooting cheat sheet

## 📖 Full Documentation

### 1. **Migration Summary** (10 min read)
→ [AIRFLOW_MIGRATION_SUMMARY.md](AIRFLOW_MIGRATION_SUMMARY.md)

**What**: Overview of all changes made
**When**: Read first to understand scope
**Contains**:
- Files added/modified/unchanged
- Comparison (Cron vs Airflow)
- Key improvements
- Phase-by-phase migration path

### 2. **Architecture & Diagrams** (15 min read)
→ [AIRFLOW_ARCHITECTURE.md](AIRFLOW_ARCHITECTURE.md)

**What**: Visual system design and execution flows
**When**: Read to understand how components interact
**Contains**:
- System architecture diagram
- Data flow (old vs new)
- File structure
- Task dependency graphs
- Configuration change flow
- Web UI layout

### 3. **Complete Migration Guide** (45 min read)
→ [AIRFLOW_MIGRATION.md](AIRFLOW_MIGRATION.md)

**What**: Comprehensive step-by-step setup and deployment
**When**: Read before production deployment
**Contains**:
- Prerequisites & installation
- Configuration guide
- Monitoring & observability
- Migration path (Phase 1-3)
- Troubleshooting guide
- Best practices
- Reverting to cron
- Scaling to production

## 📁 Core Files Created

### DAG Files (Orchestration)
- **[dags/crypto_lens_main_pipeline.py](dags/crypto_lens_main_pipeline.py)**
  - Main pipeline DAG (runs every 5 minutes)
  - Orchestrates: coin_data → hourly → daily → breadth → OI → observability
  - Schedule from: config.conf `main_cron_sched`

- **[dags/crypto_lens_logs_cleanup.py](dags/crypto_lens_logs_cleanup.py)**
  - Logs cleanup DAG (runs daily at 3 PM)
  - Single task: logs_cleaner
  - Schedule from: config.conf `logs_cleaner_cron_sched`

- **[dags/airflow_config_loader.py](dags/airflow_config_loader.py)**
  - Configuration loader for DAGs
  - Reads schedules from config.conf
  - Supports fallback defaults

- **[dags/__init__.py](dags/__init__.py)**
  - Package marker (required for DAG discovery)

### Setup & Configuration
- **[setup_airflow.py](setup_airflow.py)**
  - Automated Airflow installation & setup
  - Usage: `python setup_airflow.py`
  - Features: DB init, admin user, DAG validation

- **[airflow.cfg.template](airflow.cfg.template)**
  - Reference Airflow configuration
  - Pre-configured for crypto-lens
  - Apply to $AIRFLOW_HOME/airflow.cfg after setup

- **[requirements.txt](requirements.txt)** (Updated)
  - Added: `apache-airflow>=2.7.0`
  - All existing dependencies preserved

## ⚡ Quick Commands

### Setup
```bash
pip install -r requirements.txt
python setup_airflow.py
```

### Run
```bash
export AIRFLOW_HOME=/path/to/airflow-home

# Terminal 1: Start scheduler
airflow scheduler

# Terminal 2: Start web server
airflow webserver --port 8080
```

### Monitor
```bash
# List DAGs
airflow dags list

# View latest run
airflow dags list-runs --dag-id crypto_lens_main_pipeline

# Trigger manually
airflow dags trigger crypto_lens_main_pipeline

# View logs
airflow tasks logs crypto_lens_main_pipeline coin_data_collector

# Test task
airflow tasks test crypto_lens_main_pipeline coin_data_collector 2024-04-26
```

### Web UI
- URL: http://localhost:8080
- Login: admin / admin
- View: DAGs → Graph → Logs → Admin

## 🔄 Migration Phases

### Phase 1: Preparation (Day 1)
- [ ] Read: AIRFLOW_MIGRATION_SUMMARY.md
- [ ] Install: `pip install -r requirements.txt`
- [ ] Setup: `python setup_airflow.py`
- [ ] Verify: `airflow dags list`

### Phase 2: Parallel Testing (Day 2-3)
- [ ] Start Airflow services
- [ ] Keep cron running
- [ ] Compare outputs
- [ ] Monitor Web UI

### Phase 3: Cutover (Day 4)
- [ ] Disable cron: `sudo crontab -e`
- [ ] Monitor Airflow for 2+ days
- [ ] Validate data quality

### Phase 4: Cleanup (Day 7+)
- [ ] Remove setup.sh
- [ ] Archive logs
- [ ] Document final config

## 📊 What Changed

### Added ✨
- `dags/` directory with 2 DAGs
- `setup_airflow.py` for automated setup
- Airflow documentation (4 files)
- Apache Airflow dependency

### Modified 🔧
- `requirements.txt` (+airflow)
- `config.conf` still used (schedule source)

### Unchanged ✓
- All pipeline scripts
- Main orchestration logic
- Error handling approach
- Log locations
- Backward compatibility

## 🎯 Key Features

| Feature | Cron | Airflow |
|---------|------|---------|
| **Same Schedule** | ✓ | ✓ (from config.conf) |
| **Same Sequence** | ✓ | ✓ (DAG dependencies) |
| **Same Configurability** | ✓ | ✓ (config.conf) |
| **Web Dashboard** | ✗ | ✓ (http://localhost:8080) |
| **Retry on Failure** | ✗ | ✓ (automatic) |
| **Historical Tracking** | ✗ | ✓ (database) |
| **Easy Backfilling** | ✗ | ✓ (one command) |
| **Alert Integration** | ~ | ✓ (email/Slack) |
| **Scalability** | Limited | ✓ (distributed) |

## 🆘 Troubleshooting

### Problem: DAGs not showing
- **Solution**: Check `AIRFLOW_HOME`, verify `dags_folder` in airflow.cfg
- **More**: See [AIRFLOW_MIGRATION.md](AIRFLOW_MIGRATION.md) Troubleshooting section

### Problem: Config not being read
- **Solution**: Ensure config.conf is in parent of dags/ folder
- **Verify**: Check log output: `[INFO] Loaded config from:`

### Problem: Services won't start on EC2
- **Solution**: Check systemd service file paths and permissions
- **More**: See [AIRFLOW_MIGRATION.md](AIRFLOW_MIGRATION.md#problem-services-wont-start)

### Problem: Task fails
- **Solution**: Check logs: `airflow tasks logs [dag_id] [task_id]`
- **More**: Full troubleshooting guide in [AIRFLOW_MIGRATION.md](AIRFLOW_MIGRATION.md)

## 📚 Documentation Map

```
AIRFLOW_QUICKSTART.md
└─ Start here for quick setup

AIRFLOW_MIGRATION_SUMMARY.md
└─ High-level overview of all changes

AIRFLOW_ARCHITECTURE.md
└─ Visual diagrams and system design

AIRFLOW_MIGRATION.md
└─ Comprehensive step-by-step guide
   ├─ Installation
   ├─ Configuration
   ├─ Monitoring
   ├─ Migration path
   ├─ Troubleshooting
   └─ Best practices

setup_airflow.py
└─ Automated setup script

dags/
├─ crypto_lens_main_pipeline.py (Main DAG)
├─ crypto_lens_logs_cleanup.py (Cleanup DAG)
└─ airflow_config_loader.py (Config loader)
```

## 🔍 File Locations

### Documentation
- **Quick Start**: [AIRFLOW_QUICKSTART.md](AIRFLOW_QUICKSTART.md)
- **Summary**: [AIRFLOW_MIGRATION_SUMMARY.md](AIRFLOW_MIGRATION_SUMMARY.md)
- **Architecture**: [AIRFLOW_ARCHITECTURE.md](AIRFLOW_ARCHITECTURE.md)
- **Full Guide**: [AIRFLOW_MIGRATION.md](AIRFLOW_MIGRATION.md)
- **Index** (this file): [AIRFLOW_INDEX.md](AIRFLOW_INDEX.md)

### Configuration & Setup
- **Config Template**: [airflow.cfg.template](airflow.cfg.template)
- **Setup Script**: [setup_airflow.py](setup_airflow.py)
- **Schedules**: [config.conf](config.conf)
- **Requirements**: [requirements.txt](requirements.txt)

### DAGs & Components
- **Main Pipeline**: [dags/crypto_lens_main_pipeline.py](dags/crypto_lens_main_pipeline.py)
- **Cleanup**: [dags/crypto_lens_logs_cleanup.py](dags/crypto_lens_logs_cleanup.py)
- **Config Loader**: [dags/airflow_config_loader.py](dags/airflow_config_loader.py)
- **Package Init**: [dags/__init__.py](dags/__init__.py)

## ✅ Validation Checklist

Use this to verify your Airflow setup:

- [ ] Python 3.8+ installed
- [ ] requirements.txt installed: `pip install -r requirements.txt`
- [ ] DAG files syntactically correct: `python -m py_compile dags/*.py`
- [ ] Airflow initialized: `airflow db init`
- [ ] Admin user created: `airflow users create ...`
- [ ] config.conf exists with [schedules] section
- [ ] DAGs discovered: `airflow dags list` shows 2 DAGs
- [ ] Scheduler starts: `airflow scheduler`
- [ ] Web server starts: `airflow webserver`
- [ ] Web UI accessible: http://localhost:8080
- [ ] Task runs successfully: `airflow tasks test [dag_id] [task_id] 2024-04-26`

## 🚀 Next Steps

1. **Read**: Start with [AIRFLOW_QUICKSTART.md](AIRFLOW_QUICKSTART.md)
2. **Setup**: Run `python setup_airflow.py`
3. **Verify**: Check DAG discovery with `airflow dags list`
4. **Monitor**: Access Web UI at http://localhost:8080
5. **Deploy**: Follow Phase 1-4 migration plan
6. **Optimize**: Adjust schedules in config.conf as needed

## 📞 Support

For issues:
1. Check the appropriate documentation file (above)
2. Run validation: `python setup_airflow.py --validate`
3. Check logs: `airflow tasks logs [dag_id] [task_id]`
4. Review troubleshooting in [AIRFLOW_MIGRATION.md](AIRFLOW_MIGRATION.md)

---

**Migration Status**: ✅ Complete

**All files validated**: Syntax ✓ | Architecture ✓ | Documentation ✓

**Ready to deploy**: Yes, follow [AIRFLOW_QUICKSTART.md](AIRFLOW_QUICKSTART.md)

Last Updated: April 26, 2026
