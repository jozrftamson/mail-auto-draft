systemd deployment templates

Dateien:
- mail-auto-draft.service
- mail-auto-draft.timer

Verwendung:
1. __PROJECT_DIR__ im Service-Template durch den echten Projektpfad ersetzen.
2. Dateien nach ~/.config/systemd/user/ kopieren.
3. Danach ausfuehren:
   systemctl --user daemon-reload
   systemctl --user enable --now mail-auto-draft.timer

Beispiel fuer sed:
  PROJECT_DIR=/home/josef/Projekte/Automation/mail-auto-draft
  sed "s|__PROJECT_DIR__|$PROJECT_DIR|g" deploy/systemd/mail-auto-draft.service > ~/.config/systemd/user/mail-auto-draft.service
  cp deploy/systemd/mail-auto-draft.timer ~/.config/systemd/user/mail-auto-draft.timer
  systemctl --user daemon-reload
  systemctl --user enable --now mail-auto-draft.timer
