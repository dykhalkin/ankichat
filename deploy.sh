#!/bin/bash
#
# AnkiChat Deployment Script
# This script deploys the AnkiChat Telegram bot as a systemd service
#

set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error when substituting

# Configuration Variables
VENV_DIR="$APP_DIR/.venv"
SERVICE_NAME="telegram-anki.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
REPO_URL="https://github.com/breathman/ankichat.git"
LOG_DIR="/var/log/$APP_NAME"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Error logging function
error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
    exit 1
}

# Warning logging function
warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" >&2
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root"
fi

# Create application directory if it doesn't exist
log "Setting up application directory at $APP_DIR"
if [ ! -d "$APP_DIR" ]; then
    mkdir -p "$APP_DIR"
    log "Created application directory"
else
    log "Application directory already exists"
fi

# Create log directory if it doesn't exist
log "Setting up log directory at $LOG_DIR"
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    log "Created log directory"
    # Set proper permissions for the log directory
    chown -R www-data:www-data "$LOG_DIR"
    chmod -R 755 "$LOG_DIR"
else
    log "Log directory already exists"
fi

# Deploy the application code
log "Deploying application code"
# If we're running from a cloned repo, copy the files
if [ -f "./src/main.py" ]; then
    log "Copying application files from current directory"
    rsync -av --exclude 'venv' --exclude '.git' ./ "$APP_DIR/"
# Otherwise, clone the repository
else
    log "Cloning repository from $REPO_URL"
    if [ -d "$APP_DIR/.git" ]; then
        cd "$APP_DIR"
        git pull
        log "Updated existing repository"
    else
        rm -rf "$APP_DIR"
        git clone "$REPO_URL" "$APP_DIR"
        log "Cloned repository"
    fi
fi

# Setup virtual environment
log "Setting up Python virtual environment"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    log "Created new virtual environment"
else
    log "Using existing virtual environment"
fi

# Install dependencies
log "Installing dependencies"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"

# Create a .env file if it doesn't exist
if [ ! -f "$APP_DIR/.env" ]; then
    warning "No .env file found. Creating a template .env file."
    cat > "$APP_DIR/.env" << EOF
# AnkiChat Environment Configuration
# Update these values with your actual credentials

# Telegram Bot Token (required)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Database settings
DB_PATH=/home/ankichat/data/ankichat.db

# Logging settings
LOG_LEVEL=INFO
LOG_FILE=/home/ankichat/logs/app.log

# LLM Settings (if applicable)
# OPENAI_API_KEY=your_openai_api_key_here
EOF
    log "Created template .env file at $APP_DIR/.env"
    warning "Please update the .env file with your actual credentials"
else
    log "Using existing .env file"
fi

# Create systemd service file
log "Creating systemd service file"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Telegram Anki Flashcards Bot
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/python $APP_DIR/src/main.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=$APP_NAME
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

log "Created systemd service file at $SERVICE_FILE"

# Ensure the data directory exists
if [ ! -d "$APP_DIR/data" ]; then
    mkdir -p "$APP_DIR/data"
    log "Created data directory"
fi

# Set proper ownership for all application files
log "Setting proper file permissions"
chown -R www-data:www-data "$APP_DIR"
chmod -R 755 "$APP_DIR"

# Reload systemd, enable and restart the service
log "Reloading systemd daemon"
systemctl daemon-reload

log "Enabling and restarting service"
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

# Check if service is running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log "Deployment successful! Service is running."
    systemctl status "$SERVICE_NAME" --no-pager
else
    error "Deployment failed! Service failed to start."
fi

log "Deployment complete!"