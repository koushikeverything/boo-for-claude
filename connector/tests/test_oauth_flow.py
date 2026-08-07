"""Account-linking flow: begin_connect + complete_connect, with a fake token endpoint."""
import base64
import json
import tempfile
import unittest

from _util import seeded_store
from boo_connector.google.http import FakeHttpClient, Response
from boo_connector.google.oauth import OAuthConfig, OAuthError, TOKEN_ENDPOINT
from boo_connector.google import oauth_flow


def cfg():
    return OAuthConfig(client_id="cid", client_secret="sec", redirect_uri="https://boo.example/cb")


def make_id_token(sub, email):
    payload = base64.urlsafe_b64encode(json.dumps({"sub": sub, "email": email}).encode()).rstrip(b"=").decode()
    return f"header.{payload}.sig"


class TestOAuthFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store, self.user = seeded_store(self.tmp.name)
        self.secret = b"state-secret"

    def tearDown(self):
        self.tmp.cleanup()

    def test_begin_connect_builds_pkce_url(self):
        out = oauth_flow.begin_connect(cfg(), self.secret, "session-1")
        self.assertIn("code_challenge_method=S256", out["auth_url"])
        self.assertIn("access_type=offline", out["auth_url"])
        self.assertTrue(out["code_verifier"])
        self.assertTrue(out["state"])

    def _token_http(self, sub="sub-new", email="new@x.com", refresh="RT-new"):
        body = {"access_token": "AT", "expires_in": 3600, "scope": "openid email",
                "id_token": make_id_token(sub, email)}
        if refresh:
            body["refresh_token"] = refresh
        routes_resp = Response(200, body)
        return FakeHttpClient(lambda **kw: routes_resp if kw["url"] == TOKEN_ENDPOINT else Response(404, {}))

    def test_complete_connect_links_account_by_sub(self):
        begun = oauth_flow.begin_connect(cfg(), self.secret, "session-1")
        http = self._token_http(sub="sub-new", email="new@x.com")
        result = oauth_flow.complete_connect(
            cfg(), self.secret, "session-1", begun["state"], "auth-code",
            begun["code_verifier"], http, self.store, self.user, label="Family",
        )
        self.assertEqual(result["account_id"], "sub-new")
        self.assertTrue(result["has_refresh_token"])
        acc = self.store.get_account("sub-new")
        self.assertEqual(acc.label, "Family")
        self.assertEqual(acc.user_id, self.user)
        # refresh token stored encrypted + retrievable
        self.assertEqual(self.store.load_refresh_token("sub-new"), "RT-new")

    def test_state_is_single_use(self):
        begun = oauth_flow.begin_connect(cfg(), self.secret, "session-1")
        http = self._token_http()
        oauth_flow.complete_connect(cfg(), self.secret, "session-1", begun["state"], "c",
                                    begun["code_verifier"], http, self.store, self.user)
        # replaying the same state must fail
        with self.assertRaises(OAuthError):
            oauth_flow.complete_connect(cfg(), self.secret, "session-1", begun["state"], "c",
                                        begun["code_verifier"], http, self.store, self.user)

    def test_wrong_session_rejected(self):
        begun = oauth_flow.begin_connect(cfg(), self.secret, "session-1")
        with self.assertRaises(OAuthError):
            oauth_flow.complete_connect(cfg(), self.secret, "ATTACKER-session", begun["state"], "c",
                                        begun["code_verifier"], self._token_http(), self.store, self.user)

    def test_adding_second_account_keeps_first(self):
        # link a second account; the seeded accounts remain, proving multi-account accumulation
        begun = oauth_flow.begin_connect(cfg(), self.secret, "s")
        oauth_flow.complete_connect(cfg(), self.secret, "s", begun["state"], "c",
                                    begun["code_verifier"], self._token_http(sub="sub-3", email="c@x.com"),
                                    self.store, self.user, label="Work2")
        ids = {a.account_id for a in self.store.list_accounts(self.user)}
        self.assertIn("sub-3", ids)
        self.assertIn("sub-personal", ids)   # first account untouched
        self.assertIn("sub-work", ids)


if __name__ == "__main__":
    unittest.main()
