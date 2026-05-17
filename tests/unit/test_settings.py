from app.core.settings import Settings


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.QDRANT_URL == "http://localhost:6333"
    assert settings.EMBEDDING_DIMENSIONS == 3072
    assert settings.CHAT_INPUT_PRICE_PER_1M == 0.0
    assert settings.RUN_MIGRATIONS_ON_STARTUP is False


def test_production_settings_reject_insecure_defaults() -> None:
    settings = Settings(ENVIRONMENT="production", _env_file=None)

    try:
        settings.validate_for_runtime()
    except RuntimeError as exc:
        assert "insecure_production_settings" in str(exc)
    else:
        raise AssertionError("production settings should reject insecure defaults")


def test_production_settings_accept_hardened_values() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        ALLOW_LOCAL_DEV_AUTH=False,
        AUTH_TOKEN_PEPPER="a-long-random-secret",
        RATE_LIMIT_PER_MINUTE=120,
        TRUSTED_HOSTS="rag.internal.example.com",
        _env_file=None,
    )

    settings.validate_for_runtime()
