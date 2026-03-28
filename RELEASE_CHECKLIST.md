# Release Checklist

Diese Checkliste ist für kleine, sichere Veröffentlichungen von `mail-auto-draft` gedacht.

Nutze sie vor jedem Git-Tag oder GitHub-Release.

## 1. Repo sauber halten

- [ ] `git status` prüfen
- [ ] keine versehentlichen lokalen Runtime-Dateien im Working Tree
- [ ] keine Secrets im Diff
- [ ] `config.yaml` ist nicht im Commit enthalten
- [ ] nur `config.example.yaml` als veröffentlichbare Vorlage im Repo

## 2. Doku prüfen

- [ ] `README.md` ist aktuell
- [ ] `SCHNELLSTART_AND_INSTALLATION.md` ist aktuell
- [ ] `RELEASES_AND_TAGS.md` passt noch zum aktuellen Stand
- [ ] `CHANGELOG.md` enthält die relevanten Änderungen
- [ ] neue Dateien oder neue Workflows sind dokumentiert

## 3. Konfiguration und Sicherheit prüfen

- [ ] `config.example.yaml` ist sanitizt
- [ ] keine echten E-Mail-Adressen, Tokens oder Passwörter in Beispiel-Dateien
- [ ] `own_addresses` ist in der Doku erklärt
- [ ] Self-Reply-Schutz ist weiterhin aktiv
- [ ] `unklar`, `individuell`, `sensibel`, `ignorieren` werden nicht automatisch gesendet
- [ ] `.gitignore` deckt lokale Config-, Secret- und Runtime-Dateien ab

## 4. Technische Checks

- [ ] Syntaxcheck erfolgreich:

```bash
python3 -m py_compile process_inbox.py
```

- [ ] Git-Status nochmal prüfen:

```bash
git status
```

- [ ] optionaler manueller Draft-Test erfolgreich:

```bash
python3 process_inbox.py --mode draft --limit 5
```

- [ ] optionaler Auto-Test mit sicherem Testfall erfolgreich:

```bash
python3 process_inbox.py --mode auto --limit 1
```

## 5. Release vorbereiten

- [ ] Commit(s) abgeschlossen
- [ ] Version festgelegt, z. B. `v0.1.0`
- [ ] Changelog aktualisiert
- [ ] Release-Typ klar:
  - [ ] Patch
  - [ ] Minor
  - [ ] Major

## 6. Tag und Push

Beispiel:

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin main
git push origin v0.1.0
```

Optional mit GitHub Release:

```bash
gh release create v0.1.0 --title "v0.1.0" --notes "Short release notes here"
```

## 7. Nach dem Release

- [ ] Tag auf GitHub sichtbar
- [ ] Release Notes vorhanden oder geplant
- [ ] README/Docs zeigen noch auf existierende Dateien
- [ ] Repo ist weiterhin frei von lokalen Secrets und Runtime-Artefakten

## Kurzversion für schnelle Releases

```bash
python3 -m py_compile process_inbox.py
git status
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main
git push origin vX.Y.Z
```
