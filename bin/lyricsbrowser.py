#!/usr/bin/python3.5

import re
import curses
import socketserver
import sys
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

#---------------------------------color and text format-------------------------------------------------------------
def init_colors():
    curses.start_color()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)     # Roter Text auf schwarzem Hintergrund
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Grüner Text auf schwarzem Hintergrund
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Gelber Text auf schwarzem Hintergrund
    curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)    # Blauer Text auf schwarzem Hintergrund
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Magentafarbener Text auf schwarzem Hintergrund
    curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Cyanfarbener Text auf schwarzem Hintergrund
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Weißer Text auf schwarzem Hintergrund
    curses.init_pair(8, curses.COLOR_RED, curses.COLOR_WHITE)     # Roter Text auf weißem Hintergrund
    curses.init_pair(9, curses.COLOR_GREEN, curses.COLOR_BLUE)    # Grüner Text auf blauem Hintergrund
    curses.init_pair(10, curses.COLOR_YELLOW, curses.COLOR_CYAN)  # Gelber Text auf cyanfarbenem Hintergrund


    # Farbzuordnung per Dictionary
    color_dict = {
        "red": curses.color_pair(1),
        "green": curses.color_pair(2),
        "yellow": curses.color_pair(3),
        "blue": curses.color_pair(4),
        "magenta": curses.color_pair(5),
        "cyan": curses.color_pair(6),
        "white": curses.color_pair(7),
        "red_white": curses.color_pair(8),
        "green_blue": curses.color_pair(9),
        "yellow_cyan": curses.color_pair(10)
    }

    return color_dict

# Funktion, um die Länge des Texts ohne Tags zu berechnen
def get_visible_length(text, tag_regex):
    # Entferne alle ignorierten Tags aus dem Text für die Längenberechnung
    cleaned_text = re.sub(tag_regex, '', text)
    return len(cleaned_text)

def preprocess_text(lines, max_width, tag_regex=None):
    #lines = text.splitlines()  # Behalte vorhandene Zeilenumbrüche bei
    formatted_lines = []  # Liste für die formatierten Zeilen

    for line in lines:
        words = line.split()
        current_line = ""
        current_line_length = 0  # Verfolge die sichtbare Länge der aktuellen Zeile

        for word in words:
            word_length = get_visible_length(word, tag_regex)
            
            # Überprüfen, ob das Hinzufügen des nächsten Wortes die maximale Breite überschreiten würde
            if current_line_length + word_length + (1 if current_line else 0) > max_width:
                # Füge die aktuelle Zeile der Liste hinzu
                formatted_lines.append(current_line.rstrip())
                # Starte eine neue Zeile mit dem aktuellen Wort
                current_line = word
                current_line_length = word_length  # Setze die neue Zeilenlänge auf die Länge des Worts
            else:
                # Füge das Wort zur aktuellen Zeile hinzu
                if current_line:
                    current_line += " " + word
                    current_line_length += word_length + 1  # Inklusive Leerzeichen
                else:
                    current_line = word
                    current_line_length = word_length
        
        # Füge die letzte Zeile der Liste hinzu
        formatted_lines.append(current_line)

    return formatted_lines

# Dynamische Regex-Erstellung basierend auf den Tags im Dictionary
def create_tag_regex(color_dict):
    # Erstelle eine Regex, die alle Tags aus dem Dictionary umfasst
    tags = '|'.join(re.escape(tag) for tag in color_dict.keys())
    return re.compile(f'</?({tags})>')

# Parser und Zentrierung des Textes
def parse_and_display_text(subwin, text_lines, width, color_dict, pattern):
    current_color = curses.A_NORMAL  # Initiale Farbe
    
    # Iteriere über die Zeilen
    for line in text_lines:
        current_pos = 0  # Position des letzten unberührten Teils der Zeile
        display_text = ""  # Gesamter Text ohne Tags für die Zentrierung
        parts = []  # Liste von (Textstück, Farbe) für spätere Ausgabe

        # Durchsuche die aktuelle Zeile nach Tags
        for match in pattern.finditer(line):
            # Text vor dem Tag ausgeben
            raw_text = line[current_pos:match.start()]
            if raw_text:
                parts.append((raw_text, current_color))  # Speichere den Text und die Farbe
                display_text += raw_text  # Füge den Text zum Gesamten hinzu (ohne Tags)

            # Ändere die aktuelle Farbe basierend auf dem Tag
            current_color = color_dict.get(match.group(1), curses.A_NORMAL)

            # Setze die Position nach dem Tag
            current_pos = match.end()

        # Füge den Rest der Zeile nach dem letzten Tag hinzu
        raw_text = line[current_pos:]
        if raw_text:
            parts.append((raw_text, current_color))
            display_text += raw_text

        # Zentriere den Text, indem wir die x-Position berechnen
        x_pos = (width - len(display_text)) // 2

        # Setze den Cursor an die berechnete Position
        subwin.move(subwin.getyx()[0], x_pos)

        # Gebe den zentrierten Text mit Farben aus
        for part, color in parts:
            subwin.attron(color)
            subwin.addstr(part)
            subwin.attroff(color)

        # Zeilenumbruch für die nächste Zeile
        if line != text_lines[-1]:
            subwin.addstr("\n")
