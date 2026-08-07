import base64
import hashlib
import time
import unittest

from _util import CONNECTOR_ROOT  # noqa: F401  (path)
from boo_connector.google import oauth


class ConsumedStore:
    def __init__(self):
        self.seen = set()

    def is_consumed(self, jti):
        return jti in self.seen

    def mark(self, jti):
        self.seen.add(jti)


class TestPKCE(unittest.TestCase):
    def test_challenge_matches_verifier(self):
        p = oauth.generate_pkce()
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(p["code_verifier"].encode()).digest()
        ).rstrip(b"=").decode()
        self.assertEqual(p["code_challenge"], expected)
        self.assertEqual(p["method"], "S256")


class TestState(unittest.TestCase):
    def setUp(self):
        self.secret = b"server-state-secret"
        self.cs = ConsumedStore()

    def test_issue_and_verify(self):
        issued = oauth.issue_state(self.secret, "session-123")
        payload = oauth.verify_state(self.secret, issued["state"], "session-123",
                                     self.cs.is_consumed, self.cs.mark)
        self.assertEqual(payload["sid"], "session-123")
        self.assertEqual(payload["nonce"], issued["nonce"])

    def test_session_binding_enforced(self):
        issued = oauth.issue_state(self.secret, "session-123")
        with self.assertRaises(oauth.OAuthError):
            oauth.verify_state(self.secret, issued["state"], "different-session",
                               self.cs.is_consumed, self.cs.mark)

    def test_single_use_replay_rejected(self):
        issued = oauth.issue_state(self.secret, "s")
        oauth.verify_state(self.secret, issued["state"], "s", self.cs.is_consumed, self.cs.mark)
        with self.assertRaises(oauth.OAuthError):
            oauth.verify_state(self.secret, issued["state"], "s", self.cs.is_consumed, self.cs.mark)

    def test_expiry_enforced(self):
        issued = oauth.issue_state(self.secret, "s", ttl_seconds=10, now=1000)
        with self.assertRaises(oauth.OAuthError):
            oauth.verify_state(self.secret, issued["state"], "s", self.cs.is_consumed, self.cs.mark, now=2000)

    def test_bad_signature_rejected(self):
        issued = oauth.issue_state(self.secret, "s")
        with self.assertRaises(oauth.OAuthError):
            oauth.verify_state(b"wrong-secret", issued["state"], "s", self.cs.is_consumed, self.cs.mark)


class TestRequestBuilders(unittest.TestCase):
    def cfg(self):
        return oauth.OAuthConfig(client_id="cid", client_secret="sec",
                                 redirect_uri="https://boo.example/callback")

    def test_auth_url_requests_offline_and_pkce_and_no_send_scope(self):
        url = oauth.build_authorization_url(self.cfg(), "state123", "challenge", "nonce123")
        self.assertIn("access_type=offline", url)
        self.assertIn("code_challenge_method=S256", url)
        self.assertIn("prompt=consent", url)
        self.assertIn("gmail.compose", url)          # drafts
        self.assertNotIn("gmail.send", url)          # NEVER send

    def test_token_exchange_request_shape(self):
        req = oauth.build_token_exchange_request(self.cfg(), "code", "verifier")
        self.assertEqual(req["url"], oauth.TOKEN_ENDPOINT)
        self.assertEqual(req["data"]["grant_type"], "authorization_code")
        self.assertEqual(req["data"]["code_verifier"], "verifier")

    def test_refresh_request_shape(self):
        req = oauth.build_refresh_request(self.cfg(), "rtok")
        self.assertEqual(req["data"]["grant_type"], "refresh_token")
        self.assertEqual(req["data"]["refresh_token"], "rtok")


if __name__ == "__main__":
    unittest.main()
