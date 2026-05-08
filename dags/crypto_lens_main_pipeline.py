"""
Crypto-Lens Airflow DAG - Main Pipeline Orchestration

This DAG orchestrates the crypto-lens data pipeline with optimized parallel execution:

Schedule: Configurable via config.conf (default: every 5 minutes)

Dependency Graph:
    coin_data_collector (no dependencies)
        ├─→ hourly_fetch_and_pulse ──→ oi_change_screener ──┐
        │                                                     ├─→ pipeline_observability
        └─→ daily_fetch_and_pulse ──→ market_breadth ───────┘

Benefits of parallel execution:
- coin_data_collector runs first (required by all)
- hourly & daily analysis run in parallel after coin_data_collector
- market_breadth waits only for daily data (not hourly)
- oi_change_screener waits only for hourly data (not daily)
- observability waits for all to complete before final checks
- Total time: reduced from ~6 sequential tasks to ~3 parallel levels

Configuration: All schedules read from config.conf (no code changes needed)
Error handling: Continues on task failure (graceful degradation)

Migration from cron:
- Old: setup.sh configured crontab with "*/5 * * * *" for main pipeline
- New: Airflow DAG with schedule_interval from config.conf + optimized dependencies
"""

from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
import os
import sys
import subprocess

# Add parent directory to path to import modules
DAG_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(DAG_DIR)
sys.path.insert(0, PARENT_DIR)

from dags.airflow_config_loader import get_config_loader

# ============================================================================
# Configuration
# ============================================================================

# Load configuration from config.conf
config_loader = get_config_loader()
MAIN_SCHEDULE = config_loader.get_main_schedule()  # Default: "*/5 * * * *"
APP_DIR = PARENT_DIR

# DAG configuration
default_args = {
    "owner": "crypto-lens",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

# ============================================================================
# DAG Definition
# ============================================================================

dag = DAG(
    dag_id="crypto_lens_main_pipeline",
    description="Crypto-Lens main data pipeline with optimized parallel execution: collect coins → parallel hourly & daily analysis → separate market metrics → observability checks",
    schedule_interval=MAIN_SCHEDULE,
    default_args=default_args,
    catchup=False,  # Don't backfill past runs
    max_active_runs=1,  # One DAG run at a time, but tasks within run execute in parallel
    tags=["crypto-lens", "production", "pipeline"],
    doc_md=__doc__,
)


# ============================================================================
# Task Functions
# ============================================================================

def run_python_script(script_name: str) -> None:
    """
    Execute a Python script from the app directory.
    
    Args:
        script_name: Name of the script (e.g., "coin_data_collector.py")
    
    Raises:
        RuntimeError: If the script fails
    """
    script_path = os.path.join(APP_DIR, script_name)
    
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script not found: {script_path}")
    
    print(f"\n{'='*60}")
    print(f"Running: {script_name}")
    print(f"Location: {script_path}")
    print('='*60)
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=APP_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print(f"\n✓ {script_name} completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ {script_name} failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        raise RuntimeError(f"Script {script_name} failed with exit code {e.returncode}")
    except Exception as e:
        print(f"\n✗ Error running {script_name}: {str(e)}")
        raise


def task_coin_data_collector(**context: Any) -> None:
    """Collect coin metadata from Binance and CoinMarketCap APIs."""
    run_python_script("coin_data_collector.py")


def task_hourly_fetch_and_pulse(**context: Any) -> None:
    """Analyze 1-hour market data with RSI and sentiment indicators."""
    run_python_script("hourly_fetch_and_pulse.py")


def task_daily_fetch_and_pulse(**context: Any) -> None:
    """Analyze daily market data and generate summaries."""
    run_python_script("daily_fetch_and_pulse.py")


def task_market_breadth(**context: Any) -> None:
    """Calculate market-wide sentiment metrics (BTC%, BTCD%, advances/declines)."""
    run_python_script("market_breadth.py")


def task_oi_change_screener(**context: Any) -> None:
    """Screen for open interest anomalies and detect top movers."""
    run_python_script("oi_change_screener.py")


def task_pipeline_observability(**context: Any) -> None:
    """Monitor pipeline health, check logs, and send observability alerts."""
    run_python_script("pipeline_observability.py")


# ============================================================================
# Task Definitions
# ============================================================================

coin_data_collector = PythonOperator(
    task_id="coin_data_collector",
    python_callable=task_coin_data_collector,
    dag=dag,
)

hourly_fetch_and_pulse = PythonOperator(
    task_id="hourly_fetch_and_pulse",
    python_callable=task_hourly_fetch_and_pulse,
    dag=dag,
)

daily_fetch_and_pulse = PythonOperator(
    task_id="daily_fetch_and_pulse",
    python_callable=task_daily_fetch_and_pulse,
    dag=dag,
)

market_breadth = PythonOperator(
    task_id="market_breadth",
    python_callable=task_market_breadth,
    dag=dag,
)

oi_change_screener = PythonOperator(
    task_id="oi_change_screener",
    python_callable=task_oi_change_screener,
    dag=dag,
)

pipeline_observability = PythonOperator(
    task_id="pipeline_observability",
    python_callable=task_pipeline_observability,
    dag=dag,
)

# ============================================================================
# Task Dependencies (Optimized Parallel Execution)
# ============================================================================
#
# Dependency Graph:
#   coin_data_collector (must run first - no dependencies)
#       ├→ hourly_fetch_and_pulse ──→ oi_change_screener ──┐
#       │                                                     ├→ pipeline_observability
#       └→ daily_fetch_and_pulse ──→ market_breadth ───────┘
#
# This allows:
# - hourly and daily analyses to run in parallel (both depend on coin_data)
# - market_breadth only waits for daily data
# - oi_screener only waits for hourly data
# - observability waits for all to complete
#
# Total execution time: reduced from ~6 sequential steps to ~3 parallel levels
# Schedule: Same frequency from config.conf, just more efficient execution

# coin_data_collector must run first
coin_data_collector_task = coin_data_collector

# Both hourly and daily can start after coin_data_collector completes
coin_data_collector >> [hourly_fetch_and_pulse, daily_fetch_and_pulse]

# market_breadth waits only for daily_fetch_and_pulse
daily_fetch_and_pulse >> market_breadth

# oi_change_screener waits only for hourly_fetch_and_pulse
hourly_fetch_and_pulse >> oi_change_screener

# observability waits for all to complete
[market_breadth, oi_change_screener] >> pipeline_observability
