#!/usr/bin/env python3

from enum import Enum, auto

import curses
import os
import shutil

import browser
import config
import prompter


class State(Enum):
    BROWSER = auto()
    PROMPTER = auto()
    EXIT = auto()


class App:

    def __init__(self):
        self.state = State.BROWSER
        self.selected_folder = None
        self.handlers = {
            State.BROWSER: self.state_browser,
            State.PROMPTER: self.state_prompter,
        }

    def state_browser(self, stdscr):
        selected_folder = browser.run(stdscr)

        if selected_folder == "prompter":
            self.state = State.PROMPTER
        elif selected_folder:
            self.selected_folder = selected_folder
            self.sync_selected_folder()
            self.state = State.PROMPTER
        else:
            self.state = State.EXIT

    def sync_selected_folder(self):
        if not self.selected_folder:
            return

        os.makedirs(config.LYRIC_DESTINATION_PATH, exist_ok=True)

        for entry in os.listdir(config.LYRIC_DESTINATION_PATH):
            full = os.path.join(config.LYRIC_DESTINATION_PATH, entry)
            if os.path.isfile(full) and entry.lower().endswith(".txt"):
                os.remove(full)

        for entry in os.listdir(self.selected_folder):
            src = os.path.join(self.selected_folder, entry)
            dst = os.path.join(config.LYRIC_DESTINATION_PATH, entry)
            if os.path.isfile(src) and entry.lower().endswith(".txt"):
                shutil.copy2(src, dst)

    def state_prompter(self, stdscr):
        result = prompter.run(
            stdscr,
            config.LYRIC_DESTINATION_PATH
        )

        if result == "browser":
            self.state = State.BROWSER
        elif result in ("exit", "quit"):
            self.state = State.EXIT
        else:
            self.state = State.BROWSER

    def run(self, stdscr):

        curses.curs_set(0)

        while self.state != State.EXIT:

            handler = self.handlers.get(self.state)

            if handler is None:
                raise RuntimeError(
                    f"No handler registered for state {self.state}"
                )

            handler(stdscr)


def main(stdscr):

    app = App()

    app.run(stdscr)


if __name__ == "__main__":

    curses.wrapper(main)