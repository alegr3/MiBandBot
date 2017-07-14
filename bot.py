#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This is an activity bot using decorators and webhook with flask
import os
import re
import sys
import time
from datetime import datetime
import json
import httplib2
from oauth2client import client
from apiclient.discovery import build
from oauth2client.file import Storage
from telebot import types

import socket

import flask
import telebot
import logging

API_TOKEN = '' # Telegram Bot's Token (fill this value with your own token)

WEBHOOK_HOST = '' # Fill with a the Server FQDN that is the same FQDN used to generate SSL certificates
WEBHOOK_PORT =   # 443, 80, 88 or 8443 (port need to be 'open')
# In some VPS you may need to put here the IP addr
WEBHOOK_LISTEN = '0.0.0.0' # Change to 0.0.0.0 in Virtual Machines

LOGSTASH_HOST = '127.0.0.1'
LOGSTASH_PORT = 5044

# Self-signed certificate
WEBHOOK_SSL_CERT = '/usr/lib64/python2.7/site-packages/mibandbot/webhookutiles/webhook.pem'  # Path of Webhook SSL Certificate
WEBHOOK_SSL_PRIV = '/usr/lib64/python2.7/site-packages/mibandbot/webhookutiles/webhook.key'  # Path of Webhook SSL private key

# Quick'n'dirty SSL certificate generation:
#
# openssl genrsa -out webhook_pkey.pem 2048
# openssl req -new -x509 -days 3650 -key webhook_key.pem -out webhook_cert.pem
#
# When asked for "Common Name (e.g. server FQDN or YOUR name)" you should reply
# with the same value in you put in WEBHOOK_HOST

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % (API_TOKEN)

#########################
##  Information of Bot ##
#########################

# This is the path where the certificates should be
CREDENTIALS_PATH = "/usr/lib64/python2.7/site-packages/mibandbot/credentials/"
# File that contains Google credentials of desired application (Google Fit in this case)
CLIENT_SECRETS = 'client_secrets_web.json'

# Scope of GoogleAPI (Fitness Data in ReadOnly mode)
OAUTH_SCOPE = ['https://www.googleapis.com/auth/fitness.activity.read','https://www.googleapis.com/auth/fitness.body.read']

# IP where the OAuth Server sends the code to authenticate a Google Account (A HTTP Server in our server that is waiting for the code)
REDIRECT_URI = '' # Fill with your redirect server URI

# DataSource for Steps
DATA_SOURCE_STEP = "raw:com.google.step_count.delta:com.xiaomi.hm.health:"
# DataSource for Calories
DATA_SOURCE_CALORIES = "raw:com.google.calories.expended:com.xiaomi.hm.health:"
# DataSource for activity
DATA_SOURCE_SLEEP = "raw:com.google.activity.segment:com.xiaomi.hm.health:"

# Path to store logs of the Bot
LOG_FILE_PATH = '/var/tmp/MiBand.log'

#########################
#########################

# Starts the logger and set the logger level to INFO (Info messages + Debug + Errors)
logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

# Starts a bot instance
bot = telebot.TeleBot(API_TOKEN)
app = flask.Flask(__name__)

# Flow to comunicate with GoogleAPI
fitness_service = None

##########################
## OAuth Authentication ##
##########################
flow = client.flow_from_clientsecrets(CLIENT_SECRETS,
                                      scope = OAUTH_SCOPE,
                                      redirect_uri = REDIRECT_URI)
flow.params['access_type'] = 'offline'
auth_uri = flow.step1_get_authorize_url()
http = httplib2.Http()

##########################
##########################

# Returns the StartTime and EndTime to retrieve a DataSet of GoogleAPI
def getDataSetId(daysAgo):
    startingDay = int(daysAgo)*86400
    ahoraAyerNano = int((time.time() - startingDay) * 1e9)
    ahoraNano = int((time.time() + 3600) * 1e9)
    return '%d-%d' % (ahoraAyerNano, ahoraNano)

# Method that authenticate users on GoogleAPI
def authenticate(code):
    global fitness_service, cid
    storage = Storage("%s%dcredentials.json" % (CREDENTIALS_PATH, cid))
    credentials = flow.step2_exchange(code)
    storage.put(credentials)
    http_auth = credentials.authorize(http)
    fitness_service = build('fitness', 'v1', http=http_auth)
    bot.send_message(cid,
                     "Tu código se ha recibido correctamente.\n\n"
                     "A partir de ahora puede consultar sus datos de actividad como pasos diarios (/pasos), calorías quemadas (/calorias) o el tiempo que ha descansado (/dormir).")

