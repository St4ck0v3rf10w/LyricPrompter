#!/usr/bin/python3.5

import curses
import socketserver
import sys
import RPi.GPIO as GPIO
from threading import Thread, current_thread
from queue import Queue
from os import listdir, unlink
from os.path import isfile, join, exists

# Setup language strings
# TODO - Language handling based on locale
_e = {
    'welcome': "Welcome",
    'load_media': "Insert USB Media",
    'select': "Select",
    'menu': "Menu",
    'next': "Next",
    'prev': "Prev",
    'first': "First",
    'last': "Last",
    'prev_page': "Prev Page",
    'prev_song': "Prev Song",
    'next_page': "Next Page",
    'next_song': "Next Song",
    'page': "Page",
    'empty': "Empty File - No Text Found"
}

socket_path = "/tmp/lyricsbrowser.sock"
lyrics_path = "."

gpiopin_prev = 13
gpiopin_next = 26
gpiopin_menu = 19

filelist = []
q = Queue()
menupad = []
screenlines = 0
screencols = 0
topbar = None
displaywin = None
bottombar = None
selectedsong = 0
menuopen = False
curfilelyrics = []
selectedpage = 0


# Socket Server - Receives file path and instructions from udev
class ThreadedSocketRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = str(self.request.recv(1024), 'ascii')
        cur_thread = current_thread()
        response = bytes("{}: {}".format(cur_thread.name, data), 'ascii')
        self.request.sendall(response)
        q.put(data)


# Socket Server Thread
class ThreadedSocketServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    pass


# Helper - set global path string
def setpath(newpath):
    global lyrics_path
    lyrics_path = newpath


# Helper - determine if on last page of current song
def islastpage():
    return selectedpage == len(curfilelyrics)-1


# Helper - determine if on last song in set list
def islastsong():
    return selectedsong == len(filelist)-1


# Helper - calculate the last page number of a song
def calclastpage():
    return len(curfilelyrics)-1


# Basic text cleanup of title for display
def songtitle(title, pad=0):
    title = title.replace(".txt", "")
    title = title.replace(".TXT", "")
    if pad:
        title = title[:pad] if len(title) > pad else title
        title = title.ljust(pad)
    return title


# Titlebar update function
def updatetitlebar(clear=False):
    if clear:
        topbar.clear()
    else:
        lastpage = str(calclastpage() + 1)
        lastpagelen = len(lastpage)
        thispage = str(selectedpage + 1)
        tbarbreak = screencols - len(_e['page']) - 3 - (lastpagelen * 2)
        topbar.addstr(0, 1, songtitle(filelist[selectedsong], tbarbreak - 2))
        topbar.addstr(0, tbarbreak - 1, "%s: %s/%s" % (_e['page'], thispage.rjust(lastpagelen), lastpage))
        topbar.refresh()
    topbar.refresh()


# Main Window update function
def updatemainwindow(content=None):
    if content is None:
        content = []
    displaywin.clear()
    displaylinecounter = 0
    for displayline in content:
        displaywin.addstr(displaylinecounter, 1, displayline)
        displaylinecounter += 1
    displaywin.refresh()


# Bottombar update function
def updatebottombar(left='', middle='', right=''):
    global bottombar
    global screencols

    # Divide screen into 3 columns
    mycolwidth = int(screencols/3)

    # Display left column string
    if left:
        ltext = '<- %s' % left
        bottombar.addstr(0, 0, ltext.ljust(mycolwidth))

    # Display right column string
    if right:
        rtext = '%s ->' % right
        bottombar.addstr(0, screencols-1-mycolwidth, rtext.rjust(mycolwidth))

    # Display middle column string
    if middle:
        bottombar.addstr(0, int(screencols/2)-int(mycolwidth/2)+1, middle.center(mycolwidth-2))

    bottombar.refresh()


