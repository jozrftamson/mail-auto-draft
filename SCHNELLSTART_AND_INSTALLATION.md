============================================================
WICHTIG: SCHNELLSTART, INSTALLATION UND BETRIEB
mail-auto-draft
============================================================

Diese Datei ist die zentrale Anleitung fuer spaetere Installation,
Migration auf andere Rechner und Weitergabe an andere Nutzer.

Pfad:
/home/josef/Projekte/Automation/mail-auto-draft/SCHNELLSTART_AND_INSTALLATION.md

Merke:
- Diese Datei zuerst lesen
- Diese Datei nicht loeschen
- Diese Datei fuer Neuinstallation auf anderem Rechner verwenden

============================================================
SCHNELLSTART
============================================================

============================================================
ZIEL
============================================================
- Diese Anleitung beschreibt, wie man die Mail-Automatisierung auf einem anderen Rechner schnell nachbauen kann.
- Das System liest eingehende E-Mails via Himalaya, bewertet sie und beantwortet einfache Standardfälle automatisch.
- Eigene E-Mails werden ignoriert, damit keine Antwort-Schleife entsteht.

============================================================
FUNKTIONSUMFANG
============================================================
- neue INBOX-Mails lesen
- Reply-To vor From bevorzugen
- eigenes Postfach vor Self-Reply-Loops schützen
- Newsletter/Systemmails möglichst ignorieren
- einfache Standardanfragen automatisch beantworten
- unklare, individuelle und sensible Fälle nur als Entwurf behandeln oder blockieren
- systemd User Timer für automatischen Hintergrundbetrieb

============================================================
PROJEKTSTRUKTUR
============================================================
- Projektpfad: /home/josef/Projekte/Automation/mail-auto-draft
- Wichtige Dateien:
  - config.yaml
  - process_inbox.py
  - prompts/system_prompt.txt
  - prompts/user_prompt.txt
  - logs/mail_actions.jsonl
  - data/processed_ids.json
  - drafts/
  - runtime/

============================================================
VORAUSSETZUNGEN
============================================================
- Ubuntu / Linux
- Python 3
- Himalaya installiert
- Gmail oder anderes IMAP/SMTP-Postfach
- Python-Pakete:
  - pyyaml
  - requests

============================================================
1. HIMALAYA INSTALLIEREN
============================================================
- Prüfen:
  himalaya --version

Falls nicht installiert, je nach System z. B.:
- Ubuntu mit vorhandenem Binary oder manuell laut Himalaya-Doku
- danach erneut prüfen:
  himalaya --version

============================================================
2. PYTHON-ABHAENGIGKEITEN INSTALLIEREN
============================================================
- Beispiel:
  python3 -m pip install --user pyyaml requests

============================================================
3. PROJEKT AUF NEUEN RECHNER KOPIEREN
============================================================
- gesamten Ordner kopieren:
  /home/josef/Projekte/Automation/mail-auto-draft

Wichtige Unterordner:
- drafts/
- logs/
- data/
- runtime/

Falls sie fehlen, werden sie vom Skript beim Lauf automatisch angelegt.

============================================================
4. HIMALAYA KONFIGURIEREN
============================================================
Datei:
- ~/.config/himalaya/config.toml

Beispiel für Gmail:

[accounts.gmail]
email = "DEINE-EMAIL@gmail.com"
display-name = "DEIN NAME"
default = true

download-dir = "/home/DEINUSER/Downloads"

backend.type = "imap"
backend.host = "imap.gmail.com"
backend.port = 993
backend.encryption.type = "tls"
backend.login = "DEINE-EMAIL@gmail.com"
backend.auth.type = "password"
backend.auth.cmd = "printf '%s' 'DEIN_APP_PASSWORT'"

message.send.backend.type = "smtp"
message.send.backend.host = "smtp.gmail.com"
message.send.backend.port = 587
message.send.backend.encryption.type = "start-tls"
message.send.backend.login = "DEINE-EMAIL@gmail.com"
message.send.backend.auth.type = "password"
message.send.backend.auth.cmd = "printf '%s' 'DEIN_APP_PASSWORT'"

[accounts.gmail.folder.alias]
inbox = "INBOX"
sent = "[Gmail]/Sent Mail"
drafts = "[Gmail]/Drafts"
trash = "[Gmail]/Trash"

Wichtig:
- Bei Gmail App-Passwort verwenden, nicht das normale Passwort.
- Niemals echte Zugangsdaten in Doku, Git oder öffentliche Dateien committen.
- Besser später auth.cmd durch sicherere Secret-Verwaltung ersetzen.

============================================================
5. CONFIG.YAML ANPASSEN
============================================================
Wichtige Felder:
- mode: auto oder draft
- account: z. B. gmail
- own_addresses:
  - muss die eigene E-Mail enthalten
- paths:
  - auf den neuen Rechner anpassen, falls der Pfad anders ist

Pflichtpunkt:
own_addresses:
  - DEINE-EMAIL@gmail.com

Warum wichtig:
- verhindert, dass das System eigene gesendete Mails erneut beantwortet
- verhindert Antwort-Schleifen

Empfohlene produktive Einstellungen
- mode: auto
- confidence_threshold: 70
- require_unseen: true
- require_new_in_inbox: true
- require_whitelist: true
- require_high_confidence: true
- forbid_sensitive_categories:
  - sensibel
  - individuell
  - unklar
  - ignorieren

Bedeutung:
- nur neue Mails werden beantwortet
- nur whitelisted Standardfälle werden automatisch beantwortet
- unklare oder heikle Fälle gehen nicht automatisch raus

