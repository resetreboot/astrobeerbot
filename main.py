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

# Constants
WEEKDAYS = {
    "1": "lunes",
    "2": "martes",
    "3": "miércoles",
    "4": "jueves",
    "5": "viernes",
    "6": "sábado",
    "7": "domingo"
}

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
Con /tiempo te diré qué tal se presenta el tiempo esta misma noche.
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
        current_day = today
        for day in range(0, 4):
            if day > 0:
                current_day += datetime.timedelta(days=day)
                if current_day.hour > 23:
                    current_day -= datetime.timedelta(hours=4)

                if day == 1:
                    date_string = "Mañana por la noche"

                else:
                    date_string = "El {0} por la noche".format(WEEKDAYS[current_day.isoweekday()])

            else:
                date_string = "Esta noche"

            night = None
            for element in weather:
                forecast_time = datetime.datetime.fromtimestamp(element['dt'])
                if forecast_time.month == current_day.month and forecast_time.day == current_day.day and forecast_time.hour >= 23:
                    night = element

            if not night and day == 0:
                weather_message = 'Asómate a la ventana, o sal del bar, que ya es de noche'

            else:
                weather_message = date_string + " tendremos unos {0}º con una humedad relativa de {1}%, ".format(night['main']['temp'],
                                                                                                                 night['main']['humidity'])

                if night['wind']:
                    weather_message += "vientos de {0} km\\h y una cobertura de nubes del {1}%".format(night['wind']['speed'],
                                                                                                       night['clouds']['all'])

                else:
                    weather_message += "sin vientos y con una cobertura de nubes del {0}%".format(night['clouds']['all'])

            bot.sendMessage(update.message.chat_id, text=weather_message)

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
