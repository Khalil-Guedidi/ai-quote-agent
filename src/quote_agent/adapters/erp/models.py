"""Typed DTOs for the ERP adapter layer."""

from __future__ import annotations

from pydantic import BaseModel


class OdooVersionInfo(BaseModel):
    """Version information returned by Odoo XML-RPC common.version()."""

    server_version: str
    protocol_version: int


# Future DTOs (Epic 3/4):
# - UniversalQuote: quote data transferable between ERP and agent
# - Product: product catalog entry from ERP
# - Client: customer/client record from ERP
