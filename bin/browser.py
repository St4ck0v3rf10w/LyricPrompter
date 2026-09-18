#!/usr/bin/env python3

import curses
import os

import config

_lang = config._lang

def can_enter(path):
    try:
        os.listdir(path)
        return True
    except (PermissionError, OSError):
        return False


def is_leaf(path):
    """
    Blatt im Baum:
    Enthält keine betretbaren Unterordner.
    """
    try:
        for entry in os.listdir(path):
            full = os.path.join(path, entry)

            try:
                if os.path.isdir(full) and can_enter(full):
                    return False
            except (PermissionError, OSError):
                pass

        return True

    except (PermissionError, OSError):
        return False


def rel_path(path):
    rel = os.path.relpath(path, config.ROOT_PATH)

    if rel == ".":
        return "/"

    return "/" + rel.replace("\\", "/")


def get_directories(path):
    result = []

    try:
        for entry in sorted(os.listdir(path), key=str.lower):
            full = os.path.join(path, entry)

            try:
                if os.path.isdir(full):
                    result.append(entry)
            except (PermissionError, OSError):
                pass

    except (PermissionError, OSError):
        pass

    return result


def run(stdscr):
    return browser(stdscr)


def browser(stdscr):

    curses.curs_set(0)

    path = config.ROOT_PATH
    selected = 0

    selection_history = {}

    armed_leaf = False
    armed_path = None

    while True:

        stdscr.clear()

        entries = get_directories(path)

        if os.path.normcase(path) != os.path.normcase(config.ROOT_PATH):
            entries = [".."] + entries

        if entries:
            selected = min(selected, len(entries) - 1)
        else:
            selected = 0

        h, w = stdscr.getmaxyx()

        labels = []
        for entry in entries:
            label = entry
            if entry != "..":
                if can_enter(os.path.join(path, entry)):
                    label += "/"
                else:
                    label += f" {_lang['denied']}"
            labels.append(label)

        current_directory = rel_path(path)
        max_label_width = max(
            [len(current_directory)] + [len(label) for label in labels],
            default=0,
        )
        box_width = min(max(28, max_label_width + 4), max(4, w - 2))
        box_height = min(max(4, len(entries) + 4), max(4, h - 2))
        box_top = max(1, (h - box_height) // 2)
        box_left = max(0, (w - box_width) // 2)

        action_attr = curses.A_REVERSE if selected == -1 else curses.A_NORMAL
        action = _lang['return_to_prompter']
        action_x = max(0, (w - len(action)) // 2)
        try:
            stdscr.addnstr(max(0, box_top - 1), action_x, action, w - action_x - 1, action_attr)
        except curses.error:
            pass

        panel = curses.newwin(box_height, box_width, box_top, box_left)
        panel.box()
        try:
            panel.addnstr(
                1,
                1,
                current_directory.center(box_width - 2),
                box_width - 2,
                curses.A_BOLD,
            )
            panel.hline(2, 1, curses.ACS_HLINE, box_width - 2)
        except curses.error:
            pass

        visible_entries = entries[:max(0, box_height - 4)]
        list_top = 3
        for i, entry in enumerate(visible_entries):

            full = os.path.join(path, entry)

            label = labels[i]

            if (
                armed_leaf
                and armed_path == full
                and i == selected
            ):
                label += f" <-{_lang['select_folder']}"

            attr = curses.A_REVERSE if i == selected else curses.A_NORMAL
            row_text = label.center(box_width - 2)[:box_width - 2]

            try:
                panel.addnstr(list_top + i, 1, row_text, box_width - 2, attr)
            except curses.error:
                pass

        stdscr.refresh()

        try:
            panel.refresh()
        except curses.error:
            pass

        key = stdscr.getch()

        if key == ord("q"):
            break

        elif key == curses.KEY_UP:

            armed_leaf = False
            armed_path = None

            selected = selected - 1 if selected > 0 else -1

        elif key == curses.KEY_DOWN:

            armed_leaf = False
            armed_path = None

            selected = min(len(entries) - 1, selected + 1)

        elif key == curses.KEY_RIGHT:

            if selected == -1:
                return "prompter"

            if not entries:
                continue

            chosen = entries[selected]

            if chosen == "..":

                armed_leaf = False
                armed_path = None

                selection_history[path] = selected

                parent = os.path.dirname(path)

                if os.path.commonpath([config.ROOT_PATH, parent]) == config.ROOT_PATH:
                    path = parent
                    selected = selection_history.get(path, 0)

            else:

                target = os.path.join(path, chosen)

                try:

                    if can_enter(target):

                        if is_leaf(target):

                            if (
                                armed_leaf
                                and armed_path == target
                            ):

                                return target

                            armed_leaf = True
                            armed_path = target

                        else:

                            armed_leaf = False
                            armed_path = None

                            selection_history[path] = selected

                            path = target

                            selected = selection_history.get(
                                path,
                                0
                            )

                except (PermissionError, OSError):
                    curses.flash()

        elif key == curses.KEY_LEFT:

            armed_leaf = False
            armed_path = None

            if os.path.normcase(path) != os.path.normcase(config.ROOT_PATH):

                selection_history[path] = selected

                path = os.path.dirname(path)

                selected = selection_history.get(path, 0)


if __name__ == "__main__":
    curses.wrapper(browser)