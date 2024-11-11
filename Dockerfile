FROM python

WORKDIR /app

RUN apt-get update

RUN apt-get install ffmpeg -y

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --upgrade ytb2audiobot

COPY docker-run.sh docker-run.sh

RUN chmod +x docker-run-bot.sh

CMD ["docker-run-bot.sh"]


