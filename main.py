# -*- coding: utf-8 -*-
#! /usr/bin/env python

import logging
import requests
import sys
import datetime
import random

from bs4 import BeautifulSoup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ChatAction

from config import config

# Constants
WEEKDAYS = {
    1: "lunes",
    2: "martes",
    3: "miércoles",
    4: "jueves",
    5: "viernes",
    6: "sábado",
    7: "domingo"
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
Si usas /faselunar te diré qué fase lunar tenemos hoy.
Para ver las manchas solares, /manchas te mostrará el sol actualizado.
                    """)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


# This is were the fun begins
def apod(bot, update):
    apod_key = config.get('APOD', 'DEMO_KEY')
    payload = {'api_key': apod_key}
    apod = requests.get('https://api.nasa.gov/planetary/apod', params=payload)
    if apod.status_code > 299:
        bot.sendMessage(update.message.chat_id, text='La NASA esta como las grecas, así que no hay APOD.')
        return

    data = apod.json()
    img_url = data['url']
    title = data['title']
    description = data['explanation']

    bot.sendMessage(update.message.chat_id, text=title)
    bot.sendChatAction(update.message.chat_id, action=ChatAction.UPLOAD_PHOTO)
    bot.sendPhoto(update.message.chat_id, photo=img_url)
    bot.sendMessage(update.message.chat_id, text=description)


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
        for day in range(0, 5):
            if day > 0:
                current_day = today + datetime.timedelta(days=day)
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
                if night and night['main']:
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


def faselunar(bot, update):
    fases = [
        "nueva 🌑",
        "creciente 🌒",
        "cuarto creciente 🌓",
        "creciente gibosa 🌔",
        "llena 🌕",
        "gibosa menguante 🌖",
        "cuarto menguante 🌗",
        "menguante 🌘"
    ]
    today = datetime.datetime.now()
    year = today.year
    month = today.month
    day = today.day

    if month < 3:
        year -= 1
        month += 12

    month += 1
    c = 365.25 * year
    e = 30.6 * month    # Blame C coders saving on characters...
    jd = c + e + day - 694039.09
    jd /= 29.53
    jd -= round(jd)
    b = (jd * 8) + 0.5
    b = int(b % 7)

    message = "Hoy tenemos luna " + fases[b]
    bot.sendMessage(update.message.chat_id, text=message)


def manchas(bot, update):
    soho = requests.get('http://sohowww.nascom.nasa.gov/sunspots/')
    if soho.status_code > 299:
        bot.sendMessage(update.message.chat_id, text='La NASA esta como las grecas, así que no hay SOHO.')
        return

    soup = BeautifulSoup(soho.text, 'html.parser')
    img_url = None

    for tag in soup.find_all('img'):
        if 'synoptic' in tag['src']:
            img_url = 'http://sohowww.nascom.nasa.gov' + tag['src']

    bot.sendChatAction(update.message.chat_id, action=ChatAction.UPLOAD_PHOTO)
    bot.sendPhoto(update.message.chat_id, photo=img_url)


def randomchat(bot, update):
    msg = update.message.text.lower()

    if "jawa" in msg:
        reply = random.choice([
            "Y un objetivo de regalo.",
            "Te lo dejo a mitad de precio, porque la caja está abierta.",
            "Hombre, es un poco básico este ocular de 9mm de 70 euros.",
            "Sólo se ha usado una vez",
            "Tengo stock de sobra",
            "Estos los estoy vendiendo muy bien"
        ])

    bot.sendMessage(update.message.chat_id, text=reply)


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
    dispatcher.add_handler(CommandHandler("faselunar", faselunar))
    dispatcher.add_handler(CommandHandler("manchas", manchas))

    # on noncommand i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler([Filters.text], randomchat))

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