# Method that sends DataSet data to Logstash
def json_to_logstash(chat_id, hourStart, dateStart, hourEnd, dateEnd, fitness_type, value, duration):
    data = "%s %s %s %s %d %d FINAL pacient/%d xiaomi_mi_band %s" % (dateStart, hourStart, dateEnd, hourEnd, duration, value, chat_id, fitness_type)
    print data

    msg = {'@message': data, '@tags': ['python']}
    #print msg

    try:
        #print "llego al socket.socket"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error, msg:
        print ("[ERROR] %s\n" % msg[1])

    try:
        #print "llego al sock.connect"
        #print "%s:%s" %(LOGSTASH_HOST, LOGSTASH_PORT)
        sock.connect((LOGSTASH_HOST, LOGSTASH_PORT))
    except socket.error, msg:
        print ("[ERROR] %s\n" % msg[1])

    sock.send(data)
    sock.close()

# Method that generates an image from Kibana (Steps, Calories or Activity)
def generateImageFromKibana(chat_id, startTimestamp, endTimestamp, jsFile):
    print "generando imagen"
    ip = "mibandbot.myddns.me"
    print "start: %s" %(str(startTimestamp))
    print "end: %s" %(str(endTimestamp))
    chat_id = "pacient/" + str(chat_id)
    #print chat_id
    url = re.escape("http://" + ip + "/app/kibana#/dashboard/Mi-Band-Dashboard?_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:'" + str(startTimestamp) + "',mode:quick,to:'" + str(endTimestamp) + "'))&_a=(filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:tbot_test,key:subject,negate:!f,value:'" + str(chat_id) + "'),query:(match:(subject:(query:" + str(chat_id) + ",type:phrase))))),options:(darkTheme:!f),panels:!((col:1,id:Mi-Band-Pasos,panelIndex:1,row:1,size_x:12,size_y:4,type:visualization),(col:1,id:Mi-Band-Calorias,panelIndex:2,row:5,size_x:12,size_y:4,type:visualization),(col:1,id:Mi-Band-Actividad,panelIndex:3,row:9,size_x:12,size_y:4,type:visualization)),query:(query_string:(analyze_wildcard:!t,query:'*')),title:'Mi%20Band%20Dashboard',uiState:(P-1:(vis:(legendOpen:!f)),P-2:(vis:(legendOpen:!f)),P-3:(vis:(legendOpen:!f))),vis:(aggs:!((params:(field:chat_id,orderBy:'2',size:20),schema:segment,type:terms),(id:'2',schema:metric,type:count)),type:histogram))&indexPattern=tbot_test&type=histogram")
    string_url = "http://" + ip + "/app/kibana#/dashboard/Mi-Band-Dashboard?_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:'" + str(startTimestamp) + "',mode:quick,to:'" + str(endTimestamp) + "'))&_a=(filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:tbot_test,key:subject,negate:!f,value:'" + str(chat_id) + "'),query:(match:(subject:(query:" + str(chat_id) + ",type:phrase))))),options:(darkTheme:!f),panels:!((col:1,id:Mi-Band-Pasos,panelIndex:1,row:1,size_x:12,size_y:4,type:visualization),(col:1,id:Mi-Band-Calorias,panelIndex:2,row:5,size_x:12,size_y:4,type:visualization),(col:1,id:Mi-Band-Actividad,panelIndex:3,row:9,size_x:12,size_y:4,type:visualization)),query:(query_string:(analyze_wildcard:!t,query:'*')),title:'Mi%20Band%20Dashboard',uiState:(P-1:(vis:(legendOpen:!f)),P-2:(vis:(legendOpen:!f)),P-3:(vis:(legendOpen:!f))),vis:(aggs:!((params:(field:chat_id,orderBy:'2',size:20),schema:segment,type:terms),(id:'2',schema:metric,type:count)),type:histogram))&indexPattern=tbot_test&type=histogram"
    phamtonjs = 'phantomjs ' +jsFile+ ' ' + url
    os.system(phamtonjs)
    print "imagen generada"
    return string_url

# Calculate the time difference between two timestamps
def diff_time(startTimeDate, endTimeDate):
    diff = endTimeDate - startTimeDate
    seconds = diff.total_seconds()
    minutes = int(seconds) / 60
    hours = minutes / 60
    minutes = float(minutes) / 60.0 - float(hours)
    minutes = int(minutes * 60)

