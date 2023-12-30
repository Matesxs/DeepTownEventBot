FROM python:3.10.5-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

VOLUME /bot
WORKDIR /bot

RUN apt-get update && apt-get upgrade -y && apt-get install build-essential libffi-dev libpq-dev git -y
RUN /usr/local/bin/python -m pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt --user
RUN apt-get --purge remove build-essential -y
RUN git config --global --add safe.directory /bot

COPY . .

ENTRYPOINT [ "python3", "bot.py" ]
