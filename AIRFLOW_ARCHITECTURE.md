# Crypto-Lens Airflow Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CRYPTO-LENS AIRFLOW SYSTEM                  │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ Configuration Layer                                                  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  config.conf                   airflow.cfg                          │
│  ────────────                  ───────────                          │
│  [schedules]                   [core]                               │
│  main_cron=*/5 * * * *        dags_folder=/path/dags              │
│  logs_cron=0 15 * * *         executor=LocalExecutor               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
           ↓                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│ Orchestration Layer                                                  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│          ┌─────────────────────────────────────────┐               │
│          │    Airflow Scheduler Daemon             │               │
│          │  (Monitors schedules, triggers tasks)   │               │
│          └────────────┬────────────────────────────┘               │
│                       │                                             │
│          ┌────────────┴────────────┬────────────┐                  │
│          ↓                         ↓            ↓                  │
│    ┌──────────────┐    ┌──────────────────┐   ┌──────────────┐    │
│    │ Every 5 min  │    │    Every 5 min   │   │  Daily 3 PM  │    │
│    └──────┬───────┘    └────────┬─────────┘   └──────┬───────┘    │
│           │                     │                     │             │
│           ▼                     ▼                     ▼             │
│    ┌─────────────┐       ┌──────────────┐    ┌──────────────┐     │
│    │   DAG:      │       │  DAG:        │    │  DAG:        │     │
│    │  Main       │       │  Main        │    │  Logs        │     │
│    │  Pipeline   │       │  Pipeline    │    │  Cleanup     │     │
│    │  (Run 1)    │       │  (Run 2)     │    │  (Daily)     │     │
│    └─────────────┘       └──────────────┘    └──────────────┘     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
           ↓
