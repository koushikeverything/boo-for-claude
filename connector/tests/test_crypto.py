import unittest

from _util import make_cipher, TEST_KEYS
from boo_connector.crypto import EnvelopeCipher, CryptoError


class TestEnvelope(unittest.TestCase):
    def test_roundtrip(self):
        c = make_cipher()
        token = c.encrypt("refresh-token-secret", aad=b"sub-personal")
        self.assertNotIn("refresh-token-secret", token)  # not plaintext
        self.assertEqual(c.decrypt(token, aad=b"sub-personal"), "refresh-token-secret")

    def test_nonce_makes_ciphertext_unique(self):
        c = make_cipher()
        self.assertNotEqual(c.encrypt("same"), c.encrypt("same"))

    def test_tamper_is_detected(self):
        c = make_cipher()
        token = c.encrypt("secret")
        # flip a character in the middle of the token
        bad = list(token)
        bad[len(bad) // 2] = "A" if bad[len(bad) // 2] != "A" else "B"
        with self.assertRaises(CryptoError):
            c.decrypt("".join(bad))

    def test_aad_binding(self):
        c = make_cipher()
        token = c.encrypt("secret", aad=b"sub-personal")
        with self.assertRaises(CryptoError):
            c.decrypt(token, aad=b"sub-work")  # wrong associated data → auth fails

    def test_key_rotation_decrypts_old_version(self):
        old = EnvelopeCipher(TEST_KEYS, current_version=1)
        token_v1 = old.encrypt("secret")
        # a cipher whose current version is 2 must still decrypt a v1 token, and flag rotation
        new = EnvelopeCipher(TEST_KEYS, current_version=2)
        self.assertEqual(new.decrypt(token_v1), "secret")
        self.assertTrue(new.needs_rotation(token_v1))
        self.assertFalse(new.needs_rotation(new.encrypt("secret")))

    def test_unknown_version_rejected(self):
        c = EnvelopeCipher({1: b"k" * 32}, current_version=1)
        token = make_cipher().encrypt("secret")  # encrypted with version 2, unknown to c
        with self.assertRaises(CryptoError):
            c.decrypt(token)

    def test_short_key_rejected(self):
        with self.assertRaises(CryptoError):
            EnvelopeCipher({1: b"short"})

    def test_from_env(self):
        import base64
        k = base64.urlsafe_b64encode(b"z" * 32).rstrip(b"=").decode()
        c = EnvelopeCipher.from_env({"BOO_ENC_KEYS": f"1:{k}"})
        self.assertEqual(c.decrypt(c.encrypt("x")), "x")


if __name__ == "__main__":
    unittest.main()
