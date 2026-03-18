"""Tests for the clean() pure function."""

from __future__ import annotations

from quote_agent.services.email_cleaner import clean

# ---------------------------------------------------------------------------
# Task 4.1: Unit tests for clean() pure function
# ---------------------------------------------------------------------------


class TestCleanSignatureStripping:
    """Test signature removal patterns."""

    def test_rfc3676_signature_stripped(self) -> None:
        """Email with '-- \\n' signature block is stripped."""
        raw = "Please send me a quote for 100 bolts.\n-- \nJohn Doe\nSales Manager\n+33 1 23 45 67"
        result = clean(raw)
        assert "John Doe" not in result
        assert "Sales Manager" not in result
        assert "Please send me a quote for 100 bolts." in result

    def test_cordialement_signature_stripped(self) -> None:
        """Email with 'Cordialement' signature stripped."""
        raw = (
            "Bonjour,\n\nJe souhaite un devis pour 50 vannes.\n\n"
            "Merci de me faire parvenir votre offre.\n\n"
            "Cordialement,\nMarie Dupont\nDirectrice des achats"
        )
        result = clean(raw)
        assert "Marie Dupont" not in result
        assert "Directrice des achats" not in result
        assert "50 vannes" in result

    def test_regards_signature_stripped(self) -> None:
        """Email with 'Regards' / 'Best regards' signature stripped."""
        raw = (
            "Hello,\n\nI need a quote for 200 steel pipes.\n\n"
            "Please include delivery time.\n\n"
            "Best regards,\nJane Smith\nProcurement Officer"
        )
        result = clean(raw)
        assert "Jane Smith" not in result
        assert "200 steel pipes" in result

    def test_sent_from_iphone_stripped(self) -> None:
        """Email with 'Envoyé de mon iPhone' / 'Sent from' stripped."""
        raw = "Besoin devis 30 raccords inox urgent\n\nEnvoyé de mon iPhone"
        result = clean(raw)
        assert "Envoyé de mon iPhone" not in result
        assert "30 raccords inox" in result

    def test_sent_from_my_iphone_english(self) -> None:
        """Email with 'Sent from my iPhone' stripped."""
        raw = "Need quote for 50 flanges ASAP\n\nSent from my iPhone"
        result = clean(raw)
        assert "Sent from my iPhone" not in result
        assert "50 flanges" in result


class TestCleanReplyThreadStripping:
    """Test reply thread removal patterns."""

    def test_quoted_reply_lines_stripped(self) -> None:
        """Email with '>' quoted reply lines stripped."""
        raw = (
            "Oui, je confirme la commande.\n\n"
            "> Bonjour, souhaitez-vous confirmer?\n"
            "> Cordialement,\n"
            "> L'équipe commerciale"
        )
        result = clean(raw)
        assert "je confirme la commande" in result
        assert "> Bonjour" not in result

    def test_on_wrote_header_stripped(self) -> None:
        """Email with 'On ... wrote:' header and quoted text stripped."""
        raw = (
            "Yes, please proceed with the order.\n\n"
            "On Mon, Mar 18, 2026 at 10:00 AM John Doe <john@example.com> wrote:\n"
            "> Can you confirm the quantities?\n"
            "> Thanks"
        )
        result = clean(raw)
        assert "please proceed with the order" in result
        assert "Can you confirm" not in result

    def test_le_a_ecrit_header_stripped(self) -> None:
        """Email with 'Le ... a écrit :' header and quoted text stripped."""
        raw = (
            "D'accord, je valide les quantités.\n\n"
            "Le 18 mars 2026 à 10:00, Marie Dupont <marie@example.com> a écrit :\n"
            "> Pouvez-vous confirmer les quantités?\n"
            "> Merci"
        )
        result = clean(raw)
        assert "je valide les quantités" in result
        assert "Pouvez-vous confirmer" not in result

    def test_original_message_separator_stripped(self) -> None:
        """Email with '-----Original Message-----' stripped."""
        raw = (
            "Voici ma demande de devis.\n\n"
            "-----Original Message-----\n"
            "From: supplier@example.com\n"
            "Sent: Monday, March 18, 2026\n"
            "Subject: RE: Quote\n\n"
            "Previous message content here."
        )
        result = clean(raw)
        assert "ma demande de devis" in result
        assert "Previous message content" not in result

    def test_forwarded_message_stripped(self) -> None:
        """Email with forwarded message header stripped."""
        raw = (
            "Peux-tu traiter cette demande?\n\n"
            "---------- Forwarded message ----------\n"
            "From: client@example.com\n"
            "Subject: Demande de devis\n\n"
            "Bonjour, je souhaite un devis."
        )
        result = clean(raw)
        assert "Peux-tu traiter cette demande" in result
        assert "Bonjour, je souhaite" not in result


