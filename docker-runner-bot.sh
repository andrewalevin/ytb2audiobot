#!/bin/bash

# Script to Run Target Command within ytb2audiobot Docker Container
# This script executes a target command inside the container for the ytb2audiobot project.
# It checks if silent mode is enabled via an environment variable and adjusts the output accordingly.

echo -e "[docker-runner-bot.sh] 🐳 Running ytb2audiobot script in Docker container..."

# Set default for SILENT_MODE if not provided
: "${SILENT_MODE:=false}"

# Check if SILENT_MODE is enabled, adjust logging behavior based on its value
if [ "$SILENT_MODE" = true ]; then
    echo "[docker-runner-bot.sh] 🔐🙊 Silent mode is ON. The target command will run without any log output. [terminal_log > /dev/null 2>&1]"
    echo "[docker-runner-bot.sh] ⚠️ To disable silent mode, set the environment variable SILENT_MODE=false"
    echo "[docker-runner-bot.sh] Bot is running ... (silent mode)"
    echo ""

    # Execute the target command silently (suppress output)
    ytb2audiobot > /dev/null 2>&1

else
    echo "[docker-runner-bot.sh] 🔓📟 Silent mode is OFF. The target command will run with log output."
    echo "[docker-runner-bot.sh] ⚠️ To enable silent mode [terminal_log > /dev/null 2>&1], set the environment variable SILENT_MODE=true."
    echo ""

    ytb2audiobot

fi

# End of Script