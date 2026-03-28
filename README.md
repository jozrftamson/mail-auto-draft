mail-auto-draft

[![Release](https://img.shields.io/github/v/release/jozrftamson/mail-auto-draft?sort=semver)](https://github.com/jozrftamson/mail-auto-draft/releases)

Automatische E-Mail-Triage und Auto-Reply mit Himalaya, Python und systemd.

Ueberblick
- liest neue E-Mails aus INBOX via Himalaya
- priorisiert Reply-To vor From
- ignoriert eigene Absender, um Self-Reply-Loops zu verhindern
- blockiert typische no-reply-, Bulk- und Systemmails
- beantwortet einfache Standardfaelle automatisch
- schiebt unklare, individuelle oder sensible Faelle in sicheren Nicht-Auto-Modus
- laeuft optional dauerhaft per systemd --user timer

Geeignet fuer
- kleine Auto-Reply-Workflows
- Eingangsbestatigungen
- Termin- oder Info-Anfragen
- lokale Mail-Automatisierung auf Ubuntu/Linux

Wichtige Features
- Himalaya IMAP/SMTP Integration
- regelbasierte Klassifikation
- optionale LLM-Erweiterung
- Reply-Template-Verwendung fuer saubere Threading-Header
- Fallback auf Draft bei Unsicherheit oder Sendefehlern
- JSONL-Logging pro Mail
- systemd User-Timer fuer automatischen Dauerbetrieb

Projektstruktur
- process_inbox.py
- config.yaml
- config.example.yaml
- prompts/system_prompt.txt
- prompts/user_prompt.txt
- deploy/systemd/
- SCHNELLSTART_AND_INSTALLATION.md

Nicht ins Repository einchecken
- logs/
- drafts/
- data/
- runtime/
- lokale Secrets

Schnellstart
1. Himalaya installieren und konfigurieren
2. Python-Abhaengigkeiten installieren
3. config.example.yaml nach config.yaml kopieren und anpassen
4. py_compile-Test ausfuehren
5. zuerst im Draft-Modus testen
6. danach Auto-Modus aktivieren
7. optional systemd Timer aktivieren

Python-Abhaengigkeiten
- pyyaml
- requests

Beispiel:
python3 -m pip install --user pyyaml requests

Manuelle Tests
Draft-Test:
python3 /home/josef/Projekte/Automation/mail-auto-draft/process_inbox.py --mode draft --limit 5

Auto-Test:
python3 /home/josef/Projekte/Automation/mail-auto-draft/process_inbox.py --mode auto --limit 1

Syntax-Test:
python3 -m py_compile /home/josef/Projekte/Automation/mail-auto-draft/process_inbox.py

Produktive Sicherheitsidee
Empfohlene Produktionseinstellungen:
- require_unseen: true
- require_new_in_inbox: true
- require_whitelist: true
- require_high_confidence: true
- own_addresses korrekt gesetzt
- unklar / individuell / sensibel nicht auto-senden

Wichtige Konfigurationspunkte
In config.yaml besonders wichtig:
- account
- own_addresses
- paths
- whitelist_categories
- confidence_threshold
- safety.*

Warum own_addresses wichtig ist
Wenn die eigene E-Mail-Adresse nicht gesetzt ist, kann das System auf eigene gesendete Nachrichten antworten und Schleifen erzeugen.

Beispiel:
own_addresses:
  - your-address@example.com

systemd Deployment
Vorlagen liegen in:
- deploy/systemd/mail-auto-draft.service
- deploy/systemd/mail-auto-draft.timer
- deploy/systemd/README.md

Betriebskommandos
Status:
systemctl --user status mail-auto-draft.timer --no-pager
systemctl --user status mail-auto-draft.service --no-pager

Logs:
journalctl --user -u mail-auto-draft.service -n 50 --no-pager

Timer aktivieren:
systemctl --user daemon-reload
systemctl --user enable --now mail-auto-draft.timer

Wichtige Projekt-Logs
- logs/mail_actions.jsonl

Dort sieht man z. B.:
- action
- reason
- chosen_reply_recipient
- chosen_reply_source
- sent
- draft_path

Gmail / Himalaya Hinweis
Bei Gmail kann Himalaya nach erfolgreichem SMTP-Versand beim IMAP-Append in den Sent-Ordner scheitern.
Das Projekt behandelt die bekannte Kombination
- cannot add IMAP message
- Folder doesn't exist
als wahrscheinlichen Versand-Erfolg, um Doppelversand zu vermeiden.

Dokumentation
Ausfuehrliche Installations- und Migrationsanleitung:
- /home/josef/Projekte/Automation/mail-auto-draft/SCHNELLSTART_AND_INSTALLATION.md

Release- und Tag-Strategie:
- /home/josef/Projekte/Automation/mail-auto-draft/RELEASES_AND_TAGS.md

Changelog:
- /home/josef/Projekte/Automation/mail-auto-draft/CHANGELOG.md

Weitergabe / GitHub
Wenn du das Projekt auf GitHub veroeffentlichst, solltest du vorab:
- echte Zugangsdaten entfernen
- nur config.example.yaml veroeffentlichen
- lokale Runtime-Daten nicht committen
- systemd-Vorlagen mit Platzhaltern beilegen

Hermes-Skill Bezug
Dieses Projekt eignet sich gut fuer einen begleitenden Hermes-Skill, der beschreibt:
- wann man den Workflow benutzt
- wie Himalaya eingerichtet wird
- wie Self-Reply-Schutz funktioniert
- wie systemd-Timer eingerichtet werden
