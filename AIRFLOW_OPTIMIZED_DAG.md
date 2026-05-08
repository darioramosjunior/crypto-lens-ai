# Crypto-Lens Main Pipeline DAG - Optimized Dependency Structure

## Overview

The main pipeline DAG has been updated to use **optimized parallel execution** instead of strict linear sequencing. This maintains the same schedule frequency (every 5 minutes from config.conf) but allows tasks to run in parallel where dependencies permit.

## New Dependency Graph

```
Level 1 (Must run first):
    coin_data_collector
    └── Fetches coin metadata from Binance & CoinMarketCap
    
Level 2 (Run in parallel after coin_data_collector):
    ├── hourly_fetch_and_pulse
    │   └── 1-hour market analysis with RSI & sentiment
    │
    └── daily_fetch_and_pulse
        └── Daily market data and summaries

Level 3 (Run based on their dependencies):
    ├── oi_change_screener
    │   └── Waits only for hourly_fetch_and_pulse
    │
    └── market_breadth
        └── Waits only for daily_fetch_and_pulse

Level 4 (Final step):
    └── pipeline_observability
        └── Waits for both oi_change_screener & market_breadth
```

## Dependency Matrix

| Task | Dependencies | Waits For |
|------|--------------|-----------|
| coin_data_collector | None | — |
| hourly_fetch_and_pulse | coin_data_collector | coin_data_collector |
| daily_fetch_and_pulse | coin_data_collector | coin_data_collector |
| market_breadth | daily_fetch_and_pulse | daily_fetch_and_pulse only |
| oi_change_screener | hourly_fetch_and_pulse | hourly_fetch_and_pulse only |
| pipeline_observability | all above | market_breadth + oi_change_screener |

## What Changed

### Old (Linear) Structure
```python
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

Execution time: Task1 + Task2 + Task3 + Task4 + Task5 + Task6
(All tasks run sequentially)
```

### New (Optimized Parallel) Structure
```python
coin_data_collector
    ├→ hourly_fetch_and_pulse ──→ oi_change_screener ──┐
    │                                                     ├→ pipeline_observability
    └→ daily_fetch_and_pulse ──→ market_breadth ───────┘

Execution time: Task1 + max(hourly_path, daily_path) + Task_observability
(Tasks 2 & 3 run in parallel, then branching continues in parallel)
```

## Performance Improvement

### Time Reduction Example (Hypothetical)
Assuming each task takes ~1 minute:

**Old (Linear)**:
```
T=0:00   Start
T=1:00   coin_data_collector ✓
T=2:00   hourly_fetch_and_pulse ✓
T=3:00   daily_fetch_and_pulse ✓
T=4:00   market_breadth ✓
T=5:00   oi_change_screener ✓
T=6:00   pipeline_observability ✓
T=6:00   TOTAL TIME: 6 minutes per run
```

**New (Optimized)**:
```
T=0:00   Start
T=1:00   coin_data_collector ✓
T=2:00   ├→ hourly_fetch_and_pulse ✓   AND   └→ daily_fetch_and_pulse ✓
T=3:00   ├→ oi_change_screener ✓        AND   └→ market_breadth ✓
T=4:00   pipeline_observability ✓
T=4:00   TOTAL TIME: 4 minutes per run
SAVINGS: 33% reduction!
```

**Real-world scenario** (5-min schedule with variable task times):
- Shorter total execution time = lower resource utilization
- Better tolerance for slight delays in individual tasks
- Faster recovery from failures (only blocked dependents re-run)

## Dependency Rules Explained

### 1. coin_data_collector (Entry Point)
- **Dependencies**: None
- **Reason**: Must fetch coin metadata first; required by all downstream tasks
- **Failure impact**: Blocks entire pipeline

### 2. hourly_fetch_and_pulse & daily_fetch_and_pulse (Parallel Branch)
- **Dependencies**: coin_data_collector only
- **Reason**: Both need market data from coin_data_collector, but don't depend on each other
- **Benefit**: Can run simultaneously, cut execution time in half
- **Failure impact**: Only blocks their downstream tasks (oi_screener for hourly, market_breadth for daily)

### 3. market_breadth (Daily Branch Continuation)
- **Dependencies**: daily_fetch_and_pulse only
- **Reason**: Needs daily market data, doesn't need hourly data
- **Benefit**: Not blocked by hourly tasks; can proceed if hourly has issues
- **Failure impact**: Only blocks pipeline_observability

### 4. oi_change_screener (Hourly Branch Continuation)
- **Dependencies**: hourly_fetch_and_pulse only
- **Reason**: Analyzes hourly data for anomalies, doesn't need daily summaries
- **Benefit**: Not blocked by daily tasks; independent analysis stream
- **Failure impact**: Only blocks pipeline_observability

### 5. pipeline_observability (Final Step)
- **Dependencies**: market_breadth AND oi_change_screener
- **Reason**: Monitors health of entire pipeline; needs both analysis branches complete
- **Benefit**: Runs last, ensuring all data is available for holistic monitoring
- **Failure impact**: Non-blocking (monitoring only); won't stop pipeline execution

## Configuration & Schedule

**Schedule Source**: `config.conf` [schedules] section
```ini
[schedules]
main_cron_sched=*/5 * * * *   # Unchanged - runs DAG every 5 minutes
```

**No code changes needed!** Just update config.conf if you want to change the frequency:
- `0 * * * *` → Every hour
- `0 9 * * *` → Daily at 9 AM
- `0 0 * * 0` → Weekly (Sundays)

## Visualization in Airflow Web UI

When you view the DAG in the Airflow Web UI (Graph view), you'll see:

```
          ┌─ hourly_fetch_and_pulse ─→ oi_change_screener ─┐
          │                                                  ├─ pipeline_observability
coin_data │
collector │
          └─ daily_fetch_and_pulse ──→ market_breadth ────┘
```

