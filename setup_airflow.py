#!/usr/bin/env python
"""
Crypto-Lens Airflow Quick Setup Script

This script automates the setup and validation of Apache Airflow for the crypto-lens project.

Usage:
    python setup_airflow.py                  # Interactive setup
    python setup_airflow.py --init           # Initialize Airflow DB
    python setup_airflow.py --validate       # Validate DAG configuration
    python setup_airflow.py --start          # Start Airflow services
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Optional, List
import configparser


class Colors:
    """ANSI color codes for terminal output."""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'


def colored(text: str, color: str) -> str:
    """Apply color to text."""
    if sys.platform == "win32":
        return text  # Windows terminal doesn't support ANSI colors well
    return f"{color}{text}{Colors.RESET}"


def log_info(msg: str) -> None:
    """Log info message."""
    print(colored(f"[INFO] {msg}", Colors.BLUE))


def log_success(msg: str) -> None:
    """Log success message."""
    print(colored(f"[SUCCESS] {msg}", Colors.GREEN))


def log_warning(msg: str) -> None:
    """Log warning message."""
    print(colored(f"[WARNING] {msg}", Colors.YELLOW))


def log_error(msg: str) -> None:
    """Log error message."""
    print(colored(f"[ERROR] {msg}", Colors.RED))


def find_airflow_home() -> Path:
    """Find or create AIRFLOW_HOME directory."""
    airflow_home = os.environ.get("AIRFLOW_HOME")
    
    if airflow_home:
        return Path(airflow_home)
    
    # Default to crypto-lens-ai/airflow-home
    script_dir = Path(__file__).parent
    default_home = script_dir / "airflow-home"
    
    return default_home


def check_requirements() -> bool:
    """Check if required packages are installed."""
    log_info("Checking requirements...")
    
    required_packages = [
        ("airflow", "apache-airflow"),
        ("config", None),  # Our own config module
    ]
    
    missing = []
    for import_name, pip_name in required_packages:
        try:
            __import__(import_name)
            log_success(f"✓ {import_name}")
        except ImportError:
            pip_package = pip_name or import_name
            log_error(f"✗ {import_name} (install: pip install {pip_package})")
            missing.append(pip_package)
    
    if missing:
        log_error(f"\nMissing packages: {', '.join(missing)}")
        log_info("Install with: pip install -r requirements.txt")
        return False
    
    log_success("All requirements met")
    return True


def check_config_file(project_root: Path) -> bool:
    """Verify config.conf exists."""
    config_file = project_root / "config.conf"
    
    if config_file.exists():
        log_success(f"✓ Found config.conf: {config_file}")
        
        # Parse and display schedules
        config = configparser.ConfigParser()
        config.read(config_file)
        
        if config.has_section("schedules"):
            main_sched = config.get("schedules", "main_cron_sched", fallback="*/5 * * * *")
            cleanup_sched = config.get("schedules", "logs_cleaner_cron_sched", fallback="0 15 * * *")
            
            log_info(f"Main pipeline schedule: {main_sched}")
            log_info(f"Logs cleanup schedule: {cleanup_sched}")
        
        return True
    else:
        log_error(f"✗ config.conf not found: {config_file}")
        return False


def initialize_airflow(airflow_home: Path) -> bool:
    """Initialize Airflow database."""
    log_info("Initializing Airflow database...")
    
    airflow_home.mkdir(parents=True, exist_ok=True)
    
    env = os.environ.copy()
    env["AIRFLOW_HOME"] = str(airflow_home)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "airflow", "db", "init"],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode == 0:
            log_success("✓ Airflow database initialized")
            return True
        else:
            log_error(f"✗ Database initialization failed:")
            print(result.stderr)
            return False
    
    except subprocess.TimeoutExpired:
        log_error("✗ Airflow initialization timed out")
        return False
    except Exception as e:
        log_error(f"✗ Error initializing Airflow: {e}")
        return False


def create_admin_user(airflow_home: Path, username: str = "admin", password: str = "admin") -> bool:
    """Create Airflow admin user."""
    log_info(f"Creating admin user '{username}'...")
    
    env = os.environ.copy()
    env["AIRFLOW_HOME"] = str(airflow_home)
    
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "airflow", "users", "create",
                "--username", username,
                "--firstname", "Admin",
                "--lastname", "User",
                "--role", "Admin",
                "--email", "admin@example.com",
                "--password", password,
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        
        if result.returncode == 0:
            log_success(f"✓ Admin user created: {username}/{password}")
            return True
        else:
            # Check if user already exists
            if "already exists" in result.stderr or "already exists" in result.stdout:
                log_warning(f"✓ Admin user already exists: {username}")
                return True
            
            log_error(f"✗ Failed to create admin user:")
            print(result.stderr or result.stdout)
            return False
    
    except subprocess.TimeoutExpired:
        log_error("✗ User creation timed out")
        return False
    except Exception as e:
        log_error(f"✗ Error creating admin user: {e}")
        return False


def validate_dags(project_root: Path) -> bool:
    """Validate DAG files."""
    log_info("Validating DAGs...")
    
    dags_dir = project_root / "dags"
    if not dags_dir.exists():
        log_error(f"✗ DAGs directory not found: {dags_dir}")
        return False
    
    dag_files = list(dags_dir.glob("*.py"))
    if not dag_files:
        log_error(f"✗ No Python files found in {dags_dir}")
        return False
    
    all_valid = True
    for dag_file in dag_files:
        if dag_file.name.startswith("_"):
            continue  # Skip __init__.py and similar
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(dag_file)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode == 0:
                log_success(f"✓ {dag_file.name}")
            else:
                log_error(f"✗ {dag_file.name}: {result.stderr}")
                all_valid = False
        
        except Exception as e:
            log_error(f"✗ Error validating {dag_file.name}: {e}")
            all_valid = False
    
    if all_valid:
        log_success("All DAGs are valid")
    
    return all_valid


def list_dags(airflow_home: Path) -> bool:
    """List discovered DAGs."""
    log_info("Discovering DAGs...")
    
    env = os.environ.copy()
    env["AIRFLOW_HOME"] = str(airflow_home)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "airflow", "dags", "list"],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode == 0:
            print(result.stdout)
            log_success("DAGs discovered successfully")
            return True
        else:
            log_error("✗ Failed to list DAGs:")
            print(result.stderr)
            return False
    
    except Exception as e:
        log_error(f"✗ Error listing DAGs: {e}")
        return False


def print_next_steps(airflow_home: Path) -> None:
    """Print next steps for the user."""
    print("\n" + "="*70)
    print("✓ Airflow setup complete!")
    print("="*70)
    print("\nNext steps:\n")
    print("1. Start the Airflow Scheduler (in terminal 1):")
    print(f"   export AIRFLOW_HOME={airflow_home}")
    print("   airflow scheduler\n")
    print("2. Start the Web Server (in terminal 2):")
    print(f"   export AIRFLOW_HOME={airflow_home}")
    print("   airflow webserver --port 8080\n")
    print("3. Open your browser and navigate to:")
    print("   http://localhost:8080\n")
    print("4. Login with:")
    print("   Username: admin")
    print("   Password: admin\n")
    print("5. Monitor your DAGs in the Web UI")
    print("="*70 + "\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Crypto-Lens Airflow Setup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_airflow.py                # Interactive setup
  python setup_airflow.py --init         # Initialize only
  python setup_airflow.py --validate     # Validate DAGs only
  python setup_airflow.py --start        # Start Airflow services
        """
    )
    
    parser.add_argument("--init", action="store_true", help="Initialize Airflow database")
    parser.add_argument("--validate", action="store_true", help="Validate DAG files")
    parser.add_argument("--list-dags", action="store_true", help="List discovered DAGs")
    parser.add_argument("--start", action="store_true", help="Start Airflow services")
    parser.add_argument("--airflow-home", type=str, help="Path to AIRFLOW_HOME")
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path(__file__).parent
    
    # Set AIRFLOW_HOME
    airflow_home = Path(args.airflow_home) if args.airflow_home else find_airflow_home()
    os.environ["AIRFLOW_HOME"] = str(airflow_home)
    
    print("\n" + "="*70)
    print("Crypto-Lens Airflow Setup")
    print("="*70)
    print(f"Project Root: {project_root}")
    print(f"AIRFLOW_HOME: {airflow_home}\n")
    
    # Check prerequisites
    if not check_requirements():
        log_error("Please install missing packages: pip install -r requirements.txt")
        return 1
    
    if not check_config_file(project_root):
        return 1
    
    # Run requested operations
    if args.init:
        return 0 if initialize_airflow(airflow_home) else 1
    
    if args.validate:
        return 0 if validate_dags(project_root) else 1
    
    if args.list_dags:
        return 0 if list_dags(airflow_home) else 1
    
    if args.start:
        log_info("Starting Airflow services...")
        log_warning("Please run in separate terminals:")
        print(f"  Terminal 1: export AIRFLOW_HOME={airflow_home} && airflow scheduler")
        print(f"  Terminal 2: export AIRFLOW_HOME={airflow_home} && airflow webserver --port 8080")
        return 0
    
    # Default: Full setup
    log_info("Running full setup...\n")
    
    if not initialize_airflow(airflow_home):
        return 1
    
    if not create_admin_user(airflow_home):
        return 1
    
    if not validate_dags(project_root):
        return 1
    
    if not list_dags(airflow_home):
        return 1
    
    print_next_steps(airflow_home)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
