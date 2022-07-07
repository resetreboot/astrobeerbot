# Astrobeerbot docker file
FROM alpine:latest

RUN mkdir /astrobeerbot

RUN apk add python3 git py3-pip
RUN pip3 install --upgrade pip
RUN git clone https://github.com/resetreboot/astrobeerbot.git /astrobeerbot
RUN pip3 install -r /astrobeerbot/requirements.txt
COPY config.py /astrobeerbot/config.py
COPY run_bot.sh /run_bot.sh

ENTRYPOINT ["/bin/sh", "run_bot.sh", "/astrobeerbot"]
