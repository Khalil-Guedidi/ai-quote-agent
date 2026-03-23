"""ERP redirect endpoint — resolves Teams fragment-stripping issue.

Teams strips URL fragments (#...) from Action.OpenUrl links. This endpoint
provides a server-side path that redirects to Odoo's client-side route via
a small HTML page with JavaScript window.location (meta refresh drops fragments).
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from quote_agent.config import get_settings

router = APIRouter()

_REDIRECT_HTML = """\
<!DOCTYPE html>
<html><head><script>window.location.replace("{url}");</script></head>
<body>Redirection vers Odoo...</body></html>"""


@router.get("/erp/sale-order/{order_id}", response_class=HTMLResponse)
async def erp_sale_order_redirect(order_id: int) -> HTMLResponse:
    """Redirect to a specific sale order in Odoo."""
    erp_url = get_settings().erp.url
    target = f"{erp_url}/web#id={order_id}&model=sale.order&view_type=form"
    return HTMLResponse(_REDIRECT_HTML.format(url=target))


@router.get("/erp/sale-orders", response_class=HTMLResponse)
async def erp_sale_orders_redirect() -> HTMLResponse:
    """Redirect to the sale orders list in Odoo."""
    erp_url = get_settings().erp.url
    target = f"{erp_url}/web#action=315"
    return HTMLResponse(_REDIRECT_HTML.format(url=target))
