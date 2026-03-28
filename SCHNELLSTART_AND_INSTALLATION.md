# Schnellstart, Installation und Betrieb

Diese Datei ist die zentrale Anleitung für Neuinstallation, Migration auf andere Rechner und sichere Weitergabe des Projekts.

## Ziel

Diese Anleitung beschreibt, wie man die Mail-Automatisierung auf einem anderen Rechner sauber nachbaut.

Das System:

- liest eingehende E-Mails via Himalaya
- bewertet sie regelbasiert
- beantwortet einfache Standardfälle automatisch
- ignoriert eigene E-Mails, damit keine Antwort-Schleife entsteht

## Funktionsumfang

- neue INBOX-Mails lesen
- `Reply-To` vor `From` bevorzugen
- eigenes Postfach vor Self-Reply-Loops schützen
- Newsletter/Systemmails möglichst ignorieren
- einfache Standardanfragen automatisch beantworten
- unklare, individuelle und sensible Fälle nur als Entwurf behandeln oder blockieren
- `systemd --user` Timer für automatischen Hintergrundbetrieb

## Projektstruktur

Wichtige Dateien und Ordner:

- `config.example.yaml`
- `config.yaml` (nur lokal, nicht committen)
- `process_inbox.py`
- `prompts/system_prompt.txt`
- `prompts/user_prompt.txt`
- `logs/mail_actions.jsonl`
- `data/processed_ids.json`
- `drafts/`
- `runtime/`

## Voraussetzungen

- Ubuntu / Linux
- Python 3
- Himalaya installiert
- Gmail oder anderes IMAP/SMTP-Postfach
- Python-Pakete:
  - `pyyaml`
  - `requests`

## 1. Himalaya installieren

Prüfen:

```bash
himalaya --version
```

Falls nicht installiert:

- Himalaya je nach System installieren
- danach erneut prüfen:

```bash
himalaya --version
```

## 2. Python-Abhängigkeiten installieren

```bash
python3 -m pip install --user pyyaml requests
```

## 3. Projekt auf neuen Rechner kopieren

Repository klonen oder den Projektordner kopieren.

Wichtige Unterordner:

- `drafts/`
- `logs/`
- `data/`
- `runtime/`

Falls sie fehlen, werden sie vom Skript beim Lauf automatisch angelegt.

## 4. Himalaya konfigurieren

Datei:

- `~/.config/himalaya/config.toml`

Beispiel für Gmail:

```toml
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
backend.auth.cmd = "sh -lc '. /home/DEINUSER/.config/mail-auto-draft/secrets.env && printf %s \"$GMAIL_APP_PASSWORD\"'"

message.send.backend.type = "smtp"
message.send.backend.host = "smtp.gmail.com"
message.send.backend.port = 587
message.send.backend.encryption.type = "start-tls"
message.send.backend.login = "DEINE-EMAIL@gmail.com"
message.send.backend.auth.type = "password"
message.send.backend.auth.cmd = "sh -lc '. /home/DEINUSER/.config/mail-auto-draft/secrets.env && printf %s \"$GMAIL_APP_PASSWORD\"'"

[accounts.gmail.folder.alias]
inbox = "INBOX"
sent = "[Gmail]/Sent Mail"
drafts = "[Gmail]/Drafts"
trash = "[Gmail]/Trash"
```

Wichtig:

- Bei Gmail App-Passwort verwenden, nicht das normale Passwort.
- Niemals echte Zugangsdaten in Doku, Git oder öffentliche Dateien committen.
- Secrets besser in lokale Datei auslagern, z. B. `~/.config/mail-auto-draft/secrets.env`.

Beispiel für lokale Secret-Datei:

```bash
GMAIL_APP_PASSWORD='***'
```

## 5. Repo- und Local-Config sauber trennen

Im Repository bleibt nur:

- `config.example.yaml`

Lokal verwendest du:

- `config.yaml`

Erzeugen:

```bash
cp config.example.yaml config.yaml
```

Dann in `config.yaml` anpassen:

- `account`
- `own_addresses`
- `__PROJECT_DIR__`
- optional `mode`
- optional `confidence_threshold`

Pflichtpunkt:

```yaml
own_addresses:
  - DEINE-EMAIL@gmail.com
```

Warum wichtig:

- verhindert, dass das System eigene gesendete Mails erneut beantwortet
- verhindert Antwort-Schleifen

