from app.guardrails.pii_redactor import redact_pii


def test_common_pii_is_redacted() -> None:
    result = redact_pii("email ethan@example.com phone 415-555-0100 ssn 123-45-6789")
    assert "[EMAIL]" in result.text
    assert "[PHONE]" in result.text
    assert "[SSN]" in result.text


def test_luhn_valid_credit_card_is_redacted() -> None:
    assert "[CREDIT_CARD]" in redact_pii("4111 1111 1111 1111").text


def test_random_non_card_number_is_not_redacted() -> None:
    assert redact_pii("1234 5678 9012 3456").text == "1234 5678 9012 3456"
