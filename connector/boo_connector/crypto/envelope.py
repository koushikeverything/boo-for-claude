"""Versioned envelope encryption for refresh tokens.

Design goals (from docs/THREAT-MODEL.md):
  * Authenticated encryption (encrypt-then-MAC) — tampering is detected.
  * Versioned keys — supports rotation: decrypt any historical version, encrypt with the current one.
  * Per-record random nonce — same plaintext encrypts differently every time.
  * No plaintext key material in logs; keys come from env/secret manager, never the code.
  * Stdlib-only default so the whole connector is auditable and testable with no dependencies.

Default backend: HMAC-SHA256 keystream (CTR) + HMAC-SHA256 tag. This is a sound
encrypt-then-MAC AEAD construction using only `hmac`/`hashlib`/`secrets`. For a FIPS/AES-GCM
deployment, set backend="aesgcm" (requires the `cryptography` package) — the token format carries a
backend byte so both can coexist during migration.

Token layout (base64url, no padding):
    version(1) | backend(1) | nonce(16) | ciphertext(n) | tag(32)

`version` indexes the key registry; `backend` selects the AEAD (0 = hmac-ctr, 1 = aes-gcm).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
from typing import Dict, Optional

NONCE_LEN = 16
TAG_LEN = 32
_BACKEND_HMAC_CTR = 0
_BACKEND_AES_GCM = 1


class CryptoError(Exception):
    pass


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _derive(master: bytes, label: bytes) -> bytes:
    return hmac.new(master, label, hashlib.sha256).digest()


def _keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac.new(enc_key, nonce + struct.pack(">Q", counter), hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


class EnvelopeCipher:
    """Encrypts/decrypts secrets under a versioned key registry.

    keys: {version:int -> 32-byte master key}. current_version defaults to max(keys).
    """

    def __init__(self, keys: Dict[int, bytes], current_version: Optional[int] = None,
                 backend: str = "hmac-ctr"):
        if not keys:
            raise CryptoError("no keys provided")
        for v, k in keys.items():
            if len(k) < 32:
                raise CryptoError(f"key version {v} too short (need >= 32 bytes)")
        self.keys = dict(keys)
        self.current_version = current_version if current_version is not None else max(keys)
        if self.current_version not in self.keys:
            raise CryptoError("current_version not in key registry")
        if backend == "hmac-ctr":
            self.backend = _BACKEND_HMAC_CTR
        elif backend == "aesgcm":
            self.backend = _BACKEND_AES_GCM
            # fail fast if the optional dependency is absent
            self._aesgcm()  # raises CryptoError if unavailable
        else:
            raise CryptoError(f"unknown backend {backend!r}")

    # -- construction from environment -------------------------------------------------
    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "EnvelopeCipher":
        """Build from env vars:
            BOO_ENC_KEYS="1:<base64url-32B>,2:<base64url-32B>"  (versioned registry)
            BOO_ENC_CURRENT_VERSION="2"   (optional; defaults to highest)
            BOO_CRYPTO_BACKEND="hmac-ctr" | "aesgcm"  (optional)
        Never hard-code keys; supply them via a secret manager.
        """
        env = env or dict(os.environ)
        raw = env.get("BOO_ENC_KEYS")
        if not raw:
            raise CryptoError("BOO_ENC_KEYS not set")
        keys: Dict[int, bytes] = {}
        for part in raw.split(","):
            ver, _, b64 = part.strip().partition(":")
            keys[int(ver)] = _b64d(b64)
        cur = env.get("BOO_ENC_CURRENT_VERSION")
        backend = env.get("BOO_CRYPTO_BACKEND", "hmac-ctr")
        return cls(keys, int(cur) if cur else None, backend=backend)

    # -- public API --------------------------------------------------------------------
    def encrypt(self, plaintext: str, aad: bytes = b"") -> str:
        pt = plaintext.encode("utf-8")
        nonce = os.urandom(NONCE_LEN)
        master = self.keys[self.current_version]
        header = bytes([self.current_version & 0xFF, self.backend & 0xFF]) + nonce
        if self.backend == _BACKEND_HMAC_CTR:
            enc_key = _derive(master, b"boo-enc")
            mac_key = _derive(master, b"boo-mac")
            ks = _keystream(enc_key, nonce, len(pt))
            ct = bytes(a ^ b for a, b in zip(pt, ks))
            tag = hmac.new(mac_key, header + ct + aad, hashlib.sha256).digest()
            return _b64e(header + ct + tag)
        else:  # AES-GCM
            AESGCM = self._aesgcm()
            key = _derive(master, b"boo-aesgcm-key")  # 32B key for AES-256
            aesgcm = AESGCM(key)
            # GCM needs a 12-byte nonce; derive it from our 16-byte nonce deterministically.
            gcm_nonce = hashlib.sha256(nonce).digest()[:12]
            ct_and_tag = aesgcm.encrypt(gcm_nonce, pt, header + aad)  # tag appended by lib
            return _b64e(header + ct_and_tag)

    def decrypt(self, token: str, aad: bytes = b"") -> str:
        raw = _b64d(token)
        if len(raw) < 2 + NONCE_LEN + TAG_LEN:
            raise CryptoError("token too short")
        version = raw[0]
        backend = raw[1]
        nonce = raw[2:2 + NONCE_LEN]
        header = raw[:2 + NONCE_LEN]
        body = raw[2 + NONCE_LEN:]
        master = self.keys.get(version)
        if master is None:
            raise CryptoError(f"unknown key version {version}")
        if backend == _BACKEND_HMAC_CTR:
            ct, tag = body[:-TAG_LEN], body[-TAG_LEN:]
            mac_key = _derive(master, b"boo-mac")
            expected = hmac.new(mac_key, header + ct + aad, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, tag):
                raise CryptoError("authentication failed (tampered or wrong key)")
            enc_key = _derive(master, b"boo-enc")
            ks = _keystream(enc_key, nonce, len(ct))
            pt = bytes(a ^ b for a, b in zip(ct, ks))
            return pt.decode("utf-8")
        elif backend == _BACKEND_AES_GCM:
            AESGCM = self._aesgcm()
            key = _derive(master, b"boo-aesgcm-key")
            gcm_nonce = hashlib.sha256(nonce).digest()[:12]
            try:
                pt = AESGCM(key).decrypt(gcm_nonce, body, header + aad)
            except Exception as e:  # pragma: no cover - depends on optional lib
                raise CryptoError("authentication failed") from e
            return pt.decode("utf-8")
        raise CryptoError(f"unknown backend byte {backend}")

    def needs_rotation(self, token: str) -> bool:
        """True if a stored token was encrypted under an older key version."""
        raw = _b64d(token)
        return len(raw) >= 1 and raw[0] != self.current_version

    @staticmethod
    def _aesgcm():
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore
            return AESGCM
        except Exception as e:  # pragma: no cover
            raise CryptoError("aesgcm backend requires the 'cryptography' package") from e
