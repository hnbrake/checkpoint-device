import MySQLdb as mdb
import dbconfig as cfg
import RPi.GPIO as GPIO
import time
import threading
from RPLCD.gpio import CharLCD
from datetime import datetime


roundsDisplay = CharLCD(cols = 16, rows = 2, pin_rs = 37, pin_e = 35, pins_data=[40,38,36,32,33,31,29,23])
#GPIO.setwarnings(False)


 
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

cur.execute("""SELECT * FROM RoundsHistory as rh, RoundsRooms as rr
            WHERE
            rh.room = rr.roomID and rr.roomName = 'rightHall'""")
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
         print lastRound
         x = (lastRound - datetime(1970,1,1)).total_seconds()
         y = (currentTime - datetime(1970,1,1)).total_seconds()
         deltaTime = y-x
         print deltaTime
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
        cardSwipeData = raw_input()
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
            global isInUse
	    isInUse = False	    

            continue
   
    
        currentTime = datetime.now().replace(microsecond=0)
        timeDisplay = (" %s/%s/%s %s:%s:%s"%(currentTime.year,currentTime.month,currentTime.day,
                                    currentTime.hour,currentTime.minute,currentTime.second))
   
        cur.execute("""SELECT * FROM RoundsHistory as rh, RoundsRooms as rr
                    WHERE
                    rh.room = rr.roomID and rr.roomName = 'rightHall'""")

        loggedTimes = cur.fetchall()
        latestTime = loggedTimes[len(loggedTimes)-1][1]
        latestRoom = loggedTimes[len(loggedTimes)-1][2]

        x = (latestTime - datetime(1970,1,1)).total_seconds()
        y = (currentTime - datetime(1970,1,1)).total_seconds()

        tooSoon = y-x
        print tooSoon

        cur.execute("SELECT roomID FROM RoundsRooms WHERE roomName = 'rightHall'")
        roomID = cur.fetchone()

        if roomID is not None and tooSoon >= waitTime:
    	    cur.execute("INSERT INTO RoundsHistory (DateAndTime, room) VALUES(%s,%s)",(timeDisplay, latestRoom) ) 
	    global lastRound
            lastRound = datetime.now().replace(microsecond=0)     
    	    print "staff" 
            roundsDisplay.clear()

	    global isInUse
	    isInUse = True
            roundsDisplay.write_string('Swipe Accepted! ' + currentID[1])
            time.sleep(2)
            global isInUse
	    isInUse = False

        elif tooSoon < waitTime:
    	    print "tooSoon"
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

