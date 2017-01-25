# -*- coding: utf-8 -*-
# ! /usr/bin/env python

import logging
import requests
import sys
import datetime
import random

from bs4 import BeautifulSoup
from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters)
from telegram.ext.jobqueue import Job
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

autoapods = dict()


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    bot.sendMessage(update.message.chat_id, text='Traigo las cervezas, vosotros los telescopios. ¡Vamos allá!')


def help(bot, update):
    bot.sendMessage(update.message.chat_id, text="""Astro Beer Bot v1.0:
Para mostrar la APOD actual, escribe /apod y te la mostraré, con /autoapod la programo para traerla todos los días.
Con /tiempo te diré qué tal se presenta el tiempo esta misma noche.
Si usas /faselunar te diré qué fase lunar tenemos hoy.
Para ver las manchas solares, /manchas te mostrará el sol actualizado.
El comando /estanoche te dirá qué tal están los parámetros de tiempo específicos para astrónomos esta noche.
                    """)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


# This is were the fun begins
def fetch_apod(bot, chat_id):
    apod_key = config.get('APOD', 'DEMO_KEY')
    payload = {'api_key': apod_key}
    apod = requests.get('https://api.nasa.gov/planetary/apod', params=payload)
    if apod.status_code > 299:
        bot.sendMessage(chat_id, text='La NASA esta como las grecas, así que no hay APOD.')
        return

    data = apod.json()
    img_url = data['url']
    title = data['title']
    description = data['explanation']

    bot.sendMessage(chat_id, text=title)
    if data['media_type'] == 'image':
        bot.sendChatAction(chat_id, action=ChatAction.UPLOAD_PHOTO)
        bot.sendPhoto(chat_id, photo=img_url)

    else:
        bot.sendMessage(chat_id, text=img_url)

    bot.sendMessage(chat_id, text=description)


def apod(bot, update):
    fetch_apod(bot, update.message.chat_id)


def autoapod_job(bot, job):
    fetch_apod(bot, job.context)


def autoapod(bot, update, job_queue):
    chat_id = update.message.chat_id    # Remember the channel where the command came from
    if chat_id in autoapods:
        old_job = autoapods[chat_id]
        old_job.schedule_removal()

    job = Job(autoapod_job, 3600*24, repeat=True, context=chat_id)
    autoapods[chat_id] = job
    job_queue.put(job)

    bot.sendMessage(chat_id, text="APOD automática activada, cada día a esta hora os la traigo. ¿Una cervecita para celebrarlo?")


def stopautoapod(bot, update):
    chat_id = update.message.chat_id

    if chat_id in autoapods:
        job = autoapods[chat_id]
        job.schedule_removal()
        del autoapods[chat_id]

    else:
        bot.sendMessage(chat_id, text="No hay nada programado, astropirado.")


def tiempo(bot, update, args):
    appkey = config.get('OWM')
    if not appkey:
        bot.sendMessage(update.message.chat_id, text='Deja la cerveza y configura el servicio de OWM.')
        return

    # Now we accept parameters on this call
    city = " ".join(args)

    if not city:
        city = "Madrid"

    params = {"q": city.lower(), "APPID": appkey, "units": "metric"}

    weather_message = "A alguien se le ha pirado (jeje) la perola y no me ha dicho lo que tengo que contaros..."

    weatherdata = requests.get('http://api.openweathermap.org/data/2.5/forecast/city', params=params)
    if "list" in weatherdata.json():
        weather = weatherdata.json()['list']
        today = datetime.datetime.now()
        current_day = today
        weather_message = "El tiempo en los próximos días:\n"
        for day in range(0, 5):
            if day > 0:
                current_day = today + datetime.timedelta(days=day)
                if current_day.hour > 23:
                    current_day -= datetime.timedelta(hours=4)

                if day == 1:
                    date_string = "Mañana por la noche en " + city

                else:
                    date_string = "El {0} por la noche en ".format(WEEKDAYS[current_day.isoweekday()]) + city

            else:
                date_string = "Esta noche en " + city

            night = None
            for element in weather:
                forecast_time = datetime.datetime.fromtimestamp(element['dt'])
                if forecast_time.month == current_day.month and forecast_time.day == current_day.day and (forecast_time.hour >= 23 or forecast_time.hour <= 4):
                    night = element
                    break

            if not night and day == 0:
                weather_message += "Asómate a la ventana, o sal del bar, que ya es de noche.\n"

            else:
                if night and night['main']:
                    weather_message += date_string + " tendremos unos {0}º con una humedad relativa de {1}%, ".format(
                        night['main']['temp'],
                        night['main']['humidity'])

                    if night['wind']:
                        weather_message += "vientos de {0} km\\h y una cobertura de nubes del {1}%".format(
                            night['wind']['speed'],
                            night['clouds']['all'])

                    else:
                        weather_message += "sin vientos y con una cobertura de nubes del {0}%".format(
                            night['clouds']['all'])

                    weather_message += "\n"

                else:
                    print("Main not found: {}".format(night))

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
    e = 30.6 * month  # Blame C coders saving on characters...
    jd = c + e + day - 694039.09
    jd /= 29.53
    jd -= round(jd)
    b = (jd * 8) + 0.5
    b = int(b % 7)

    message = "Hoy tenemos luna " + fases[b]
    bot.sendMessage(update.message.chat_id, text=message)


