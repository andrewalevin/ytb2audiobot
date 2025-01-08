FROM python

WORKDIR /app

# Update and install necessary dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    gnupg2 \
    lsb-release

# Install Node.js and npm
RUN curl -sL https://deb.nodesource.com/setup_current.x | sh - \
    && apt-get install -y nodejs

# Update npm to the latest version
RUN npm install -g npm@latest

# Install vot-cli globally using npm
RUN npm install -g vot-cli

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --upgrade ytb2audiobot

RUN pip install --no-cache-dir  pydub

COPY docker-runner-bot.sh /app/docker-runner-bot.sh

RUN chmod +x /app/docker-runner-bot.sh

CMD ["/usr/bin/bash", "/app/docker-runner-bot.sh"]


