"""Live Google client + token manager, exercised with a FakeHttpClient (no network)."""
import tempfile
import unittest

from _util import seeded_store
from boo_connector.google.http import FakeHttpClient, Response
from boo_connector.google.oauth import OAuthConfig, TOKEN_ENDPOINT
from boo_connector.google.tokens import TokenManager, TokenError
from boo_connector.google.live import LiveGoogleClient, GMAIL, CALENDAR


def cfg():
    return OAuthConfig(client_id="cid", client_secret="sec", redirect_uri="https://boo.example/cb")


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def make_handler(routes):
    """routes: list of (predicate(method,url)->bool, Response). First match wins."""
    def handler(method, url, params=None, form=None, json_body=None, headers=None):
        for pred, resp in routes:
            if pred(method, url):
                return resp
        return Response(404, {"error": "no route", "url": url})
    return handler


class TestTokenManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store, self.user = seeded_store(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_refresh_and_cache(self):
        routes = [(lambda m, u: u == TOKEN_ENDPOINT, Response(200, {"access_token": "AT-1", "expires_in": 3600}))]
        http = FakeHttpClient(make_handler(routes))
        clock = Clock()
        tm = TokenManager(self.store, cfg(), http, clock=clock)
        self.assertEqual(tm.access_token("sub-personal"), "AT-1")
        self.assertEqual(len([c for c in http.calls if c["url"] == TOKEN_ENDPOINT]), 1)
        # cached — no second refresh
        self.assertEqual(tm.access_token("sub-personal"), "AT-1")
        self.assertEqual(len([c for c in http.calls if c["url"] == TOKEN_ENDPOINT]), 1)
        # advance past expiry → refreshes again
        clock.t += 4000
        tm.access_token("sub-personal")
        self.assertEqual(len([c for c in http.calls if c["url"] == TOKEN_ENDPOINT]), 2)

    def test_invalid_grant_marks_reconnect(self):
        routes = [(lambda m, u: u == TOKEN_ENDPOINT, Response(400, {"error": "invalid_grant"}))]
        tm = TokenManager(self.store, cfg(), FakeHttpClient(make_handler(routes)))
        with self.assertRaises(TokenError):
            tm.access_token("sub-personal")
        self.assertEqual(self.store.get_account("sub-personal").status, "reconnect_needed")


class TestLiveClient(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store, self.user = seeded_store(self.tmp.name)
        self.token_route = (lambda m, u: u == TOKEN_ENDPOINT,
                            Response(200, {"access_token": "AT-1", "expires_in": 3600}))

    def tearDown(self):
        self.tmp.cleanup()

    def _client(self, routes):
        http = FakeHttpClient(make_handler([self.token_route] + routes))
        tm = TokenManager(self.store, cfg(), http)
        return LiveGoogleClient(tm, http), http

    def test_search_relevant_mail_normalizes(self):
        routes = [
            (lambda m, u: u == f"{GMAIL}/messages", Response(200, {"messages": [{"id": "m1"}]})),
            (lambda m, u: u == f"{GMAIL}/messages/m1", Response(200, {
                "snippet": "Invoice due today",
                "payload": {"headers": [
                    {"name": "From", "value": "Biller <b@x.com>"},
                    {"name": "Subject", "value": "Invoice"},
                    {"name": "Date", "value": "Fri, 7 Aug 2026"},
                ]},
            })),
        ]
        client, http = self._client(routes)
        items = client.search_relevant_mail("sub-personal", ["bill"], 7)
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it["source_ref"], "gmail:m1")
        self.assertEqual(it["subject"], "Invoice")
        self.assertEqual(it["sender"], "Biller <b@x.com>")
        self.assertNotIn("AT-1", str(it))  # no token leakage
        # bearer token was actually attached
        api_call = [c for c in http.calls if c["url"] == f"{GMAIL}/messages"][0]
        self.assertEqual(api_call["headers"]["Authorization"], "Bearer AT-1")

    def test_list_day_events_detects_all_day(self):
        routes = [
            (lambda m, u: u == f"{CALENDAR}/users/me/calendarList",
             Response(200, {"items": [{"id": "primary"}]})),
            (lambda m, u: u == f"{CALENDAR}/calendars/primary/events", Response(200, {"items": [
                {"id": "e1", "summary": "All hands", "start": {"date": "2026-08-07"},
                 "end": {"date": "2026-08-08"}, "htmlLink": "http://x"},
                {"id": "e2", "summary": "1:1", "start": {"dateTime": "2026-08-07T13:00:00-07:00"},
                 "end": {"dateTime": "2026-08-07T13:30:00-07:00"}},
            ]})),
        ]
        client, _ = self._client(routes)
        events = client.list_day_events("sub-personal", "2026-08-07", "America/Los_Angeles")
        self.assertEqual(len(events), 2)
        self.assertTrue(events[0]["all_day"])
        self.assertFalse(events[1]["all_day"])
        self.assertEqual(events[0]["source_ref"], "calendar:e1")

    def test_create_gmail_draft_never_sends(self):
        routes = [(lambda m, u: u == f"{GMAIL}/drafts" and m == "POST", Response(200, {"id": "d1"}))]
        client, http = self._client(routes)
        r = client.create_gmail_draft("sub-personal", ["x@y.com"], "Hi", "Body", "idem-1")
        self.assertEqual(r["draft_id"], "d1")
        self.assertFalse(r["sent"])
        # assert we hit the drafts endpoint, never a send endpoint
        self.assertTrue(any(c["url"].endswith("/drafts") for c in http.calls))
        self.assertFalse(any("/send" in c["url"] for c in http.calls))

    def test_http_error_becomes_source_error(self):
        from boo_connector.google.client import SourceError
        routes = [(lambda m, u: u == f"{GMAIL}/messages", Response(500, {"error": "boom"}))]
        client, _ = self._client(routes)
        with self.assertRaises(SourceError):
            client.search_relevant_mail("sub-personal", ["bill"], 7)


if __name__ == "__main__":
    unittest.main()
