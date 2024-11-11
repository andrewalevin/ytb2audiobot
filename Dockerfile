FROM python

WORKDIR /app

RUN apt-get update

RUN apt-get install ffmpeg -y

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --upgrade ytb2audiobot

RUN pwd

RUN ls -lha

COPY docker-run.sh /app/docker-run.sh

RUN echo "🟢🔵🟣 After COPY"

RUN ls -lha

CMD ["/app/docker-run-bot.sh"]