# Handle NEXT operations
def nexthandler(*args):
    global selectedsong
    global selectedpage

    if len(filelist) > 0:
        if menuopen:
            selectedsong = (selectedsong + 1) % len(filelist)
            displaysetlist()
        else:
            if islastpage():
                if islastsong():
                    displaysetlist(True)
                else:
                    selectedpage = 0
                    selectedsong += 1
                    loadsong()
                    displaysong()
            else:
                selectedpage += 1
                displaysong()


# Handle PREV operations
def prevhandler(*args):
    global selectedsong
    global selectedpage

    if len(filelist) > 0:
        if menuopen:
            selectedsong = selectedsong - 1 if selectedsong > 0 else len(filelist) - 1
            displaysetlist()
        else:
            if selectedsong == 0:
                displaysetlist(True)
            else:
                if selectedpage == 0:
                    selectedsong -= 1
                    loadsong()
                    selectedpage = calclastpage()
                    displaysong()
                else:
                    selectedpage -= 1
                    displaysong()


# Handle MENU/SELECT operations
def menuhandler(*args):
    global selectedsong
    global selectedpage

    if len(filelist) > 0:
        if menuopen:
            loadsong()
            selectedpage = 0
            displaysong()
        else:
            displaysetlist(True)


# Load set list from path
def loadsongs():
    global filelist
    del filelist[:]

    # If default path, show load media message
    if lyrics_path == ".":
        displayloadmedia()
    else:
        # Loop through files in directory, append to list if "valid"
        for f in listdir(lyrics_path):
            if isfile(join(lyrics_path, f)):
                if not f.startswith('.'):
                    filelist.append(f)
        # Sort list alphabetically
        filelist.sort()
        # If there are files display list, otherwise show load media
        if len(filelist) > 0:
            displaysetlist(True)
        else:
            displayloadmedia()


# Load/parse lyrics from a given song
def loadsong():
    global curfilelyrics
    displaylines = []

    # Empty the current lyrics
    del curfilelyrics[:]
    # Load path, chunk lines into temp array
    songpath = join(lyrics_path, filelist[selectedsong])
    with open(songpath) as f:
        all_lines = f.readlines()

    # Loop through temp array, split lines if too long
    for fileline in all_lines:
        fileline = fileline.rstrip()
        parsedline = parseline(fileline)
        first = True
        for partline in parsedline:
            if first:
                displaylines.append(partline)
                first = False
            else:
                displaylines.append(" - %s" % partline)

    # If no text lines found in file, display error
    if len(displaylines) == 0:
        displaylines.append(_e['empty'])

    # Split lyrics into pages if too long
    for page in [displaylines[i:i+screenlines-5] for i in range(0, len(displaylines), screenlines-5)]:
        curfilelyrics.append(page)


# Break up long lines, do some parsing
def parseline(fileline, maxlen=0):
    returnlines = []
    maxlen = maxlen if maxlen > 0 else screencols - 4

    while maxlen < len(fileline):
        breakpoint = fileline[0:maxlen].rfind(" ")
        returnlines.append(fileline[0:breakpoint])
        fileline = fileline[breakpoint:]
    returnlines.append(fileline)

    return returnlines


# Display Load Media Message if lyrics directory not present
def displayloadmedia():
    # Clear Top Bar
    updatetitlebar(clear=True)

    # Display load media string
    updatemainwindow(content=[_e['load_media']])


