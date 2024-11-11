#!/bin/bash

# Script to Run Target Command within ytb2audiobot Docker Container
# This script executes a target command inside the container for the ytb2audiobot project.
# It checks if silent mode is enabled via an environment variable and adjusts the output accordingly.

echo -e "🐳 Running ytb2audiobot script in Docker container..."

# Set default for SILENT_MODE if not provided
: "${SILENT_MODE:=false}"

# Check if SILENT_MODE is enabled, adjust logging behavior based on its value
if [ "$SILENT_MODE" = true ]; then
    echo "[Runner] 🔐🙊 Silent mode is ON. The target command will run without any log output. [terminal_log > /dev/null 2>&1]"
    echo "[Runner] ⚠️ To disable silent mode, set the environment variable SILENT_MODE=false"
    echo "[Runner] Bot is running ... (silent mode)"
    echo ""

    # Execute the target command silently (suppress output)
    ytb2audiobot > /dev/null 2>&1

else
    echo "[Runner] 🔓📟 Silent mode is OFF. The target command will run with log output."
    echo "[Runner] ⚠️ To enable silent mode [terminal_log > /dev/null 2>&1], set the environment variable SILENT_MODE=true."
    echo ""

    ytb2audiobot

fi

# End of Script