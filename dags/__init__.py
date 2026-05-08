"""
Crypto-Lens Airflow DAGs Package

This package contains all Airflow DAGs for the Crypto-Lens pipeline.

DAGs included:
- crypto_lens_main_pipeline: Main orchestration (5-minute interval)
- crypto_lens_logs_cleanup: Log file cleanup (daily at 3 PM)

Configuration is read from ../config.conf
"""
