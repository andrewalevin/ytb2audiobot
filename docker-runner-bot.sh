#!/bin/bash

# Docker runner script for the ytb2audiobot project.
# This script executes a target command inside the Docker container for ytb2audiobot.
# It supports silent mode to suppress output based on the SILENT_MODE environment variable.

echo -e "[docker-runner-bot.sh] 🐳 Starting ytb2audiobot in Docker container..."

# Set default for SILENT_MODE if not provided
SILENT_MODE="${SILENT_MODE:-false}"

LOG_TO_FILE="${LOG_TO_FILE:-false}"

# Function to log messages based on silent mode
log_message() {
    if [ "$SILENT_MODE" != true ]; then
        echo "[docker-runner-bot.sh] $1"
    fi
}

log_message "SILENT_MODE is set to $SILENT_MODE."
log_message "To change the silent mode setting, set the environment variable SILENT_MODE to true or false."

# Execute the ytb2audiobot command with or without output suppression
if [ "$SILENT_MODE" = true ]; then
    log_message "Silent mode is ON. The command will run without log output."
    ytb2audiobot > /dev/null 2>&1
elif [ "$LOG_TO_FILE" = true ]; then
    log_message "Logging mode is ON. The command output will be saved to output.log."
    ytb2audiobot | tee -a output.log
else
    log_message "Silent mode is OFF. Running command with log output."
    ytb2audiobot
fi
