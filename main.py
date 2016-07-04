# -*- coding: utf-8 -*-
#! /usr/bin/env python

import logging
import requests
import sys
import datetime

from bs4 import BeautifulSoup
from telegram.ext import Updater, Handler, CommandHandler, MessageHandler
from telegram import ChatAction

from config import config

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    bot.sendMessage(update.message.chat_id, text='Traigo las cervezas, vosotros los telescopios. ¡Vamos allá!')


def help(bot, update):
    bot.sendMessage(update.message.chat_id, text="""Astro Beer Bot v1.0:
Para mostrar la APOD actual, escribe /apod y te la mostraré.
                    """)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


# This is were the fun begins
def apod(bot, update):
    apod = requests.get('http://apod.nasa.gov/apod/astropix.html')
    if apod.status_code > 299:
        bot.sendMessage(update.message.chat_id, text='La NASA esta como las grecas, así que no hay APOD.')
        return

    soup = BeautifulSoup(apod.text, 'html.parser')
    img_url = 'http://apod.nasa.gov/'
    img_url += soup.find_all('img')[0]['src']
    meta = "Astronomy Picture of the Day"
    for tag in soup.find_all('meta'):
        if tag['name'] == 'keywords':
            meta = tag['content']

    print(img_url)
    print(meta)

    bot.sendMessage(update.message.chat_id, text=meta)
    bot.sendChatAction(update.message.chat_id, action=ChatAction.UPLOAD_PHOTO)
    bot.sendPhoto(update.message.chat_id, photo=img_url)


def tiempo(bot, update):
    appkey = config.get('OWM')
    if not appkey:
        bot.sendMessage(update.message.chat_id, text='Deja la cerveza y configura el servicio de OWM.')
        return

    # TODO: Accept parameters on this call
    city = None

    if not city:
        city = "Madrid,ES"

    params = {"q": city, "APPID": appkey, "units": "metric"}

    weatherdata = requests.get('http://api.openweathermap.org/data/2.5/forecast/city', params=params)
    if "list" in weatherdata.json():
        weather = weatherdata.json()['list']
        today = datetime.datetime.now()
        tonight = None
        for element in weather:
            forecast_time = datetime.datetime.fromtimestamp(element['dt'])
            if forecast_time.month == today.month and forecast_time.day == today.day and forecast_time.hour >= 23:
                tonight = element

        if not tonight:
            weather_message = 'Asómate a la ventana, o sal del bar, que ya es de noche'

        else:
            weather_message = "Esta noche tendremos unos {0}º con una humedad relativa de {1}%, ".format(tonight['main']['temp'],
                                                                                                          tonight['main']['humidity'])
            weather_message += "vientos de {0} km\\h y una cobertura de nubes del {1}%".format(tonight['wind']['speed'],
                                                                                               tonight['clouds']['all'])

    else:
        weather_message = 'El meteorólogo anda chuzo, así que no sabe de chuzos de punta'

    bot.sendMessage(update.message.chat_id, text=weather_message)


def main():
    token = config.get('TOKEN')

    if token is None:
        print("Please, configure your token first")
        sys.exit(1)

    updater = Updater(token)
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("apod", apod))
    dispatcher.add_handler(CommandHandler("tiempo", tiempo))

    # log all errors
    dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    print("Starting AstroBeerBot")
    main()
