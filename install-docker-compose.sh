#!/bin/bash

# Set the script to exit immediately on any errors
set -e

# Prompt for input token
# shellcheck disable=SC2162
read -p "📟 Please enter your telegram bot token: " TG_TOKEN < /dev/tty
if [ -z "$TG_TOKEN" ]; then
    echo "🚫 No input token!"
    echo "🪂 Exit."
    exit 1
fi

# shellcheck disable=SC2162
read -p "🧂 Please enter salt hash if exists. If not - press Enter - it will be generated: " HASH_SALT < /dev/tty

# Check if the user provided a salt
if [ -z "$HASH_SALT" ]; then
    HASH_SALT=$(openssl rand -hex 32)
    echo "💚 Generated random salt: $HASH_SALT"
fi

if [[ -z "$TG_TOKEN" || -z "$HASH_SALT" ]]; then
  echo "🚫 TG_TOKEN and SALT must be set."
  exit 1
  echo "🪂 Exit."
fi

CONTENT=$(curl -sL https://andrewalevin.github.io/ytb2audiobot/template-docker-compose.yaml)

CONTENT="${CONTENT//YOUR_TG_TOKEN/$TG_TOKEN}"

CONTENT="${CONTENT//YOUR_HASH_SALT/$HASH_SALT}"

echo -e "$CONTENT" > "docker-compose.yaml"

echo "💚📝 Docker compose file successfully generated!"

if ! command -v docker &> /dev/null; then
  echo "🚫 Docker is not installed."
  exit 1
  echo "🪂 Exit."
fi


if ! docker info > /dev/null 2>&1; then
  echo "🚫 Docker daemon is not running."
  exit 1
  echo "🪂 Exit."
fi

sudo docker-compose up -d

echo "💚 Installation and setup completed successfully!"





