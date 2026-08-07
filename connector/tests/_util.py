"""Path setup + seeded-store helper for connector tests."""
import json
import os
import sys

CONNECTOR_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CONNECTOR_ROOT not in sys.path:
    sys.path.insert(0, CONNECTOR_ROOT)

from boo_connector.crypto import EnvelopeCipher  # noqa: E402
from boo_connector.store import Store  # noqa: E402
from boo_connector.google.client import FixturesGoogleClient  # noqa: E402

FIXTURES = os.path.join(CONNECTOR_ROOT, "fixtures")

# Two deterministic test keys (versions 1 and 2) so rotation is testable.
TEST_KEYS = {1: b"k" * 32, 2: b"j" * 40}


def make_cipher(current_version=2) -> EnvelopeCipher:
    return EnvelopeCipher(TEST_KEYS, current_version=current_version)


def seeded_store(tmp_path) -> Store:
    """A Store backed by a temp sqlite db, seeded from fixtures/accounts.json with fake tokens."""
    cipher = make_cipher()
    store = Store(os.path.join(str(tmp_path), "boo_test.db"), cipher)
    with open(os.path.join(FIXTURES, "accounts.json")) as f:
        seed = json.load(f)
    for a in seed["accounts"]:
        store.upsert_account(a["account_id"], seed["user_id"], a["label"], a["scopes"], a["email_verified"])
        store.store_refresh_token(a["account_id"], a["fake_refresh_token"])
    return store, seed["user_id"]


def fixtures_client() -> FixturesGoogleClient:
    return FixturesGoogleClient(FIXTURES)
