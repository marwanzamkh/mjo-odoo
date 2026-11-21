from urllib.parse import urlencode

from odoo import http
from odoo.http import request

MJO = "https://app.mjo.marketing/products/sources"


class MjoConnect(http.Controller):
    @http.route("/mjo/connect", type="http", auth="user")
    def connect(self, **kw):
        """Open MJO's «connect Odoo» form with this database's address and name already filled in.
        Nothing secret travels: no password, no key, no user name. The owner pastes the API key in MJO."""
        if not request.env.user.has_group("base.group_system"):
            return request.not_found()
        base = request.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
        q = urlencode({"api_url": base, "database_name": request.env.cr.dbname})
        return request.redirect(f"{MJO}?{q}#odoo", local=False)
