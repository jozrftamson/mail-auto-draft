# Changelog

All notable changes to this project will be documented in this file.

## v0.1.0

First public working release.

Added:
- Himalaya-based inbound email auto-reply workflow
- local Python inbox processor with JSONL logging
- self-reply protection via `own_addresses`
- Reply-To-aware recipient selection
- fallback repair for empty `To:` fields in reply templates
- systemd user timer deployment
- public project README and installation guide
- release and tag strategy documentation

Changed:
- safer production-oriented config defaults
- optional Hermes skill prepared and proposed upstream

Security:
- Gmail app password moved out of repo config flow into local `secrets.env`
- self-sender mail ignored to prevent reply loops

Known behavior:
- Gmail may report IMAP append failure after successful SMTP send; the workflow treats this as likely sent to avoid duplicate replies