============================================================
6. SYNTAX UND GRUNDFUNKTION PRUEFEN
============================================================
Im Projektordner:
- python3 -m py_compile process_inbox.py

Manueller Testlauf im Entwurfsmodus:
- python3 /home/josef/Projekte/Automation/mail-auto-draft/process_inbox.py --mode draft --limit 5

Manueller Testlauf im Auto-Modus:
- python3 /home/josef/Projekte/Automation/mail-auto-draft/process_inbox.py --mode auto --limit 1

============================================================
7. SYSTEMD USER TIMER EINRICHTEN
============================================================
Datei:
- ~/.config/systemd/user/mail-auto-draft.service

Inhalt:
[Unit]
Description=Process inbox and auto-reply via Himalaya
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/home/josef/Projekte/Automation/mail-auto-draft
ExecStart=/usr/bin/flock -n /home/josef/Projekte/Automation/mail-auto-draft/runtime/process_inbox.lock /usr/bin/python3 /home/josef/Projekte/Automation/mail-auto-draft/process_inbox.py --limit 5

Datei:
- ~/.config/systemd/user/mail-auto-draft.timer

Inhalt:
[Unit]
Description=Run mail auto-draft every minute

[Timer]
OnBootSec=2min
OnUnitActiveSec=60s
Persistent=true
Unit=mail-auto-draft.service

[Install]
WantedBy=timers.target

Aktivieren:
- systemctl --user daemon-reload
- systemctl --user enable --now mail-auto-draft.timer

Sofortiger Testlauf:
- systemctl --user start mail-auto-draft.service

============================================================
8. WICHTIGE BETRIEBS-KOMMANDOS
============================================================
Status:
- systemctl --user status mail-auto-draft.timer --no-pager
- systemctl --user status mail-auto-draft.service --no-pager

Timer anzeigen:
- systemctl --user list-timers --all --no-pager | grep mail-auto-draft

Logs ansehen:
- journalctl --user -u mail-auto-draft.service -n 50 --no-pager

Timer stoppen:
- systemctl --user stop mail-auto-draft.timer

Timer starten:
- systemctl --user start mail-auto-draft.timer

Timer dauerhaft deaktivieren:
- systemctl --user disable --now mail-auto-draft.timer

============================================================
9. WICHTIGE PROJEKT-LOGS
============================================================
JSONL-Protokoll:
- /home/josef/Projekte/Automation/mail-auto-draft/logs/mail_actions.jsonl

Darin sieht man pro Mail zum Beispiel:
- action
- reason
- chosen_reply_recipient
- chosen_reply_source
- sent
- draft_path

Wichtige Werte:
- action: auto_sent
  => Mail wurde gesendet
- action: drafted
  => nur Entwurf, nicht gesendet
- action: ignored
  => bewusst ignoriert
- reason: self_sender
  => eigene Mail erkannt, daher keine Antwort

============================================================
10. BEKANNTE BESONDERHEIT BEI GMAIL / HIMALAYA
============================================================
Es kann vorkommen, dass SMTP erfolgreich sendet, aber Himalaya danach meldet:
- cannot add IMAP message
- Folder doesn't exist

Bedeutung:
- Die Mail wurde oft trotzdem gesendet.
- Nur das anschließende IMAP-Ablegen in den Sent-Ordner schlägt fehl.

Darum behandelt das Skript diesen Fall als:
- wahrscheinlich gesendet
- kein erneuter Doppelversand

============================================================
11. EMPFEHLUNG FUER PRODUKTIVEN EINSATZ
============================================================
Empfohlen:
- erst im Draft-Modus testen
- dann Auto-Modus aktivieren
- own_addresses korrekt pflegen
- nur neue/unread Mails verarbeiten
- Whitelist und Confidence aktiv lassen

Nicht empfohlen:
- confidence_threshold auf 0 in Produktion
- require_whitelist deaktivieren
- unklar oder individuell automatisch senden
- eigene Absender nicht zu definieren

============================================================
12. CHECKLISTE FUER NEUEN RECHNER
============================================================
- Himalaya installiert
- Python-Pakete installiert
- ~/.config/himalaya/config.toml eingerichtet
- App-Passwort gesetzt
- Projektordner kopiert
- config.yaml angepasst
- own_addresses gesetzt
- py_compile erfolgreich
- Draft-Test erfolgreich
- Auto-Test erfolgreich
- systemd Timer aktiviert

============================================================
13. SCHNELLBEFEHLE FUER SETUP AUF NEUEM RECHNER
============================================================
- python3 -m pip install --user pyyaml requests
- python3 -m py_compile /PFAD/zu/mail-auto-draft/process_inbox.py
- systemctl --user daemon-reload
- systemctl --user enable --now mail-auto-draft.timer
- systemctl --user start mail-auto-draft.service
- journalctl --user -u mail-auto-draft.service -n 50 --no-pager

============================================================
14. WENN ETWAS SCHIEFGEHT
============================================================
Prüfen:
- Ist der Himalaya-Account korrekt?
- Ist own_addresses richtig gesetzt?
- Ist die Mail wirklich neu/unread?
- Ist der Timer aktiv?
- Ist die Mail im Log als ignored/drafted/auto_sent markiert?
- Ist chosen_reply_recipient korrekt?

============================================================
15. EMPFEHLUNG FUER WEITERGABE AN ANDERE
============================================================
Für andere Nutzer diese 4 Dinge immer individuell anpassen:
- eigene E-Mail-Adresse
- Himalaya config.toml
- App-Passwort / Secret-Verwaltung
- Projektpfade in config.yaml und systemd-Dateien