def manchas(bot, update):
    soho = requests.get('https://sohowww.nascom.nasa.gov/sunspots/', verify=False)
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
    reply = None

    if "jawa" in msg:
        reply = random.choice([
            "Y un objetivo de regalo.",
            "Te lo dejo a mitad de precio, porque la caja está abierta.",
            "Hombre, es un poco básico este ocular de 9mm de 70 euros.",
            "Sólo se ha usado una vez",
            "Tengo stock de sobra",
            "Estos los estoy vendiendo muy bien"
        ])

    if reply is not None:
        bot.sendMessage(update.message.chat_id, text=reply)


def estanoche(bot, update):
    # Initalize coordinates
    lon = None
    lat = None

    # TODO pass location as argument an resolve coordinates

    if not lon or not lat:
        # Yeah, Robledo de Chavela coordinates by default
        lat = 40.498333
        lon = -4.238889

    # Building URL to query the service
    url_service = 'http://202.127.24.18/bin/astro.php'
    url_params = {'lon': str(lon), 'lat': str(lat), 'output': "json", 'tzshift': "0", 'unit': "metric", 'ac': "0"}

    # Query service
    timer7 = requests.get(url_service, params=url_params)
    if timer7.status_code > 299:
        bot.sendMessage(update.message.chat_id, text='Servicio de informacion astronómica esta a por uvas. Relax')
        return

    json_timer7 = timer7.json()

    timer7_data = json_timer7["dataseries"][1]
    timer7_cloud = timer7_data["cloudcover"]
    timer7_seeing = timer7_data["seeing"]
    timer7_transparency = timer7_data["transparency"]
    timer7_temp = timer7_data["temp2m"]
    timer7_precipitation = timer7_data["prec_type"]

    # Conditions where observation is imposible: 100% cloud or rain
    if timer7_precipitation == "rain":
        bot.sendMessage(update.message.chat_id, text='Esta noche llueve en Base Alfa, deja el telescopio en casa.')
        return
    if timer7_cloud > 5:
        bot.sendMessage(update.message.chat_id, text='Demasiado nublado en Base Alfa para hacer observación.')
        return

    # Compose messages about clouds
    if 3 < timer7_cloud < 5:
        mensaje_cloud = " habrá bastantes nubes"
    elif 3 > timer7_cloud > 1:
        mensaje_cloud = " habrá pocas nubes"
    elif timer7_cloud == 1:
        mensaje_cloud = " habrá cielo despejado"

    # Compose messages about seeing
    if timer7_seeing > 6:
        mensaje_seeing = " insuficiente seeing"
    elif 6 >= timer7_seeing > 4:
        mensaje_seeing = " bastante poco seeing"
    elif 4 >= timer7_seeing > 2:
        mensaje_seeing = " seeing bastante aceptable"
    elif 2 >= timer7_seeing > 0:
        mensaje_seeing = " seeing estupendo"

    # Compose messages about transparency
    if timer7_transparency > 6:
        mensaje_transparency = " insuficiente transparencia atmosferica"
    elif 6 >= timer7_transparency > 4:
        mensaje_transparency = " bastante poca transparencia atmosferica"
    elif 4 >= timer7_transparency > 2:
        mensaje_transparency = " transparencia atmosferica bastante aceptable"
    elif 2 >= timer7_transparency > 0:
        mensaje_transparency = " transparencia atmosferica estupenda"

    # Message about temperature
    mensaje_temp = " y una temperatura de " + str(timer7_temp) + " grados celsius (via timer7)"

    # Now compose full message
    mensaje = "(6h) Esta noche en Robledo de Chavela" + mensaje_cloud + "," + mensaje_seeing + "," + mensaje_transparency + mensaje_temp

    # Vomit the response
    bot.sendMessage(update.message.chat_id, text=mensaje)
    return


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
    dispatcher.add_handler(CommandHandler("autoapod", autoapod, pass_job_queue=True))
    dispatcher.add_handler(CommandHandler("stopautoapod", stopautoapod, pass_job_queue=True))
    dispatcher.add_handler(CommandHandler("tiempo", tiempo, pass_args=True))
    dispatcher.add_handler(CommandHandler("faselunar", faselunar))
    dispatcher.add_handler(CommandHandler("manchas", manchas))
    dispatcher.add_handler(CommandHandler("estanoche", estanoche))

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
