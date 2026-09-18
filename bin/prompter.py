#!/usr/bin/python3

import re
import curses
import sys
import locale
from pathlib import Path
from config import _lang

# System-Locale für UTF-8 aktivieren
locale.setlocale(locale.LC_ALL, '')

lyrics_path = Path(".")


def run(stdscr, lyric_dir):
    setpath(lyric_dir)
    return curseswrapper(stdscr)

filelist = []
screenlines = 0
screencols = 0
topbar = None
displaywin = None
bottombar = None
screenwin = None
selectedsong = 0
menuopen = False
curfilelyrics = []
selectedpage = 0
colors = {}
tag_pattern = None


def init_colors():
    curses.start_color()
    pairs = [
        (1, curses.COLOR_RED, curses.COLOR_BLACK),
        (2, curses.COLOR_GREEN, curses.COLOR_BLACK),
        (3, curses.COLOR_YELLOW, curses.COLOR_BLACK),
        (4, curses.COLOR_BLUE, curses.COLOR_BLACK),
        (5, curses.COLOR_MAGENTA, curses.COLOR_BLACK),
        (6, curses.COLOR_CYAN, curses.COLOR_BLACK),
        (7, curses.COLOR_WHITE, curses.COLOR_BLACK),
        (8, curses.COLOR_RED, curses.COLOR_WHITE),
        (9, curses.COLOR_GREEN, curses.COLOR_BLUE),
        (10, curses.COLOR_YELLOW, curses.COLOR_CYAN)
    ]
    for pair_id, fg, bg in pairs:
        curses.init_pair(pair_id, fg, bg)

    return {
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


def get_visible_length(text, tag_regex):
    return len(re.sub(tag_regex, '', text))


def preprocess_text(lines, max_width, tag_regex=None):
    formatted_lines = []
    for line in lines:
        words = line.split()
        if not words:
            formatted_lines.append("")
            continue

        current_line = ""
        current_line_length = 0

        for word in words:
            word_length = get_visible_length(word, tag_regex)

            if current_line_length + word_length + (1 if current_line else 0) > max_width:
                formatted_lines.append(current_line.rstrip())
                current_line = word
                current_line_length = word_length
            else:
                current_line += (" " if current_line else "") + word
                current_line_length += word_length + (1 if current_line_length > 0 else 0)

        formatted_lines.append(current_line)

    return formatted_lines


def create_tag_regex(color_dict):
    tags = '|'.join(re.escape(tag) for tag in color_dict.keys())
    return re.compile(f'</?({tags})>')


def parse_and_display_text(subwin, text_lines, width, color_dict, pattern):
    current_color = curses.A_NORMAL

    for line_idx, line in enumerate(text_lines):
        current_pos = 0
        display_text = ""
        parts = []

        for match in pattern.finditer(line):
            raw_text = line[current_pos:match.start()]
            if raw_text:
                parts.append((raw_text, current_color))
                display_text += raw_text

            current_color = color_dict.get(match.group(1), curses.A_NORMAL)
            current_pos = match.end()

        raw_text = line[current_pos:]
        if raw_text:
            parts.append((raw_text, current_color))
            display_text += raw_text

        x_pos = max(0, (width - len(display_text)) // 2)

        try:
            subwin.move(line_idx, x_pos)
            for part, color in parts:
                subwin.attron(color)
                subwin.addstr(part)
                subwin.attroff(color)
        except curses.error:
            pass


def setpath(newpath):
    global lyrics_path
    lyrics_path = Path(newpath)


def islastpage():
    return selectedpage >= len(curfilelyrics) - 1


def islastsong():
    return selectedsong >= len(filelist) - 1


def calclastpage():
    return max(0, len(curfilelyrics) - 1)


def songtitle(title, pad=0):
    title = title.removesuffix(".txt").removesuffix(".TXT")
    if pad:
        title = title[:pad].ljust(pad)
    return title


def updatetitlebar(clear=False, title_override=None):
    topbar.clear()
    if clear:
        topbar.refresh()
        return

    if title_override:
        try:
            topbar.addstr(0, 1, title_override)
        except curses.error:
            pass
    elif filelist:
        lastpage = str(calclastpage() + 1)
        thispage = str(selectedpage + 1)
        tbarbreak = screencols - len(_lang['page']) - 3 - (len(lastpage) * 2)
        try:
            topbar.addstr(0, 1, songtitle(filelist[selectedsong], max(1, tbarbreak - 2)))
            topbar.addstr(0, max(0, tbarbreak - 1), f"{_lang['page']}: {thispage.rjust(len(lastpage))}/{lastpage}")
        except curses.error:
            pass
    topbar.refresh()


def updatemainwindow(content=None, colored=False):
    content = content or []
    displaywin.clear()

    if colored:
        _, width = displaywin.getmaxyx()
        parse_and_display_text(displaywin, content, width, colors, tag_pattern)
    else:
        for idx, line in enumerate(content):
            try:
                displaywin.addstr(idx, 1, line)
            except curses.error:
                pass
    displaywin.refresh()


def updatebottombar(left='', middle='', right=''):
    bottombar.clear()
    mycolwidth = int(screencols / 3)

    try:
        if left:
            ltext = f'<- {left}'
            bottombar.addstr(0, 0, ltext.ljust(mycolwidth)[:mycolwidth])

        if right:
            rtext = f'{right} ->'
            start_x = screencols - mycolwidth - 1
            bottombar.addstr(0, max(0, start_x), rtext.rjust(mycolwidth)[:mycolwidth])

        if middle:
            start_x = int(screencols / 2) - int(mycolwidth / 2)
            bottombar.addstr(0, max(0, start_x), middle.center(mycolwidth)[:mycolwidth])
    except curses.error:
        pass

    bottombar.refresh()


def nexthandler(*args):
    global selectedsong, selectedpage
    if not filelist:
        return

    if menuopen:
        loadsong()
        selectedpage = 0
        displaysong()
    else:
        if islastsong():
            displaysetlist(True)
        else:
            selectedpage = 0
            selectedsong += 1
            loadsong()
            displaysong()


def prevhandler(*args):
    global selectedsong, selectedpage
    if not filelist:
        return

    if not menuopen:
        if selectedpage > 0:
            selectedpage -= 1
            displaysong()
        elif selectedsong > 0:
            selectedsong -= 1
            loadsong()
            selectedpage = 0
            displaysong()
        else:
            displaysetlist(True)


def menuhandler(*args):
    if filelist and not menuopen:
        displaysetlist(True)


def uphandler(*args):
    global selectedsong, selectedpage
    if menuopen:
        if not filelist:
            selectedsong = -1
            return
        selectedsong = selectedsong - 1 if selectedsong > 0 else -1
        displaysetlist()
    else:
        if selectedpage > 0:
            selectedpage -= 1
            displaysong()


def downhandler(*args):
    global selectedsong, selectedpage
    if menuopen:
        if not filelist:
            selectedsong = -1
            return
        selectedsong = 0 if selectedsong == -1 else (selectedsong + 1) % len(filelist)
        displaysetlist()
    else:
        if not islastpage():
            selectedpage += 1
            displaysong()


def loadsongs():
    global filelist
    filelist.clear()

    if lyrics_path == Path(".") or not lyrics_path.exists():
        displayloadmedia()
    else:
        filelist = sorted([f.name for f in lyrics_path.iterdir() if f.is_file() and not f.name.startswith('.')])
        if filelist:
            displaysetlist(True)
        else:
            displayloadmedia()


def loadsong():
    global curfilelyrics
    curfilelyrics.clear()

    if not filelist or selectedsong >= len(filelist):
        return

    songpath = lyrics_path / filelist[selectedsong]
    try:
        all_lines = songpath.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception:
        all_lines = []

    displaylines = preprocess_text(all_lines, screencols - 4, tag_pattern)
    if not displaylines:
        displaylines.append(_lang['empty'])

    displaypagesize = max(1, displaywin.getmaxyx()[0])
    curfilelyrics = [displaylines[i:i + displaypagesize] for i in range(0, len(displaylines), displaypagesize)]


def displayloadmedia():
    global menuopen, selectedsong

    menuopen = True
    selectedsong = -1
    screenwin.erase()
    screenwin.hline(1, 0, curses.ACS_HLINE, screencols)
    screenwin.hline(screenlines - 2, 0, curses.ACS_HLINE, screencols)
    screenwin.refresh()
    updatetitlebar(clear=True)
    displaywin.clear()

    message = _lang['load_media']
    action = _lang['go_to_browser']
    display_height, display_width = displaywin.getmaxyx()
    action_row = max(0, (display_height - 2) // 2)
    message_row = min(display_height - 1, action_row + 1)
    action_x = max(0, (display_width - len(action)) // 2)
    message_x = max(0, (display_width - len(message)) // 2)

    try:
        displaywin.addnstr(
            action_row,
            action_x,
            action,
            display_width - action_x - 1,
            curses.A_REVERSE,
        )
        displaywin.addnstr(
            message_row,
            message_x,
            message,
            display_width - message_x - 1,
        )
    except curses.error:
        pass

    displaywin.refresh()
    updatebottombar(left='', middle='', right=_lang['select'])


def displaysetlist(clearscreen=False):
    global menuopen
    menuopen = True

    if clearscreen:
        updatetitlebar(title_override=_lang['setlist'])
        updatemainwindow()

    updatebottombar(left='', middle='', right=_lang['select'])

    maxstrlen = max((len(songtitle(f)) for f in filelist), default=0)
    maxstrlen = min(maxstrlen, screencols - 6)

    pad_height = len(filelist) + 2
    pad_width = maxstrlen + 4
    pad = curses.newpad(pad_height, pad_width)
    pad.box()

    for songnum, f in enumerate(filelist):
        title = songtitle(f, maxstrlen)
        if songnum == selectedsong:
            pad.attron(curses.A_STANDOUT)
        else:
            pad.attroff(curses.A_STANDOUT)
        try:
            pad.addstr(songnum + 1, 2, title)
        except curses.error:
            pass

    topy = max(0, int((screenlines - pad_height) / 2))
    topx = max(0, int((screencols - pad_width) / 2))

    try:
        browser_label = _lang['go_to_browser']
        browser_attr = curses.A_REVERSE if selectedsong == -1 else curses.A_NORMAL
        browser_x = max(0, int((screencols - len(browser_label)) / 2))
        screenwin.addnstr(max(0, topy - 1), browser_x, browser_label, screencols - browser_x - 1, browser_attr)
        pad.refresh(0, 0, topy, topx, topy + pad_height, topx + pad_width)
    except curses.error:
        pass


def displaysong():
    global menuopen
    menuopen = False

    updatetitlebar()

    right_label = _lang['menu'] if islastsong() else _lang['next_song']
    middle_label = _lang['next_page'] if not islastpage() else ''
    left_label = _lang['prev_song']

    updatebottombar(left=left_label, middle=middle_label, right=right_label)

    if curfilelyrics and selectedpage < len(curfilelyrics):
        updatemainwindow(content=curfilelyrics[selectedpage], colored=True)


def curseswrapper(stdscr):
    global screenlines, screencols, topbar, displaywin, bottombar, screenwin, colors, tag_pattern

    colors = init_colors()
    tag_pattern = create_tag_regex(colors)
    screenwin = stdscr

    screenlines, screencols = curses.LINES, curses.COLS
    curses.halfdelay(1)
    stdscr.clear()
    curses.curs_set(0)

    topbar = stdscr.subwin(1, screencols, 0, 0)
    stdscr.hline(1, 0, curses.ACS_HLINE, screencols)
    displaywin = stdscr.subwin(screenlines - 4, screencols, 2, 0)
    stdscr.hline(screenlines - 2, 0, curses.ACS_HLINE, screencols)
    bottombar = stdscr.subwin(1, screencols, screenlines - 1, 0)

    stdscr.refresh()
    loadsongs()

    while True:
        key = stdscr.getch()
        if key in (ord('q'), ord('Q'), 27):
            return "quit"
        elif key == curses.KEY_LEFT:
            prevhandler()
        elif key == curses.KEY_RIGHT:
            if menuopen and selectedsong == -1:
                return "browser"
            nexthandler()
        elif key == curses.KEY_UP:
            uphandler()
        elif key == curses.KEY_DOWN:
            downhandler()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        setpath(sys.argv[1])

    curses.wrapper(curseswrapper)