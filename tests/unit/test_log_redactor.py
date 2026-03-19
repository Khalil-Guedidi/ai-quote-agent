"""Unit tests for security.log_redactor — confidential data redaction."""

from __future__ import annotations

from quote_agent.security.log_redactor import redact, redact_context


def test_clean_text_passes_unchanged() -> None:
    """Text without confidential data passes through unchanged."""
    text = "Bonjour, je souhaite un devis pour 50 roulements SKF 6205."
    result = redact(text)

    assert result.redacted_text == text
    assert result.redaction_count == 0
    assert result.redactions_applied == []


def test_email_address_redacted() -> None:
    """Email address detected and replaced with [REDACTED_EMAIL]."""
    text = "Contact: dupont@acme.fr pour le devis"
    result = redact(text)

    assert "[REDACTED_EMAIL]" in result.redacted_text
    assert "dupont@acme.fr" not in result.redacted_text
    assert result.redaction_count >= 1
    assert any(m.category == "email" for m in result.redactions_applied)


def test_french_phone_06_redacted() -> None:
    """French mobile phone (06 xx xx xx xx) detected and replaced."""
    text = "Appelez-moi au 06 12 34 56 78"
    result = redact(text)

    assert "[REDACTED_PHONE]" in result.redacted_text
    assert "06 12 34 56 78" not in result.redacted_text
    assert any(m.category == "phone" for m in result.redactions_applied)


def test_international_phone_plus33_redacted() -> None:
    """International phone (+33) detected and replaced."""
    text = "Tel: +33 6 12 34 56 78"
    result = redact(text)

    assert "[REDACTED_PHONE]" in result.redacted_text
    assert "+33 6 12 34 56 78" not in result.redacted_text


def test_price_euro_symbol_redacted() -> None:
    """Price with € symbol detected and replaced with [REDACTED_PRICE]."""
    text = "Le montant est de 500€ HT"
    result = redact(text)

    assert "[REDACTED_PRICE]" in result.redacted_text
    assert "500€" not in result.redacted_text
    assert any(m.category == "price" for m in result.redactions_applied)


def test_price_eur_redacted() -> None:
    """Price with EUR detected and replaced."""
    text = "Total: 1500 EUR"
    result = redact(text)

    assert "[REDACTED_PRICE]" in result.redacted_text
    assert "1500 EUR" not in result.redacted_text


def test_french_pricing_terms_redacted() -> None:
    """French pricing terms (prix, tarif, remise + amount) detected."""
    text = "prix: 250 pour les roulements"
    result = redact(text)

    assert "[REDACTED_PRICE]" in result.redacted_text
    assert "prix: 250" not in result.redacted_text


def test_iban_pattern_redacted() -> None:
    """IBAN pattern detected and replaced."""
    text = "Virement sur FR76 3000 1007 9412 3456 7890 185"
    result = redact(text)

    assert "[REDACTED_IBAN]" in result.redacted_text
    assert "FR76" not in result.redacted_text


def test_multiple_confidential_items_all_redacted() -> None:
    """Multiple confidential items in single text — all redacted."""
    text = "Client dupont@acme.fr demande 500€ de tubes, tel 06 12 34 56 78"
    result = redact(text)

    assert "dupont@acme.fr" not in result.redacted_text
    assert "500€" not in result.redacted_text
    assert "06 12 34 56 78" not in result.redacted_text
    assert result.redaction_count >= 3


def test_redact_context_recursive_string_values() -> None:
    """redact_context() recursively redacts string values in nested dict."""
    context = {
        "sender": "dupont@acme.fr",
        "nested": {"email": "test@example.com", "count": 5},
    }
    result = redact_context(context)

    assert result["sender"] == "[REDACTED_EMAIL]"
    assert result["nested"]["email"] == "[REDACTED_EMAIL]"
    assert result["nested"]["count"] == 5


def test_redact_context_preserves_non_string_values() -> None:
    """redact_context() preserves non-string values (int, float, bool, None)."""
    context = {
        "count": 42,
        "ratio": 3.14,
        "active": True,
        "error": None,
    }
    result = redact_context(context)

    assert result == context


def test_empty_string_handled() -> None:
    """Empty string handled gracefully."""
    result = redact("")

    assert result.redacted_text == ""
    assert result.redaction_count == 0


def test_none_handled_gracefully() -> None:
    """None input handled gracefully."""
    result = redact(None)

    assert result.redacted_text == ""
    assert result.original_text == ""
    assert result.redaction_count == 0


def test_redact_context_with_list_values() -> None:
    """redact_context handles list values with mixed types."""
    context = {
        "recipients": ["dupont@acme.fr", "martin@corp.com"],
        "counts": [1, 2, 3],
    }
    result = redact_context(context)

    assert result["recipients"][0] == "[REDACTED_EMAIL]"
    assert result["recipients"][1] == "[REDACTED_EMAIL]"
    assert result["counts"] == [1, 2, 3]