Empfohlene produktive Einstellungen:

- `mode: auto`
- `confidence_threshold: 70`
- `require_unseen: true`
- `require_new_in_inbox: true`
- `require_whitelist: true`
- `require_high_confidence: true`
- `forbid_sensitive_categories:`
  - `sensibel`
  - `individuell`
  - `unklar`
  - `ignorieren`

## 6. Syntax und Grundfunktion prüfen

Im Projektordner:

```bash
python3 -m py_compile process_inbox.py
```

Manueller Testlauf im Draft-Modus:

```bash
python3 process_inbox.py --mode draft --limit 5
```

Manueller Testlauf im Auto-Modus:

```bash
python3 process_inbox.py --mode auto --limit 1
```

## 7. systemd User Timer einrichten

Datei:

- `~/.config/systemd/user/mail-auto-draft.service`

Inhalt:

```ini
[Unit]
Description=Process inbox and auto-reply via Himalaya
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=__PROJECT_DIR__
ExecStart=/usr/bin/flock -n __PROJECT_DIR__/runtime/process_inbox.lock /usr/bin/python3 __PROJECT_DIR__/process_inbox.py --limit 5
```

Datei:

- `~/.config/systemd/user/mail-auto-draft.timer`

Inhalt:

```ini
[Unit]
Description=Run mail auto-draft every minute

[Timer]
OnBootSec=2min
OnUnitActiveSec=60s
Persistent=true
Unit=mail-auto-draft.service

[Install]
WantedBy=timers.target
```

Aktivieren:

```bash
systemctl --user daemon-reload
systemctl --user enable --now mail-auto-draft.timer
```

Sofortiger Testlauf:

```bash
systemctl --user start mail-auto-draft.service
```

## 8. Wichtige Betriebs-Kommandos

Status:

```bash
systemctl --user status mail-auto-draft.timer --no-pager
systemctl --user status mail-auto-draft.service --no-pager
```

Timer anzeigen:

```bash
systemctl --user list-timers --all --no-pager | grep mail-auto-draft
```

Logs ansehen:

```bash
journalctl --user -u mail-auto-draft.service -n 50 --no-pager
```

Timer stoppen:

```bash
systemctl --user stop mail-auto-draft.timer
```

Timer starten:

```bash
systemctl --user start mail-auto-draft.timer
```

Timer dauerhaft deaktivieren:

```bash
systemctl --user disable --now mail-auto-draft.timer
```

## 9. Wichtige Projekt-Logs

Wichtigste Datei:

- `logs/mail_actions.jsonl`

Dort sieht man z. B.:

- `action`
- `reason`
- `chosen_reply_recipient`
- `chosen_reply_source`
- `sent`
- `draft_path`

Weitere Dateien:

- `data/processed_ids.json`
- `drafts/*.eml`

## 10. Bekannte Probleme und Hinweise

### Gmail / Himalaya Sent-Append-Problem

Nach erfolgreichem SMTP-Versand kann Himalaya beim IMAP-Append in den Sent-Ordner scheitern.

Typische Meldungen:

- `cannot add IMAP message`
- `Folder doesn't exist`

Praktische Bewertung:

- Nachricht oft bereits gesendet
- nicht sofort erneut senden
- erst Logs und Mailbox prüfen

### Leeres `To:` im Reply-Template

Wenn Himalaya ein Reply-Template ohne Empfänger erzeugt:

- `Reply-To` bevorzugen
- sonst `From` als Fallback verwenden

### Self-Reply-Schleifen

Wenn das System auf eigene Mails antwortet:

- `own_addresses` prüfen
- lokale `config.yaml` prüfen
- Testmails erneut auswerten

## 11. Sichere Weitergabe / GitHub

Vor Veröffentlichung:

- keine echten Zugangsdaten committen
- `config.yaml` nicht committen
- nur `config.example.yaml` veröffentlichen
- lokale Runtime-Daten nicht einchecken
- systemd-Vorlagen mit Platzhaltern beilegen

## 12. Verwandte Dokumente

- [README](./README.md)
- [Releases und Tags](./RELEASES_AND_TAGS.md)
- [Changelog](./CHANGELOG.md)
- [Contributing / Hermes Skill](./CONTRIBUTING_AND_HERMES_SKILL.md)
- [systemd Deployment Notes](./deploy/systemd/README.md)
