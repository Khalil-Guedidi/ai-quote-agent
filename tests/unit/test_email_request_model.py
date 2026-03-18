"""Tests for the EmailRequest SQLAlchemy model."""

from __future__ import annotations

import uuid

from quote_agent.models.email_request import EmailRequest


def test_email_request_fields() -> None:
    """EmailRequest stores all fields correctly."""
    record = EmailRequest(
        message_id="<test-123@example.com>",
        subject="Test Subject",
        sender="sender@example.com",
        recipients=["recipient@example.com"],
        raw_content="Hello world",
        folder="INBOX",
        status="received",
    )
    assert record.message_id == "<test-123@example.com>"
    assert record.subject == "Test Subject"
    assert record.sender == "sender@example.com"
    assert record.raw_content == "Hello world"
    assert record.folder == "INBOX"
    assert record.status == "received"
    assert record.error_message is None
    assert record.received_at is None


def test_email_request_table_name() -> None:
    """EmailRequest uses the correct table name."""
    assert EmailRequest.__tablename__ == "email_requests"


def test_email_request_id_is_uuid() -> None:
    """EmailRequest id column accepts UUID values."""
    record = EmailRequest(
        message_id="<test@example.com>",
        subject="Test",
        sender="sender@example.com",
        recipients=[],
        raw_content="body",
        folder="INBOX",
        status="received",
    )
    record.id = uuid.uuid4()
    assert isinstance(record.id, uuid.UUID)


def test_email_request_unique_message_id_constraint() -> None:
    """EmailRequest has a unique constraint on message_id."""
    table = EmailRequest.__table__
    message_id_col = table.c.message_id
    assert message_id_col.unique is True


def test_email_request_status_index() -> None:
    """EmailRequest has an index on status column."""
    table = EmailRequest.__table__
    index_names = {idx.name for idx in table.indexes}
    assert "ix_email_requests_status" in index_names


def test_email_request_recipients_json() -> None:
    """EmailRequest stores recipients as JSON list."""
    record = EmailRequest(
        message_id="<test@example.com>",
        subject="Test",
        sender="sender@example.com",
        recipients=["a@test.com", "b@test.com"],
        raw_content="body",
        folder="INBOX",
        status="received",
    )
    assert record.recipients == ["a@test.com", "b@test.com"]


def test_email_request_column_default_for_status() -> None:
    """EmailRequest status column has a schema-level default of 'received'."""
    table = EmailRequest.__table__
    status_col = table.c.status
    assert status_col.default.arg == "received"
