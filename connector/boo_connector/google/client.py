"""Google source access, per account.

`GoogleClient` is the narrow interface the MCP tools use. Two implementations:

  * `FixturesGoogleClient` — reads connector/fixtures/*.json keyed by account_id. Deterministic,
    offline, used by all tests. Never touches tokens.
  * `LiveGoogleClient` (in live.py) — the real implementation against Gmail/Calendar/Drive REST
    APIs, signed with per-account access tokens from the TokenManager. Fully implemented and
    unit-tested with a fake HTTP client; going live needs only real OAuth credentials + hosting.

Returned records are normalized and contain a non-secret `source_ref`. Tokens NEVER appear in any
return value.
"""
from __future__ import annotations

import json
import os
from typing import Callable, Dict, List, Optional

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fixtures")


class SourceError(Exception):
    """A per-account, per-source failure. Callers isolate it so one bad account never aborts a run."""


class GoogleClient:
    def search_relevant_mail(self, account_id: str, categories: List[str], window_days: int) -> List[Dict]:
        raise NotImplementedError

    def list_day_events(self, account_id: str, local_date: str, tz: str) -> List[Dict]:
        raise NotImplementedError

    def get_referenced_drive_metadata(self, account_id: str, refs: List[str]) -> List[Dict]:
        raise NotImplementedError

    def get_source_details(self, account_id: str, source_ref: str) -> Dict:
        raise NotImplementedError

    def create_gmail_draft(self, account_id: str, to: List[str], subject: str, body: str,
                           idempotency_key: str) -> Dict:
        raise NotImplementedError

    def create_calendar_event(self, account_id: str, calendar_id: str, event: Dict,
                              idempotency_key: str) -> Dict:
        raise NotImplementedError


class FixturesGoogleClient(GoogleClient):
    def __init__(self, fixtures_dir: str = FIXTURES_DIR):
        self.dir = fixtures_dir
        self._cache: Dict[str, Dict] = {}
        # tracks created drafts/events so idempotency + "never send" can be asserted in tests
        self.created_drafts: List[Dict] = []
        self.created_events: List[Dict] = []

    def _load(self, name: str) -> Dict:
        if name not in self._cache:
            path = os.path.join(self.dir, f"{name}.json")
            with open(path) as f:
                self._cache[name] = json.load(f)
        return self._cache[name]

    def _account_present(self, name: str, account_id: str):
        data = self._load(name)
        if account_id not in data:
            # An account with no data for this source is simply empty, not an error.
            return []
        entry = data[account_id]
        if isinstance(entry, dict) and entry.get("__error__"):
            raise SourceError(entry["__error__"])
        return entry

    def search_relevant_mail(self, account_id, categories, window_days):
        items = self._account_present("gmail", account_id)
        cats = set(categories) if categories else None
        out = []
        for m in items:
            if cats and not (set(m.get("categories", [])) & cats):
                continue
            out.append({k: m[k] for k in m if k != "body"})  # snippet only; body via get_source_details
        return out

    def list_day_events(self, account_id, local_date, tz):
        events = self._account_present("calendar", account_id)
        return [e for e in events if e.get("local_date") == local_date]

    def get_referenced_drive_metadata(self, account_id, refs):
        files = self._account_present("drive", account_id)
        wanted = set(refs)
        return [f for f in files if f.get("source_ref") in wanted]

    def get_source_details(self, account_id, source_ref):
        for name in ("gmail", "calendar", "drive"):
            try:
                items = self._account_present(name, account_id)
            except SourceError:
                continue
            for it in items:
                if it.get("source_ref") == source_ref:
                    return it
        raise SourceError(f"source_ref not found: {source_ref}")

    def create_gmail_draft(self, account_id, to, subject, body, idempotency_key):
        # idempotent: same key returns the same draft
        for d in self.created_drafts:
            if d["idempotency_key"] == idempotency_key:
                return d
        draft = {
            "draft_id": f"draft-{len(self.created_drafts) + 1}",
            "account_id": account_id,
            "to": to,
            "subject": subject,
            "sent": False,  # Boo NEVER sends
            "idempotency_key": idempotency_key,
            "location": "Gmail > Drafts",
        }
        self.created_drafts.append(draft)
        return draft

    def create_calendar_event(self, account_id, calendar_id, event, idempotency_key):
        for e in self.created_events:
            if e["idempotency_key"] == idempotency_key:
                return e
        created = {
            "event_id": f"evt-{len(self.created_events) + 1}",
            "account_id": account_id,
            "calendar_id": calendar_id,
            "link": f"https://calendar.google.com/event?eid=evt-{len(self.created_events) + 1}",
            "idempotency_key": idempotency_key,
            **event,
        }
        self.created_events.append(created)
        return created


# LiveGoogleClient now lives in live.py (fully implemented against Gmail/Calendar/Drive REST).
