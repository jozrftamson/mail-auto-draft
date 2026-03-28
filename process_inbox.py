#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from email.parser import Parser
from email.utils import getaddresses, parseaddr
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml


DEFAULT_ENCODING = "utf-8"


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def read_text(path: str) -> str:
    return Path(path).read_text(encoding=DEFAULT_ENCODING)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=DEFAULT_ENCODING)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding=DEFAULT_ENCODING)


def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding=DEFAULT_ENCODING) as fh:
        return yaml.safe_load(fh) or {}


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def lower(text: str) -> str:
    return (text or "").casefold()


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip())
    text = re.sub(r"-+", "-", text).strip("-._")
    return text or "mail"


def strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return text.strip()


class HimalayaRunner:
    def __init__(self, config: Dict[str, Any]):
        self.binary = config.get("binary", "himalaya")
        self.config_path = (config.get("config_path") or "").strip()

    def run(self, args: List[str], stdin_text: Optional[str] = None, timeout: int = 120) -> subprocess.CompletedProcess:
        cmd = [self.binary]
        if self.config_path:
            cmd += ["--config", self.config_path]
        cmd += args
        return subprocess.run(
            cmd,
            input=stdin_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )

    def run_json(self, args: List[str], timeout: int = 120) -> Any:
        result = self.run(args + ["--output", "json"], timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Himalaya JSON command failed")
        return json.loads(result.stdout)


class Store:
    def __init__(self, cfg: Dict[str, Any]):
        self.processed_ids_path = Path(cfg["paths"]["processed_ids"])
        self.logs_jsonl_path = Path(cfg["paths"]["logs_jsonl"])
        self.drafts_dir = Path(cfg["paths"]["drafts_dir"])
        self.runtime_dir = Path(cfg["paths"]["runtime_dir"])
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.logs_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self.processed_ids_path.parent.mkdir(parents=True, exist_ok=True)

    def load_processed_ids(self) -> set:
        if not self.processed_ids_path.exists():
            return set()
        try:
            data = json.loads(self.processed_ids_path.read_text(encoding=DEFAULT_ENCODING))
        except json.JSONDecodeError:
            return set()
        if isinstance(data, dict):
            ids = data.get("ids", [])
        elif isinstance(data, list):
            ids = data
        else:
            ids = []
        return {str(x) for x in ids}

    def save_processed_ids(self, ids: set) -> None:
        write_json(self.processed_ids_path, {"ids": sorted(ids)})

    def append_log(self, entry: Dict[str, Any]) -> None:
        with open(self.logs_jsonl_path, "a", encoding=DEFAULT_ENCODING) as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


class MailAutoDraft:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.runner = HimalayaRunner(cfg.get("himalaya", {}))
        self.store = Store(cfg)
        self.processed_ids = self.store.load_processed_ids()

    def list_envelopes(self) -> List[Dict[str, Any]]:
        args = [
            "envelope",
            "list",
            "--folder",
            self.cfg.get("inbox_folder", "INBOX"),
            "--page-size",
            str(self.cfg.get("page_size", 25)),
            "--account",
            self.cfg.get("account", "default"),
        ]
        data = self.runner.run_json(args)
        candidates = self._collect_dict_candidates(data)
        envelopes = []
        for item in candidates:
            if any(k in item for k in ["id", "subject", "from", "message_id", "message-id", "flags"]):
                envelopes.append(item)
        return envelopes

    def _collect_dict_candidates(self, value: Any) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        if isinstance(value, dict):
            items.append(value)
            for v in value.values():
                items.extend(self._collect_dict_candidates(v))
        elif isinstance(value, list):
            for v in value:
                items.extend(self._collect_dict_candidates(v))
        return items

    def normalize_envelope(self, env: Dict[str, Any]) -> Dict[str, Any]:
        def pick(obj: Dict[str, Any], *keys: str, default: Any = "") -> Any:
            for key in keys:
                if key in obj and obj[key] not in (None, ""):
                    return obj[key]
            return default

        sender = pick(env, "from", "sender", "from_addr", default="")
        to_value = pick(env, "to", "recipients", default="")
        cc_value = pick(env, "cc", default="")
        flags = pick(env, "flags", "flag", default=[])
        if isinstance(flags, str):
            flags = [flags]
        msg_id = pick(env, "message_id", "message-id", "msgid", default="")
        return {
            "id": str(pick(env, "id", "ID", default="")).strip(),
            "message_id": str(msg_id).strip(),
            "from": self._stringify_address_field(sender),
            "to": self._stringify_address_field(to_value),
            "cc": self._stringify_address_field(cc_value),
            "subject": str(pick(env, "subject", default="")).strip(),
            "date": str(pick(env, "date", "received", default="")).strip(),
            "flags": [str(x) for x in flags],
            "raw": env,
        }

    def _stringify_address_field(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            name = value.get("name") or value.get("display_name") or ""
            addr = value.get("addr") or value.get("email") or value.get("address") or ""
            return f"{name} <{addr}>".strip()
        if isinstance(value, list):
            return ", ".join(self._stringify_address_field(v) for v in value if v)
        return str(value or "")

    def _extract_emails(self, value: Any) -> List[str]:
        if isinstance(value, dict):
            candidates = [value.get("addr"), value.get("email"), value.get("address")]
            return [str(v).strip().casefold() for v in candidates if v]
        if isinstance(value, list):
            emails: List[str] = []
            for item in value:
                emails.extend(self._extract_emails(item))
            return emails
        if isinstance(value, str):
            parsed = [addr.casefold() for _, addr in getaddresses([value]) if addr]
            if parsed:
                return parsed
            _, addr = parseaddr(value)
            return [addr.casefold()] if addr else []
        return []

    def own_addresses(self) -> set:
        own = self.cfg.get("own_addresses", []) or []
        return {str(x).strip().casefold() for x in own if str(x).strip()}

    def is_own_sender(self, env: Dict[str, Any], message: Dict[str, Any]) -> bool:
        own = self.own_addresses()
        if not own:
            return False
        candidates = set(self._extract_emails(env.get("from", "")))
        headers = message.get("headers") or {}
        for key, value in headers.items():
            if lower(str(key)) == "from":
                candidates.update(self._extract_emails(value))
        return bool(candidates & own)

    def is_unseen(self, env: Dict[str, Any]) -> bool:
        if not self.cfg.get("filters", {}).get("require_unseen", True):
            return True
        flags = {lower(x) for x in env.get("flags", [])}
        seen_variants = {"seen", "read", "opened"}
        return flags.isdisjoint(seen_variants)

    def stable_id(self, env: Dict[str, Any]) -> str:
        return env.get("message_id") or f"{self.cfg.get('account','default')}:{self.cfg.get('inbox_folder','INBOX')}:{env.get('id','')}"

    def read_message(self, env: Dict[str, Any]) -> Dict[str, Any]:
        args = [
            "message",
            "read",
            "--folder",
            self.cfg.get("inbox_folder", "INBOX"),
            "--preview",
            "--account",
            self.cfg.get("account", "default"),
            env["id"],
        ]
        try:
            data = self.runner.run_json(args)
            return self._normalize_message_json(data, env)
        except Exception:
            result = self.runner.run(args, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Cannot read message {env['id']}")
            return self._normalize_message_plain(result.stdout, env)

    def _normalize_message_json(self, data: Any, env: Dict[str, Any]) -> Dict[str, Any]:
        candidates = self._collect_dict_candidates(data)
        headers = {}
        body = ""
        for item in candidates:
            if not body:
                body = item.get("body") or item.get("text") or item.get("plain") or item.get("content") or ""
            hdrs = item.get("headers")
            if isinstance(hdrs, dict) and hdrs:
                headers = {str(k): self._stringify_address_field(v) for k, v in hdrs.items()}
                break
        if not headers and isinstance(data, dict):
            for key in ["from", "to", "cc", "subject", "date", "message-id", "message_id"]:
                if key in data:
                    headers[key] = self._stringify_address_field(data[key])
        return {
            "headers": headers,
            "body": body or "",
            "raw": data,
            "envelope": env,
        }

    def _normalize_message_plain(self, text: str, env: Dict[str, Any]) -> Dict[str, Any]:
        parsed = Parser().parsestr(text)
        body = parsed.get_payload()
        if isinstance(body, list):
            body = "\n".join(str(part) for part in body)
        headers = {k: v for k, v in parsed.items()}
        if not headers:
            header_part, _, body = text.partition("\n\n")
            headers = self._parse_header_block(header_part)
        return {
            "headers": headers,
            "body": body if isinstance(body, str) else str(body),
            "raw": text,
            "envelope": env,
        }

    def _parse_header_block(self, header_text: str) -> Dict[str, str]:
        headers = {}
        current_key = None
        for line in header_text.splitlines():
            if line.startswith((" ", "\t")) and current_key:
                headers[current_key] += " " + line.strip()
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            current_key = key.strip()
            headers[current_key] = value.strip()
        return headers

    def analyze(self, env: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        rule = self.rule_based_analysis(env, message)
        llm_cfg = self.cfg.get("llm", {})
        if rule["category"] == "ignorieren":
            return rule
        if not llm_cfg.get("enabled", False):
            return rule
        try:
            llm_result = self.llm_analysis(env, message)
            merged = self.merge_analysis(rule, llm_result)
            return self.apply_final_safety(merged, env, message)
        except Exception as exc:
            rule["reason"] = f"llm_fallback: {exc}"
            return rule

    def merge_analysis(self, rule: Dict[str, Any], llm: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(rule)
        for key in [
            "relevant",
            "language",
            "business_context",
            "category",
            "confidence",
            "ignore_reason",
            "needs_human_review",
            "draft_only",
            "suggested_reply_subject",
            "suggested_reply_body",
        ]:
            if key in llm and llm[key] not in (None, ""):
                merged[key] = llm[key]
        forbidden_categories = set(self.cfg.get("safety", {}).get("forbid_sensitive_categories", []))
        if merged.get("category") in forbidden_categories:
            merged["draft_only"] = True
            merged["needs_human_review"] = True
        return merged

    def apply_final_safety(self, analysis: Dict[str, Any], env: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        combined = lower("\n".join([env.get("subject", ""), env.get("from", ""), message.get("body", "")]))
        for token in self.cfg.get("safety", {}).get("forbid_if_subject_or_body_contains", []):
            if lower(token) in combined:
                analysis["category"] = "sensibel"
                analysis["draft_only"] = True
                analysis["needs_human_review"] = True
                analysis["confidence"] = min(int(analysis.get("confidence", 0)), 60)
                analysis["reason"] = f"safety_token:{token}"
                return analysis
        return analysis

    def rule_based_analysis(self, env: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        filters = self.cfg.get("filters", {})
        headers = {lower(k): str(v) for k, v in (message.get("headers") or {}).items()}
        subject = env.get("subject", "")
        body = message.get("body", "") or ""
        sender = env.get("from", "")
        fulltext = "\n".join([subject, body, sender])
        l_fulltext = lower(fulltext)
        l_sender = lower(sender)
        l_subject = lower(subject)

        if self.is_own_sender(env, message):
            return self._ignored(env, "self_sender")

        strict_sender = filters.get("sender_substrings_strict", [])
        if any(token in l_sender for token in map(lower, strict_sender)):
            return self._ignored(env, "sender_strict_rule")

        soft_sender_hits = sum(1 for token in filters.get("sender_substrings_soft", []) if lower(token) in l_sender)
        subject_ignore_terms = (
            filters.get("subject_keywords_newsletter", [])
            + filters.get("subject_keywords_system", [])
            + filters.get("subject_keywords_bulk", [])
        )
        body_ignore_terms = filters.get("body_ignore_patterns", [])
        header_ignore_keys = {lower(x) for x in filters.get("header_ignore_keys", [])}
        if any(k in headers for k in header_ignore_keys):
            return self._ignored(env, "header_ignore_key")
        for header_name, expected_values in filters.get("header_ignore_values", {}).items():
            actual = lower(headers.get(lower(header_name), ""))
            if actual and any(lower(v) in actual for v in expected_values):
                return self._ignored(env, f"header_ignore_value:{header_name}")

        recipient_count = self.count_recipients(env)
        if recipient_count > int(filters.get("max_visible_recipients", 6)):
            return self._ignored(env, "too_many_visible_recipients")

        if any(lower(token) in l_subject for token in subject_ignore_terms):
            return self._ignored(env, "subject_ignore_rule")
        if any(lower(token) in l_fulltext for token in body_ignore_terms):
            return self._ignored(env, "body_ignore_rule")
        if soft_sender_hits >= 1 and any(lower(token) in l_subject for token in subject_ignore_terms):
            return self._ignored(env, "soft_sender_plus_subject_rule")

        language, language_score = self.detect_language(body, subject)
        business_context, business_score = self.detect_business_context(body, subject, sender)
        if filters.get("require_german", True) and language != "de":
            return {
                "relevant": False,
                "language": language,
                "business_context": business_context,
                "category": "ignorieren",
                "confidence": max(35, min(70, 40 + language_score * 5)),
                "ignore_reason": "non_german",
                "needs_human_review": False,
                "draft_only": True,
                "suggested_reply_subject": "",
                "suggested_reply_body": "",
                "reason": "language_filter",
            }
        if filters.get("require_business_context", True) and not business_context:
            return {
                "relevant": False,
                "language": language,
                "business_context": False,
                "category": "ignorieren",
                "confidence": max(40, min(75, 45 + business_score * 5)),
                "ignore_reason": "no_business_context",
                "needs_human_review": False,
                "draft_only": True,
                "suggested_reply_subject": "",
                "suggested_reply_body": "",
                "reason": "business_filter",
            }

        category = self.classify_category(l_fulltext)
        confidence = self.estimate_confidence(category, language_score, business_score, l_fulltext)
        forbidden_categories = set(self.cfg.get("safety", {}).get("forbid_sensitive_categories", []))
        needs_review = category in forbidden_categories
        draft_only = needs_review or self.cfg.get("mode", "draft") != "auto"
        subject_reply, body_reply = self.build_reply(category, env)

        return {
            "relevant": True,
            "language": language,
            "business_context": business_context,
            "category": category,
            "confidence": confidence,
            "ignore_reason": "",
            "needs_human_review": needs_review,
            "draft_only": draft_only,
            "suggested_reply_subject": subject_reply,
            "suggested_reply_body": body_reply,
            "reason": "rule_based",
        }

    def detect_language(self, body: str, subject: str) -> Tuple[str, int]:
        filters = self.cfg.get("filters", {})
        text = lower(subject + "\n" + body)
        positives = sum(1 for token in filters.get("german_positive_signals", []) if lower(token) in text)
        negatives = sum(1 for token in filters.get("german_negative_signals", []) if lower(token) in text)
        common_german = len(re.findall(r"\b(und|der|die|das|nicht|wir|sie|mit|für|eine|einen|ihre|anfrage|termin)\b", text))
        umlauts = len(re.findall(r"[äöüß]", text))
        score = positives + common_german + min(umlauts, 3) - negatives
        return ("de" if score >= 2 else "other", score)

    def detect_business_context(self, body: str, subject: str, sender: str) -> Tuple[bool, int]:
        filters = self.cfg.get("filters", {})
        text = lower("\n".join([body, subject, sender]))
        positives = sum(1 for token in filters.get("business_positive_signals", []) if lower(token) in text)
        negatives = len(re.findall(r"\b(privat|party|urlaub|familie|geburtstag|grüße von zuhause)\b", text))
        score = positives - negatives
        return (score >= 1, score)

    def classify_category(self, text: str) -> str:
        filters = self.cfg.get("filters", {})
        sensitive_hits = sum(1 for token in filters.get("sensitive_signals", []) if lower(token) in text)
        if sensitive_hits:
            return "sensibel"
        individual_hits = sum(1 for token in filters.get("individual_signals", []) if lower(token) in text)
        if individual_hits:
            return "individuell"
        category_rules = filters.get("category_rules", {})
        for category in ["termin_standard", "unterlagen_standard", "info_standard"]:
            rules = category_rules.get(category, {})
            any_hits = [token for token in rules.get("any", []) if lower(token) in text]
            if any_hits:
                return category
        if any(lower(token) in text for token in category_rules.get("eingangsbestaetigung", {}).get("any", [])):
            return "eingangsbestaetigung"
        if any(word in text for word in ["anfrage", "rückmeldung", "bitte", "interesse"]):
            return "eingangsbestaetigung"
        return "unklar"

    def estimate_confidence(self, category: str, language_score: int, business_score: int, text: str) -> int:
        confidence = 55 + language_score * 4 + business_score * 5
        if category in {"info_standard", "termin_standard", "unterlagen_standard", "eingangsbestaetigung"}:
            confidence += 10
        if category in {"sensibel", "individuell", "unklar"}:
            confidence -= 10
        if any(token in text for token in ["?", "bitte", "anfrage"]):
            confidence += 5
        return max(0, min(100, confidence))

    def build_reply(self, category: str, env: Dict[str, Any]) -> Tuple[str, str]:
        templates = self.cfg.get("reply_templates", {})
        tpl = templates.get(category) or templates.get("fallback_draft", {})
        subject = env.get("subject", "")
        if lower(subject).startswith("re:"):
            reply_subject = subject
        else:
            reply_subject = f"{tpl.get('subject_prefix', 'Re: ')}{subject}".strip()
        body = tpl.get("body", "").rstrip() + "\n"
        return reply_subject, body

    def llm_analysis(self, env: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        llm_cfg = self.cfg.get("llm", {})
        api_key = os.environ.get(llm_cfg.get("api_key_env", "OPENAI_API_KEY"), "")
        if not api_key:
            raise RuntimeError("missing_api_key")
        system_prompt = read_text(llm_cfg["system_prompt_file"])
        user_template = read_text(llm_cfg["user_prompt_file"])
        body = message.get("body", "") or ""
        user_prompt = user_template.format(
            **{
                "from": env.get("from", ""),
                "subject": env.get("subject", ""),
                "to": env.get("to", ""),
                "cc": env.get("cc", ""),
                "date": env.get("date", ""),
                "message_id": env.get("message_id", ""),
                "body": body[:12000],
            }
        )
        url = llm_cfg.get("base_url", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        payload = {
            "model": llm_cfg.get("model", "gpt-4o-mini"),
            "temperature": llm_cfg.get("temperature", 0.1),
            "max_tokens": llm_cfg.get("max_tokens", 1200),
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=int(llm_cfg.get("timeout_seconds", 60)),
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(strip_code_fences(content))
        return {
            "relevant": bool(parsed.get("relevant", False)),
            "language": parsed.get("language", "other"),
            "business_context": bool(parsed.get("business_context", False)),
            "category": parsed.get("category", "unklar"),
            "confidence": int(parsed.get("confidence", 0)),
            "ignore_reason": parsed.get("ignore_reason", ""),
            "needs_human_review": bool(parsed.get("needs_human_review", False)),
            "draft_only": bool(parsed.get("draft_only", False)),
            "suggested_reply_subject": parsed.get("suggested_reply_subject", ""),
            "suggested_reply_body": parsed.get("suggested_reply_body", ""),
        }

    def decide_action(self, analysis: Dict[str, Any]) -> Tuple[str, str, bool]:
        mode = self.cfg.get("mode", "draft")
        whitelist = set(self.cfg.get("whitelist_categories", []))
        threshold = int(self.cfg.get("confidence_threshold", 85))
        safety = self.cfg.get("safety", {})
        category = analysis.get("category", "unklar")

        if category == "ignorieren" or not analysis.get("relevant", False):
            return "ignored", analysis.get("ignore_reason") or analysis.get("reason") or "ignored", False
        if mode != "auto":
            return "drafted", "draft_mode_enabled", False
        if safety.get("require_whitelist", True) and category not in whitelist:
            return "drafted", "category_not_whitelisted", True
        if safety.get("require_high_confidence", True) and int(analysis.get("confidence", 0)) < threshold:
            return "drafted", "confidence_below_threshold", True
        if analysis.get("needs_human_review", False):
            return "drafted", "needs_human_review", True
        if analysis.get("draft_only", False):
            return "drafted", "draft_only", True
        if category in set(safety.get("forbid_sensitive_categories", [])):
            return "drafted", "forbidden_category", True
        return "auto_sent", "auto_mode_whitelisted_and_confident", False

    def create_reply_template(self, env: Dict[str, Any], analysis: Dict[str, Any], message: Dict[str, Any]) -> str:
        args = [
            "template",
            "reply",
            "--folder",
            self.cfg.get("inbox_folder", "INBOX"),
            "--account",
            self.cfg.get("account", "default"),
        ]
        if self.cfg.get("allow_reply_all", False):
            args.append("--all")
        args.append(env["id"])
        result = self.runner.run(args, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "template reply failed")
        return self.inject_reply_body(
            result.stdout,
            analysis.get("suggested_reply_body", ""),
            analysis.get("suggested_reply_subject", ""),
            env,
            message,
        )

    def inject_reply_body(self, template_text: str, reply_body: str, reply_subject: str, env: Dict[str, Any], message: Dict[str, Any]) -> str:
        header_part, separator, body_part = template_text.partition("\n\n")
        headers = []
        subject_set = False
        to_set = False
        fallback_to = self._reply_recipient(env, message)
        for line in header_part.splitlines():
            if lower(line).startswith("subject:") and reply_subject:
                headers.append(f"Subject: {reply_subject}")
                subject_set = True
            elif lower(line).startswith("to:"):
                current_to = line.split(":", 1)[1].strip() if ":" in line else ""
                if current_to:
                    headers.append(line)
                    to_set = True
                elif fallback_to:
                    headers.append(f"To: {fallback_to}")
                    to_set = True
                else:
                    headers.append(line)
            else:
                headers.append(line)
        if not subject_set and reply_subject:
            headers.append(f"Subject: {reply_subject}")
        if not to_set and fallback_to:
            headers.append(f"To: {fallback_to}")
        existing_body = body_part.lstrip("\n")
        final_body = reply_body.rstrip() + "\n\n"
        if existing_body:
            final_body += existing_body
        return "\n".join(headers) + "\n\n" + final_body

    def _reply_recipient_info(self, env: Dict[str, Any], message: Dict[str, Any]) -> Tuple[str, str]:
        headers = message.get("headers") or {}
        reply_to = ""
        for key, value in headers.items():
            if lower(str(key)) == "reply-to":
                reply_to = str(value).strip()
                break
        sender = reply_to or (env.get("from") or "").strip()
        source = "reply-to" if reply_to else "from"
        name, addr = parseaddr(sender)
        if addr:
            return (f"{name} <{addr}>".strip() if name else addr, source)
        return sender, source

    def _reply_recipient(self, env: Dict[str, Any], message: Dict[str, Any]) -> str:
        recipient, _ = self._reply_recipient_info(env, message)
        return recipient

    def save_draft_files(self, env: Dict[str, Any], analysis: Dict[str, Any], reply_template: str, message: Dict[str, Any]) -> Dict[str, str]:
        ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        base_name = slugify(f"{ts}-{env.get('subject')[:60]}-{env.get('id')}")
        draft_path = self.store.drafts_dir / f"{base_name}.eml"
        analysis_path = self.store.drafts_dir / f"{base_name}.analysis.json"
        raw_path = self.store.drafts_dir / f"{base_name}.raw.txt"
        write_text(draft_path, reply_template)
        if self.cfg.get("save_analysis_json", True):
            write_json(analysis_path, {"envelope": env, "analysis": analysis})
        if self.cfg.get("save_raw_message", True):
            raw_value = message.get("raw", "")
            if not isinstance(raw_value, str):
                raw_value = json.dumps(raw_value, ensure_ascii=False, indent=2)
            write_text(raw_path, raw_value)
        return {
            "draft_path": str(draft_path),
            "analysis_path": str(analysis_path),
            "raw_path": str(raw_path),
        }

    def send_reply(self, reply_template: str) -> Tuple[bool, str]:
        result = self.runner.run(["template", "send", "--account", self.cfg.get("account", "default")], stdin_text=reply_template, timeout=180)
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        if result.returncode == 0:
            return True, combined.strip()
        if "cannot add IMAP message" in combined and "Folder doesn't exist" in combined:
            return True, "smtp_sent_but_imap_append_failed: " + normalize_ws(combined)
        return False, normalize_ws(combined)

    def count_recipients(self, env: Dict[str, Any]) -> int:
        joined = ",".join([env.get("to", ""), env.get("cc", "")])
        if not joined.strip():
            return 0
        return len([x for x in re.split(r",\s*", joined) if x.strip()])

    def _ignored(self, env: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            "relevant": False,
            "language": "de",
            "business_context": False,
            "category": "ignorieren",
            "confidence": 95,
            "ignore_reason": reason,
            "needs_human_review": False,
            "draft_only": True,
            "suggested_reply_subject": "",
            "suggested_reply_body": "",
            "reason": reason,
        }

    def should_mark_processed(self, action: str) -> bool:
        return {
            "ignored": self.cfg.get("mark_processed_on_ignore", True),
            "drafted": self.cfg.get("mark_processed_on_draft", True),
            "auto_sent": self.cfg.get("mark_processed_on_send", True),
        }.get(action, False)

    def log_entry(self, env: Dict[str, Any], message: Dict[str, Any], analysis: Dict[str, Any], action: str, reason: str, draft_meta: Dict[str, str], sent: bool, fallback_triggered: bool) -> None:
        chosen_reply_recipient, chosen_reply_source = self._reply_recipient_info(env, message)
        entry = {
            "timestamp": now_iso(),
            "account": self.cfg.get("account", "default"),
            "message_id": self.stable_id(env),
            "from": env.get("from", ""),
            "subject": env.get("subject", ""),
            "folder": self.cfg.get("inbox_folder", "INBOX"),
            "chosen_reply_recipient": chosen_reply_recipient,
            "chosen_reply_source": chosen_reply_source,
            "language_detected": analysis.get("language", ""),
            "business_context": analysis.get("business_context", False),
            "category": analysis.get("category", "unklar"),
            "confidence": analysis.get("confidence", 0),
            "action": action,
            "reason": reason,
            "draft_path": draft_meta.get("draft_path", ""),
            "draft_id": draft_meta.get("draft_id", ""),
            "sent": sent,
            "fallback_triggered": fallback_triggered,
        }
        if self.cfg.get("logging", {}).get("include_analysis_excerpt", True):
            entry["analysis_excerpt"] = normalize_ws(analysis.get("suggested_reply_body", ""))[: int(self.cfg.get("logging", {}).get("max_body_chars_in_log", 400))]
        self.store.append_log(entry)

    def process(self, limit: Optional[int] = None) -> int:
        envelopes = [self.normalize_envelope(e) for e in self.list_envelopes()]
        processed_now = 0
        for env in envelopes:
            if limit is not None and processed_now >= limit:
                break
            if not env.get("id"):
                continue
            if not self.is_unseen(env):
                continue
            stable_id = self.stable_id(env)
            if stable_id in self.processed_ids:
                continue
            try:
                message = self.read_message(env)
                analysis = self.analyze(env, message)
                action, reason, fallback_triggered = self.decide_action(analysis)
                draft_meta: Dict[str, str] = {}
                sent = False

                if action != "ignored":
                    reply_template = self.create_reply_template(env, analysis, message)
                    draft_meta = self.save_draft_files(env, analysis, reply_template, message)
                    if action == "auto_sent":
                        ok, send_reason = self.send_reply(reply_template)
                        if ok:
                            sent = True
                            reason = send_reason or reason
                        else:
                            if self.cfg.get("safety", {}).get("fallback_to_draft_on_send_error", True):
                                action = "drafted"
                                fallback_triggered = True
                                reason = f"send_error_fallback:{send_reason}"
                            else:
                                action = "skipped_error"
                                reason = f"send_error:{send_reason}"
                self.log_entry(env, message, analysis, action, reason, draft_meta, sent, fallback_triggered)
                if self.should_mark_processed(action):
                    self.processed_ids.add(stable_id)
                processed_now += 1
            except Exception as exc:
                analysis = {
                    "language": "",
                    "business_context": False,
                    "category": "unklar",
                    "confidence": 0,
                    "suggested_reply_body": "",
                }
                self.log_entry(env, message if 'message' in locals() else {"headers": {}}, analysis, "skipped_error", str(exc), {}, False, False)
        self.store.save_processed_ids(self.processed_ids)
        return processed_now


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verarbeitet neue INBOX-Mails mit Himalaya im Entwurfs- oder Auto-Modus.")
    parser.add_argument("--config", default="/home/josef/Projekte/Automation/mail-auto-draft/config.yaml", help="Pfad zur config.yaml")
    parser.add_argument("--limit", type=int, default=None, help="Maximale Anzahl zu verarbeitender Mails")
    parser.add_argument("--mode", choices=["draft", "auto"], default=None, help="Modus temporär überschreiben")
    parser.add_argument("--account", default=None, help="Himalaya-Account temporär überschreiben")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_yaml(args.config)
    if args.mode:
        cfg["mode"] = args.mode
    if args.account:
        cfg["account"] = args.account
    app = MailAutoDraft(cfg)
    count = app.process(limit=args.limit)
    print(json.dumps({"processed": count, "mode": cfg.get("mode"), "account": cfg.get("account")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