#----------------------------------------------------------------------------------------------


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
def updatemainwindow(content=None, colored=False):
    if content is None:
        content = []
    displaywin.clear()
    
    if colored is True:
        height, width = displaywin.getmaxyx()
        parse_and_display_text(displaywin, content, width - 2, colors, tag_pattern)
    else:
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
            loadsong()
            selectedpage = 0
            displaysong()
          # selectedsong = (selectedsong + 1) % len(filelist)
          # displaysetlist()
        else:
            #if islastpage():
                if islastsong():
                    displaysetlist(True)
                else:
                    selectedpage = 0
                    selectedsong += 1
                    loadsong()
                    displaysong()
            #else:
                #selectedpage += 1
                #displaysong()


# Handle PREV operations
def prevhandler(*args):
    global selectedsong
    global selectedpage

    if len(filelist) > 0:
        #if menuopen:
        #    selectedsong = selectedsong - 1 if selectedsong > 0 else len(filelist) - 1
         #   displaysetlist()
        #else:
        if not menuopen:
            if selectedsong == 0:
                displaysetlist(True)
            else:
                if selectedpage == 0:
                    selectedsong -= 1
                    loadsong()
                    selectedpage = 0#calclastpage()
                    displaysong()
                else:
                    selectedpage -= 1
                    displaysong()


# Handle MENU/SELECT operations
def menuhandler(*args):
    global selectedsong
    global selectedpage

    if len(filelist) > 0:
        #if menuopen:
           # loadsong()
           # selectedpage = 0
           # displaysong()
        #else:
        if not menuopen:
            displaysetlist(True)

def uphandler(*args):
    global selectedsong
    global selectedpage
    
    if menuopen:
        selectedsong = selectedsong - 1 if selectedsong > 0 else len(filelist) - 1
        displaysetlist()
    else:
        if selectedpage != 0:
            selectedpage -= 1
            displaysong()

def downhandler(*args):
    global selectedsong
    global selectedpage
    
    if menuopen:
        selectedsong = (selectedsong + 1) % len(filelist)
        displaysetlist()
    else:
        if not islastpage():
            selectedpage += 1
            displaysong()



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
        
    displaylines = preprocess_text( all_lines, screencols - 4, tag_pattern)

 #   # Loop through temp array, split lines if too long
 #   for fileline in all_lines:
 #       fileline = fileline.rstrip()
 #       parsedline = parseline(fileline)
 #       first = True
 #       for partline in parsedline:
 #           if first:
 #               displaylines.append(partline)
 #               first = False
 #           else:
 #               displaylines.append(" - %s" % partline)
 #
 #   # If no text lines found in file, display error
    if len(displaylines) == 0:
        displaylines.append(_e['empty'])
 
    #pagesize in lines
    displaypagesize = (displaywin.getmaxyx()[0])-1
    # Split lyrics into pages if too long
    for page in [displaylines[i:i+displaypagesize] for i in range(0, len(displaylines), displaypagesize)]:
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

    updatemainwindow(content=curfilelyrics[selectedpage],colored=True)


# Interface Wrapper
def curseswrapper(stdscr):
    global screenlines
    global screencols
    global topbar
    global displaywin
    global bottombar
    global colors
    global tag_pattern
    
     # Farben initialisieren und Dictionary mit Farben zurückbekommen
    colors = init_colors()

    # Dynamische Regex basierend auf den Tags im color_dict erstellen
    tag_pattern = create_tag_regex(colors)

    screenlines = curses.LINES - 1
    screencols = curses.COLS
    stdscr.nodelay(True)
    
    # Clear screen
    stdscr.clear()

    # Hide the cursor
    curses.curs_set(0)

    # Setup Top Bar
    topbar = stdscr.subwin(1, screencols, 0, 0)

    # Setup Display Window
    stdscr.hline(1, 0, '_', screencols)
    displaywin = stdscr.subwin(screenlines-4, screencols, 2, 0)
    stdscr.hline(screenlines-2, 0, '_', screencols)

    # Bottom Bar
    bottombar = stdscr.subwin(1, screencols, screenlines-1, 0)
    bottombar.clear()
    updatebottombar(middle=_e['welcome'])

    stdscr.refresh()

    loadsongs()

    # Handle queue events from socket
    while True:
        key = stdscr.getch()
        if key == curses.KEY_LEFT:
            prevhandler()
        elif key == curses.KEY_RIGHT:
            nexthandler()
        elif key == curses.KEY_UP:
            uphandler()
        elif key == curses.KEY_DOWN:
            downhandler()
            
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
if len(sys.argv) > 1:
    setpath(sys.argv[1])

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

# Start the interface
curses.wrapper(curseswrapper)