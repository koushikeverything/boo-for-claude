"""Live Google API client (Gmail / Calendar / Drive) for Mode B.

Implements the same narrow interface as FixturesGoogleClient using real REST calls signed with a
per-account access token from the TokenManager. Returns normalized records with a non-secret
`source_ref`; tokens never appear in results. Drafts only — there is no send path.

Testable without network: inject a FakeHttpClient (see connector/tests/test_live_client.py).
"""
from __future__ import annotations

import base64
from email.message import EmailMessage
from typing import Dict, List

from .client import GoogleClient, SourceError
from .http import HttpClient
from .tokens import TokenManager

GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
CALENDAR = "https://www.googleapis.com/calendar/v3"
DRIVE = "https://www.googleapis.com/drive/v3"

# Targeted Gmail queries per morning-brief category (see retrieval-policy.md).
_CATEGORY_Q = {
    "bill": "invoice OR bill OR payment OR \"amount due\" OR receipt",
    "deadline": "due OR deadline OR EOD OR \"by tomorrow\"",
    "rsvp": "invite OR invitation OR RSVP",
    "delivery": "delivery OR shipped OR \"out for delivery\" OR tracking",
    "document": "sign OR signature OR form OR document OR contract",
    "logistics": "school OR pickup OR practice OR appointment",
    "travel": "flight OR itinerary OR booking OR reservation",
    "reply": "is:unread",
}


