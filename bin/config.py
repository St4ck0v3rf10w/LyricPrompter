USB_MOUNT_PATH = "C:\\Users\\Ludwig\\Documents\\GitHub\\LyricPrompter\\TestData"
LYRIC_DESTINATION_PATH = "C:\\Users\\Ludwig\\Documents\\GitHub\\LyricPrompter\\Lyrics"


# Single source of truth for the fixed filesystem layout.
ROOT_PATH = USB_MOUNT_PATH

# Set this to "english" or "german" to change the user interface language.
LANGUAGE = "german"

english = {
    'welcome': "Welcome",
    'load_media': "Insert USB Stick",
    'select': "Select",
    'setlist': "Setlist",
    'menu': "Menu",
    'prev_song': "Prev Song",
    'next_song': "Next Song",
    'next_page': "Next Page",
    'prev_page': "Prev Page",
    'page': "Page",
    'empty': "Empty File - No Text Found",
    'return_to_prompter': "Return to prompter",
    'go_to_browser': "Go to browser",
    'select_folder': "Select",
    'denied': "[DENIED]"
}

german = {
    'welcome': "Willkommen",
    'load_media': "USB-Stick einlegen",
    'select': "Auswählen",
    'setlist': "Setlist",
    'menu': "Menü",
    'prev_song': "Vorheriger Song",
    'next_song': "Nächster Song",
    'next_page': "Nächste Seite",
    'prev_page': "Vorherige Seite",
    'page': "Seite",
    'empty': "Leere Datei - Kein Text gefunden",
    'return_to_prompter': "Zum Prompter zurück",
    'go_to_browser': "Zum Browser",
    'select_folder': "Auswählen",
    'denied': "[VERWEIGERT]"
}

languages = {
    "english": english,
    "german": german,
}

_lang = languages[LANGUAGE]