"""ERP adapter package — Odoo XML-RPC integration."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from quote_agent.adapters.erp.models import OdooVersionInfo
from quote_agent.adapters.erp.protocol import ERPAdapter

if TYPE_CHECKING:
    from quote_agent.adapters.erp.odoo import OdooAdapter

__all__ = [
    "ERPAdapter",
    "OdooVersionInfo",
    "get_erp_adapter",
]


@lru_cache(maxsize=1)
def get_erp_adapter() -> OdooAdapter:
    """Create and return a cached ERP adapter singleton."""
    from quote_agent.adapters.erp.odoo import OdooAdapter
    from quote_agent.config import get_settings

    return OdooAdapter(get_settings().erp)
