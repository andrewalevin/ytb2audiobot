FROM python:slim

WORKDIR /app

RUN apt-get update

RUN apt-get install ffmpeg -y

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --upgrade ytb2audiobot

CMD ["ytb2audiobot"]
