import inspect
import logging
from urllib.parse import urlencode

import requests
from markupsafe import Markup, escape

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

MJO = "https://app.mjo.marketing"
LOGIN = "mjo-connector"
KEY_NAME = "MJO"
SCOPE = "rpc"          # Odoo 20 checks the scope exactly; 17–19 accept a key scoped to "rpc" for XML-RPC/JSON-RPC as well

PAGE = Markup("""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>MJO</title>
<style>body{font-family:Tahoma,Arial,sans-serif;background:#F5F7F8;color:#0B1626;margin:0;padding:32px 16px}
.c{max-width:560px;margin:0 auto;background:#fff;border:1px solid #E3E8EC;border-radius:18px;padding:24px}
h1{font-size:22px;margin:0 0 12px}p{line-height:1.8;margin:0 0 12px}.en{direction:ltr;text-align:left;color:#4A5568;font-size:14px}
button,.b{display:inline-block;background:#00C9B7;color:#06231F;font-weight:bold;border:0;border-radius:999px;padding:12px 26px;font-size:16px;cursor:pointer;text-decoration:none}
a.l{color:#4A5568;font-size:14px}code{display:block;direction:ltr;text-align:left;background:#0B1626;color:#E6FAF8;border-radius:10px;padding:12px;word-break:break-all;margin:0 0 12px}
</style></head><body><div class="c">%s</div></body></html>""")


class MjoConnect(http.Controller):
    # ------------------------------------------------------------------ helpers
    def _admin_only(self):
        if not request.env.user.has_group("base.group_system"):
            raise request.not_found()

    def _param(self, key, default=""):
        params = request.env["ir.config_parameter"].sudo()
        read = getattr(params, "get_param", None) or getattr(params, "get_str", None)    # Odoo 20 renamed it
        return (read(key) if read else "") or default

    def _base(self):
        return self._param("web.base.url") or request.httprequest.url_root.rstrip("/")

    def _mjo(self):
        return self._param("mjo_connector.base_url", MJO).rstrip("/")

    def _manual_url(self, login=None):
        q = {"api_url": self._base(), "database_name": request.env.cr.dbname}
        if login:
            q["username"] = login
        return f"{self._mjo()}/products/sources?{urlencode(q)}#odoo"

    def _connector_user(self):
        """The one user MJO signs in with: internal, in «MJO read access» only, no password (it cannot sign in to Odoo's
        screens; the API key is its only way in). Made once and reused."""
        Users = request.env["res.users"].sudo().with_context(no_reset_password=True, active_test=False)
        group = request.env.ref("mjo_connector.group_mjo_read").sudo()
        gf = "group_ids" if "group_ids" in Users._fields else "groups_id"                # renamed in Odoo 19
        user = Users.search([("login", "=", LOGIN)], limit=1)
        me = request.env.user
        if not user:
            user = Users.create({"name": "MJO Connector", "login": LOGIN, gf: [(6, 0, [group.id])],
                                 "company_id": me.company_id.id, "company_ids": [(6, 0, me.company_ids.ids)]})
        else:
            vals = {}
            if not user.active:
                vals["active"] = True
            if group not in user[gf]:
                vals[gf] = [(4, group.id)]
            if vals:
                user.write(vals)
        return user

    def _new_key(self, user):
        """A fresh API key for the connector user; its earlier «MJO» keys are removed so only one is ever valid."""
        Keys = request.env["res.users.apikeys"]
        Keys.sudo().search([("user_id", "=", user.id), ("name", "=", KEY_NAME)]).unlink()
        gen = Keys.with_user(user).sudo()._generate
        if "expiration_date" in inspect.signature(gen).parameters:                       # Odoo 18+: None = no expiry (sudo only)
            return gen(SCOPE, KEY_NAME, None)
        return gen(SCOPE, KEY_NAME)

    # ------------------------------------------------------------------ pages
    @http.route("/mjo/connect", type="http", auth="user", methods=["GET"])
    def connect(self, **kw):
        """Explain what the button does, then wait for the press: nothing is created by opening this page."""
        self._admin_only()
        body = Markup("""<h1>ربط أودو مع MJO</h1>
<p>بضغطة وحدة: ننشئ مستخدم باسم <b>MJO Connector</b> للقراءة فقط (فواتير، منتجات، عملاء، مخزون) ومفتاح API له، ونرسله لـ MJO مباشرة من خادم أودو. ما يقدر يضيف أو يعدّل أو يحذف شي، وما له كلمة مرور لشاشات أودو.</p>
<p>في Odoo Enterprise المستخدم الداخلي الجديد يُحسب ضمن عدد مستخدمي اشتراكك.</p>
<p class="en">One click: this creates a read-only user <b>MJO Connector</b> (invoices, products, customers, stock) with an API key and sends it to MJO straight from your Odoo server. It cannot create, change or delete anything and has no password for Odoo's screens. On Odoo Enterprise the new internal user counts towards your subscription's users.</p>
<form method="post" action="/mjo/connect/go"><input type="hidden" name="csrf_token" value="%s">
<p><button type="submit">اربط MJO الحين · Connect now</button></p></form>
<p><a class="l" href="/mjo/connect/manual">أفضّل أربط يدويًا بمستخدم ومفتاح من عندي · I prefer to connect manually</a></p>""") % request.csrf_token()
        return request.make_response(PAGE % body, headers=[("Content-Type", "text/html; charset=utf-8"), ("Cache-Control", "no-store")])

    @http.route("/mjo/connect/manual", type="http", auth="user", methods=["GET"])
    def manual(self, **kw):
        """MJO's form with this database's address and name filled in. Nothing secret travels."""
        self._admin_only()
        return request.redirect(self._manual_url(), local=False)

    @http.route("/mjo/connect/go", type="http", auth="user", methods=["POST"], csrf=True)
    def go(self, **kw):
        self._admin_only()
        user = self._connector_user()
        key = self._new_key(user)
        url = None
        try:
            r = requests.post(f"{self._mjo()}/products/sources/odoo/handoff", timeout=15, json={
                "api_url": self._base(), "database_name": request.env.cr.dbname, "username": user.login, "password": key})
            if r.status_code == 200:
                url = (r.json() or {}).get("url")
            else:
                _logger.warning("MJO handoff answered %s", r.status_code)
        except Exception:  # noqa: BLE001 — no outbound internet, DNS, TLS… the page below still lets the owner finish
            _logger.warning("MJO handoff could not be reached", exc_info=True)
        if url and url.startswith(self._mjo() + "/"):
            return request.redirect(url, local=False)
        body = Markup("""<h1>انسخ المفتاح وكمّل في MJO</h1>
<p>ما قدر خادم أودو يوصل لـ MJO مباشرة (أو رابط أودو مو https). المستخدم والمفتاح جاهزين: انسخ المفتاح، افتح MJO، والصقه في خانة «كلمة المرور أو مفتاح API». المفتاح يظهر هنا مرة وحدة فقط.</p>
<p class="en">Your Odoo server could not reach MJO directly (or Odoo's address is not https). The user and key are ready: copy the key, open MJO and paste it into «Password or API key». The key is shown here once only.</p>
<p class="en">User: <b>%s</b></p><code>%s</code>
<p><a class="b" href="%s" target="_blank" rel="noopener">افتح MJO · Open MJO</a></p>""") % (escape(user.login), escape(key), escape(self._manual_url(user.login)))
        return request.make_response(PAGE % body, headers=[("Content-Type", "text/html; charset=utf-8"), ("Cache-Control", "no-store")])