class LiveGoogleClient(GoogleClient):
    def __init__(self, token_manager: TokenManager, http: HttpClient):
        self.tokens = token_manager
        self.http = http

    # -- helpers -----------------------------------------------------------------------
    def _auth(self, account_id: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.tokens.access_token(account_id)}"}

    def _get(self, account_id: str, url: str, params=None) -> Dict:
        resp = self.http.request("GET", url, headers=self._auth(account_id), params=params)
        if not resp.ok:
            raise SourceError(f"GET {url} -> HTTP {resp.status}")
        return resp.body

    def _post(self, account_id: str, url: str, json_body: Dict) -> Dict:
        resp = self.http.request("POST", url, headers=self._auth(account_id), json_body=json_body)
        if not resp.ok:
            raise SourceError(f"POST {url} -> HTTP {resp.status}")
        return resp.body

    # -- reads -------------------------------------------------------------------------
    def search_relevant_mail(self, account_id, categories, window_days) -> List[Dict]:
        cats = categories or list(_CATEGORY_Q.keys())
        clauses = [f"({_CATEGORY_Q[c]})" for c in cats if c in _CATEGORY_Q]
        q = f"newer_than:{max(window_days, 1)}d -category:promotions"
        if clauses:
            q = "(" + " OR ".join(clauses) + ") " + q
        listing = self._get(account_id, f"{GMAIL}/messages", params={"q": q, "maxResults": 15})
        out = []
        for m in listing.get("messages", [])[:15]:
            msg = self._get(account_id, f"{GMAIL}/messages/{m['id']}",
                            params={"format": "metadata",
                                    "metadataHeaders": ["From", "Subject", "Date"]})
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            out.append({
                "source": "gmail",
                "account_id": account_id,
                "source_ref": f"gmail:{m['id']}",
                "sender": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
                "categories": cats,
                "link": f"https://mail.google.com/mail/u/0/#all/{m['id']}",
            })
        return out

    def list_day_events(self, account_id, local_date, tz) -> List[Dict]:
        time_min = f"{local_date}T00:00:00"
        # end-exclusive next day
        y, mo, d = (int(x) for x in local_date.split("-"))
        import datetime as _dt
        nxt = (_dt.date(y, mo, d) + _dt.timedelta(days=1)).isoformat()
        cals = self._get(account_id, f"{CALENDAR}/users/me/calendarList").get("items", [])
        events: List[Dict] = []
        for cal in cals:
            cid = cal.get("id")
            listing = self._get(account_id, f"{CALENDAR}/calendars/{cid}/events", params={
                "timeMin": f"{time_min}Z", "timeMax": f"{nxt}T00:00:00Z",
                "singleEvents": "true", "orderBy": "startTime", "maxResults": 40,
            })
            for e in listing.get("items", []):
                start = e.get("start", {})
                end = e.get("end", {})
                all_day = "date" in start
                events.append({
                    "source": "calendar",
                    "account_id": account_id,
                    "source_ref": f"calendar:{e.get('id')}",
                    "calendar_id": cid,
                    "title": e.get("summary", "(no title)"),
                    "local_date": local_date,
                    "start": start.get("dateTime") or start.get("date"),
                    "end": end.get("dateTime") or end.get("date"),
                    "timezone": start.get("timeZone", tz),
                    "all_day": all_day,
                    "location": e.get("location"),
                    "attendees": [a.get("email") for a in e.get("attendees", []) if a.get("email")],
                    "description": e.get("description"),
                    "link": e.get("htmlLink"),
                })
        return events

    def get_referenced_drive_metadata(self, account_id, refs) -> List[Dict]:
        out = []
        for ref in refs:
            file_id = ref.split(":", 1)[-1]
            f = self._get(account_id, f"{DRIVE}/files/{file_id}",
                          params={"fields": "id,name,mimeType,owners,modifiedTime,webViewLink"})
            out.append({
                "source": "drive",
                "account_id": account_id,
                "source_ref": f"drive:{f.get('id', file_id)}",
                "name": f.get("name"),
                "mime_type": f.get("mimeType"),
                "owner": (f.get("owners") or [{}])[0].get("emailAddress"),
                "modified": f.get("modifiedTime"),
                "link": f.get("webViewLink"),
            })
        return out

    def get_source_details(self, account_id, source_ref) -> Dict:
        kind, _, ident = source_ref.partition(":")
        if kind == "gmail":
            msg = self._get(account_id, f"{GMAIL}/messages/{ident}", params={"format": "full"})
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            return {
                "source": "gmail", "account_id": account_id, "source_ref": source_ref,
                "sender": headers.get("From", ""), "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""), "snippet": msg.get("snippet", ""),
                "body": _extract_gmail_body(msg.get("payload", {})),
            }
        if kind == "calendar":
            e = self._get(account_id, f"{CALENDAR}/calendars/primary/events/{ident}")
            return {"source": "calendar", "account_id": account_id, "source_ref": source_ref, **e}
        raise SourceError(f"unsupported source_ref kind: {kind}")

    # -- actions (drafts only; approval enforced in the tool layer) ---------------------
    def create_gmail_draft(self, account_id, to, subject, body, idempotency_key) -> Dict:
        msg = EmailMessage()
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        msg.set_content(body)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        created = self._post(account_id, f"{GMAIL}/drafts", {"message": {"raw": raw}})
        return {
            "draft_id": created.get("id"),
            "account_id": account_id,
            "to": to,
            "subject": subject,
            "sent": False,  # drafts.create never sends
            "idempotency_key": idempotency_key,
            "location": "Gmail > Drafts",
        }

    def create_calendar_event(self, account_id, calendar_id, event, idempotency_key) -> Dict:
        created = self._post(account_id, f"{CALENDAR}/calendars/{calendar_id}/events", event)
        return {
            "event_id": created.get("id"),
            "account_id": account_id,
            "calendar_id": calendar_id,
            "link": created.get("htmlLink"),
            "idempotency_key": idempotency_key,
        }


def _extract_gmail_body(payload: Dict) -> str:
    """Best-effort plain-text extraction from a Gmail message payload."""
    def decode(data: str) -> str:
        try:
            return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")
        except Exception:
            return ""

    if payload.get("mimeType", "").startswith("text/plain"):
        data = payload.get("body", {}).get("data")
        if data:
            return decode(data)
    for part in payload.get("parts", []) or []:
        text = _extract_gmail_body(part)
        if text:
            return text
    data = payload.get("body", {}).get("data")
    return decode(data) if data else ""
