#!/bin/bash

# Docker runner script for the ytb2audiobot project.
# This script executes a target command inside the Docker container for ytb2audiobot.
# It supports silent mode to suppress output based on the Y2A_SILENT_MODE environment variable.

echo -e "[docker-runner-bot.sh] 🐳 Starting ytb2audiobot in Docker container..."

# Set default for Y2A_SILENT_MODE if not provided
Y2A_SILENT_MODE="${Y2A_SILENT_MODE:-false}"

Y2A_LOG_TO_FILE="${Y2A_LOG_TO_FILE:-false}"
LOG_FILE_NAME="output.log"

echo "[docker-runner-bot.sh] Y2A_SILENT_MODE is set to $Y2A_SILENT_MODE."
echo "[docker-runner-bot.sh] ❗️ To change the silent mode setting, set the environment variable Y2A_SILENT_MODE to true or false."

# Execute the ytb2audiobot command with or without output suppression
if [ "$Y2A_SILENT_MODE" = true ]; then
    echo "[docker-runner-bot.sh] 🔐 Silent mode is ON. The command will run without log output."
    ytb2audiobot > /dev/null 2>&1

elif [ "$Y2A_LOG_TO_FILE" = true ]; then
    if [[ -n "${LOG2TELEGRAM_BOT_TOKEN}" && -n "${LOG2TELEGRAM_CHAT_ID}" ]]; then
      echo "[docker-runner-bot.sh] 🦨 Running with log2telegram bot "
      log2telegram --filter-color-chars --filter-timestamps $LOG_FILE_NAME > log2telegram.log 2>&1 &
      ytb2audiobot 2>&1 | tee -a $LOG_FILE_NAME
    else
      echo "[docker-runner-bot.sh] 💾 Logging mode is ON. The command output will be saved to output.log."
      ytb2audiobot 2>&1 | tee -a $LOG_FILE_NAME
    fi
else
    echo "[docker-runner-bot.sh] 📟 Silent mode is OFF. Running command with standart log output."
    ytb2audiobot
fi

