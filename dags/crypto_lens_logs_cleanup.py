"""
Crypto-Lens Airflow DAG - Logs Cleanup

This DAG handles periodic log file cleanup.

Migration from cron:
- Old: setup.sh configured crontab with "0 15 * * *" (daily at 3 PM)
- New: Airflow DAG with schedule_interval from config.conf
"""

from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.python import PythonOperator
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
CLEANUP_SCHEDULE = config_loader.get_cleanup_schedule()  # Default: "0 15 * * *" (3 PM daily)
APP_DIR = PARENT_DIR

# DAG configuration
default_args = {
    "owner": "crypto-lens",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# ============================================================================
# DAG Definition
# ============================================================================

dag = DAG(
    dag_id="crypto_lens_logs_cleanup",
    description="Clean up crypto-lens log files (scheduled: daily at 3 PM by default)",
    schedule_interval=CLEANUP_SCHEDULE,
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
    tags=["crypto-lens", "maintenance", "logs"],
    doc_md=__doc__,
)


# ============================================================================
# Task Functions
# ============================================================================

def run_python_script(script_name: str) -> None:
    """
    Execute a Python script from the app directory.
    
    Args:
        script_name: Name of the script (e.g., "logs_cleaner.py")
    
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


def task_logs_cleaner(**context: Any) -> None:
    """Clean up log files in the configured log directory."""
    run_python_script("logs_cleaner.py")


# ============================================================================
# Task Definitions
# ============================================================================

logs_cleaner = PythonOperator(
    task_id="logs_cleaner",
    python_callable=task_logs_cleaner,
    dag=dag,
)
