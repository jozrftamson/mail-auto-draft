RELEASES AND TAGS

Ziel
- Diese Datei definiert eine einfache, kleine und praktische Release-Strategie fuer mail-auto-draft.
- Sie ist absichtlich leichtgewichtig gehalten.

Empfohlene Versionierung
- SemVer-light:
  - MAJOR: groessere inkompatible Aenderungen
  - MINOR: neue Features, neue sichere Erweiterungen, neue Doku- oder Deployment-Verbesserungen
  - PATCH: Bugfixes, kleine Sicherheitsverbesserungen, kleine Filterkorrekturen, Doku-Fixes

Empfohlene erste Linie
- v0.x solange sich Struktur und Konfiguration noch schneller aendern
- spaeter v1.0.0 wenn das Setup als stabil gilt

Praktischer Vorschlag
- v0.1.0
  erste veroeffentlichte funktionierende Version
- v0.1.1
  kleine Fixes
- v0.2.0
  neue Features oder groessere Verbesserungen
- v1.0.0
  stabiler produktiver Stand mit sauberer Doku und sicherer Konfiguration

Wann ein Tag sinnvoll ist
Tagge neue Versionen, wenn mindestens eines davon zutrifft:
- wichtige Sicherheitsverbesserung
- neue Deployment-Variante
- neue produktionsreife Funktion
- groessere Aenderung an Filter-/Safety-Logik
- stabile Doku-Version fuer Weitergabe an andere

Wann kein Tag noetig ist
- kleine lokale Experimente
- unfertige Zwischenstaende
- rein persoenliche Mini-Aenderungen ohne allgemeinen Nutzen

Empfohlene Release-Arten
1. Patch Release
- kleine Bugfixes
- kleine Doku-Fixes
- kleine Filterkorrekturen

2. Minor Release
- neue Features
- neue Referenzdateien
- neue Setup-Wege
- deutliche Betriebsverbesserungen

3. Major Release
- brechende Konfigurationsaenderungen
- neue Projektstruktur
- neue Architektur

Empfohlene Git-Tags
Beispiele:
- v0.1.0
- v0.1.1
- v0.2.0
- v1.0.0

Typischer Ablauf fuer ein Release
1. Arbeitsstand pruefen
   git status

2. Letzte Aenderungen committen
   git add .
   git commit -m "chore(release): prepare v0.1.0"

3. Tag setzen
   git tag -a v0.1.0 -m "Release v0.1.0"

4. Branch pushen
   git push

5. Tag pushen
   git push origin v0.1.0

Optional mit GitHub Release
- gh release create v0.1.0 --title "v0.1.0" --notes "First public working release"

Empfohlene einfache Changelog-Struktur
Pro Release kurz notieren:
- Added
- Changed
- Fixed
- Security

Beispiel
v0.1.0
- Added: erstes funktionierendes Himalaya auto-reply setup
- Added: systemd user timer deployment
- Added: self-reply protection via own_addresses
- Added: Reply-To vor From
- Fixed: leeres To:-Feld in Reply-Templates
- Security: lokales secrets.env statt Klartext-Passwort in config.toml

Empfohlene Release-Qualitaetspruefung vor Tag
- python3 -m py_compile process_inbox.py
- externer Test mit echter eingehender E-Mail erfolgreich
- self_sender Schutz funktioniert
- Timer laeuft
- README aktuell
- SCHNELLSTART_AND_INSTALLATION.md aktuell
- config.example.yaml aktuell

Empfehlung fuer dieses Projekt jetzt
Sinnvoller erster Tag:
- v0.1.0

Warum:
- Repo ist auf GitHub
- Doku ist vorhanden
- systemd deployment ist vorhanden
- Skill-PR fuer Hermes existiert
- Funktion wurde praktisch erfolgreich getestet
