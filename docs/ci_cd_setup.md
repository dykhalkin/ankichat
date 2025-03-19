# CI/CD Setup for AnkiChat

This document explains the Continuous Integration and Continuous Deployment (CI/CD) setup for the AnkiChat Telegram bot application.

## Overview

The CI/CD pipeline uses GitHub Actions to automatically test and deploy the application when changes are pushed to the `master` branch. The setup includes:

1. A GitHub Actions workflow that runs tests and quality checks
2. A deployment script that sets up the application as a systemd service on an Ubuntu server

## GitHub Actions Workflow

The workflow is defined in `.github/workflows/ci.yml` and performs the following steps:

### Test and Lint Job
- Runs on every push to the `master` branch and pull requests
- Sets up Python 3.10
- Installs all dependencies from `requirements.txt`
- Runs all quality checks (formatting, linting, type checking, and tests with coverage)
- Archives the code coverage reports as artifacts

### Deploy Job
- Only runs when commits are pushed to the `master` branch (not on pull requests)
- Uses SSH to connect to the production server
- Executes the deployment script on the server

## Deployment Script

The `deploy.sh` script sets up the application as a systemd service on an Ubuntu server. It:

1. Creates the application directory (`/opt/ankichat`)
2. Sets up a logs directory (`/var/log/ankichat`)
3. Copies or updates the application code
4. Sets up a Python virtual environment and installs dependencies
5. Creates a template `.env` file if one doesn't exist
6. Creates a systemd service file
7. Sets appropriate permissions
8. Enables and starts the service

## Required GitHub Secrets

The following secrets must be set in the GitHub repository settings:

### Deployment Secrets (Required)
- `DEPLOY_HOST`: The hostname or IP address of the deployment server
- `DEPLOY_USER`: The SSH username to use for deployment
- `DEPLOY_KEY`: The SSH private key for authentication

### Application Secrets (Required)
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token

### Optional Application Secrets
- `DB_PATH`: Database file path (defaults to `/opt/ankichat/data/ankichat.db`)
- `LOG_LEVEL`: Logging level (defaults to `INFO`)
- `LOG_FILE`: Log file path (defaults to `/var/log/ankichat/app.log`)
- `OPENAI_API_KEY`: OpenAI API key for LLM features (omitted if not provided)

## Environment Configuration

The deployment script will create a `.env` file using the secrets provided in GitHub. If you need to manually update the environment variables after deployment:

```bash
sudo nano /opt/ankichat/.env
```

The deployment process is designed to:
1. Use values from GitHub secrets if available
2. Fall back to existing values in the `.env` file if present
3. Use default values as a last resort

## Manual Deployment

If needed, you can manually deploy the application by running the deployment script on the server:

```bash
# Clone the repository
git clone https://github.com/breathman/ankichat.git
cd ankichat

# Run the deployment script (requires sudo)
sudo ./deploy.sh
```

## Monitoring the Service

You can monitor the service status with:

```bash
sudo systemctl status telegram-anki
```

And view logs with:

```bash
sudo journalctl -u telegram-anki -f
```

## Security Considerations

- The SSH key used for deployment should have the minimum necessary permissions
- The `.env` file containing sensitive credentials is not committed to the repository
- The application runs as the `www-data` user, not as root