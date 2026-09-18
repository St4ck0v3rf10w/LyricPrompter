import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
BIN = os.path.join(ROOT, "bin")
if BIN not in sys.path:
    sys.path.insert(0, BIN)

import browser
import prompter


def test_browser_run_delegates_to_browser_function(monkeypatch):
    seen = {}

    def fake_browser(stdscr):
        seen["stdscr"] = stdscr
        return "/tmp/lyrics"

    monkeypatch.setattr(browser, "browser", fake_browser)
    assert browser.run("screen") == "/tmp/lyrics"
    assert seen["stdscr"] == "screen"


def test_prompter_run_delegates_to_curseswrapper(monkeypatch):
    seen = {}

    def fake_curseswrapper(stdscr):
        seen["stdscr"] = stdscr
        return "browser"

    monkeypatch.setattr(prompter, "curseswrapper", fake_curseswrapper)
    assert prompter.run("screen", "/tmp/lyrics") == "browser"
    assert seen["stdscr"] == "screen"