┌──────────────────────────────────────────────────────────────────────┐
│ DAG Execution Layer - Main Pipeline (Sequential)                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Task 1          Task 2          Task 3         Task 4     Task 5  │
│  ┌──────────┐    ┌──────────┐    ┌────────┐   ┌─────────┐ ┌──┐    │
│  │  Coin    │    │  Hourly  │    │ Daily  │   │ Market  │ │OI│    │
│  │  Data    ├──→ │  Fetch & ├──→ │ Fetch &├──→│Breadth  ├→│ │    │
│  │Collector │    │ Analyze  │    │Analyze │   │Screener │ │ │    │
│  │(fetch    │    │(RSI,1h) │    │(daily) │   │(BTC%,   │ │S│    │
│  │markets)  │    │sentiment)│    │summary │   │advances)│ │c│    │
│  └──────────┘    └──────────┘    └────────┘   └─────────┘ │r│    │
│                                                            │e│    │
│  Output:            Output:           Output:     Output: │e│    │
│  coin_data.csv      prices_1h.csv     prices_1d   breadth_│n│    │
│                     +alert_1h.png     .csv+alerts metrics │e│    │
│                                                            │r│    │
│                                                            └──┘    │
│                                                             │       │
│                                                    Task 6 (Pipeline│
│                                                    Observability)  │
│                                                    ┌───────────┐   │
│                                                    │  Monitor  │   │
│                                                    │  Logs &   │   │
│                                                    │Send Alerts│   │
│                                                    └───────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ Storage & Monitoring Layer                                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  File Outputs:                                                      │
│  • /var/log/crypto-lens/*.txt    (Pipeline logs)                   │
│  • prices_1h.csv, prices_1d.csv  (OHLCV data)                      │
│  • coin_data.csv                 (Market metadata)                 │
│  • *.png                         (Alert charts)                    │
│                                                                      │
│  Airflow Metadata:                                                  │
│  • $AIRFLOW_HOME/airflow.db      (SQLite database)                │
│  • $AIRFLOW_HOME/logs/           (Task execution logs)            │
│                                                                      │
│  Monitoring:                                                        │
│  • Web UI: http://localhost:8080  (DAG status, task logs)         │
│  • Discord Webhooks               (Real-time alerts)              │
│  • Email Alerts                   (Task failures)                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
CRON-BASED (Old)              →         AIRFLOW-BASED (New)
─────────────────                       ──────────────────

System Crontab                          Airflow Scheduler
   ↓                                           ↓
setup.sh                                 config.conf (schedule source)
   ↓                                           ↓
main.py                              crypto_lens_main_pipeline.py
   ↓                                           ↓
Sequential subprocess calls        DAG task dependencies
   ↓                                           ↓
coin_data_collector              coin_data_collector (Task 1)
   ↓                                           ↓
hourly_fetch_and_pulse           hourly_fetch_and_pulse (Task 2)
   ↓                                           ↓
daily_fetch_and_pulse            daily_fetch_and_pulse (Task 3)
   ↓                                           ↓
market_breadth                   market_breadth (Task 4)
   ↓                                           ↓
oi_change_screener               oi_change_screener (Task 5)
   ↓                                           ↓
pipeline_observability           pipeline_observability (Task 6)
   ↓                                           ↓
Log files: /var/log/              Airflow logs + /var/log/
No monitoring UI              Web UI: localhost:8080
Manual log inspection         Automatic retry on failure
```

## File Structure

```
crypto-lens-ai/
│
├── 📄 config.conf (SCHEDULE SOURCE - don't edit main.py or setup.sh)
│   ├── [schedules]
│   ├── main_cron_sched=*/5 * * * *        ← Main pipeline interval
│   └── logs_cleaner_cron_sched=0 15 * * * ← Cleanup interval
│
├── 📁 dags/ (NEW - Airflow DAGs directory)
│   ├── 📄 __init__.py (Package marker)
│   │
│   ├── 📄 airflow_config_loader.py
│   │   ├── AirflowConfigLoader class
│   │   ├── Reads: config.conf [schedules]
│   │   └── Returns: Cron expressions for DAGs
│   │
│   ├── 📄 crypto_lens_main_pipeline.py (MAIN DAG)
│   │   ├── DAG ID: crypto_lens_main_pipeline
│   │   ├── Schedule: from config.conf (*/5 * * * *)
│   │   ├── Tasks:
│   │   │   1. coin_data_collector
│   │   │   2. hourly_fetch_and_pulse
│   │   │   3. daily_fetch_and_pulse
│   │   │   4. market_breadth
│   │   │   5. oi_change_screener
│   │   │   6. pipeline_observability
│   │   └── Dependencies: Linear (1→2→3→4→5→6)
│   │
│   └── 📄 crypto_lens_logs_cleanup.py (CLEANUP DAG)
│       ├── DAG ID: crypto_lens_logs_cleanup
│       ├── Schedule: from config.conf (0 15 * * *)
│       ├── Tasks:
│       │   1. logs_cleaner
│       └── Dependencies: None (single task)
│
├── 📄 setup_airflow.py (NEW - Automated setup)
│   ├── Checks requirements
│   ├── Initializes Airflow DB
│   ├── Creates admin user
│   ├── Validates DAGs
│   └── Lists discovered DAGs
│
├── 📄 AIRFLOW_MIGRATION.md (NEW - Full guide)
├── 📄 AIRFLOW_QUICKSTART.md (NEW - Quick reference)
├── 📄 airflow.cfg.template (NEW - Config template)
│
├── 📄 requirements.txt (UPDATED - +apache-airflow)
│
├── 📄 main.py (UNCHANGED - Can coexist with Airflow)
├── 📄 setup.sh (UNCHANGED - Can disable after cutover)
│
└── 📁 [other files unchanged]
    ├── coin_data_collector.py
    ├── hourly_fetch_and_pulse.py
    ├── daily_fetch_and_pulse.py
    ├── market_breadth.py
    ├── oi_change_screener.py
    ├── pipeline_observability.py
    ├── logs_cleaner.py
    └── [etc.]
```

## Execution Sequence Timeline

```
TIME    CRON-BASED (OLD)              AIRFLOW-BASED (NEW)
────    ──────────────────            ───────────────────