# Display the set list
def displaysetlist(clearscreen=False):
    global menupad
    global menuopen
    global selectedsong
    del menupad[:]
    maxstrlen = 0
    menuopen = True

    if clearscreen:
        # Clear Top Bar
        updatetitlebar(clear=True)

        # Clear contents from main window
        updatemainwindow()

    # Bottom Bar Context Menu
    updatebottombar(
        middle=_e['select'],
        left=_e['prev'] if selectedsong > 0 else _e['last'],
        right=_e['next'] if selectedsong < len(filelist) - 1 else _e['first']
    )

    # Find the longest title
    for f in filelist:
        fnamelen = len(songtitle(f))
        maxstrlen = fnamelen if fnamelen > maxstrlen else maxstrlen

    # If longest title is wider than the screen width, limit to screen width
    maxstrlen = maxstrlen if maxstrlen + 6 <= screencols else screencols - 6

    # Create the pad and border
    menupad.append(curses.newpad(len(filelist)+2, maxstrlen + 4))
    menupad.append(maxstrlen + 2)
    menupad[0].box()

    # Loop through file list, add to set list
    songnum = 0
    for f in filelist:
        title = songtitle(f, maxstrlen)
        # Highlight if current
        if songnum == selectedsong:
            menupad[0].attron(curses.A_STANDOUT)
        else:
            menupad[0].attroff(curses.A_STANDOUT)
        # Add title to menu
        menupad[0].addstr(songnum + 1, 2, title)
        songnum += 1

    # Determine where the pad should go and display it
    topy = int((screenlines-len(filelist)-2)/2)
    topx = int((screencols-menupad[1]-4)/2)
    menupad[0].refresh(0, 0, topy, topx, topy + len(filelist)+2, topx + menupad[1]+4)


# Display song lyrics page
def displaysong():
    global menuopen
    global selectedsong
    menuopen = False

    # Update Top Bar
    updatetitlebar()

    # Bottom Bar Context Menu
    updatebottombar(
        middle=_e['menu'],
        left=_e['prev_page']
            if selectedpage > 0 else _e['prev_song'] if selectedsong > 0 else _e['menu'],
        right=_e['next_page']
            if selectedpage < calclastpage() else _e['next_song'] if selectedsong < len(filelist) - 1 else _e['menu']
    )

    updatemainwindow(content=curfilelyrics[selectedpage])


# Interface Wrapper
def curseswrapper(stdscr):
    global screenlines
    global screencols
    global topbar
    global displaywin
    global bottombar

    screenlines = curses.LINES - 1
    screencols = curses.COLS

    # Clear screen
    stdscr.clear()

    # Hide the cursor
    curses.curs_set(0)

    # Setup Top Bar
    topbar = stdscr.subwin(1, screencols, 0, 0)

    # Setup Display Window
    stdscr.hline(1, 0, '_', screencols)
    displaywin = stdscr.subwin(screenlines-5, screencols, 2, 0)
    stdscr.hline(screenlines-2, 0, '_', screencols)

    # Bottom Bar
    bottombar = stdscr.subwin(1, screencols, screenlines-1, 0)
    bottombar.clear()
    updatebottombar(middle=_e['welcome'])

    stdscr.refresh()

    loadsongs()

    # Handle queue events from socket
    while True:
        while not q.empty():
            item = q.get()
            if item[:1] in ['/', '.']:
                setpath(item)
                loadsongs()
            elif item[:1].lower() == 'n':
                nexthandler()
            elif item[:1].lower() == 'p':
                prevhandler()
            elif item[:1].lower() == 'm':
                menuhandler()
            q.task_done()


# Set path if passed
for line in sys.stdin:
    sys.stderr.write("DEBUG: got line: " + line)
    setpath(line)

# Setup Socket Server
try:
    unlink(socket_path)
except OSError:
    if exists(socket_path):
        raise
server = ThreadedSocketServer(socket_path, ThreadedSocketRequestHandler)
server_thread = Thread(target=server.serve_forever)
server_thread.daemon = True
server_thread.start()

# GPIO setup
GPIO.setwarnings(False)
GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
# Prev Button
GPIO.setup(gpiopin_prev, GPIO.IN)
GPIO.add_event_detect(gpiopin_prev, GPIO.FALLING, callback=prevhandler, bouncetime=100)
# Next Button
GPIO.setup(gpiopin_next, GPIO.IN)
GPIO.add_event_detect(gpiopin_next, GPIO.FALLING, callback=nexthandler, bouncetime=100)
# Menu Button
GPIO.setup(gpiopin_menu, GPIO.IN)
GPIO.add_event_detect(gpiopin_menu, GPIO.FALLING, callback=menuhandler, bouncetime=100)

# Start the interface
curses.wrapper(curseswrapper)


