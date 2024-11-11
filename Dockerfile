FROM python

WORKDIR /app

RUN apt-get update

RUN apt-get install ffmpeg -y

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --upgrade ytb2audiobot

RUN pwd

RUN ls -lha

COPY docker-run.sh docker-run.sh

RUN "🟢🔵🟣 After COPY"

RUN ls -lha

CMD ["docker-run-bot.sh"]