# Functions that retrieves steps, calories and acitivy from Google Database
def steps(cid, daysPeriod):
    global fitness_service,log
    totalSteps = 0
    text = ''
    http = httplib2.Http()
    startingDay = int(daysPeriod)*86400
    startTimeNano = int((time.time() - startingDay) * 1e9)
    startTS = datetime.fromtimestamp(startTimeNano // 1000000000)
    startTimeStamp = startTS.strftime('%Y-%m-%dT%H:%M:%SZ')
    endTimeNano = int((time.time() + 3600) * 1e9)
    endTS = datetime.fromtimestamp(endTimeNano // 1000000000)
    endTimeStamp = endTS.strftime('%Y-%m-%dT%H:%M:%SZ')
    storage = Storage("%s%dcredentials.json" % (CREDENTIALS_PATH, cid))
    credentials = storage.get()
    print "las credenciales son: " + str(credentials)

    if credentials:
        print "son invalidas?: " + str(credentials.invalid)
    if credentials is None:
        print "entro aqui"
        flow = client.flow_from_clientsecrets(CLIENT_SECRETS,
                                              scope=OAUTH_SCOPE,
                                              redirect_uri=REDIRECT_URI)
        auth_uri = flow.step1_get_authorize_url()
        text = 'No se pueden obtener unas credenciales recientes. Por favor, vuelve a autorizar los permisos de lectura de tus ' \
                       'datos deportivos de Google en la siguiente URL, por favor:\n'
        bot.send_message(cid, text + str(auth_uri))

    elif credentials.invalid:
        credentials.revoke(http)
        flow = client.flow_from_clientsecrets(CLIENT_SECRETS,
                                              scope=OAUTH_SCOPE,
                                              redirect_uri=REDIRECT_URI)
        auth_uri = flow.step1_get_authorize_url()
        text = 'Sus credenciales han expirado. Por favor, vuelve a autorizar los permisos de lectura de tus datos deportivos ' \
                       'de Google en la siguiente URL, por favor:\n'
        bot.send_message(cid, text + str(auth_uri))

    else:
        try:
            http_auth = credentials.authorize(http)
            #print credentials
            #print http_auth
            fitness_service = build('fitness', 'v1', http=http_auth)
            if daysPeriod == '1':
                text_totales = 'del dia'
            elif daysPeriod == '2':
                text_totales = 'de los dos últimos dias'
            elif daysPeriod == '7':
                text_totales = 'de la última semana'
            dataSetId = getDataSetId(daysPeriod)
            print dataSetId
            googleData = fitness_service.users().dataSources().datasets().get(userId='me',
                                                                              dataSourceId=DATA_SOURCE_STEP,
                                                                              datasetId=dataSetId).execute()

            print googleData

            dataSets = googleData.get('point')
            if dataSets:
                for dataSet in dataSets:
                    #print dataSet
                    step_value = dataSet['value']
                    start_value = dataSet['startTimeNanos']
                    startValue_int = int(start_value) + 3600*1e9
                    startTimeDate = datetime.fromtimestamp(startValue_int // 1000000000)
                    end_value = dataSet['endTimeNanos']
                    endValue_int = int(end_value) + 3600*1e9
                    endTimeDate = datetime.fromtimestamp(endValue_int // 1000000000)
                    steps = step_value.pop(0)
                    step_count = steps['intVal']
                    if step_count > 0:
                        totalSteps = totalSteps + step_count
                        text = text + "<i>%d pasos</i> (%s - %s)\n" \
                                      %(step_count, startTimeDate.strftime('%H:%M'), endTimeDate.strftime('%H:%M del día %d-%m-%Y'))
                        diff = endValue_int - startValue_int
                        duration = int((diff / (1e9 * 60)))
                        print "duration: %d" %(duration)
                        json_to_logstash(cid,
                                         startTimeDate.strftime('%H:%M:%S'),
                                         startTimeDate.strftime('%Y-%m-%d'),
                                         endTimeDate.strftime('%H:%M:%S'),
                                         endTimeDate.strftime('%Y-%m-%d'),
                                         'pasos',
                                         step_count,
                                         duration)
                url = generateImageFromKibana(cid, startTimeStamp, endTimeStamp, 'PasosPNG.js')
                if daysPeriod == '7':
                    text = "<b>Pasos totales %s: %d</b>\n\nPuede ver la gráfica dinámica en:\n\n%s" %(text_totales, totalSteps, url)
                else:
                    text = text +  "<b>Pasos totales %s: %d</b>\n\nPuede ver la gráfica dinámica en:\n%s" %(text_totales, totalSteps, url)
                log.info("[%d] Se envia mensaje al usuario 'Pasos totales del dia: %d'" %(cid, totalSteps))


                send_image(cid, 'Pasos.png')
                bot.send_message(cid, text, parse_mode="HTML")

            else:
                print "[%d] No hay información de dataSet disponible." %(cid)
                text = "No hay información de pasos disponible hoy."
                log.info('[%d] ' %(cid) + text)
                bot.send_message(cid, text)

        except Exception as e:
            print "[%d] Ha ocurrido un error: " %(cid, str(e))
            log.error('[%d] ' %(cid, str(e)))

def calories(cid, daysPeriod):
    global fitness_service, log
    text = ''
    dataSets = None
    totalCalories = 0
    http = httplib2.Http()
    startingDay = int(daysPeriod)*86400
    startTimeNano = int((time.time() - startingDay) * 1e9)
    startTS = datetime.fromtimestamp(startTimeNano // 1000000000)
    startTimeStamp = startTS.strftime('%Y-%m-%dT%H:%M:%SZ')
    endTimeNano = int((time.time() + 3600) * 1e9)
    endTS = datetime.fromtimestamp(endTimeNano // 1000000000)
    endTimeStamp = endTS.strftime('%Y-%m-%dT%H:%M:%SZ')
    storage = Storage("%s%dcredentials.json" % (CREDENTIALS_PATH, cid))
    credentials = storage.get()
    print "las credenciales son: " + str(credentials)

    if credentials:
        print "son invalidas?: " + str(credentials.invalid)
    if credentials is None:
        print "entro aqui"
        flow = client.flow_from_clientsecrets(CLIENT_SECRETS,
                                              scope=OAUTH_SCOPE,
                                              redirect_uri=REDIRECT_URI)
        auth_uri = flow.step1_get_authorize_url()
        text = 'No se pueden obtener unas credenciales recientes. Por favor, vuelve a autorizar los permisos de lectura de tus ' \
               'datos deportivos de Google en la siguiente URL, por favor:\n'
        cid = message.chat.id
        bot.send_message(cid, text + str(auth_uri))

    elif credentials.invalid:
        credentials.revoke(http)
        flow = client.flow_from_clientsecrets(CLIENT_SECRETS,
                                              scope=OAUTH_SCOPE,
                                              redirect_uri=REDIRECT_URI)
        auth_uri = flow.step1_get_authorize_url()
        text = 'Sus credenciales han expirado. Por favor, vuelve a autorizar los permisos de lectura de tus datos deportivos ' \
               'de Google en la siguiente URL, por favor:\n'
        bot.send_message(cid, text + str(auth_uri))
    else:
        try:
            http_auth = credentials.authorize(http)
            fitness_service = build('fitness', 'v1', http=http_auth)

	    if daysPeriod == '1':
                text_totales = 'hoy'
            elif daysPeriod == '2':
                text_totales = 'en los dos últimos dias'
            elif daysPeriod == '7':
                text_totales = 'en la última semana'
            dataSetId = getDataSetId(daysPeriod)
            googleData = fitness_service.users().dataSources().datasets().get(userId='me',
                                                                              dataSourceId=DATA_SOURCE_CALORIES,
                                                                              datasetId=dataSetId).execute()
            print googleData
            dataSets = googleData.get('point')
            print dataSets
            if dataSets:
                for dataSet in dataSets:
                    calories_value = dataSet['value']
                    start_value = dataSet['startTimeNanos']
                    startValue_int = long(start_value) + 3600*1e9
                    startTimeDate = datetime.fromtimestamp(startValue_int // 1000000000)
                    end_value = dataSet['endTimeNanos']
                    endValue_int = int(end_value) + 3600*1e9
                    endTimeDate = datetime.fromtimestamp(endValue_int // 1000000000)
                    calories = calories_value.pop(0)
                    calories_count = calories['fpVal']
                    diff = endValue_int - startValue_int
                    duration = int((diff / (1e9 * 60)))
                    print "duration: %d" % (duration)
                    json_to_logstash(cid,
                                     startTimeDate.strftime('%H:%M:%S'),
                                     startTimeDate.strftime('%Y-%m-%d'),
                                     endTimeDate.strftime('%H:%M:%S'),
                                     endTimeDate.strftime('%Y-%m-%d'),
                                     'calorias',
                                     calories_count,
                                     duration)
                    totalCalories = totalCalories + calories_count
                    text = text + "<i>%d cal. (%s - %s)</i>\n" \
                                  % (calories_count, startTimeDate.strftime('%H:%M'), endTimeDate.strftime('%H:%M del día %d-%m-%Y'))
                url = generateImageFromKibana(cid, startTimeStamp, endTimeStamp, 'CaloriasPNG.js')
                if daysPeriod == '7':
                    text = "<b>Calorias totales consumidas %s: %d</b>\n\nPuede ver la gráfica dinámica en:\n\n%s" %(text_totales, totalCalories, url)
                else:
                    text = text + "<b>Calorias totales consumidas %s: %d</b>\n\nPuede ver la gráfica dinámica en:\n%s" %(text_totales, totalCalories, url)
                log.info("[%d] Se envia mensaje al usuario 'Calorias totales consumidas hoy: %d'" %(cid, totalCalories))

                send_image(cid, 'Calorias.png')
                bot.send_message(cid, text,parse_mode="HTML")
            else:
                print "[%d] No hay información de dataSet disponible." %(cid)
                text = "No hay información de calorías disponible hoy."
                log.info("[%d] Se envia mensaje al usuario 'No hay informacion de calorias disponible hoy'" %(cid))
                bot.send_message(cid, text)

        except Exception as e:
            print "[%d] Ha ocurrido un error: %s" %(cid, str(e))
            log.error('[%d] %s" ' %(cid, str(e)))

def activity(cid, daysPeriod):
    global fitness_service, log
    primerSegmento = True
    text = ''
    end_sleep_value_ligero = 0
    end_sleep_value_profundo = 0
    total_sueno_profundo = 0
    total_sueno_ligero = 0
    total_andando = 0
    total_tiempo_despierto = 0
    http = httplib2.Http()
    startingDay = int(daysPeriod)*86400
    startTimeNano = int((time.time() - startingDay) * 1e9)
    startTS = datetime.fromtimestamp(startTimeNano // 1000000000)
    startTimeStamp = startTS.strftime('%Y-%m-%dT%H:%M:%SZ')
    endTimeNano = int((time.time() + 3600) * 1e9)
    endTS = datetime.fromtimestamp(endTimeNano // 1000000000)
    endTimeStamp = endTS.strftime('%Y-%m-%dT%H:%M:%SZ')

    storage = Storage("%s%dcredentials.json" % (CREDENTIALS_PATH, cid))
    credentials = storage.get()
    print "las credenciales son: " + str(credentials)

    if credentials:
        print "son invalidas?: " + str(credentials.invalid)
    if credentials is None:
        print "entro aqui"
        flow = client.flow_from_clientsecrets(CLIENT_SECRETS,
                                              scope=OAUTH_SCOPE,
                                              redirect_uri=REDIRECT_URI)
        auth_uri = flow.step1_get_authorize_url()
        text = 'No se pueden obtener unas credenciales recientes. Por favor, vuelve a autorizar los permisos de lectura de tus ' \
               'datos deportivos de Google en la siguiente URL, por favor:\n'
        cid = message.chat.id
        bot.send_message(cid, text + str(auth_uri))

    elif credentials.invalid:
        credentials.revoke(http)
        flow = client.flow_from_clientsecrets(CLIENT_SECRETS,
                                              scope=OAUTH_SCOPE,
                                              redirect_uri=REDIRECT_URI)
        auth_uri = flow.step1_get_authorize_url()
        text = 'Sus credenciales han expirado. Por favor, vuelve a autorizar los permisos de lectura de tus datos deportivos ' \
               'de Google en la siguiente URL, por favor:\n'
        bot.send_message(cid, text + str(auth_uri))

    else:
        try:
            http_auth = credentials.authorize(http)
            fitness_service = build('fitness', 'v1', http=http_auth)

            if daysPeriod == '1':
                text_totales = 'Hoy'
            elif daysPeriod == '2':
                text_totales = 'En los últimos dos dias'
            elif daysPeriod == '7':
                text_totales = 'En la última semana'
            dataSetId = getDataSetId(daysPeriod)
            googleData = fitness_service.users().dataSources().datasets().get(userId='me',
                                                                              dataSourceId=DATA_SOURCE_SLEEP,
                                                                              datasetId=dataSetId).execute()
            dataSets = googleData.get('point')
            #print googleData
            if dataSets:
                for dataSet in dataSets:
                    tipo = ""
                    sleep_value = dataSet['value']
                    start_value_segmento = dataSet['startTimeNanos']
                    startValue_int = int(start_value_segmento) + 3600 * 1e9
                    startTimeDate_segmento = datetime.fromtimestamp(startValue_int // 1000000000)
                    sleep_data = sleep_value.pop(0)
                    sleep_count = sleep_data['intVal']
                    if sleep_count == 7:
                        tipo = "tiempo andando"
                        print "El segmento corresponde a tiempo despierto"
                        end_walking_value = dataSet['endTimeNanos']
                        endValue_segment_int = long(end_walking_value) + 3600 * 1e9
                        endTimeDate_segmento = datetime.fromtimestamp(endValue_segment_int // 1000000000)
                        diff_segment_despierto = endValue_segment_int - long(startValue_int)
                        total_andando = total_andando + diff_segment_despierto
                        diff = endValue_segment_int - startValue_int
                        duration = int((diff / (1e9 * 60)))
                        json_to_logstash(cid,
                                         startTimeDate_segmento.strftime('%H:%M:%S'),
                                         startTimeDate_segmento.strftime('%Y-%m-%d'),
                                         endTimeDate_segmento.strftime('%H:%M:%S'),
                                         endTimeDate_segmento.strftime('%Y-%m-%d'),
                                         'actividad(andando)',
                                         30,
                                         duration)

                    elif sleep_count == 109:
                        if primerSegmento:
                            primerSegmento = False
                            start_value = dataSet['startTimeNanos']
                            startValue_int = int(start_value) + 3600 * 1e9
                            startTimeDate_sleep = datetime.fromtimestamp(startValue_int // 1000000000)

                        tipo = "sueño ligero"
                        print "El segmento corresponde a sueño ligero"
                        end_sleep_value_ligero = dataSet['endTimeNanos']
                        endValue_segment_int = long(end_sleep_value_ligero) + 3600 * 1e9
                        endTimeDate_segmento = datetime.fromtimestamp(endValue_segment_int // 1000000000)
                        diff_segment_ligero = endValue_segment_int - long(startValue_int)
                        total_sueno_ligero = total_sueno_ligero + diff_segment_ligero
                        diff = endValue_segment_int - startValue_int
                        duration = int((diff / (1e9 * 60)))
                        json_to_logstash(cid,
                                         startTimeDate_segmento.strftime('%H:%M:%S'),
                                         startTimeDate_segmento.strftime('%Y-%m-%d'),
                                         endTimeDate_segmento.strftime('%H:%M:%S'),
                                         endTimeDate_segmento.strftime('%Y-%m-%d'),
                                         'actividad(ligero)',
                                         90,
                                         duration)

                    elif sleep_count == 110:
                        if primerSegmento:
                            primerSegmento = False
                            start_value = dataSet['startTimeNanos']
                            startValue_int = int(start_value) + 3600 * 1e9
                            startTimeDate_sleep = datetime.fromtimestamp(startValue_int // 1000000000)

                        tipo = "sueño profundo"
                        print "El segmento corresponde a sueño profundo"
                        end_sleep_value_profundo = dataSet['endTimeNanos']
                        endValue_segment_int = long(end_sleep_value_profundo) + 3600 * 1e9
                        endTimeDate_segmento = datetime.fromtimestamp(endValue_segment_int // 1000000000)
                        diff_segment_profundo = endValue_segment_int - long(startValue_int)
                        total_sueno_profundo = total_sueno_profundo + diff_segment_profundo
                        diff = endValue_segment_int - startValue_int
                        duration = int((diff / (1e9 * 60)))
                        json_to_logstash(cid,
                                         startTimeDate_segmento.strftime('%H:%M:%S'),
                                         startTimeDate_segmento.strftime('%Y-%m-%d'),
                                         endTimeDate_segmento.strftime('%H:%M:%S'),
                                         endTimeDate_segmento.strftime('%Y-%m-%d'),
                                         'actividad(profundo)',
                                         100,
                                         duration)

                    elif sleep_count == 112:
                        tipo = "tiempo DESPIERTO"
                        print "El segmento corresponde a tiempo despierto"
                        end_sleep_value_despierto = dataSet['endTimeNanos']
                        endValue_segment_int = long(end_sleep_value_despierto) + 3600 * 1e9
                        endTimeDate_segmento = datetime.fromtimestamp(endValue_segment_int // 1000000000)
                        diff_segment_despierto = endValue_segment_int - long(startValue_int)
                        total_tiempo_despierto = total_tiempo_despierto + diff_segment_despierto
                        diff = endValue_segment_int - startValue_int
                        duration = int((diff / (1e9 * 60)))
                        json_to_logstash(cid,
                                         startTimeDate_segmento.strftime('%H:%M:%S'),
                                         startTimeDate_segmento.strftime('%Y-%m-%d'),
                                         endTimeDate_segmento.strftime('%H:%M:%S'),
                                         endTimeDate_segmento.strftime('%Y-%m-%d'),
                                         'actividad(despierto)',
                                         10,
                                         duration)

                    diff_segment_date = endTimeDate_segmento - startTimeDate_segmento
                    seconds = diff_segment_date.total_seconds()
                    minutes = int(seconds) / 60
                    hours = minutes / 60
                    minutes = float(minutes) / 60.0 - float(hours)
                    minutes = int(minutes * 60)
                    if minutes < 10:
                        minutes = "0%d" %(minutes)
                    else:
                        minutes = str(minutes)
                    text = text + "<i>Segmento de %s: %d:%sh </i>\n " \
                                  "(%s - %s)\n\n" %(tipo, hours, minutes, startTimeDate_segmento.strftime('%H:%M'), endTimeDate_segmento.strftime('%H:%M del día %d-%m-%Y'))

                    #print text

                if end_sleep_value_ligero != 0 and end_sleep_value_profundo != 0:
                    print "ligero: " + str(end_sleep_value_ligero) + " y profundo: " + str(end_sleep_value_profundo)

                    if end_sleep_value_ligero >= end_sleep_value_profundo:
                        endValue_int = int(end_sleep_value_ligero) + 3600 * 1e9
                    else:
                        endValue_int = int(end_sleep_value_profundo) + 3600 * 1e9

                    endTimeDate_sleep = datetime.fromtimestamp(endValue_int // 1000000000)
                    awakeSeconds = int(total_tiempo_despierto) // 1e9
                    diff = endTimeDate_sleep - startTimeDate_sleep
                    seconds = diff.total_seconds() - awakeSeconds
                    minutes = int(seconds) / 60
                    hours = minutes / 60
                    minutes = float(minutes)/60.0-float(hours)
                    minutes = int(minutes*60)
                    if minutes < 10:
                        minutes = "0%d" %(minutes)
                    else:
                        minutes = str(minutes)
                    lightSleepTime = "\n - <b>Tiempo de sueño ligero: %d minutos</b>" %((total_sueno_ligero // 1e9) / 60)
                    deepSleepTime = "\n - <b>Tiempo de sueño profundo: %d minutos</b>" % ((total_sueno_profundo // 1e9) / 60)
                    awakeTime = "\n - Tiempo despierto: %d minutos" %(awakeSeconds / 60)
                    #restTime =  "%s ha descansado durante %d:%sh\n " \
                    #              "(Se acostó a las %sh y se levantó a las %sh)" \
                    #              %(text_totales, hours, minutes, startTimeDate_sleep.strftime("%H:%M"), endTimeDate_sleep.strftime("%H:%M"))
                    #text = text + restTime + lightSleepTime + deepSleepTime +  awakeTime
                    if daysPeriod == '7':
                    	text = lightSleepTime + deepSleepTime +  awakeTime
                    else:
                    	text = text + lightSleepTime + deepSleepTime +  awakeTime
                    log.info("[%d] Se envia mensaje al usuario '%s'" % (cid, text))

                else:
                    print "ligero y profundo = 0"
                url = generateImageFromKibana(cid, startTimeStamp, endTimeStamp, 'ActividadPNG.js')
                text = text + "\n\nPuede ver la gráfica dinámica en:\n%s" %(url)
                send_image(cid, 'Actividad.png')
                bot.send_message(cid, text, parse_mode="HTML")

            else:
                print "[%d] No hay información de dataSet disponible." %(cid)
                text = "No hay información de sueño disponible hoy."
                log.info("[%d] Se envia mensaje al usuario 'No hay informacion de sueño disponible hoy'" %(cid))
                bot.send_message(cid, text)
        except Exception as e:
            print "[%d] Ha ocurrido un error: " %(cid, str(e))
            log.error('[%d] %s' %(cid, str(e)))

# Empty webserver index, return nothing, just http 200
@app.route('/<path:code>', methods=['GET', 'HEAD'])
def index(code):
    authenticate(code)
    return ''

# Process webhook calls
@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    print 'Flask.request.headers:\n' + str(flask.request.headers)
    try:
	if flask.request.headers.get('content-type') == 'application/json':
	    json_string = flask.request.get_data()
	    update = telebot.types.Update.de_json(json_string)
	    #bot.process_new_messages([update.message])
            bot.process_new_updates([update])
	    print "JSON:\n" + str(json_string)
	    return ''
        else:
	    flask.abort(403)
    except Exception as e:
        print "Ha ocurrido una excepcion: " + str(e)
        #log.error(e)
        return ''

# Handle '/start' and '/help' commands
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    global fitness_service, credentials, http, cid, log
    cid = message.chat.id
    http = httplib2.Http()
    storage = Storage("%s%dcredentials.json" %(CREDENTIALS_PATH, cid))
    credentials = storage.get()
    welcome_text = 'Bienvenido a MiBandBot. Para empezar la configuración debes ingresar en la siguiente URL y habilitar los permisos ' \
                   'de lectura de tus datos deportivos de Google.\n'
    log.info('[%d] El usuario acaba de iniciar el bot' %(cid))
    bot.send_message(cid, welcome_text + str(auth_uri))

# Send image to the user
def send_image(cid, imageType):
    photo = open('/usr/lib64/python2.7/site-packages/mibandbot/'+imageType, 'rb')
    bot.send_photo(cid, photo)

# Handle '/teclado' to send custom keyboard
@bot.message_handler(commands=['teclado'])
def retrieve_commands(message):
    cid = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(u'\U0001F463' 'Pasos', u'\U00002764' 'Calorias', u'\U0001F4A4' 'Actividad')
    markup.row(u'\U00002753' 'Ayuda')
    bot.send_message(cid, "Custom Keyboard:", reply_markup=markup)

# Handle the custom keyboard steps, calories and activity buttons
@bot.message_handler(func=lambda message: True, content_types=['text'], regexp='Pasos')
def echo_message(message):
    cid = message.chat.id
    keyboard = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton(text='Hoy', callback_data="Pasos 1")
    btn2 = types.InlineKeyboardButton(text='Últimos 2 días', callback_data='Pasos 2')
    btn3 = types.InlineKeyboardButton(text='Última semana', callback_data='Pasos 7')
    keyboard.add(btn, btn2)
    keyboard.add(btn3)
    bot.send_message(cid, "¿De qué periodo quiere obtener los pasos?:", reply_markup=keyboard)
    print "[" + str(cid) + "]" + 'PASOS'

@bot.message_handler(func=lambda message: True, content_types=['text'], regexp='Calorias')
def echo_message(message):
    cid = message.chat.id
    keyboard = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton(text='Hoy', callback_data="Calorias 1")
    btn2 = types.InlineKeyboardButton(text='Últimos 2 días', callback_data='Calorias 2')
    btn3 = types.InlineKeyboardButton(text='Última semana', callback_data='Calorias 7')
    keyboard.add(btn, btn2)
    keyboard.add(btn3)
    bot.send_message(cid, "¿De qué periodo quiere obtener las calorías consumidas?:", reply_markup=keyboard)
    print "[" + str(cid) + "]" + 'CALORIAS'

@bot.message_handler(func=lambda message: True, content_types=['text'], regexp='Actividad')
def echo_message(message):
    cid = message.chat.id
    keyboard = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton(text='Hoy', callback_data="Actividad 1")
    btn2 = types.InlineKeyboardButton(text='Últimos 2 días', callback_data='Actividad 2')
    btn3 = types.InlineKeyboardButton(text='Última semana', callback_data='Actividad 7')
    keyboard.add(btn, btn2)
    keyboard.add(btn3)
    bot.send_message(cid, "¿De qué periodo quiere obtener la actividad?:", reply_markup=keyboard)
    print "[" + str(cid) + "]" + 'Actividad'

@bot.message_handler(func=lambda message: True, content_types=['text'], regexp='Ayuda')
def echo_message(message):
    cid = message.chat.id
    bot.send_message(cid, "Ayuda sobre el funcionamiento de la aplicación:\n\n-----------------------------------------------------------------------------------------------\n\n<b> · PASOS:</b>\n\n  Envía una gráfica con los pasos registrados por el usuario.\n  El eje de abscisas indica el intervalo temporal en el que se muestran los pasos mientras que el eje de ordenadas indica la cantidad de pasos realizados\n\n-----------------------------------------------------------------------------------------------\n\n<b>· CALORÍAS:</b>\n\n  Envía una gráfica con las calorías registradas por el usuario.\n  El eje de abscisas indica el intervalo temporal en el que se muestran las calorías mientras que el eje de ordenadas indica la cantidad de calorías consumidas\n\n-----------------------------------------------------------------------------------------------\n\n<b> · ACTIVIDAD</b>:\n\n  Envía una gráfica con la actividad registrada por el usuario.\n  El eje de abscisas indica el intervalo temporal en el que se muestra la actividad mientras que el eje de ordenadas indica el tipo de actividad realizada correspondiéndo un cada actividad con un valor determinado:\n\n  <b>· Despierto:</b> corresponde a un valor 10 en la gráfica.\n  <b>· Andando:</b> corresponde a un valor 30 en la gráfica.\n  <b>· Sueño ligero:</b> corresponde a un valor 90 en la gráfica.\n  <b>· Sueño profundo:</b> corresponde a un valor 100 en la gráfica.\n\n-----------------------------------------------------------------------------------------------", parse_mode="HTML")
    print "[" + str(cid) + "]" + 'Ayuda'

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    cid = call.message.chat.id
    period = call.data.split(' ')
    if call.data.startswith('Pasos'):
        if period[1] == "1":
	    bot.send_message(cid, "Ha elegido Pasos del último día")
            bot.send_message(cid, 'Espera unos segundos mientras se genera la gráfica:')
            steps(cid, period[1])
        elif period[1] == "2":
            bot.send_message(cid, "Ha elegido Pasos de los dos últimos días")
            bot.send_message(cid, 'Espera unos segundos mientras se genera la gráfica:')
            steps(cid, period[1])
        elif period[1] == "7":
            bot.send_message(cid, "Ha elegido Pasos de la última semana")
            bot.send_message(cid, 'Espera unos segundos mientras se genera la gráfica:')
            steps(cid, period[1])
        time.sleep(2)
        os.system('sudo rm Pasos.png')

    elif call.data.startswith('Calorias'):
        if period[1] == "1":
            bot.send_message(cid, "Ha elegido Calorías del último día")
            bot.send_message(cid, 'Espera unos segundos mientras se genera la gráfica:')
            calories(cid, period[1])
        elif period[1] == "2":
            bot.send_message(cid, "Ha elegido Calorías de los dos últimos días")
            bot.send_message(cid, 'Espera unos segundos mientras se genera la gráfica:')
            calories(cid, period[1])
        elif period[1] == "7":
            bot.send_message(cid, "Ha elegido Calorías de la última semana")
            bot.send_message(cid, 'Espera unos segundos mientras se genera la gráfica:')
            calories(cid, period[1])
        time.sleep(2)
        os.system('sudo rm Calorias.png')

    elif call.data.startswith('Actividad'):
        if period[1] == "1":
            bot.send_message(cid, "Ha elegido Actividad del último día")
            bot.send_message(cid, 'Espera unos segundos mientras se genera la gráfica:')
            print period[1]
            print "actividad dia 1"
            activity(cid, period[1])
        elif period[1] == "2":
            bot.send_message(cid, "Ha elegido Actividad de los dos últimos días")
            bot.send_message(cid, 'Espera unos segundos mientras se genera la gráfica:')
            activity(cid, period[1])
        elif period[1] == "7":
            bot.send_message(cid, "Ha elegido Actividad de la última semana")
            bot.send_message(cid, 'Espera unos segundos mientras se genera la gráfica:')
            activity(cid, period[1])
        time.sleep(2)
        os.system('sudo rm Actividad.png')

# Handle all other messages
@bot.message_handler(func=lambda message: True, content_types=['text'])
def echo_message(message):
    cid = message.chat.id
    print "[" + str(cid) + "]" + message.text
    bot.send_message(message, "No es un comando o palabra válida para el bot.\n\nPuede probar '/start' para registrarse o '/teclado' para obtener el teclado que permite utilizar la aplicación.")

# Remove webhook, it fails sometimes the set if there is a previous webhook
bot.remove_webhook()
time.sleep(2)

# Logging
log = logging.getLogger(__name__)
hdlr = logging.FileHandler(LOG_FILE_PATH)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
log.addHandler(hdlr)
log.setLevel(logging.INFO) # Para que en el log esten: mensajes + errores


# Set webhook
bot.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))
print 'Creando el logger...'

# Start flask server
app.run(host=WEBHOOK_LISTEN,
        port=WEBHOOK_PORT,
        ssl_context=(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV),
        debug=True)
