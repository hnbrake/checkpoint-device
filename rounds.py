#!/usr/bin/python3
import requests
import json
import hashlib
import dateutil.parser
import config as cfg
import dictionary
import RPi.GPIO as GPIO
import time
import threading
import urllib.request
from RPLCD.gpio import CharLCD
from datetime import datetime,timezone
from evdev import InputDevice, categorize, ecodes

# INITIALIZATION ####################################################################################
roundsDisplay = CharLCD(cols=16, rows=2, pin_rs=3, pin_e=5, pins_data=[7,11,13,15,19,21,23,29])
dev = InputDevice('/dev/input/event0')

global isInUse
isInUse = False
waitTime = 1800

def startMessage():
    roundsDisplay.clear()
    roundsDisplay.write_string('Ready to Party!')
    time.sleep(2)
    roundsDisplay.clear()

def getHashValue(value):
    hashValue = (hashlib.sha1(value.encode())).hexdigest()
    return hashValue

dev.grab()
def getCardNumber():
    x = ''
    caps = False

    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY:
            data = categorize(event)  # Save the event temporarily to introspect it
            if data.scancode == 42:
                if data.keystate == 1:
                    caps = True
                if data.keystate == 0:
                    caps = False
            if data.keystate == 1:  # Down events only
                if caps:
                    key_lookup = u'{}'.format(dictionary.capscodes.get(data.scancode)) or u'UNKNOWN:[{}]'.format(data.scancode)  # Lookup or return UNKNOWN:XX
                else:
                    key_lookup = u'{}'.format(dictionary.scancodes.get(data.scancode)) or u'UNKNOWN:[{}]'.format(data.scancode)  # Lookup or return UNKNOWN:XX
                if (data.scancode != 42) and (data.scancode != 28):
                    x += key_lookup
                if(data.scancode == 28):
                   return x

# START OF FUNCTIONALITY #############################################################################
startMessage()

internetConnected = False

roundsDisplay.clear()
roundsDisplay.write_string('Connecting to   Network...')

while (not internetConnected):
    try:
        response=urllib.request.urlopen("https://google.com",timeout=1)
        internetConnected = True;
    except urllib.request.URLError:
        continue

roundsDisplay.clear()
roundsDisplay.write_string('Connected to    Network!')
time.sleep(2)

timestamp = str(int(time.time()))
preHash = cfg.path + timestamp + cfg.secret
headerInfo = {'X-API-Key-UUID': cfg.apiUUID, 'X-API-Key-TS': timestamp, 'X-API-Key' : getHashValue(preHash) };
r = requests.get(cfg.path, headers = headerInfo)
q = r.json()
latestTime = dateutil.parser.parse(q["station"]["lastSwipe"])

global lastRound
lastRound = latestTime

# THREAD DEFINITIONS #################################################################################
def IdleDisplayThread():
     while True:
         currentTime = datetime.now()

         global lastRound
         lastRound = lastRound.replace(tzinfo=None)
         deltaTime = (currentTime-lastRound).total_seconds()
         lastRoundDisplay = datetime.strftime(lastRound, "%b %-d %-I:%M %p")
         if (deltaTime >= waitTime):
             if not isInUse:
                roundsDisplay.clear()
                roundsDisplay.write_string('Swipe Card      Rounds Needed!')
         else:
              if not isInUse:
                roundsDisplay.clear()
                roundsDisplay.write_string('Last Swipe:     ' + lastRoundDisplay)
         time.sleep(3)

def MainThread():

    while True:
        cardSwipeData = getCardNumber()
        roundsDisplay.clear()
        cardID = cardSwipeData[19:24] if len(cardSwipeData) >= 25 else "00000"
        if(cardID is "00000"):
            roundsDisplay.clear()
            global isInUse
            isInUse = True
            roundsDisplay.write_string('Please Swipe    Again!')
            time.sleep(1)
            isInUse = False
            continue

        currentTime = datetime.now().replace(microsecond=0)
        timestamp = str(int(time.time()))
        preHash = cfg.path + timestamp + cfg.secret
        headerInfo = {'X-API-Key-UUID': cfg.apiUUID, 'X-API-Key-TS': timestamp, 'X-API-Key' : getHashValue(preHash)};
        r = requests.get(cfg.path, headers = headerInfo)
        q = r.json()
        latestTime = dateutil.parser.parse(q["station"]["lastSwipe"])
        latestTime = latestTime.replace(tzinfo=None)
        tooSoon = (currentTime-latestTime).total_seconds()

        if tooSoon >= waitTime:
            payload = {'memorial_number': str(cardID)}
            timestamp = str(int(time.time()))
            preHash = cfg.path + timestamp + cfg.secret + json.dumps(payload, separators=(',', ':'))
            payload = {'payload': payload}
            headerInfo = {'X-API-Key-UUID': cfg.apiUUID, 'X-API-Key-TS': timestamp, 'X-API-Key' : getHashValue(preHash) };
            r = requests.post(cfg.path, json = payload, headers = headerInfo)
            print(r.status_code)
            print(r.text)

            if (r.status_code == 200):
                roundsDisplay.clear()
                isInUse = True
                fullName = ((json.loads(r.text))["user"]["name"])
                firstName = fullName[(fullName.find(",") + 2):]
                roundsDisplay.write_string("Swipe Accepted  " + firstName +"!")
                time.sleep(2)
                isInUse = False
                global lastRound
                lastRound = datetime.now().replace(microsecond=0)

            elif (r.status_code == 400):
                roundsDisplay.clear()
                isInUse = True
                roundsDisplay.write_string('Swipe Not Accepted')
                time.sleep(2)
                isInUse = False

            elif (r.status_code == 401):
                roundsDisplay.clear()
                isInUse = True
                roundsDisplay.write_string('User Not        Authorized!')
                time.sleep(2)
                isInUse = False

            else:
                roundsDisplay.clear()
                isInUse = True
                roundsDisplay.write_string("Error: " + str(r.status_code))
                time.sleep(2)
                isInUse = False


        elif tooSoon < waitTime:
            roundsDisplay.clear()
            roundsDisplay.write_string('Swiped Too Soon')
            time.sleep(3)


# STARTING THREADS ##########################################################################################
threads = []
t = threading.Thread(target=MainThread)
threads.append(t)
t.start();

u = threading.Thread(target=IdleDisplayThread)
threads.append(u)
u.start();