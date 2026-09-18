# LyricPrompter

Ein textbasierter Prompter für Liedtexte auf einem Raspberry Pi mit piCore/TinyCore Linux. Das Programm wird vollständig im Terminal ausgeführt und kann mit einer USB-Fußschalter-Tastatur bedient werden. Die vier Pfeiltasten reichen für die Navigation aus.

Das Projekt durchsucht Verzeichnisse nach Lyrics, zeigt die Liedauswahl an und stellt den Text seitenweise dar. USB-Datenträger können über eine udev-Regel automatisch read-only eingehängt und beim Entfernen wieder ausgehängt werden.

## Inhaltsverzeichnis

- [Funktionen](#funktionen)
- [Projektstruktur](#projektstruktur)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [Lyrics vorbereiten](#lyrics-vorbereiten)
- [Bedienung](#bedienung)
- [USB-Automount unter piCore](#usb-automount-unter-picore)
- [Autostart](#autostart)
- [Tests](#tests)
- [Fehlersuche](#fehlersuche)
- [Bekannte Grenzen](#bekannte-grenzen)

## Funktionen

- Terminal-Oberfläche auf Basis von Python `curses`
- Navigation ausschließlich über `Up`, `Down`, `Left` und `Right`
- Auswahl eines Lyrics-Verzeichnisses über einen integrierten Browser
- Rückkehr vom Browser zum Prompter über die sichtbare Option „Return to prompter“ beziehungsweise deren Übersetzung
- Anzeige der Lieddateien in einer mittig dargestellten, umrandeten Auswahl
- Seitenweise Anzeige langer Liedtexte
- Zentrierte Darstellung der Textzeilen
- Farbige Textabschnitte über Tags wie `<red>` und `</red>`
- Deutsch und Englisch als konfigurierbare Benutzeroberflächen
- Read-only-USB-Mount über eine udev-Regel
- Kopieren des gewählten Verzeichnisses in das lokale Lyrics-Zielverzeichnis
- Funktioniert auch ohne angeschlossenen USB-Datenträger: Der Prompter zeigt dann die Option zum Öffnen des Browsers an

## Projektstruktur

```text
LyricPrompter/
├── bin/
│   ├── browser.py       # Verzeichnisbrowser
│   ├── config.py        # Pfade und Sprache
│   ├── main.py          # Haupteinstieg und Zustandswechsel
│   └── prompter.py      # Liedauswahl und Textanzeige
├── etc/
│   └── udev/rules.d/
│       └── 11-media-by-label-auto-mount.rules
├── tests/
│   └── test_app_entrypoints.py
├── Lyrics/              # lokale Beispieldaten, nicht für Git bestimmt
├── TestData/            # Test-/USB-Ersatzdaten, nicht für Git bestimmt
├── .gitignore
└── README.md
```

Die Verzeichnisse `Lyrics/`, `TestData/`, Python-Cache-Dateien und `__pycache__/` werden durch `.gitignore` vom Git-Upload ausgeschlossen.

## Voraussetzungen

### Entwicklung unter Windows, Linux oder macOS

- Python 3.11 oder neuer
- Ein Terminal mit Unterstützung für `curses`
- Schreibrechte auf das konfigurierte Zielverzeichnis

Unter Windows wird das Standardmodul `curses` nicht von jeder Python-Installation mitgeliefert. Für die eigentliche piCore-Zielumgebung ist Linux mit `ncurses` vorgesehen.

### Zielsystem piCore

Getestet wurde das Projekt mit:

- piCore 14.1.0
- Raspberry Pi 3B+
- Python 3.11
- `ncurses-terminfo`
- `socat` wird vom aktuellen Programm nicht benötigt, kann aber bei älteren Versionen oder eigenen Integrationen vorhanden sein

Die Python-Version und Paketnamen können je nach piCore-Version abweichen.

## Installation

### Repository holen

```sh
git clone <REPOSITORY-URL> ~/LyricPrompter
cd ~/LyricPrompter
```

Falls das Repository bereits vorhanden ist:

```sh
cd ~/LyricPrompter
git pull
```

### Programm testen

Das Programm wird vom Projektverzeichnis aus gestartet:

```sh
python3 bin/main.py
```

Alternativ kann der aktuelle Arbeitsordner direkt als Testwurzel verwendet werden, wenn die Pfade in `bin/config.py` entsprechend gesetzt sind.

Beim Start öffnet sich zunächst der Browser. Dort wird ein Verzeichnis mit Lieddateien ausgewählt. Nach der Auswahl werden dessen Dateien nach `LYRIC_DESTINATION_PATH` kopiert und im Prompter geöffnet.

## Konfiguration

Alle wichtigen Einstellungen befinden sich in [bin/config.py](bin/config.py).

### Pfade

```python
USB_MOUNT_PATH = "/media/MeinUSBStick"
LYRIC_DESTINATION_PATH = "/home/tc/LyricPrompter/Lyrics"
ROOT_PATH = USB_MOUNT_PATH
```

`ROOT_PATH` ist die Wurzel des Browsers. Normalerweise zeigt sie auf das Verzeichnis, unter dem der USB-Stick eingehängt wird.

`LYRIC_DESTINATION_PATH` ist das lokale Ziel, in das der Inhalt des ausgewählten Ordners kopiert wird. Der Prompter liest die Lieddateien anschließend aus diesem Verzeichnis.

Die momentan im Repository eingetragenen Windows-Pfade sind für die lokale Entwicklung gedacht. Für piCore müssen sie durch Linux-Pfade ersetzt werden.

### Sprache

Die Sprache wird über `LANGUAGE` eingestellt:

```python
LANGUAGE = "german"
```

Mögliche Werte:

```python
LANGUAGE = "german"
LANGUAGE = "english"
```

Die sichtbaren Texte liegen in den Dictionaries `german` und `english`. Wenn eine weitere Sprache benötigt wird, kann dort ein weiteres Dictionary ergänzt und anschließend in `languages` registriert werden.

## Lyrics vorbereiten

### Verzeichnisaufbau

Der Browser zeigt Verzeichnisse an. Ein ausgewähltes Verzeichnis sollte direkt die Lieddateien enthalten, zum Beispiel:

```text
USB-Stick/
├── Konzert/
│   ├── 01_Erster Song.txt
│   ├── 02_Zweiter Song.txt
│   └── 03_Dritter Song.txt
└── Probe/
    └── 01_Test.txt
```

Ein Ordner ohne weitere Unterordner wird als Lyrics-Ordner behandelt. Bei der ersten Auswahl eines solchen Ordners wird die Auswahl markiert. Mit `Right` wird sie bestätigt.

### Dateiformat

- Unterstützt werden normale Textdateien mit der Endung `.txt` oder `.TXT`.
- Die Dateien werden alphabetisch sortiert.
- Nummerierte Dateinamen sorgen für eine gewünschte Reihenfolge, zum Beispiel `01_...`, `02_...` und `03_...`.
- Versteckte Dateien werden ignoriert.
- Die Dateien sollten UTF-8 verwenden.

### Farb-Tags

Der Prompter kann bestimmte Farb-Tags im Text interpretieren. Beispiel:

```text
<red>Strophe in Rot</red>
<green>Strophe in Grün</green>
<yellow>Hinweis in Gelb</yellow>
```

Verfügbare Farbnamen entsprechen den Farbschlüsseln in `init_colors()` in [bin/prompter.py](bin/prompter.py), unter anderem:

```text
red, green, yellow, blue, magenta, cyan, white
```

Die Tags werden nicht als sichtbarer Text ausgegeben. Nicht geschlossene oder unbekannte Tags sollten vermieden werden.

## Bedienung

Die Bedienung ist für eine Tastatur oder einen Fußschalter ausgelegt, der die vier Pfeiltasten erzeugt.

### Browser

| Taste | Funktion |
|---|---|
| `Up` | Vorherigen Eintrag auswählen; vom ersten Eintrag zur Option „Return to prompter“ wechseln |
| `Down` | Nächsten Eintrag auswählen; von der oberen Option zurück zur Liste wechseln |
| `Right` | Verzeichnis öffnen, über `..` zum übergeordneten Verzeichnis wechseln oder eine Auswahl bestätigen |
| `Left` | Zum übergeordneten Verzeichnis wechseln |
| `q` | Anwendung beenden |

Ein Blattverzeichnis wird bei der ersten Bestätigung markiert. Die zweite Bestätigung mit `Right` übernimmt es als Lyrics-Verzeichnis.

Die Aktion oberhalb des Browser-Rahmens führt zurück zum Prompter. Das ist besonders hilfreich, wenn bereits ein Lyrics-Zielverzeichnis geladen ist.

### Prompter

| Taste | Funktion |
|---|---|
| `Up` | Vorheriges Lied oder vorherige Seite; aus der ersten Auswahl zur Browser-Option wechseln |
| `Down` | Nächstes Lied oder nächste Seite |
| `Right` | Lied öffnen, nächste Seite anzeigen oder die Browser-Option öffnen |
| `Left` | Vorheriges Lied beziehungsweise vorherige Seite |
| `q` oder `Esc` | Anwendung beenden |

Wenn keine Lyrics vorhanden sind, wird `USB-Stick einlegen` mittig angezeigt. Die Option `Zum Browser` beziehungsweise `Go to browser` steht darüber und kann mit `Up` und `Right` ausgewählt werden.

## USB-Automount unter piCore

Die Datei [etc/udev/rules.d/11-media-by-label-auto-mount.rules](etc/udev/rules.d/11-media-by-label-auto-mount.rules) übernimmt das automatische Mounten und Unmounten.

Die Regel:

1. erkennt USB-Datenträger beziehungsweise deren Partitionen,
2. liest das Dateisystem-Label mit `blkid`,
3. erstellt ein Verzeichnis unter `/media/`,
4. mountet das Gerät read-only,
5. hängt es beim Entfernen wieder aus und entfernt das leere Mount-Verzeichnis.

Es werden keine zusätzlichen `usbmount`- oder `usbumount`-Skripte benötigt. Das Mounten erfolgt direkt über `/bin/mount`, das Aushängen über `/bin/umount`.

### Regel installieren

```sh
sudo mkdir -p /etc/udev/rules.d
sudo cp ~/LyricPrompter/etc/udev/rules.d/11-media-by-label-auto-mount.rules \
    /etc/udev/rules.d/11-media-by-label-auto-mount.rules
```

Danach Regeln neu laden:

```sh
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Bei piCore müssen Änderungen außerdem persistent gespeichert werden. Je nach Installation gehören die Regel und die Projektdateien in die Persistenzkonfiguration, zum Beispiel `/opt/filelist.lst`, und anschließend muss gespeichert werden:

```sh
filetool.sh -b
```

### Mount-Optionen

Die Regel verwendet grundsätzlich:

```text
relatime,ro
```

Für FAT- und NTFS-Dateisysteme werden zusätzlich unter anderem UTF-8 und die Gruppen-/Maskenoptionen gesetzt. Der USB-Stick wird damit read-only eingebunden. Das schützt die Daten auf dem Stick, ersetzt aber kein Backup.

### Wichtiger Hinweis zur udev-Regel

udev-Regeln laufen mit einer eingeschränkten Umgebung. Verwende deshalb absolute Pfade wie `/bin/mount`, `/bin/umount` und `/bin/mkdir`. Prüfe auf deinem piCore-System mit `which mount`, `which umount` und `which mkdir`, ob die Pfade stimmen.

Nach Änderungen sollte die Regel mit einem echten USB-Gerät getestet werden. Bereits eingehängte Geräte werden durch das bloße Neuladen der Regeln nicht immer automatisch neu verarbeitet.

## Autostart

Damit der Prompter nach dem Booten automatisch startet, kann er aus `~/.profile` aufgerufen werden. Ein einfaches Beispiel:

```sh
cd ~/LyricPrompter
python3 bin/main.py
```

Für einen größeren Terminaltext kann vor dem Programmstart eine passende Konsole-Schrift gesetzt werden. Der genaue Pfad hängt von der installierten piCore-Schrift ab, zum Beispiel:

```sh
setfont /usr/share/consolefonts/Lat15-TerminusBold32x16.psf.gz
cd ~/LyricPrompter
python3 bin/main.py
```

Wenn eine grafische Desktop-Umgebung nicht benötigt wird, sollte piCore auf Konsolen-Autologin eingerichtet werden. Die genaue Konfiguration hängt vom verwendeten piCore-Image ab.

### Terminal-Eingabe sicherstellen

Das Programm benötigt die echte Terminal-Eingabe, damit die Pfeiltasten zuverlässig ankommen. Starte es deshalb aus einer interaktiven Login-Shell und nicht aus einer Pipe oder einem Prozess, der die Standardeingabe umleitet.

## Tests

Die Tests benötigen `pytest`:

```sh
python3 -m pip install pytest
python3 -m pytest -q
```

Die vorhandenen Tests prüfen aktuell die Einstiegspunkte von Browser und Prompter. Sie laufen ohne curses-Oberfläche und sind daher auch für die Entwicklung auf einem Desktop-System geeignet.

Für einen manuellen Funktionstest:

1. Lege mindestens ein Verzeichnis mit `.txt`-Dateien in der konfigurierten Browser-Wurzel an.
2. Starte `python3 bin/main.py`.
3. Öffne das Verzeichnis mit `Right`.
4. Bestätige einen Lyrics-Ordner zweimal mit `Right`.
5. Navigiere im Prompter durch Auswahl, Lied und Seiten.
6. Prüfe mit `Up` die Option zum Browser und öffne sie mit `Right`.
7. Teste den Fall ohne USB-Stick beziehungsweise ohne Lyrics.

## Fehlersuche

### Der Browser zeigt keine Verzeichnisse

Prüfe:

```sh
ls -la /media
ls -la /media/<USB-LABEL>
```

Kontrolliere anschließend `ROOT_PATH` in `bin/config.py`. Der Pfad muss exakt auf den tatsächlichen Mount-Punkt zeigen.

### Der USB-Stick wird nicht automatisch eingehängt

Prüfe die udev-Regel:

```sh
udevadm control --reload-rules
udevadm monitor --udev --property
```

Stecke den USB-Stick danach neu ein und kontrolliere mit:

```sh
mount
ls -la /media
```

Prüfe außerdem, ob das Dateisystem erkannt wird:

```sh
blkid
```

### Der Prompter zeigt „USB-Stick einlegen“

Das bedeutet, dass `LYRIC_DESTINATION_PATH` nicht existiert oder keine passenden Textdateien enthält. Prüfe:

```sh
ls -la /home/tc/LyricPrompter/Lyrics
```

Der Pfad muss mit `LYRIC_DESTINATION_PATH` übereinstimmen.

### Die Pfeiltasten reagieren nicht

- Starte das Programm in einer echten interaktiven Konsole.
- Prüfe, ob der Fußschalter tatsächlich normale Pfeiltasten sendet.
- Teste die Eingabe vorübergehend mit `showkey` oder einem einfachen Terminalprogramm.
- Stelle sicher, dass kein Autostart-Skript die Standardeingabe umleitet.

### Ein Lyrics-Ordner lässt sich nicht auswählen

Ein Ordner wird erst nach der ersten Bestätigung markiert. Drücke `Right` ein zweites Mal, sobald `Select` beziehungsweise `Auswählen` angezeigt wird.

### Das Mount-Verzeichnis bleibt bestehen

Das Verzeichnis wird nur entfernt, wenn es nach dem Aushängen leer ist. Prüfe, ob das Gerät wirklich ausgehängt wurde:

```sh
mount | grep /media
```

Falls noch ein Prozess auf den Mount-Punkt zugreift, kann `rmdir` fehlschlagen.

## Bekannte Grenzen

- Die Oberfläche ist für Terminalgrößen mit ausreichend Höhe und Breite ausgelegt.
- Es gibt aktuell keine automatische Synchronisation zurück auf den USB-Stick. Die Auswahl wird in das lokale Zielverzeichnis kopiert.
- Das Zielverzeichnis wird aktuell nicht automatisch vollständig geleert, bevor neue Dateien kopiert werden. Alte Dateien können daher erhalten bleiben.
- Konflikte beim Kopieren bereits vorhandener Dateien oder Verzeichnisse müssen auf dem Zielsystem beachtet werden.
- Nur Textdateien werden unterstützt; PDF, Word, RTF und Bilddateien werden nicht verarbeitet.
- Die udev-Regel ist auf Linux/piCore ausgelegt und funktioniert nicht unter Windows.
- Eine sichere Entfernung des USB-Sticks sollte erst erfolgen, wenn keine Lesezugriffe mehr stattfinden.

## Sicherheit und Datensicherung

Der USB-Mount erfolgt read-only, damit der Prompter keine Dateien auf dem Stick verändert. Trotzdem sollte der Stick nicht als einzige Kopie der Liedtexte verwendet werden. Halte immer eine separate Sicherung der Lyrics bereit.

Die Pfade in `bin/config.py` können absolute lokale Pfade enthalten. Prüfe vor dem Commit, ob dort keine privaten Verzeichnisnamen oder Zugangsdaten stehen.

## Lizenz

Siehe [LICENSE](LICENSE).

## Projektstatus

Das Projekt ist auf den persönlichen Einsatz als einfacher Bühnen-Prompter ausgerichtet. Vor einem Live-Einsatz sollten insbesondere USB-Wechsel, Stromausfall, Terminalgröße, Fußschalter-Eingaben und die komplette Bootsequenz auf der konkreten piCore-Hardware getestet werden.
