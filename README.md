# MJO Connector for Odoo (Odoo Apps)

`mjo_connector/` is a small Odoo module for the Odoo Apps store. It does two things:

1. Adds the group **MJO read access**: read-only rights on the models MJO's Odoo connector reads
   (`account.move`, `account.move.line`, `account.account`, `res.partner`, `product.*`, `stock.location`, `stock.move`, `stock.quant`).
2. Adds an **MJO** menu for administrators (`/mjo/connect`): a page with one button, **Connect now**.
   Pressing it (`POST /mjo/connect/go`) creates the user `mjo-connector` («MJO Connector», member of «MJO read access» only,
   no password), generates an API key for it (scope `rpc`, no expiry; earlier «MJO» keys of that user are removed) and
   posts `{api_url, database_name, username, password}` to `https://app.mjo.marketing/products/sources/odoo/handoff`
   from the Odoo server. MJO answers with a sealed ticket (30 minutes) and the browser is sent to
   `…/products/sources?odoo_ticket=…`, where the signed-in store owner presses «اربط أودو الحين».
   * If Odoo cannot reach MJO, or Odoo's address is not https, the page shows the key once with a link to MJO's form.
   * `/mjo/connect/manual` is the old behaviour: MJO's form with the address and database name filled in, nothing secret.
   * Opening `/mjo/connect` creates nothing; only the POST does. Non-administrators get 404 on all three routes.
   * `ir.config_parameter` `mjo_connector.base_url` overrides MJO's address (testing only).

The only outside call is that one POST, made when an administrator presses the button.

## Tested (2026-11-21, Odoo Community 17.0, 19.0 and 20.0, PostgreSQL 16)
On each version, over real HTTP against a running server:
* The module installs / upgrades with no error.
* Opening the page creates no user. The button creates one user; a second press keeps one user, gives a new key and the
  old key stops working.
* The key signs in over the external API as the connector user: read works on `account.move`, `product.template`,
  `res.partner`, `stock.quant`; create, write and delete on `res.partner` are refused. The user cannot sign in with a password.
* MJO's own Odoo connector passes `test_connection` with that key.
* With MJO unreachable the key page is shown; `/mjo/connect/manual` redirects with `api_url` and `database_name`.
* The handoff target in these runs was a local stand-in for MJO; MJO's side (seal, sign-in on the way, claim, expiry) is
  covered by `tests/test_store_sync.py::test_179_odoo_one_click_handoff`.
Not tested: the whole chain against a public https Odoo and production MJO, Odoo 18, Odoo Enterprise (seat counting,
Odoo.sh outbound rules), a database with real invoices, multi-company rules.

## Differences between versions
* **17.0 and 19.0:** the same files; only `version` in `__manifest__.py` changes (`17.0.1.1.0`, `19.0.1.1.0`).
* **20.0:** Odoo 20 replaced `ir.model.access` with `ir.access`. Use `v20/ir.access.csv` as `security/ir.access.csv`,
  remove `security/ir.model.access.csv`, and list `security/ir.access.csv` in the manifest's `data`. Version `20.0.1.1.0`.
* The controller reads `web.base.url` with `get_param` (17, 19) or `get_str` (20); `_generate` takes an expiry from 18 on;
  Odoo 20 checks the key's scope exactly, so the key is made with scope `rpc` on every version.

## Repository
https://github.com/marwanzamkh/mjo-odoo — branches `17.0`, `19.0`, `20.0`, one folder `mjo_connector` at the root.

## Publishing on apps.odoo.com
* Odoo Apps reads a Git repository with one branch per Odoo version (`17.0`, `18.0`), the module folder at the root.
* Set `version` in `__manifest__.py` per branch: `17.0.1.0.0`, `18.0.1.0.0`.
* Register the repository at https://apps.odoo.com/apps/upload (the vendor account's owner does this).
* Free module (no `price`), licence LGPL-3.