class TestCleanDisclaimerStripping:
    """Test legal disclaimer removal."""

    def test_confidentiality_notice_stripped(self) -> None:
        """Email with 'CONFIDENTIALITY NOTICE' disclaimer stripped."""
        raw = (
            "Please provide a quote for 100 widgets.\n\n"
            "CONFIDENTIALITY NOTICE: This email and any attachments are confidential "
            "and intended solely for the use of the individual to whom it is addressed."
        )
        result = clean(raw)
        assert "100 widgets" in result
        assert "CONFIDENTIALITY" not in result

    def test_french_confidential_disclaimer_stripped(self) -> None:
        """Email with 'Ce message est confidentiel' disclaimer stripped."""
        raw = (
            "Merci de m'envoyer un devis pour 200 pièces.\n\n"
            "Ce message est confidentiel et destiné uniquement à la personne "
            "à laquelle il est adressé."
        )
        result = clean(raw)
        assert "200 pièces" in result
        assert "confidentiel" not in result


class TestCleanPassthrough:
    """Test that clean emails pass through unchanged."""

    def test_simple_email_passes_through(self) -> None:
        """Simple email with no noise passes through unchanged."""
        raw = "Bonjour,\n\nJe souhaite un devis pour 50 vannes DN80 en inox 316L.\n\nMerci."
        result = clean(raw)
        assert result == raw.strip()

    def test_empty_email_returns_empty(self) -> None:
        """Empty email returns empty string."""
        assert clean("") == ""

    def test_content_with_double_dash_not_overstripped(self) -> None:
        """Product containing '--' is NOT over-stripped (not RFC 3676 signature)."""
        # Note: RFC 3676 requires "-- " (with trailing space). A plain "--" is NOT a signature.
        raw = "Besoin de 10 raccords type DN50--PN16 en acier.\n\nMerci de confirmer."
        result = clean(raw)
        assert "DN50--PN16" in result


class TestCleanCombinedNoise:
    """Test emails with multiple noise types."""

    def test_multiple_noise_types_all_cleaned(self) -> None:
        """Email with signature + reply thread + disclaimer all cleaned."""
        raw = (
            "Oui, je confirme ma commande de 100 boulons M12.\n\n"
            "Cordialement,\n"
            "Pierre Martin\n"
            "Chef des achats\n"
            "+33 1 99 88 77 66\n\n"
            "CONFIDENTIALITY NOTICE: This message is confidential.\n\n"
            "On Mon, Mar 18, 2026 at 09:00 AM Supplier <s@ex.com> wrote:\n"
            "> Here is the revised quote.\n"
            "> Best regards,\n"
            "> The sales team"
        )
        result = clean(raw)
        assert "100 boulons M12" in result
        assert "Pierre Martin" not in result
        assert "CONFIDENTIALITY" not in result
        assert "revised quote" not in result

    def test_french_email_cleaned_correctly(self) -> None:
        """Email in French with French-specific patterns cleaned correctly."""
        raw = (
            "Bonjour,\n\n"
            "Suite à notre échange, je vous confirme ma demande de devis:\n"
            "- 50 vannes papillon DN100\n"
            "- 30 raccords inox 316L\n\n"
            "Merci de me faire parvenir votre meilleure offre.\n\n"
            "Bien cordialement,\n"
            "Sophie Lefèvre\n"
            "Responsable Achats\n"
            "Tél: 04 78 99 00 11\n\n"
            "AVERTISSEMENT: Ce courriel est confidentiel et réservé à l'usage "
            "exclusif de son destinataire."
        )
        result = clean(raw)
        assert "50 vannes papillon DN100" in result
        assert "30 raccords inox 316L" in result
        assert "Sophie Lefèvre" not in result
        assert "AVERTISSEMENT" not in result


class TestCleanSafetyValve:
    """Test the >90% stripping safety valve."""

    def test_safety_valve_prevents_overstripping(self) -> None:
        """If cleaning removes >90% of content, return original (normalized)."""
        # An email where the entire body matches a signature pattern
        raw = "Cordialement,\nJohn"
        result = clean(raw)
        # Safety valve should return the original content (normalized) instead of empty
        assert result == raw.strip()
