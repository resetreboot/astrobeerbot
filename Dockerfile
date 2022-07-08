# Astrobeerbot docker file
FROM python:3.8-alpine

RUN mkdir /astrobeerbot

RUN apk add --no-cache git alpine-sdk
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools
RUN git clone https://github.com/resetreboot/astrobeerbot.git /astrobeerbot
RUN pip3 install -r /astrobeerbot/requirements.txt
COPY config.py /astrobeerbot/config.py
COPY run_bot.sh /run_bot.sh

ENTRYPOINT ["/bin/sh", "run_bot.sh", "/astrobeerbot"]
