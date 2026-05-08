"""
Airflow configuration loader for Crypto-Lens.
This module reads the cron schedule expressions from config.conf
and converts them to Airflow schedule_interval format.
"""

import os
import re
from configparser import ConfigParser
from typing import Optional, Dict


class CronToAirflowConverter:
    """Convert cron expressions to Airflow schedule_interval."""
    
    @staticmethod
    def convert_cron_to_airflow(cron_expr: str) -> Optional[str]:
        """
        Convert Unix cron expression to Airflow format.
        Airflow uses the same format, so direct pass-through works.
        
        Args:
            cron_expr: Unix cron expression (e.g., "*/5 * * * *")
        
        Returns:
            Cron expression for Airflow schedule_interval, or None if invalid
        """
        # Basic validation: cron should have 5 fields
        fields = cron_expr.strip().split()
        if len(fields) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expr}")
        
        return cron_expr
    
    @staticmethod
    def cron_to_timedelta(cron_expr: str) -> Optional[str]:
        """
        For simple intervals like "*/5 * * * *", convert to Python timedelta format.
        Returns the cron expression as-is for Airflow (which understands cron natively).
        
        Args:
            cron_expr: Unix cron expression
        
        Returns:
            Cron expression (Airflow understands cron natively)
        """
        return cron_expr


class AirflowConfigLoader:
    """Load Airflow configuration from config.conf."""
    
    CONFIG_FILE = "config.conf"
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the config loader.
        
        Args:
            config_path: Path to config.conf. If None, searches in parent directories.
        """
        self.config = ConfigParser()
        self.config_file_path = self._find_config_file(config_path)
        
        if self.config_file_path:
            self.config.read(self.config_file_path)
            print(f"[INFO] Loaded config from: {self.config_file_path}")
    
    def _find_config_file(self, config_path: Optional[str]) -> Optional[str]:
        """
        Find config.conf by searching up the directory tree.
        
        Args:
            config_path: Explicit path to config.conf
        
        Returns:
            Path to config.conf or None if not found
        """
        if config_path and os.path.exists(config_path):
            return config_path
        
        # Search in current directory and parent directories
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for _ in range(3):  # Search up to 3 levels
            candidate = os.path.join(current_dir, self.CONFIG_FILE)
            if os.path.exists(candidate):
                return candidate
            current_dir = os.path.dirname(current_dir)
        
        print(f"[WARNING] config.conf not found. Using default values.")
        return None
    
    def get_schedule(self, schedule_key: str, default: str) -> str:
        """
        Get a schedule expression from config.conf.
        
        Args:
            schedule_key: Key in [schedules] section (e.g., "main_cron_sched")
            default: Default value if not found
        
        Returns:
            Schedule expression (cron format)
        """
        if self.config.has_section("schedules") and self.config.has_option("schedules", schedule_key):
            return self.config.get("schedules", schedule_key)
        
        print(f"[WARNING] Schedule '{schedule_key}' not found in config. Using default: {default}")
        return default
    
    def get_paths(self) -> Dict[str, str]:
        """
        Get all path configurations.
        
        Returns:
            Dictionary with log_path and output_path
        """
        paths = {
            "log_path": "/var/log/crypto-lens/",
            "output_path": "/var/run/crypto-lens/",
        }
        
        if self.config.has_section("paths"):
            if self.config.has_option("paths", "log_path"):
                paths["log_path"] = self.config.get("paths", "log_path")
            if self.config.has_option("paths", "output_path"):
                paths["output_path"] = self.config.get("paths", "output_path")
        
        return paths
    
    def get_main_schedule(self) -> str:
        """Get main pipeline schedule (default: every 5 minutes)."""
        return self.get_schedule("main_cron_sched", "*/5 * * * *")
    
    def get_cleanup_schedule(self) -> str:
        """Get logs cleanup schedule (default: daily at 3 PM)."""
        return self.get_schedule("logs_cleaner_cron_sched", "0 15 * * *")


# Global config instance
_config_loader: Optional[AirflowConfigLoader] = None


def get_config_loader() -> AirflowConfigLoader:
    """Get or create the global config loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = AirflowConfigLoader()
    return _config_loader
