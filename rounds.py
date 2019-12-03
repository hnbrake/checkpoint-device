#!/usr/bin/python3
import MySQLdb as mdb
import config as cfg
import RPi.GPIO as GPIO
import time
import threading
from RPLCD.gpio import CharLCD
from datetime import datetime
from evdev import InputDevice, categorize, ecodes

roundsDisplay = CharLCD(cols=16, rows=2, pin_rs=3, pin_e=7, pins_data=[11,13,15,19,21,23,29,31])
dev = InputDevice('/dev/input/event0')

# Dictionaries for /Dev file to readable string conversion:
scancodes = {
    # Scancode: ASCIICode
    0: None, 1: u'ESC', 2: u'1', 3: u'2', 4: u'3', 5: u'4', 6: u'5', 7: u'6', 8: u'7', 9: u'8',
    10: u'9', 11: u'0', 12: u'-', 13: u'=', 14: u'BKSP', 15: u'TAB', 16: u'q', 17: u'w', 18: u'e', 19: u'r',
    20: u't', 21: u'y', 22: u'u', 23: u'i', 24: u'o', 25: u'p', 26: u'[', 27: u']', 28: u'CRLF', 29: u'LCTRL',
    30: u'a', 31: u's', 32: u'd', 33: u'f', 34: u'g', 35: u'h', 36: u'j', 37: u'k', 38: u'l', 39: u';',
    40: u'"', 41: u'`', 42: u'LSHFT', 43: u'\\', 44: u'z', 45: u'x', 46: u'c', 47: u'v', 48: u'b', 49: u'n',
    50: u'm', 51: u',', 52: u'.', 53: u'/', 54: u'RSHFT', 56: u'LALT', 57: u' ', 100: u'RALT'
}

capscodes = {
    0: None, 1: u'ESC', 2: u'!', 3: u'@', 4: u'#', 5: u'$', 6: u'%', 7: u'^', 8: u'&', 9: u'*',
    10: u'(', 11: u')', 12: u'_', 13: u'+', 14: u'BKSP', 15: u'TAB', 16: u'Q', 17: u'W', 18: u'E', 19: u'R',
    20: u'T', 21: u'Y', 22: u'U', 23: u'I', 24: u'O', 25: u'P', 26: u'{', 27: u'}', 28: u'CRLF', 29: u'LCTRL',
    30: u'A', 31: u'S', 32: u'D', 33: u'F', 34: u'G', 35: u'H', 36: u'J', 37: u'K', 38: u'L', 39: u':',
    40: u'\'', 41: u'~', 42: u'LSHFT', 43: u'|', 44: u'Z', 45: u'X', 46: u'C', 47: u'V', 48: u'B', 49: u'N',
    50: u'M', 51: u'<', 52: u'>', 53: u'?', 54: u'RSHFT', 56: u'LALT',  57: u' ', 100: u'RALT'
}


#grab provides exclusive access to the device
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
                    key_lookup = u'{}'.format(capscodes.get(data.scancode)) or u'UNKNOWN:[{}]'.format(data.scancode)  # Lookup or return UNKNOWN:XX
                else:
                    key_lookup = u'{}'.format(scancodes.get(data.scancode)) or u'UNKNOWN:[{}]'.format(data.scancode)  # Lookup or return UNKNOWN:XX
                if (data.scancode != 42) and (data.scancode != 28):
                    x += key_lookup
                if(data.scancode == 28):
                   return x

try:

    con = mdb.connect(host=cfg.mysql['host'], user=cfg.mysql['user'], passwd=cfg.mysql['passwd'], db=cfg.mysql['db'])
    con.autocommit(True)
    cur = con.cursor()
    roundsDisplay.clear()
    roundsDisplay.write_string('Connected to DB')
    time.sleep(2)
    roundsDisplay.clear()
    roundsDisplay.write_string('Ready to Party!')
    time.sleep(2)
    roundsDisplay.clear()

