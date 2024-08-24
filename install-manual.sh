#!/bin/bash

# Set the script to exit immediately on any errors
set -e

confirm() {
    read -r -p "$1 [Y/n]: " response
    case "$response" in
        [nN][oO]|[nN])
            return 1
            ;;
        *)
            return 0
            ;;
    esac
}


# Determine the OS type (Linux or macOS)
OS=$(uname)
if [ "$OS" == "Linux" ]; then
  :
elif [ "$OS" == "Darwin" ]; then
  :
else
  # shellcheck disable=SC2028
  echo "🚫 💻 Unsupported OS: $OS.\n🔚 Exit"
  echo "🪂 Exit."
  exit 1
fi


dirname="ytb2audiobot"

dir=""

# Initialize counter
counter=1

# Loop to find a directory name that doesn't exist
while true; do
    # If counter is 0, use the base name; otherwise, append the counter to the name
    if [ $counter -eq 1 ]; then
        dir="$dirname"
    else
        dir="${dirname}${counter}"
    fi

    # Check if directory exists
    if [ ! -d "$dir" ]; then
        # Directory doesn't exist, create it
        mkdir "$dir"
        break
    fi

    # Increment counter for the next loop
    counter=$((counter + 1))
done

cd "$dir"

echo "💚 Installing required packages..."
packages=("python3" "ffmpeg")
# Install packages based on the OS type
if [ "$OS" == "Linux" ]; then
  sudo apt-get update

  for package in "${packages[@]}"; do
    sudo apt-get install -y "$package"
    done

elif [ "$OS" == "Darwin" ]; then
  if ! command -v brew &> /dev/null; then
    echo "🚫 Homebrew not found. You need to install Homebrew firstly..."
    echo "🪂 Exit."
    exit 1
  fi

  for package in "${packages[@]}"; do
    brew install "$package"
    done
else
  :
fi

# Check if the virtual environment directory exists
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

source venv/bin/activate

pip install ytb2audiobot


# shellcheck disable=SC2028
echo "\n\n💚 All right! \n Now let s set bot settings ... \n"

# shellcheck disable=SC2162
read -p "📟 Please enter your telegram bot token: " TG_TOKEN  < /dev/tty
if [ -z "$TG_TOKEN" ]; then
    echo "🚫 No input token!"
    echo "🪂 Exit."
    exit 1
fi

# shellcheck disable=SC2162
read -p "🧂 Please enter salt hash if exists. If not - press Enter - it will be generated: " SALT  < /dev/tty
if [ -z "$SALT" ]; then
    SALT=$(openssl rand -hex 32)
    echo "💚🧂 Generated random salt: $SALT"
fi


if [[ -z "$TG_TOKEN" || -z "$SALT" ]]; then
  echo "🚫 TG_TOKEN and SALT must be set."
  echo "🪂 Exit."
  exit 1
fi

# Write to .env file
echo -e "TG_TOKEN='$TG_TOKEN'\nSALT='$SALT'" > .env

# Confirm that the file has been written
echo "💚🖌 .env file has been created with TG_TOKEN and SALT."


SERVICE_FILE_NAME=""
if [ "$OS" == "Linux" ]; then
  DEMON_CONTENT=$(curl -sL https://andrewalevin.github.io/ytb2audiobot/template-ytb2audiobot.service)
  SERVICE_FILE_NAME="ytb2audiobot.service"
  echo -e "${DEMON_CONTENT//\ROOT_DIR/$(pwd)}" > "$SERVICE_FILE_NAME"

elif [ "$OS" == "Darwin" ]; then
  DEMON_CONTENT=$(curl -sL https://andrewalevin.github.io/ytb2audiobot/template-com.andrewlevin.ytb2audiobot.plist)
  SERVICE_FILE_NAME="com.andrewlevin.ytb2audiobot.plist"
  echo -e "${DEMON_CONTENT//\ROOT_DIR/$(pwd)}" > "$SERVICE_FILE_NAME"
fi
echo "💚📝 Service file successfully generated: $SERVICE_FILE_NAME"


if ! confirm "🚀 Set service, enable and start service unit?"; then
  echo "🖐 Exiting."
  exit 0
fi

echo "⚙️ Setting and starting service unit ..."
if [ "$OS" == "Linux" ]; then
  sudo cp "$SERVICE_FILE_NAME" "/etc/systemd/system/$SERVICE_FILE_NAME"
  sudo systemctl daemon-reload
  sudo systemctl enable   "$SERVICE_FILE_NAME"
  sudo systemctl start    "$SERVICE_FILE_NAME"
  sudo systemctl status   "$SERVICE_FILE_NAME"

elif [ "$OS" == "Darwin" ]; then
  RES=$(plutil -lint "$SERVICE_FILE_NAME")
  if ! echo "$RES" | grep -q "OK"; then
    echo "🚫 The plist file is not valid. Please check the following details:"
    echo "$RES"
    echo "🪂 Exit."
    exit 1
  fi

  cp "$SERVICE_FILE_NAME" "$HOME/Library/LaunchAgents/$SERVICE_FILE_NAME"
  launchctl unload "$SERVICE_FILE_NAME"
  launchctl load "$SERVICE_FILE_NAME"
fi

echo "💚 Installation completed successfully!"





