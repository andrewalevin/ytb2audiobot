FROM python

WORKDIR /app

RUN apt-get update

RUN apt-get install ffmpeg -y

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --upgrade ytb2audiobot

COPY docker-runner-bot.sh /app/docker-runner-bot.sh

RUN chmod +x /app/docker-runner-bot.sh

CMD ["/usr/bin/bash", "/app/docker-runner-bot.sh"]