except:
    roundsDisplay.clear()
    roundsDisplay.write_string('Connection      Failed!')
    while True:
        continue

cur.execute("SELECT * FROM RoundsHistory as rh, RoundsRooms as rr WHERE rh.room = rr.roomID and rr.roomName = '" + cfg.deviceLocation + "'" )
loggedTimes = cur.fetchall()
latestTime = loggedTimes[len(loggedTimes)-1][1]

global lastRound
lastRound = latestTime

global isInUse
isInUse = False

waitTime = 1800

def IdleDisplayThread():
     while True:

         roundsDisplay.clear()
         roundsDisplay.write_string('Please Swipe    Card...')
         time.sleep(5)
         currentTime = datetime.now()
         print (lastRound)
         x = (lastRound - datetime(1970,1,1)).total_seconds()
         y = (currentTime - datetime(1970,1,1)).total_seconds()
         deltaTime = y-x
         print (deltaTime)
         lastRoundDisplay = datetime.strftime(lastRound, "%b %-d %-I:%M %p")

         if (deltaTime >= waitTime):
             if not isInUse:
                roundsDisplay.clear()
                roundsDisplay.write_string('Rounds Needed!')
                time.sleep(5)
         elif deltaTime < waitTime:
              if not isInUse:
                roundsDisplay.clear()
                roundsDisplay.write_string('Last Swipe:     ' + lastRoundDisplay)
                time.sleep(5)


def MainThread():

    while True:
        cardSwipeData = getCardNumber()
        roundsDisplay.clear()
        cardID = cardSwipeData[19:24] if len(cardSwipeData) >= 25 else "00000"

        cur.execute("SELECT * FROM RoundsCards WHERE studentNumber LIKE %s",['%'+cardID+'%'])
        currentID = cur.fetchone()
        print(currentID)
        if(currentID is None):
            roundsDisplay.clear()

            global isInUse
            isInUse = True
            roundsDisplay.write_string('Swipe Again!')
            time.sleep(1)
            isInUse = False
            continue

        currentTime = datetime.now().replace(microsecond=0)
        timeDisplay = (" %s/%s/%s %s:%s:%s"%(currentTime.year,currentTime.month,currentTime.day,
                                    currentTime.hour,currentTime.minute,currentTime.second))
        cur.execute("SELECT * FROM RoundsHistory as rh, RoundsRooms as rr WHERE rh.room = rr.roomID and rr.roomName = '" + cfg.deviceLocation + "'")

        loggedTimes = cur.fetchall()
        latestTime = loggedTimes[len(loggedTimes)-1][1]
        latestRoom = loggedTimes[len(loggedTimes)-1][2]

        x = (latestTime - datetime(1970,1,1)).total_seconds()
        y = (currentTime - datetime(1970,1,1)).total_seconds()

        tooSoon = y-x
        print (tooSoon)

        cur.execute("SELECT roomID FROM RoundsRooms WHERE roomName = '" + cfg.deviceLocation + "'" )
        roomID = cur.fetchone()

        if roomID is not None and tooSoon >= waitTime:
            cur.execute("INSERT INTO RoundsHistory (DateAndTime, room) VALUES(%s,%s)",(timeDisplay, latestRoom) )
            global lastRound
            lastRound = datetime.now().replace(microsecond=0)
            print ("staff")
            roundsDisplay.clear()
            isInUse = True
            roundsDisplay.write_string('Swipe Accepted! ' + currentID[1])
            time.sleep(2)
            isInUse = False

        elif tooSoon < waitTime:
            print ("tooSoon")
            roundsDisplay.clear()
            roundsDisplay.write_string('Too Soon        ' + currentID[1] + '!')
            time.sleep(2)

        #cur.close()
        #con.close()

threads = []

t = threading.Thread(target=MainThread)
threads.append(t)
t.start();

u = threading.Thread(target=IdleDisplayThread)
threads.append(u)
u.start();