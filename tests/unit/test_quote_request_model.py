"""Tests for the QuoteRequest SQLAlchemy model."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import inspect

from quote_agent.models.quote_request import QuoteRequest


def test_quote_request_creation_with_all_fields() -> None:
    """QuoteRequest model can be created with all fields."""
    email_id = uuid.uuid4()
    qr = QuoteRequest(
        email_request_id=email_id,
        request_index=0,
        line_items=[{"description": "Vis M8", "quantity": 100}],
        client_name="Dupont SA",
        client_identifier="CLI-001",
        client_email="dupont@example.com",
        urgency="urgent",
        delivery_address="12 rue de Paris",
        notes="Livraison rapide",
        status="pending",
        error_message=None,
        confidence=0.85,
    )
    assert qr.email_request_id == email_id
    assert qr.request_index == 0
    assert qr.line_items == [{"description": "Vis M8", "quantity": 100}]
    assert qr.client_name == "Dupont SA"
    assert qr.status == "pending"
    assert qr.confidence == 0.85


def test_quote_request_fk_to_email_requests() -> None:
    """QuoteRequest has a FK relationship to email_requests.id."""
    mapper = inspect(QuoteRequest)
    fk_columns = [
        col
        for col in mapper.columns
        if col.foreign_keys
    ]
    assert len(fk_columns) == 1
    fk = next(iter(fk_columns[0].foreign_keys))
    assert fk.target_fullname == "email_requests.id"


def test_quote_request_unique_constraint_on_email_and_index() -> None:
    """QuoteRequest has a unique constraint on (email_request_id, request_index)."""
    table = QuoteRequest.__table__
    unique_constraints = [
        c for c in table.constraints
        if hasattr(c, "columns") and len(c.columns) == 2
        and "email_request_id" in {col.name for col in c.columns}
        and "request_index" in {col.name for col in c.columns}
    ]
    assert len(unique_constraints) == 1
    assert unique_constraints[0].name == "uq_quote_requests_email_request_id_request_index"
