#!/bin/bash

#pip install -e . && ytb2audiobot --mode DEV
pip install -e . --no-deps

# shellcheck disable=SC2046
# export $(grep -v '^#' .env | xargs)


# Load the environment variables from the .env file, ignoring comments and handling special characters properly
set -a  # Automatically export all variables defined
source .env
set +a  # Disable automatic export


ytb2audiobot 2>&1 | tee -a output.log
