from __future__ import annotations

from app.core.auth import generate_api_key, hash_api_key


def test_generated_api_keys_are_prefixed_and_hashed() -> None:
    token = generate_api_key()

    assert token.startswith("srg_live_")
    assert hash_api_key(token) != token
    assert hash_api_key(token) == hash_api_key(token)