00:00   Setup cron job                Scheduler running (daemon)
(boot)  ────────────────              ────────────────────────

00:05   ┌─ Cron triggers              ┌─ DAG triggered (scheduled)
        │  main.py                    │
        │                             │
        ├─ coin_data_collector       ├─ Task 1 starts
        │  (5 min)                   │  (concurrent with scheduler)
        │                            │
        ├─ hourly_fetch              ├─ Task 2 queued, waits for Task 1
        │  (wait for Task 1)         │
        │                            │
        ├─ daily_fetch               ├─ Task 3 queued
        │  (wait)                    │
        │                            │
        ├─ market_breadth            ├─ Task 4 queued
        │  (wait)                    │
        │                            │
        ├─ oi_change_screener        ├─ Task 5 queued
        │  (wait)                    │
        │                            │
        └─ observability             └─ Task 6 starts when ready
           (wait) ✓                    ✓ All tasks complete
           (logs written)              (Airflow logs + pipeline logs)

00:10   Idle (waiting for 00:10)     ┌─ DAG triggered again
        ────────────────              │  (next scheduled run)
                                      └─ Tasks 1-6 run again
                                         (same as 00:05)

00:15   ┌─ Cron triggers              ┌─ DAG triggered
        │  (repeat)                   │  (repeat)
        └─ 3rd run                    └─ 3rd run

[...]

15:00   Idle                          ┌─ Logs cleanup DAG triggered
        (no cleanup scheduled)        │  (0 15 * * * schedule)
                                      │
                                      └─ logs_cleaner runs
                                         (independent DAG)

Every 5 minutes: Main pipeline runs
Every day 3 PM: Logs cleanup runs
```

## Task Dependency Graph (Web UI Visualization)

### Main Pipeline DAG

```
coin_data_collector
        │
        ▼
hourly_fetch_and_pulse
        │
        ▼
daily_fetch_and_pulse
        │
        ▼
market_breadth
        │
        ▼
oi_change_screener
        │
        ▼
pipeline_observability
```

**View in Web UI**: DAGs → crypto_lens_main_pipeline → Graph

### Logs Cleanup DAG

```
logs_cleaner
```

**View in Web UI**: DAGs → crypto_lens_logs_cleanup → Graph

## Configuration Change Flow

```
User edits config.conf
        │
        ▼
[schedules]
main_cron_sched=0 0 * * *    (Change from */5 * * * * to daily)
        │
        ▼
Airflow scheduler scans DAGs
(every 30 seconds by default)
        │
        ▼
DAG config_loader reads config.conf
        │
        ▼
DAG schedule_interval updated
        │
        ▼
Next scheduled run uses NEW interval
(No restart needed!)
```

## Monitoring Views in Web UI

```
http://localhost:8080

├─ DAGs (List all DAGs)
│  ├─ crypto_lens_main_pipeline ✓
│  └─ crypto_lens_logs_cleanup ✓
│
├─ Graph (Task dependencies)
│  └─ Visualizes: task_1 → task_2 → ... → task_6
│
├─ Logs (Task execution output)
│  ├─ coin_data_collector
│  ├─ hourly_fetch_and_pulse
│  ├─ daily_fetch_and_pulse
│  ├─ market_breadth
│  ├─ oi_change_screener
│  └─ pipeline_observability
│
├─ Admin
│  ├─ Connections (External APIs)
│  ├─ Variables (Secrets)
│  ├─ XComs (Inter-task data)
│  └─ Logs (System logs)
│
└─ Statistics (Execution metrics)
   ├─ Task success rate
   ├─ Average duration
   └─ Total runs
```

---

This architecture maintains **identical execution semantics** to the original cron-based system while adding:
- ✅ Web UI for monitoring
- ✅ Automatic retry on failure
- ✅ Historical run tracking
- ✅ Better error alerting
- ✅ Easy backfilling
- ✅ Scalability path to distributed systems
