FROM python:slim

WORKDIR /app

RUN apt-get update

RUN apt-get install ffmpeg -y

RUN pip install ytb2audiobot>=2.604

RUN pip list

ENV PYTHONUNBUFFERED=1

CMD ["ytb2audiobot"]