Tasks will show colors:
- 🟩 Green = Succeeded
- 🟥 Red = Failed  
- 🟨 Yellow = Upstream dependency failed
- 🟦 Blue = Running/In Progress

## Error Handling & Resilience

### Failure Scenarios

**If coin_data_collector fails**:
- All downstream tasks blocked
- Entire pipeline fails (expected)
- Retry once after 2 minutes (default config)

**If hourly_fetch_and_pulse fails**:
- oi_change_screener blocked
- market_breadth & daily_fetch_and_pulse proceed normally
- pipeline_observability waits for market_breadth only
- Partial pipeline continues

**If daily_fetch_and_pulse fails**:
- market_breadth blocked
- hourly_fetch_and_pulse & oi_change_screener proceed normally
- pipeline_observability waits for oi_change_screener only
- Partial pipeline continues

**If both hourly & daily fail**:
- Both branches blocked
- pipeline_observability never runs (no dependencies met)
- Entire analysis suspended until retry succeeds

## Backward Compatibility

✅ **All scripts unchanged**: No modifications to individual Python scripts needed
✅ **Same schedule**: Uses config.conf [schedules] main_cron_sched
✅ **Same configurability**: Change schedules in config.conf, auto-reloads
✅ **Same output**: Same files generated in same locations
✅ **Same log format**: Logs still written to /var/log/crypto-lens/

## Implementation Details

### Airflow Dependency Syntax
```python
# Both tasks start after coin_data_collector completes
coin_data_collector >> [hourly_fetch_and_pulse, daily_fetch_and_pulse]

# market_breadth waits for daily_fetch_and_pulse
daily_fetch_and_pulse >> market_breadth

# oi_change_screener waits for hourly_fetch_and_pulse
hourly_fetch_and_pulse >> oi_change_screener

# pipeline_observability waits for both market_breadth and oi_change_screener
[market_breadth, oi_change_screener] >> pipeline_observability
```

### DAG Configuration
```python
max_active_runs=1  # One DAG run at a time (respects 5-min schedule)
                   # But tasks within each run can execute in parallel
depends_on_past=False  # Each run independent
catchup=False  # Don't backfill past runs
```

## Testing the New DAG

### Manual Trigger
```bash
# Trigger the DAG manually to see parallel execution
airflow dags trigger crypto_lens_main_pipeline

# View the execution
airflow dags list-runs --dag-id crypto_lens_main_pipeline --limit 5
```

### Test Individual Task
```bash
# Test a task (dry-run, no side effects)
airflow tasks test crypto_lens_main_pipeline hourly_fetch_and_pulse 2024-04-29

# Test another branch
airflow tasks test crypto_lens_main_pipeline market_breadth 2024-04-29
```

### Monitor in Web UI
```
1. Open http://localhost:8080
2. Go to: DAGs → crypto_lens_main_pipeline → Graph
3. Click on tasks to see their status
4. Check "Gantt" view to see execution timeline
5. Check "Logs" tab for detailed output
```

## Gantt Chart Timeline (Web UI)

In the Airflow Web UI Gantt view, you'll see something like:

```
Task                    Timeline
─────────────────────────────────────────────────
coin_data_collector     [████████]
hourly_fetch_and_pulse      [████████]
daily_fetch_and_pulse       [████████]
oi_change_screener              [████████]
market_breadth              [████████]
pipeline_observability              [████████]

Time axis →
```

Tasks on the same horizontal level run in parallel!

## Monitoring & Observability

### View Task Status
```bash
# Get detailed info about a task
airflow tasks info crypto_lens_main_pipeline hourly_fetch_and_pulse

# View recent runs
airflow tasks list-runs crypto_lens_main_pipeline hourly_fetch_and_pulse --limit 10
```

### Log Locations
- **Airflow scheduler logs**: $AIRFLOW_HOME/logs/scheduler.log
- **Task logs**: $AIRFLOW_HOME/logs/crypto_lens_main_pipeline/task_id/
- **Pipeline script logs**: /var/log/crypto-lens/

## When to Adjust Dependencies

You might want to modify dependencies if:

**Add dependency**: A task needs data from another task not yet complete
```python
new_task = PythonOperator(task_id="new_task", ...)
oi_change_screener >> new_task  # new_task waits for oi_change_screener
```

**Remove dependency**: A task no longer needs specific data
```python
# If market_breadth no longer needs daily_fetch data:
# Remove: daily_fetch_and_pulse >> market_breadth
# Add: coin_data_collector >> market_breadth
```

**Make parallel**: Two tasks can now run simultaneously
```python
# If both tasks just need coin_data:
coin_data_collector >> [task1, task2]
```

## Rollback to Linear Execution

If you need to revert to strict linear execution:

```python
# Replace the dependency section with:
(
    coin_data_collector
    >> hourly_fetch_and_pulse
    >> daily_fetch_and_pulse
    >> market_breadth
    >> oi_change_screener
    >> pipeline_observability
)
```

No other changes needed! The schedule stays the same.

## Summary

| Aspect | Old (Linear) | New (Optimized) |
|--------|--------------|-----------------|
| **Schedule** | Every 5 minutes | Every 5 minutes (unchanged) |
| **Execution Levels** | 6 sequential | 4 parallel levels |
| **Potential Time Savings** | — | ~33% reduction |
| **Resilience** | Full failure if any task fails | Partial execution if single branch fails |
| **Parallelization** | None | Maximum possible |
| **Config Changes** | None | None |
| **Script Changes** | None | None |
| **Web UI Complexity** | Simple chain | Clear branching structure |

---

**Result**: Same frequency, same configurability, optimized execution with intelligent parallelism! ✨
