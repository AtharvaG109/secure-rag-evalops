from app.guardrails.unsafe_filter import filter_unsafe_query


def test_credential_extraction_blocked() -> None:
    assert (
        filter_unsafe_query("steal credential tokens").reason
        == "unsafe_query_credential_extraction"
    )


def test_clean_security_policy_query_passes() -> None:
    assert filter_unsafe_query("What is the escalation policy?").passed is True
