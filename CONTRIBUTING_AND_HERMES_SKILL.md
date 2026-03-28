CONTRIBUTING AND HERMES SKILL GUIDE

Ziel
- Diese Datei erklaert, wie das Projekt spaeter erweitert, als Pull Request eingebracht oder als Hermes-Skill weitergegeben werden kann.

1. Wann dieses Projekt als GitHub-PR geeignet ist
Geeignet fuer Pull Requests, wenn:
- die Doku verbessert wurde
- Filterregeln sinnvoll erweitert wurden
- Self-Reply-Schutz verbessert wurde
- systemd Deployment sauberer gemacht wurde
- Himalaya/Gmail-Fallstricke robuster behandelt werden

Weniger geeignet fuer PRs:
- lokale Zugangsdaten
- persoenliche Mail-Adressen anderer Nutzer
- Logs, Drafts, Runtime-Daten
- maschinenspezifische Pfade ohne Platzhalter

2. Was vor einem PR geprueft werden sollte
- keine Secrets im Repo
- keine App-Passwoerter im Repo
- README aktuell
- config.example.yaml aktuell
- deploy/systemd Vorlagen aktuell
- process_inbox.py laeuft mit py_compile
- Self-Reply-Schutz bleibt erhalten
- own_addresses Konzept bleibt dokumentiert

3. Minimale lokale Pruefung vor Commit
python3 -m py_compile process_inbox.py

git status

git diff --stat

4. Typischer GitHub-Workflow spaeter
Neuen Branch anlegen:
  git checkout -b feature/improve-mail-classification

Aenderungen committen:
  git add .
  git commit -m "Improve mail classification and safety rules"

Pushen:
  git push -u origin feature/improve-mail-classification

PR erstellen:
  gh pr create --fill

5. Vorschlag fuer gute PR-Themen
- bessere Newsletter-Erkennung
- bessere Reply-To / From Heuristik
- Konfigurationsvalidierung beim Start
- sauberere Sent-Ordner-Behandlung fuer Gmail
- Tests fuer Klassifikation und Sicherheitsregeln
- Dokumentation fuer weitere Mail-Provider

6. Wie man daraus einen Hermes-Skill macht
Ein Hermes-Skill ist nicht das ganze Projekt, sondern das wiederverwendbare Wissen.

Ein guter Skill sollte enthalten:
- wann man den Workflow benutzt
- welche Dateien noetig sind
- welche Schritte beim Setup wichtig sind
- welche typischen Fehler auftreten
- wie Self-Reply-Schleifen verhindert werden
- wie systemd Timer eingerichtet werden
- wie Gmail/Himalaya-Sonderfaelle behandelt werden

7. Was in einen Hermes-Skill gehoert
- Beschreibung des Workflows
- sichere Standardwerte
- typische Kommandos
- Projektstruktur
- Fallstricke und Troubleshooting
- Verifikation

8. Was NICHT in einen Hermes-Skill gehoert
- persoenliche Runtime-Logs
- Draft-Dateien
- Zugangsdaten
- lokale absolute Pfade ohne Erklaerung
- nutzerspezifische App-Passwoerter

9. Vorschlag fuer spaetere oeffentliche Skill- oder Repo-Beitraege
Wenn du das spaeter in ein Skill-Repo oder Open-Source-Repo einbringen willst, solltest du vorher:
- README kurz und oeffentlich formulieren
- config.example.yaml pflegen
- lokale config.yaml ggf. noch weiter neutralisieren
- Secrets komplett entfernen
- systemd Vorlagen mit Platzhaltern behalten
- Installationsanleitung aktuell halten

10. Empfohlene Struktur fuer Open-Source-Freigabe
- README.md
- SCHNELLSTART_AND_INSTALLATION.md
- CONTRIBUTING_AND_HERMES_SKILL.md
- config.example.yaml
- process_inbox.py
- prompts/
- deploy/systemd/
- .gitignore

11. Empfehlung fuer spaeteren Hermes-Beitrag
Wenn du das als Hermes-Skill offiziell weitergeben willst, ist die beste Form:
- kompaktes SKILL.md
- Fokus auf Einrichtung und Betrieb
- keine lokalen Laufzeitdaten
- klare Hinweise zu own_addresses, Reply-To, Gmail append failure und systemd timer
