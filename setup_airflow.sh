#!/bin/bash

################################################################################
# Crypto-Lens Airflow Setup Script
# 
# Purpose: Create and configure Apache Airflow environment with systemd services
# Prerequisites: Python 3.11 installed at OS level
# Usage: bash setup_airflow.sh
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

APP_DIR="/opt/crypto-lens-ai"
AIRFLOW_HOME="${APP_DIR}/airflow-home"
VENV_DIR="${APP_DIR}/airflow-venv"
PYTHON_BIN="python3.11"

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# VALIDATION
# ============================================================================

validate_python() {
    log_info "Checking Python 3.11..."
    
    if ! command -v ${PYTHON_BIN} &> /dev/null; then
        log_error "Python 3.11 not found. Install with: sudo apt-get install -y python3.11 python3.11-venv python3.11-dev"
        exit 1
    fi
    
    PYTHON_VERSION=$(${PYTHON_BIN} --version 2>&1 | awk '{print $2}')
    log_success "Found ${PYTHON_BIN}: ${PYTHON_VERSION}"
}

validate_directories() {
    log_info "Validating directory structure..."
    
    if [ ! -d "${APP_DIR}" ]; then
        log_error "Application directory not found: ${APP_DIR}"
        exit 1
    fi
    
    if [ ! -f "${APP_DIR}/config.conf" ]; then
        log_warning "config.conf not found in ${APP_DIR}"
    fi
    
    log_success "Directories validated"
}

# ============================================================================
# VIRTUAL ENVIRONMENT SETUP
# ============================================================================

setup_venv() {
    log_info "Setting up Airflow virtual environment..."
    
    if [ -d "${VENV_DIR}" ]; then
        log_warning "Virtual environment already exists at ${VENV_DIR}"
        read -p "Remove and recreate? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "${VENV_DIR}"
            log_info "Removed existing venv"
        else
            log_info "Skipping venv creation"
            return 0
        fi
    fi
    
    ${PYTHON_BIN} -m venv "${VENV_DIR}"
    log_success "Virtual environment created at ${VENV_DIR}"
}

activate_venv() {
    log_info "Activating virtual environment..."
    source "${VENV_DIR}/bin/activate"
    log_success "Virtual environment activated"
}

# ============================================================================
# HELPER: Use venv python/pip directly
# ============================================================================

VENV_PIP="${VENV_DIR}/bin/pip"
VENV_PYTHON="${VENV_DIR}/bin/python"

# ============================================================================
# AIRFLOW INSTALLATION
# ============================================================================

install_airflow() {
    log_info "Installing Apache Airflow 2.7.3..."
    
    # Upgrade pip using explicit venv path
    ${VENV_PIP} install --upgrade pip setuptools wheel
    log_success "pip, setuptools, wheel upgraded"
    
    # Install Airflow (with visible output for debugging)
    log_info "Installing apache-airflow==2.7.3..."
    ${VENV_PIP} install apache-airflow==2.7.3
    
    # Install missing dependencies that Airflow doesn't include by default
    log_info "Installing required dependencies..."
    ${VENV_PIP} install flask-session
    
    log_success "Apache Airflow 2.7.3 installed with all dependencies"
}

# ============================================================================
# AIRFLOW INITIALIZATION
# ============================================================================

initialize_airflow_db() {
    log_info "Initializing Airflow database..."
    
    mkdir -p "${AIRFLOW_HOME}"
    
    export AIRFLOW_HOME="${AIRFLOW_HOME}"
    
    # Initialize database (with visible output)
    if airflow db init; then
        log_success "Airflow database initialized at ${AIRFLOW_HOME}"
    else
        log_error "Failed to initialize Airflow database"
        return 1
    fi
}

create_admin_user() {
    log_info "Creating Airflow admin user..."
    
    export AIRFLOW_HOME="${AIRFLOW_HOME}"
    
    # Create admin user (with visible output)
    if airflow users create \
        --username admin \
        --firstname Admin \
        --lastname User \
        --role Admin \
        --email admin@example.com \
        --password airflow123 2>&1; then
        log_success "Airflow admin user created (admin/airflow123)"
    else
        log_warning "Admin user may already exist or creation encountered an issue"
    fi
}

# ============================================================================
# ENVIRONMENT FILE
# ============================================================================

create_env_file() {
    log_info "Creating environment file..."
    
    ENV_FILE="${APP_DIR}/.env.airflow"
    
    cat > "${ENV_FILE}" << 'EOF'
# Airflow Environment Variables
export AIRFLOW_HOME=/opt/crypto-lens-ai/airflow-home
export PYTHONPATH=/opt/crypto-lens-ai:$PYTHONPATH

# Airflow Configuration
export AIRFLOW__CORE__DAGS_FOLDER=/opt/crypto-lens-ai/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL=30
export AIRFLOW__SCHEDULER__MAX_ACTIVE_TASKS_PER_DAG=1

# Timezone
export AIRFLOW__CORE__DEFAULT_TIMEZONE=UTC

# Add your API keys here (optional)
# export CMC_API_KEY="your-key"
# export HOURLY_WEBHOOK="your-webhook"
# export DAILY_WEBHOOK="your-webhook"
EOF
    
    chmod 600 "${ENV_FILE}"
    log_success "Environment file created at ${ENV_FILE}"
}

# ============================================================================
# SYSTEMD SERVICES
# ============================================================================

create_systemd_services() {
    log_info "Creating systemd service files..."
    
    # Scheduler service
    sudo tee /etc/systemd/system/airflow-scheduler.service > /dev/null << EOF
[Unit]
Description=Airflow Scheduler
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env.airflow
ExecStart=${VENV_DIR}/bin/airflow scheduler
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # Webserver service
    sudo tee /etc/systemd/system/airflow-webserver.service > /dev/null << EOF
[Unit]
Description=Airflow Webserver
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env.airflow
ExecStart=${VENV_DIR}/bin/airflow webserver --port 8080
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    log_success "Systemd service files created"
}

enable_systemd_services() {
    log_info "Enabling and starting systemd services..."
    
    sudo systemctl daemon-reload
    sudo systemctl enable airflow-scheduler airflow-webserver
    sudo systemctl start airflow-scheduler airflow-webserver
    
    log_success "Services enabled and started"
}

check_service_status() {
    log_info "Checking service status..."
    
    sleep 2  # Give services time to start
    
    echo ""
    if sudo systemctl is-active --quiet airflow-scheduler; then
        log_success "✓ airflow-scheduler is running"
    else
        log_error "✗ airflow-scheduler failed to start"
        echo "  Check logs: sudo journalctl -u airflow-scheduler -f"
    fi
    
    if sudo systemctl is-active --quiet airflow-webserver; then
        log_success "✓ airflow-webserver is running"
    else
        log_error "✗ airflow-webserver failed to start"
        echo "  Check logs: sudo journalctl -u airflow-webserver -f"
    fi
    echo ""
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     Apache Airflow Setup for Crypto-Lens AI Project      ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    validate_python
    validate_directories
    
    setup_venv
    activate_venv
    
    install_airflow
    initialize_airflow_db
    create_admin_user
    create_env_file
    
    create_systemd_services
    enable_systemd_services
    check_service_status
    
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    Setup Complete! ✓                      ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Open browser: http://<your-ec2-ip>:8080"
    echo "  2. Login: admin / airflow123"
    echo "  3. View logs: sudo journalctl -u airflow-scheduler -f"
    echo ""
    echo "To verify DAG discovery:"
    echo "  source ${VENV_DIR}/bin/activate"
    echo "  airflow dags list"
    echo ""
}

# Run main function
main
